# ВНЕСЕНЫ ИЗМЕНЕИЯ ДОПЛНИТЕЛЬНО ПО ЗАДАНИЮ. движок + get_db + close_engine
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker

    # ВАЖНО для тестов/anyio:
    # engine привязан к текущему event loop на практике (через pool/asyncpg).
    # Поэтому при пересоздании loop (pytest/anyio) мы должны уметь пересоздать engine.
    if _engine is None:
        settings = get_settings()

        # future=True в SQLAlchemy 2.x не нужен, но можно оставить — не мешает.
        _engine = create_async_engine(
            settings.database_url,
            future=True,
            pool_pre_ping=True,
        )

        _sessionmaker = async_sessionmaker(
            bind=_engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # Гарантируем, что sessionmaker создаётся вместе с engine
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Сессия на каждый запрос (FastAPI dependency)
    Session = get_sessionmaker()
    async with Session() as session:
        try:
            yield session
        finally:
            # На всякий случай: если где-то забыли commit/rollback,
            # закрытие сессии не должно оставлять "подвисшие" транзакции.
            # (async with сам закроет, но rollback делает поведение стабильнее)
            await session.rollback()


async def close_engine() -> None:
    global _engine, _sessionmaker

    # ВАЖНО:
    # Dispose закрывает пул соединений. В тестах и при перезапуске приложения
    # нужно ещё и обнулить ссылки, чтобы новый loop создал новый engine/pool.
    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _sessionmaker = None
