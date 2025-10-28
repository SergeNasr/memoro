#!/usr/bin/env python3
"""Rollback TSV import by deleting contacts by name."""

import asyncio
import csv
import sys
from pathlib import Path
from uuid import UUID

import asyncpg
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings

logger = structlog.get_logger(__name__)

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def parse_name(name: str) -> tuple[str, str]:
    """Parse full name into first and last name."""
    name = name.strip()
    parts = name.split(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


async def delete_contact_by_name(
    conn: asyncpg.Connection,
    user_id: UUID,
    first_name: str,
    last_name: str,
) -> bool:
    """
    Delete a contact by name.

    Returns True if deleted, False if not found.
    """
    # First find the contact
    query = """
        SELECT id FROM contact
        WHERE user_id = $1
          AND LOWER(first_name) = LOWER($2)
          AND LOWER(last_name) = LOWER($3)
        LIMIT 1
    """
    row = await conn.fetchrow(query, user_id, first_name, last_name)

    if not row:
        return False

    contact_id = row["id"]

    # Delete the contact (CASCADE will handle interactions and family_members)
    delete_query = """
        DELETE FROM contact
        WHERE id = $1 AND user_id = $2
        RETURNING id
    """
    result = await conn.fetchrow(delete_query, contact_id, user_id)

    return result is not None


async def rollback_import(
    tsv_path: Path,
    user_id: UUID = DEFAULT_USER_ID,
    preview: bool = True,
):
    """
    Rollback import by deleting all contacts from the TSV file.

    Args:
        tsv_path: Path to original TSV file
        user_id: User ID to delete contacts for
        preview: If True (default), only show what would be deleted
    """
    if not tsv_path.exists():
        logger.error("tsv_file_not_found", path=str(tsv_path))
        sys.exit(1)

    conn = await asyncpg.connect(settings.database_url)

    try:
        # Parse TSV to get all names (including related people)
        names_to_delete = set()

        with open(tsv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            for row in reader:
                name = row.get("Name", "").strip()
                if name:
                    names_to_delete.add(name)

                # Also get related person names
                relationship_field = row.get("Related to (person) / Relationship", "").strip()
                if relationship_field:
                    parts = relationship_field.split("/", 1)
                    if parts:
                        related_name = parts[0].strip()
                        if related_name:
                            names_to_delete.add(related_name)

        # Check which contacts exist
        existing_contacts = []
        for name in names_to_delete:
            first_name, last_name = parse_name(name)

            query = """
                SELECT id, first_name, last_name FROM contact
                WHERE user_id = $1
                  AND LOWER(first_name) = LOWER($2)
                  AND LOWER(last_name) = LOWER($3)
                LIMIT 1
            """
            row = await conn.fetchrow(query, user_id, first_name, last_name)

            if row:
                existing_contacts.append(
                    {
                        "id": row["id"],
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "full_name": f"{row['first_name']} {row['last_name']}".strip(),
                    }
                )

        # Print summary
        print("\n" + "=" * 80)
        if preview:
            print("PREVIEW MODE - No deletions will be made")
        else:
            print("EXECUTE MODE - Deleting contacts from database")
        print("=" * 80 + "\n")

        if existing_contacts:
            print(f"🗑️  CONTACTS TO DELETE ({len(existing_contacts)}):\n")
            for contact in existing_contacts:
                print(f"  • {contact['full_name']}")
            print()
        else:
            print("✓ No contacts found to delete\n")

        print("=" * 80)
        print(f"Total contacts to delete: {len(existing_contacts)}")
        print("=" * 80)

        if preview:
            print("\n💡 Run with --execute to actually delete these contacts")
            print("⚠️  WARNING: This will also delete all interactions and family relationships!")
        else:
            # Actually delete
            print("\n⏳ Deleting contacts...")
            deleted_count = 0

            async with conn.transaction():
                for contact in existing_contacts:
                    try:
                        success = await delete_contact_by_name(
                            conn,
                            user_id,
                            contact["first_name"],
                            contact["last_name"],
                        )
                        if success:
                            deleted_count += 1
                            logger.info("contact_deleted", name=contact["full_name"])
                    except Exception as e:
                        logger.error("failed_to_delete", name=contact["full_name"], error=str(e))

            print("\n✓ Rollback completed!")
            print(f"  Deleted: {deleted_count} contacts")

    finally:
        await conn.close()


async def main():
    """Main entry point for the rollback script."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/rollback_import.py [--execute] <path_to_tsv>")
        print("\nBy default, runs in preview mode (no deletions)")
        print("\nOptions:")
        print("  --execute    Actually delete the contacts (DESTRUCTIVE!)")
        sys.exit(1)

    execute_mode = "--execute" in sys.argv
    tsv_path_arg = sys.argv[-1]
    tsv_path = Path(tsv_path_arg)

    mode_str = "EXECUTE" if execute_mode else "PREVIEW"
    print(f"[{mode_str}] Rolling back import from: {tsv_path}")

    if execute_mode:
        print("⚠️  This will DELETE contacts and all associated data!")
        print("⚠️  Press Ctrl-C within 3 seconds to cancel...")
        await asyncio.sleep(3)

    try:
        await rollback_import(tsv_path, preview=not execute_mode)
    except Exception as e:
        logger.error("rollback_failed", error=str(e))
        print(f"\n✗ Rollback failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
