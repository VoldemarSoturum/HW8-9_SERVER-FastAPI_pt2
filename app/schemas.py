from __future__ import annotations

from datetime import datetime
from decimal import Decimal  # Исправил ошибку с прошлой лабораторной
from typing import Optional, Literal  # ПО ЗАДАНИЮ. Дополнил импорты

from pydantic import BaseModel, ConfigDict, Field

# ====================ДОБАВЛЯЕМ СХЕМЫ ПОЛЬЗОВАТЕЛЕЙ И ЛОГИН==================

# -------------------- AUTH --------------------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------------------- USER --------------------

# ВАЖНО:
# - root существует (bootstrap через env), и в ответах API должен отображаться как "root"
# - создавать root через API всё равно запрещаем в main.py
UserGroup = Literal["user", "admin", "root"]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)
    group: UserGroup = "user"   # неавторизованный может создавать только user (проверим в роуте)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    password: Optional[str] = Field(default=None, min_length=4, max_length=128)
    group: Optional[UserGroup] = None  # менять группу может только admin/root (проверим в роуте)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    group: UserGroup
    created_at: datetime


# -------------------- ADVERTISEMENT --------------------
class AdvertisementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    price: Decimal = Field(gt=0)  # Тут Decimal, так что всё ок)
    author: str = Field(min_length=1, max_length=120)


class AdvertisementUpdate(BaseModel):
    # PATCH — все поля опциональны
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)
    price: Optional[Decimal] = Field(default=None, gt=0) # Тут Decimal, так что всё ок)
    author: Optional[str] = Field(default=None, min_length=1, max_length=120)


class AdvertisementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    price: Decimal # Тут Decimal, так что всё ок)
    author: str
    created_at: datetime
