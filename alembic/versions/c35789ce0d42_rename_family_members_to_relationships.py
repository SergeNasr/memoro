"""rename_family_members_to_relationships

Revision ID: c35789ce0d42
Revises: 5899cb3bf7f7
Create Date: 2025-10-28 21:48:31.805384

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c35789ce0d42"
down_revision: str | Sequence[str] | None = "5899cb3bf7f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("family_member", "relationship")
    op.execute(
        "ALTER TABLE relationship RENAME CONSTRAINT uq_family_member_relationship TO uq_relationship_relationship"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE relationship RENAME CONSTRAINT uq_relationship_relationship TO uq_family_member_relationship"
    )
    op.rename_table("relationship", "family_member")
