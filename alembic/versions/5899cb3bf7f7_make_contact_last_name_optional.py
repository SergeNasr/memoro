"""make_contact_last_name_optional

Revision ID: 5899cb3bf7f7
Revises: 399cbbf99688
Create Date: 2025-10-28 21:25:01.964439

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5899cb3bf7f7"
down_revision: str | Sequence[str] | None = "399cbbf99688"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("contact", "last_name", nullable=True, existing_type=sa.Text())


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("contact", "last_name", nullable=False, existing_type=sa.Text())
