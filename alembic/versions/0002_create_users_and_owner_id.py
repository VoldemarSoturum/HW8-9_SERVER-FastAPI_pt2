# ДОПОЛНИТЕЛЬНО ПО ЗАДАНИЮ. НОВАЯ МИГРАЦИЯ С СОЗДАНИЕМ ПОЛЬЗОВАТЕЛЕЙ
# И ИД-ВЛАДЕЛЬЦА.

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("group", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.add_column("advertisements", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_advertisements_owner_id_users",
        "advertisements",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_advertisements_owner_id_users", "advertisements", type_="foreignkey")
    op.drop_column("advertisements", "owner_id")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
