from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Advertisement, User  # ПО ЗАДАНИЮ. Дополнил импорты
from app.security import hash_password, verify_password  # ПО ЗАДАНИЮ. Дополнил импорты

# ПО ЗАДАНИЮ. Добавляем UserCRUD + права на объявления


class UserCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, username: str, password: str, group: str = "user") -> User:
        user = User(username=username, password_hash=hash_password(password), group=group)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get(self, user_id: int) -> Optional[User]:
        res = await self.db.execute(select(User).where(User.id == user_id))
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        res = await self.db.execute(select(User).where(User.username == username))
        return res.scalar_one_or_none()

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        stmt = select(User).order_by(User.id.asc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def patch(
        self,
        user_id: int,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        group: Optional[str] = None,
    ) -> Optional[User]:
        values: dict = {}
        if username is not None:
            values["username"] = username
        if password is not None:
            values["password_hash"] = hash_password(password)
        if group is not None:
            values["group"] = group

        if not values:
            return await self.get(user_id)

        stmt = update(User).where(User.id == user_id).values(**values).returning(User)
        res = await self.db.execute(stmt)
        updated = res.scalar_one_or_none()
        if updated is None:
            return None
        await self.db.commit()
        return updated

    async def delete(self, user_id: int) -> bool:
        res = await self.db.execute(delete(User).where(User.id == user_id).returning(User.id))
        deleted = res.scalar_one_or_none()
        if deleted is None:
            return False
        await self.db.commit()
        return True

    async def verify_credentials(self, username: str, password: str) -> Optional[User]:
        user = await self.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


# ------------------------------------ Оставляем без изменений
class AdvertisementCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        title: str,
        description: str,
        price: Decimal,
        author: str,
        owner_id: int | None = None,  # ПО ЗАДАНИЮ. Добавили owner_id
    ) -> Advertisement:
        ad = Advertisement(
            title=title,
            description=description,
            price=price,
            author=author,
            owner_id=owner_id,  # ПО ЗАДАНИЮ. Привязали объявление к владельцу
        )
        self.db.add(ad)
        await self.db.commit()
        await self.db.refresh(ad)
        return ad

    async def get(self, ad_id: int) -> Optional[Advertisement]:
        res = await self.db.execute(select(Advertisement).where(Advertisement.id == ad_id))
        return res.scalar_one_or_none()

    async def delete(self, ad_id: int) -> bool:
        res = await self.db.execute(delete(Advertisement).where(Advertisement.id == ad_id).returning(Advertisement.id))
        deleted = res.scalar_one_or_none()
        if deleted is None:
            return False
        await self.db.commit()
        return True

    async def patch(
        self,
        ad_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Decimal] = None,
        author: Optional[str] = None,
    ) -> Optional[Advertisement]:
        values = {}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if price is not None:
            values["price"] = price
        if author is not None:
            values["author"] = author

        if not values:
            # ничего обновлять
            return await self.get(ad_id)

        stmt = (
            update(Advertisement)
            .where(Advertisement.id == ad_id)
            .values(**values)
            .returning(Advertisement)
        )
        res = await self.db.execute(stmt)
        updated = res.scalar_one_or_none()
        if updated is None:
            return None
        await self.db.commit()
        return updated

    async def search(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        q: Optional[str] = None,
        price_from: Optional[Decimal] = None,
        price_to: Optional[Decimal] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Advertisement]:
        filters = []

        if title:
            filters.append(Advertisement.title.ilike(f"%{title}%"))
        if description:
            filters.append(Advertisement.description.ilike(f"%{description}%"))
        if author:
            filters.append(Advertisement.author.ilike(f"%{author}%"))

        # q — общий поиск по title/description/author
        if q:
            filters.append(
                (Advertisement.title.ilike(f"%{q}%"))
                | (Advertisement.description.ilike(f"%{q}%"))
                | (Advertisement.author.ilike(f"%{q}%"))
            )

        if price_from is not None:
            filters.append(Advertisement.price >= price_from)
        if price_to is not None:
            filters.append(Advertisement.price <= price_to)

        if created_from is not None:
            filters.append(Advertisement.created_at >= created_from)
        if created_to is not None:
            filters.append(Advertisement.created_at <= created_to)

        stmt = select(Advertisement).order_by(Advertisement.created_at.desc())

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.limit(min(max(limit, 1), 200)).offset(max(offset, 0))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
