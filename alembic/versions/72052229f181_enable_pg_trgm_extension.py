"""enable_pg_trgm_extension

Revision ID: 72052229f181
Revises: d892e083fe19
Create Date: 2025-10-05 21:44:29.582995

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72052229f181"
down_revision: str | Sequence[str] | None = "d892e083fe19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pg_trgm extension for fuzzy text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    """Downgrade schema."""
    # Disable pg_trgm extension
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
