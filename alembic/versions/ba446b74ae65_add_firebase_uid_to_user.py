"""add_firebase_uid_to_user

Revision ID: ba446b74ae65
Revises: c35789ce0d42
Create Date: 2026-01-11 11:05:42.489516

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ba446b74ae65"
down_revision: str | Sequence[str] | None = "c35789ce0d42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("user", sa.Column("firebase_uid", sa.Text(), nullable=True))
    op.create_index("ix_user_firebase_uid", "user", ["firebase_uid"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_user_firebase_uid", table_name="user")
    op.drop_column("user", "firebase_uid")
