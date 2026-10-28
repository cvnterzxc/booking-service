import enum
from datetime import datetime, time

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    client = "client"
    master = "master"
    admin = "admin"


class BookingStatus(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.client
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    master_profile: Mapped["Master | None"] = relationship(back_populates="user")


class Master(Base):
    """Профиль мастера. Отделён от User: клиент может позже стать мастером."""

    __tablename__ = "masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    # Публичный адрес страницы мастера: /m/{slug}
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Almaty")

    user: Mapped[User] = relationship(back_populates="master_profile")
    services: Mapped[list["Service"]] = relationship(back_populates="master")
    working_hours: Mapped[list["WorkingHours"]] = relationship(back_populates="master")


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="duration_positive"),
        CheckConstraint("price >= 0", name="price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    master_id: Mapped[int] = mapped_column(
        ForeignKey("masters.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    duration_minutes: Mapped[int]
    # Цена в тенге целым числом: float для денег не используют
    price: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    master: Mapped[Master] = relationship(back_populates="services")


class WorkingHours(Base):
    """Рабочий интервал в день недели. Перерыв задаётся двумя интервалами: 10-14 и 15-19."""

    __tablename__ = "working_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("start_time < end_time", name="start_before_end"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    master_id: Mapped[int] = mapped_column(
        ForeignKey("masters.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger)  # 0 = понедельник
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    master: Mapped[Master] = relationship(back_populates="working_hours")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="starts_before_ends"),
        # Защита от двойного бронирования на уровне БД: у одного мастера
        # не может быть двух активных записей с пересекающимся временем.
        # Даже если два запроса придут одновременно, второй получит ошибку.
        ExcludeConstraint(
            ("master_id", "="),
            (func.tstzrange(text("starts_at"), text("ends_at")), "&&"),
            name="no_overlapping_bookings",
            using="gist",
            where=text("status = 'confirmed'"),
        ),
        Index("ix_bookings_master_starts", "master_id", "starts_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id", ondelete="CASCADE"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Храним конец явно: если мастер потом изменит длительность услуги,
    # старые записи не должны «поехать».
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), default=BookingStatus.confirmed
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    master: Mapped[Master] = relationship()
    service: Mapped[Service] = relationship()
    client: Mapped[User] = relationship()
