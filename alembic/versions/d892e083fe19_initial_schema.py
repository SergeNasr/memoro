"""initial_schema

Revision ID: d892e083fe19
Revises:
Create Date: 2025-10-01 22:15:25.257855

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d892e083fe19"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create user table
    op.create_table(
        "user",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_user_email", "user", ["email"])

    # Create contact table
    op.create_table(
        "contact",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("birthday", sa.Date(), nullable=True),
        sa.Column("latest_news", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_contact_user_id", "contact", ["user_id"])
    op.create_index("ix_contact_name", "contact", ["first_name", "last_name"])

    # Create interaction table
    op.create_table(
        "interaction",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "contact_id", sa.UUID(), sa.ForeignKey("contact.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", sa.UUID(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("interaction_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column(
            "embedding", sa.Text(), nullable=True
        ),  # Will be vector type, stored as text for now
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_interaction_contact_id", "interaction", ["contact_id"])
    op.create_index("ix_interaction_user_id", "interaction", ["user_id"])
    op.create_index("ix_interaction_date", "interaction", ["interaction_date"])

    # Create family_member table
    op.create_table(
        "family_member",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "contact_id", sa.UUID(), sa.ForeignKey("contact.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "family_contact_id",
            sa.UUID(),
            sa.ForeignKey("contact.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_family_member_contact_id", "family_member", ["contact_id"])
    op.create_unique_constraint(
        "uq_family_member_relationship", "family_member", ["contact_id", "family_contact_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("family_member")
    op.drop_table("interaction")
    op.drop_table("contact")
    op.drop_table("user")
    op.execute("DROP EXTENSION IF EXISTS vector")
