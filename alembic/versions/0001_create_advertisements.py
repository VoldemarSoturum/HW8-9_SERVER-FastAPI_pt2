"""create advertisements table

Revision ID: 0001
Revises:
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advertisements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_advertisements_title", "advertisements", ["title"])
    op.create_index("ix_advertisements_author", "advertisements", ["author"])
    op.create_index("ix_advertisements_price", "advertisements", ["price"])
    op.create_index("ix_advertisements_created_at", "advertisements", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_advertisements_created_at", table_name="advertisements")
    op.drop_index("ix_advertisements_price", table_name="advertisements")
    op.drop_index("ix_advertisements_author", table_name="advertisements")
    op.drop_index("ix_advertisements_title", table_name="advertisements")
    op.drop_table("advertisements")
