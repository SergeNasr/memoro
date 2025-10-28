#!/usr/bin/env python3
"""Import contacts and interactions from TSV file into Memoro database."""

import asyncio
import csv
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

import asyncpg
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings
from backend.app.db import load_sql

logger = structlog.get_logger(__name__)

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

# SQL queries
SQL_FIND_OR_CREATE_CONTACT = load_sql("contacts/find_or_create.sql")
SQL_CREATE_INTERACTION = load_sql("interactions/create.sql")
SQL_UPDATE_LATEST_NEWS = load_sql("contacts/update_latest_news.sql")
SQL_CREATE_FAMILY_MEMBER = load_sql("family_members/create.sql")


def parse_name(name: str) -> tuple[str, str]:
    """Parse full name into first and last name."""
    name = name.strip()
    parts = name.split(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


def parse_relationship(relationship_field: str) -> tuple[str | None, str | None]:
    """
    Parse relationship field into related person name and relationship type.

    Format: "Person Name / Relationship"
    Examples:
        "Drew / Girlfriend" -> ("Drew", "girlfriend")
        "Kimia Hamidi / Son" -> ("Kimia Hamidi", "son")
    """
    if not relationship_field or not relationship_field.strip():
        return None, None

    parts = relationship_field.split("/", 1)
    if len(parts) == 2:
        related_name = parts[0].strip()
        relationship = parts[1].strip().lower()
        return related_name, relationship

    return parts[0].strip(), None


def parse_row_data(row: dict) -> dict | None:
    """
    Parse and extract data from a TSV row.

    Returns: dict with parsed data or None if row should be skipped
    """
    name = row.get("Name", "").strip()
    relationship_field = row.get("Related to (person) / Relationship", "").strip()
    place = row.get("Place", "").strip()
    description = row.get("Description", "").strip()

    if not name:
        return None

    first_name, last_name = parse_name(name)
    related_name, relationship = parse_relationship(relationship_field)

    # Parse related person if exists
    # Note: relationship field means "Related Person is my X"
    # e.g., "Kimia Hamidi / Son" means "Kimia Hamidi is my son"
    # So we need to store the INVERSE for the main person
    related_data = None
    if related_name and relationship:
        related_first, related_last = parse_name(related_name)
        # Store the inverse relationship for the main person
        # e.g., if "Kimia is my son", then I am Kimia's parent
        inverse_rel = get_inverse_relationship(relationship)
        related_data = {
            "first_name": related_first,
            "last_name": related_last,
            "full_name": f"{related_first} {related_last}".strip(),
            "relationship": inverse_rel,  # Store inverse for main person
            "original_relationship": relationship,  # Keep original for related person
        }

    # Build interaction notes (only use description if present)
    notes = description.strip() if description else ""

    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}".strip(),
        "place": place or None,
        "notes": notes,
        "has_description": bool(notes),
        "related_data": related_data,
        "from_csv": True,  # Mark as original CSV entry
    }


async def check_contact_exists(
    conn: asyncpg.Connection,
    user_id: UUID,
    first_name: str,
    last_name: str,
) -> bool:
    """Check if contact already exists."""
    query = """
        SELECT EXISTS(
            SELECT 1 FROM contact
            WHERE user_id = $1
              AND LOWER(first_name) = LOWER($2)
              AND LOWER(last_name) = LOWER($3)
        )
    """
    row = await conn.fetchrow(query, user_id, first_name, last_name)
    return row["exists"]


def get_inverse_relationship(relationship: str) -> str:
    """Get the inverse relationship for bidirectional family links."""
    inverses = {
        "parent": "child",
        "child": "parent",
        "spouse": "spouse",
        "sibling": "sibling",
        "wife": "husband",
        "husband": "wife",
        "girlfriend": "boyfriend",
        "boyfriend": "girlfriend",
        "son": "parent",
        "daughter": "parent",
    }
    return inverses.get(relationship.lower(), "related_to")


async def create_contact_with_interaction(
    conn: asyncpg.Connection,
    user_id: UUID,
    first_name: str,
    last_name: str,
    notes: str,
    location: str | None,
    interaction_date: date,
    preview: bool = False,
) -> UUID | None:
    """
    Create or find contact and add interaction (without embedding in preview mode).

    Returns contact_id or None if preview mode.
    """
    if preview:
        return None

    # Import here to avoid import in preview mode
    from backend.app.services.llm import generate_embedding

    # Find or create contact
    contact_row = await conn.fetchrow(
        SQL_FIND_OR_CREATE_CONTACT,
        user_id,
        first_name,
        last_name,
        None,  # birthday
        notes,  # Use interaction notes as initial latest_news
    )
    contact_id = contact_row["id"]

    # Generate embedding
    embedding = await generate_embedding(notes)
    embedding_str = f"[{','.join(map(str, embedding))}]"

    # Create interaction
    await conn.fetchrow(
        SQL_CREATE_INTERACTION,
        user_id,
        contact_id,
        interaction_date,
        notes,
        location,
        embedding_str,
    )

    # Update latest news
    await conn.execute(SQL_UPDATE_LATEST_NEWS, contact_id, notes)

    return contact_id


async def link_family_members(
    conn: asyncpg.Connection,
    contact_id: UUID,
    family_contact_id: UUID,
    relationship: str,
    preview: bool = False,
) -> None:
    """Link two contacts as family members bidirectionally."""
    if preview:
        return

    inverse_relationship = get_inverse_relationship(relationship)

    # Create forward relationship
    await conn.fetchrow(
        SQL_CREATE_FAMILY_MEMBER,
        contact_id,
        family_contact_id,
        relationship,
    )

    # Create reverse relationship
    await conn.fetchrow(
        SQL_CREATE_FAMILY_MEMBER,
        family_contact_id,
        contact_id,
        inverse_relationship,
    )


async def get_or_fetch_contact_id(
    conn: asyncpg.Connection,
    user_id: UUID,
    first_name: str,
    last_name: str,
    contact_cache: dict[str, UUID | None],
) -> UUID | None:
    """
    Get contact ID from cache or fetch from database.
    Cache stores: full_name -> contact_id (or None if doesn't exist)
    """
    full_name = f"{first_name} {last_name}".strip()

    if full_name in contact_cache:
        return contact_cache[full_name]

    # Check if exists in DB
    query = """SELECT id FROM contact
               WHERE user_id = $1
               AND LOWER(first_name) = LOWER($2)
               AND LOWER(last_name) = LOWER($3)
               LIMIT 1"""
    row = await conn.fetchrow(query, user_id, first_name, last_name)

    contact_id = row["id"] if row else None
    contact_cache[full_name] = contact_id
    return contact_id


def _print_person_details(person: dict, contact_cache: dict[str, UUID | None]) -> None:
    """Print details for a single person."""
    print(f"  • {person['full_name']}")
    if person["place"]:
        print(f"    Location: {person['place']}")
    if person["has_description"]:
        print(f"    Notes: {person['notes']}")
    if person.get("related_data"):
        rel = person["related_data"]
        rel_exists = contact_cache.get(rel["full_name"]) is not None
        status = "[already exists]" if rel_exists else "[will be created]"
        print(f"    Family: {rel['full_name']} ({rel['relationship']}) {status}")
    print()


def _print_import_summary(
    preview: bool,
    new_contacts: list[dict],
    existing_contacts: list[dict],
    contact_cache: dict[str, UUID | None],
) -> None:
    """Print summary of what will be imported."""
    print("\n" + "=" * 80)
    if preview:
        print("PREVIEW MODE - No changes will be made")
    else:
        print("EXECUTE MODE - Making changes to database")
    print("=" * 80 + "\n")

    if new_contacts:
        print(f"📝 NEW CONTACTS ({len(new_contacts)}):\n")
        for person in new_contacts:
            _print_person_details(person, contact_cache)

    if existing_contacts:
        print(f"♻️  EXISTING CONTACTS ({len(existing_contacts)}):")
        print("   (Already exist, will be used for family relationships only)\n")
        for person in existing_contacts:
            _print_person_details(person, contact_cache)

    print("=" * 80)
    print(f"Summary: {len(new_contacts)} new, {len(existing_contacts)} existing")
    print("=" * 80)


def _parse_tsv_file(tsv_path: Path) -> list[dict]:
    """
    Parse TSV file and build list of people to import.
    Automatically includes related people.
    """
    people_to_import = []

    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            parsed = parse_row_data(row)
            if parsed:
                people_to_import.append(parsed)
                # If they have a related person, add that person to the list too
                # with the REVERSE relationship back to the main person
                if parsed["related_data"]:
                    rel = parsed["related_data"]
                    # Create entry for related person WITHOUT relationship data
                    # (relationships will only be created from original CSV entries)
                    related_parsed = {
                        "first_name": rel["first_name"],
                        "last_name": rel["last_name"],
                        "full_name": rel["full_name"],
                        "notes": "",
                        "place": parsed["place"],
                        "has_description": False,
                        "related_data": None,  # Don't create reverse relationship
                        "from_csv": False,  # Mark as auto-added
                    }
                    people_to_import.append(related_parsed)

    return people_to_import


async def _build_contact_cache(
    conn: asyncpg.Connection,
    user_id: UUID,
    people_to_import: list[dict],
    contact_cache: dict[str, UUID | None],
) -> list[dict]:
    """
    Build contact cache and return deduplicated list of unique people.
    Cache stores: full_name -> contact_id (or None if doesn't exist)
    """
    # Populate cache for all people
    for person in people_to_import:
        await get_or_fetch_contact_id(
            conn,
            user_id,
            person["first_name"],
            person["last_name"],
            contact_cache,
        )

    # Deduplicate by full_name (keep first occurrence)
    seen_names = set()
    unique_people = []
    for person in people_to_import:
        if person["full_name"] not in seen_names:
            seen_names.add(person["full_name"])
            unique_people.append(person)

    return unique_people


async def _execute_import(
    conn: asyncpg.Connection,
    user_id: UUID,
    unique_people: list[dict],
    contact_cache: dict[str, UUID | None],
    today: date,
) -> tuple[int, int]:
    """
    Execute the actual import with database changes.

    Returns: (imported_count, skipped_count)
    """
    imported_count = 0
    skipped_count = 0

    async with conn.transaction():
        # Phase 1: Create all contacts
        for person in unique_people:
            try:
                contact_id = contact_cache.get(person["full_name"])

                # Only create contact with interaction if it doesn't exist
                if not contact_id:
                    new_contact_id = await create_contact_with_interaction(
                        conn=conn,
                        user_id=user_id,
                        first_name=person["first_name"],
                        last_name=person["last_name"],
                        notes=person["notes"],
                        location=person["place"],
                        interaction_date=today,
                        preview=False,
                    )
                    contact_cache[person["full_name"]] = new_contact_id
                    logger.info("contact_created", name=person["full_name"])
                    imported_count += 1

            except Exception as e:
                logger.error("failed_to_import_person", person=person["full_name"], error=str(e))
                skipped_count += 1

        # Phase 2: Link all family relationships (after all contacts are created)
        for person in unique_people:
            try:
                # Only process relationships from original CSV entries to avoid duplicates
                if person.get("related_data") and person.get("from_csv"):
                    rel = person["related_data"]
                    main_id = contact_cache.get(person["full_name"])
                    rel_id = contact_cache.get(rel["full_name"])

                    if main_id and rel_id:
                        await link_family_members(
                            conn,
                            main_id,
                            rel_id,
                            rel["relationship"],
                            preview=False,
                        )
                        logger.info(
                            "family_linked",
                            person=person["full_name"],
                            related=rel["full_name"],
                            relationship=rel["relationship"],
                        )

            except Exception as e:
                logger.error(
                    "failed_to_link_relationship", person=person["full_name"], error=str(e)
                )

    return imported_count, skipped_count


async def import_tsv(
    tsv_path: Path,
    user_id: UUID = DEFAULT_USER_ID,
    preview: bool = True,
):
    """
    Import contacts from TSV file.

    Args:
        tsv_path: Path to TSV file
        user_id: User ID to import contacts for
        preview: If True (default), only print what would be imported (no DB changes, no API calls)
    """
    if not tsv_path.exists():
        logger.error("tsv_file_not_found", path=str(tsv_path))
        sys.exit(1)

    conn = await asyncpg.connect(settings.database_url)
    today = date.today()

    try:
        # Parse TSV and build list of people (including related people)
        people_to_import = _parse_tsv_file(tsv_path)

        # Build contact cache and get unique people
        contact_cache: dict[str, UUID | None] = {}
        unique_people = await _build_contact_cache(conn, user_id, people_to_import, contact_cache)

        # Categorize into new vs existing
        new_contacts = [p for p in unique_people if not contact_cache.get(p["full_name"])]
        existing_contacts = [p for p in unique_people if contact_cache.get(p["full_name"])]

        # Print summary
        _print_import_summary(preview, new_contacts, existing_contacts, contact_cache)

        if preview:
            print("\n💡 Run with --execute to actually import these contacts")
        else:
            # Execute the import
            print("\n⏳ Importing...")
            imported_count, skipped_count = await _execute_import(
                conn, user_id, unique_people, contact_cache, today
            )
            print("\n✓ Import completed successfully!")
            print(f"  Imported: {imported_count} contacts")
            print(f"  Skipped: {skipped_count} rows")

    finally:
        await conn.close()


async def main():
    """Main entry point for the import script."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_tsv.py [--execute] <path_to_tsv>")
        print("\nBy default, runs in preview mode (no changes)")
        print("\nOptions:")
        print("  --execute    Actually import the contacts (makes DB changes, calls OpenAI)")
        sys.exit(1)

    execute_mode = "--execute" in sys.argv
    tsv_path_arg = sys.argv[-1]
    tsv_path = Path(tsv_path_arg)

    mode_str = "EXECUTE" if execute_mode else "PREVIEW"
    print(f"[{mode_str}] Importing contacts from: {tsv_path}")

    if execute_mode:
        print("⚠️  This will create contacts and generate embeddings using OpenAI API")

    try:
        await import_tsv(tsv_path, preview=not execute_mode)
    except Exception as e:
        logger.error("import_failed", error=str(e))
        print(f"\n✗ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
