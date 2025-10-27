"""convert_embedding_to_vector_type

Revision ID: 399cbbf99688
Revises: 72052229f181
Create Date: 2025-10-24 13:58:57.096791

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "399cbbf99688"
down_revision: str | Sequence[str] | None = "72052229f181"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Convert embedding column from TEXT to vector(1536)
    # text-embedding-3-small produces 1536-dimensional vectors
    op.execute(
        "ALTER TABLE interaction ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Convert back to TEXT
    op.execute("ALTER TABLE interaction ALTER COLUMN embedding TYPE TEXT")
