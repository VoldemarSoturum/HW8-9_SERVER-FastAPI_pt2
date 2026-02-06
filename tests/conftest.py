# tests/conftest.py

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import httpx
import pytest
from asgi_lifespan import LifespanManager  # ДОБАВИЛИ: корректный lifespan для любых httpx версий

from app.main import app  # если у тебя другой путь — поправь импорт


@dataclass(frozen=True)
class TestUser:
    id: int
    username: str
    password: str
    group: str
    token: str


def _uniq(base: str) -> str:
    # alice -> alice_1a2b3c4d
    return f"{base}_{uuid4().hex[:8]}"


async def _register_user(
    client: httpx.AsyncClient,
    *,
    base_username: str,
    password: str,
    group: str = "user",
    token: str | None = None,
) -> dict:
    """
    Регистрирует пользователя.
    - anon может создать только group=user
    - admin/root может создать group=admin
    """
    payload = {
        "username": _uniq(base_username),
        "password": password,
        "group": group,
    }
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = await client.post("/user", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    data = r.json()
    return {
        "id": data["id"],
        "username": payload["username"],
        "password": password,
        "group": data.get("group", group),
    }


async def _login(client: httpx.AsyncClient, username: str, password: str) -> str:
    r = await client.post("/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _create_user_and_token(
    client: httpx.AsyncClient,
    *,
    base_username: str,
    password: str,
    group: str = "user",
    creator_token: str | None = None,
) -> TestUser:
    reg = await _register_user(
        client,
        base_username=base_username,
        password=password,
        group=group,
        token=creator_token,
    )
    token = await _login(client, reg["username"], reg["password"])
    return TestUser(
        id=reg["id"],
        username=reg["username"],
        password=reg["password"],
        group=reg["group"],
        token=token,
    )


@pytest.fixture
async def client():
    # httpx>=0.24: app передаём через ASGITransport (параметра app= больше нет)
    # ВАЖНО: lifespan должен отрабатываться в тестах, иначе engine/подключения могут “залипать”.
    async with LifespanManager(app):  # ✅ ВКЛЮЧАЕМ startup/shutdown FastAPI
        transport = httpx.ASGITransport(app=app)  # lifespan=... УБРАЛИ (у тебя его нет)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def user_a(client) -> TestUser:
    return await _create_user_and_token(client, base_username="alice", password="alice_pass_123", group="user")


@pytest.fixture
async def user_b(client) -> TestUser:
    return await _create_user_and_token(client, base_username="bob", password="bob_pass_123", group="user")


@pytest.fixture
async def auth_client_a(client, user_a: TestUser) -> httpx.AsyncClient:
    # ВАЖНО: не мутируем headers общего client (чтобы не протекало в другие тесты)
    return httpx.AsyncClient(
        transport=client._transport,  # используем тот же ASGITransport
        base_url=str(client.base_url),
        headers={"Authorization": f"Bearer {user_a.token}"},
    )


@pytest.fixture
async def auth_client_b(client, user_b: TestUser) -> httpx.AsyncClient:
    # ВАЖНО: не мутируем headers общего client (чтобы не протекало в другие тесты)
    return httpx.AsyncClient(
        transport=client._transport,  # используем тот же ASGITransport
        base_url=str(client.base_url),
        headers={"Authorization": f"Bearer {user_b.token}"},
    )
