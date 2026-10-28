"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("client", "master", "admin", name="user_role")
booking_status = postgresql.ENUM(
    "confirmed", "cancelled", "completed", "no_show", name="booking_status"
)


def upgrade() -> None:
    # btree_gist нужен, чтобы в одном GiST-индексе сравнивать и master_id (=),
    # и временные интервалы (&&) для ограничения no_overlapping_bookings
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "masters",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("bio", sa.Text),
        sa.Column("timezone", sa.String(50), nullable=False),
    )

    op.create_table(
        "services",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "master_id",
            sa.Integer,
            sa.ForeignKey("masters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("price", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.CheckConstraint("duration_minutes > 0", name="duration_positive"),
        sa.CheckConstraint("price >= 0", name="price_non_negative"),
    )

    op.create_table(
        "working_hours",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "master_id",
            sa.Integer,
            sa.ForeignKey("masters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        sa.CheckConstraint("start_time < end_time", name="start_before_end"),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "master_id",
            sa.Integer,
            sa.ForeignKey("masters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("service_id", sa.Integer, sa.ForeignKey("services.id"), nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("starts_at < ends_at", name="starts_before_ends"),
        postgresql.ExcludeConstraint(
            ("master_id", "="),
            (sa.func.tstzrange(sa.text("starts_at"), sa.text("ends_at")), "&&"),
            name="no_overlapping_bookings",
            using="gist",
            where=sa.text("status = 'confirmed'"),
        ),
    )

    # Индексы под частые запросы: «мои записи» клиента и расписание мастера
    op.create_index("ix_bookings_client_id", "bookings", ["client_id"])
    op.create_index("ix_bookings_master_starts", "bookings", ["master_id", "starts_at"])
    op.create_index("ix_services_master_id", "services", ["master_id"])
    op.create_index("ix_working_hours_master_id", "working_hours", ["master_id"])


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("working_hours")
    op.drop_table("services")
    op.drop_table("masters")
    op.drop_table("users")
    booking_status.drop(op.get_bind())
    user_role.drop(op.get_bind())
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
