# ПО ЗАДАНИЮ. НОВЫЙ ФАЙЛ. Зависимости авторизации/прав

from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import UserCRUD
from app.db import get_db
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _is_admin_like(user) -> bool:
    # root должен иметь права admin, но сам root создаётся только bootstrap-ом через env
    return user.group in ("admin", "root")


async def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    if creds is None:
        return None

    token = creds.credentials
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await UserCRUD(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


async def get_current_user(
    user=Depends(get_current_user_optional),
):
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(user):
    # admin и root имеют полный доступ
    if not _is_admin_like(user):
        raise HTTPException(status_code=403, detail="Forbidden")


def require_self_or_admin(user, target_user_id: int):
    if _is_admin_like(user):
        return
    if user.id != target_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")


def require_owner_or_admin(user, owner_id: int | None):
    if _is_admin_like(user):
        return
    if owner_id is None or user.id != owner_id:
        raise HTTPException(status_code=403, detail="Forbidden")
