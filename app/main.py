from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status  # Добавил для DELETE Response И Response, ДОБАВЛЯЕМ ИПОРТЫ ПО ЗАДАНИЮ status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crud import AdvertisementCRUD, UserCRUD  # ДОБАВЛЯЕМ ИПОРТЫ ПО ЗАДАНИЮ
from app.db import close_engine, get_db
from app.deps import get_current_user_optional, get_current_user
from app.schemas import (
    AdvertisementCreate,
    AdvertisementOut,
    AdvertisementUpdate,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.security import create_access_token


settings = get_settings()

# -------------------- LIFESPAN (startup/shutdown) + BOOTSTRAP ROOT --------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # “первый админ” через env (bootstrap)
    # Root создаётся ТОЛЬКО при старте приложения, и только если заданы env-переменные.
    # Root — отдельная роль (group="root"), обычные админы остаются group="admin".

    if settings.bootstrap_root_username and settings.bootstrap_root_password:
        # bcrypt ограничение: пароль > 72 bytes нельзя (иначе будет ValueError)
        if len(settings.bootstrap_root_password.encode("utf-8")) > 72:
            raise RuntimeError(
                "BOOTSTRAP_ROOT_PASSWORD is longer than 72 bytes (bcrypt limit). "
                "Use a shorter password (<= 72 bytes)."
            )

        # get_db — dependency-generator, можно использовать его вручную
        # ВАЖНО: нельзя делать `async for ... break` без корректного закрытия генератора,
        # иначе сессия/соединение может остаться “подвешенным” (особенно в тестах с разными event loop).
        db_gen = get_db()
        db = await anext(db_gen)
        try:
            existing = await UserCRUD(db).get_by_username(settings.bootstrap_root_username)
            if not existing:
                # создаём root (самый первый админ)
                await UserCRUD(db).create(
                    username=settings.bootstrap_root_username,
                    password=settings.bootstrap_root_password,
                    group="root",
                )
        finally:
            await db_gen.aclose()

    # startup done
    yield

    # shutdown
    await close_engine()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

# -------------------- AUTH --------------------

@app.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await UserCRUD(db).verify_credentials(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user_id=user.id, username=user.username, group=user.group)
    return TokenResponse(access_token=token)


# -------------------- USERS --------------------

@app.post("/user", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    # неавторизованный пользователь НЕ должен создавать admin
    # (и уж точно не должен создавать root)
    if payload.group == "root":
        raise HTTPException(status_code=403, detail="Forbidden")

    # Неавторизованный может создавать только обычного user
    if current_user is None:
        if payload.group != "user":
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        # Admin/Root — любые действия с любыми сущностями
        # Значит они могут создавать и user, и admin (но не root).
        if current_user.group not in ("admin", "root") and payload.group != "user":
            raise HTTPException(status_code=403, detail="Forbidden")

    exists = await UserCRUD(db).get_by_username(payload.username)
    if exists:
        raise HTTPException(status_code=409, detail="Username already exists")

    return await UserCRUD(db).create(username=payload.username, password=payload.password, group=payload.group)


@app.get("/user/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await UserCRUD(db).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/user", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    # require_admin(current_user)
    # root тоже должен иметь права admin
    if current_user.group not in ("admin", "root"):
        raise HTTPException(status_code=403, detail="Forbidden")

    return await UserCRUD(db).list(limit=limit, offset=offset)


@app.patch("/user/{user_id}", response_model=UserOut)
async def patch_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # user может править только себя, admin — любого
    # require_self_or_admin(current_user, user_id)
    if current_user.group not in ("admin", "root") and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # менять группу может только admin (и root тоже)
    if payload.group is not None and current_user.group not in ("admin", "root"):
        raise HTTPException(status_code=403, detail="Forbidden")

    # запретим менять group на root через API
    if payload.group == "root":
        raise HTTPException(status_code=403, detail="Forbidden")

    # ✅ Запретим изменять ROOT-пользователя через API всем, кроме самого root
    target = await UserCRUD(db).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.group == "root" and current_user.group != "root":
        raise HTTPException(status_code=403, detail="Forbidden")

    updated = await UserCRUD(db).patch(
        user_id,
        username=payload.username,
        password=payload.password,
        group=payload.group,
    )
    return updated


@app.delete("/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # require_self_or_admin(current_user, user_id)
    if current_user.group not in ("admin", "root") and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # ✅ Запретим удаление ROOT-пользователя через API (root остаётся только bootstrap)
    target = await UserCRUD(db).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.group == "root":
        raise HTTPException(status_code=403, detail="Forbidden")

    ok = await UserCRUD(db).delete(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return None


# -------------------- ADVERTISEMENTS тут почти ничего не тронуто, дополнено и переделан DELETE --> 204-----

@app.post("/advertisement", response_model=AdvertisementOut, status_code=201)
async def create_advertisement(
    payload: AdvertisementCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),  # теперь только авторизованный
):
    return await AdvertisementCRUD(db).create(
        title=payload.title,
        description=payload.description,
        price=payload.price,
        author=payload.author,
        owner_id=current_user.id,
    )


@app.patch("/advertisement/{advertisement_id}", response_model=AdvertisementOut)
async def patch_advertisement(
    advertisement_id: int,
    payload: AdvertisementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ad = await AdvertisementCRUD(db).get(advertisement_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # require_owner_or_admin(current_user, ad.owner_id)
    if current_user.group not in ("admin", "root") and current_user.id != ad.owner_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    updated = await AdvertisementCRUD(db).patch(
        advertisement_id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        author=payload.author,
    )
    assert updated is not None
    return updated


# Поправил тут. Теперь 204 No Content + пустое тело. Теперь соответствует практике REST :)
@app.delete("/advertisement/{advertisement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_advertisement(
    advertisement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ad = await AdvertisementCRUD(db).get(advertisement_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # require_owner_or_admin(current_user, ad.owner_id)
    if current_user.group not in ("admin", "root") and current_user.id != ad.owner_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    ok = await AdvertisementCRUD(db).delete(advertisement_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return None


@app.get("/advertisement/{advertisement_id}", response_model=AdvertisementOut)
async def get_advertisement(advertisement_id: int, db: AsyncSession = Depends(get_db)):
    ad = await AdvertisementCRUD(db).get(advertisement_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return ad


@app.get("/advertisement", response_model=list[AdvertisementOut])
async def search_advertisements(
    db: AsyncSession = Depends(get_db),
    title: Optional[str] = None,
    description: Optional[str] = None,
    author: Optional[str] = None,
    q: Optional[str] = None,
    price_from: Optional[Decimal] = Query(default=None, gt=0),
    price_to: Optional[Decimal] = Query(default=None, gt=0),
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return await AdvertisementCRUD(db).search(
        title=title,
        description=description,
        author=author,
        q=q,
        price_from=price_from,
        price_to=price_to,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
