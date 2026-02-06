from __future__ import annotations

from datetime import datetime
from decimal import Decimal  # Исправил ошибку с прошлой лабораторной

from sqlalchemy import DateTime, Numeric, String, Text, func, ForeignKey, Integer  # ПО ЗАДАНИЮ. Дополнил импорты
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship  # ПО ЗАДАНИЮ. Дополнил импорты


class Base(DeclarativeBase):
    pass


# ПО ЗАДАНИЮ. Модель пользователей и групп для управления правами и разграничениями.
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ПО ЗАДАНИЮ. Группа пользователя:
    # - user: обычный пользователь
    # - admin: администратор (расширенные права)
    # - root: "первый админ" (bootstrap через env), имеет максимальные права
    group: Mapped[str] = mapped_column(String(16), nullable=False, default="user")  # user|admin|root

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    advertisements: Mapped[list["Advertisement"]] = relationship(back_populates="owner")


class Advertisement(Base):
    __tablename__ = "advertisements"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Исправил ошибку с прошлой лабораторной — Decimal вместо float
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    author: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # По заданию. Теперь владелец объявления тот, кто создал его.
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    owner: Mapped[User | None] = relationship(back_populates="advertisements")
