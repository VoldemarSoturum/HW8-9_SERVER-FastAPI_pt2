from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.anyio
async def test_crud_flow_authorized_user(auth_client_a):
    # CREATE (authorized user can create)
    payload = {
        "title": "Продам RTX 4090",
        "description": "Новая, в коробке",
        "price": "2500.00",
        "author": "Alice",
    }
    r = await auth_client_a.post("/advertisement", json=payload)
    assert r.status_code == 201, r.text
    created = r.json()
    ad_id = created["id"]

    assert created["title"] == payload["title"]
    assert created["description"] == payload["description"]
    assert Decimal(created["price"]) == Decimal(payload["price"])
    assert created["author"] == payload["author"]
    assert created["created_at"]

    # GET by id (public endpoint)
    r = await auth_client_a.get(f"/advertisement/{ad_id}")
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["id"] == ad_id
    assert got["title"] == payload["title"]
    assert Decimal(got["price"]) == Decimal(payload["price"])

    # PATCH (owner can patch)
    patch_payload = {"price": "2399.99", "description": "Срочно. Возможен торг."}
    r = await auth_client_a.patch(f"/advertisement/{ad_id}", json=patch_payload)
    assert r.status_code == 200, r.text
    patched = r.json()
    assert Decimal(patched["price"]) == Decimal("2399.99")
    assert patched["description"] == "Срочно. Возможен торг."

    # DELETE (owner can delete) -> 204 No Content
    r = await auth_client_a.delete(f"/advertisement/{ad_id}")
    assert r.status_code == 204, r.text

    # GET after delete -> 404
    r = await auth_client_a.get(f"/advertisement/{ad_id}")
    assert r.status_code == 404, r.text


@pytest.mark.anyio
async def test_unauthorized_cannot_create_advertisement(client):
    # Неавторизованный НЕ может создавать объявления -> 401
    payload = {
        "title": "Нельзя создать без токена",
        "description": "Должно упасть",
        "price": "100.00",
        "author": "Anon",
    }
    r = await client.post("/advertisement", json=payload)
    assert r.status_code == 401, r.text


@pytest.mark.anyio
async def test_user_cannot_delete_foreign_advertisement(auth_client_a, auth_client_b):
    # Пользователь A создаёт объявление
    payload = {
        "title": "Продам велосипед",
        "description": "Горный",
        "price": "300.00",
        "author": "Alice",
    }
    r = await auth_client_a.post("/advertisement", json=payload)
    assert r.status_code == 201, r.text
    ad_id = r.json()["id"]

    # Пользователь B пытается удалить чужое -> 403
    r = await auth_client_b.delete(f"/advertisement/{ad_id}")
    assert r.status_code == 403, r.text

    # Пользователь B пытается править чужое -> 403
    r = await auth_client_b.patch(f"/advertisement/{ad_id}", json={"price": "1.00"})
    assert r.status_code == 403, r.text

    # Владелец A удаляет -> 204
    r = await auth_client_a.delete(f"/advertisement/{ad_id}")
    assert r.status_code == 204, r.text


@pytest.mark.anyio
async def test_unauthorized_cannot_delete_advertisement(client, auth_client_a):
    # Создаём объявление авторизованно
    payload = {
        "title": "Тест на удаление без токена",
        "description": "Удаление должно быть запрещено",
        "price": "10.00",
        "author": "Alice",
    }
    r = await auth_client_a.post("/advertisement", json=payload)
    assert r.status_code == 201, r.text
    ad_id = r.json()["id"]

    # Пытаемся удалить без токена -> 401
    r = await client.delete(f"/advertisement/{ad_id}")
    assert r.status_code == 401, r.text

    # cleanup (владелец удаляет)
    r = await auth_client_a.delete(f"/advertisement/{ad_id}")
    assert r.status_code == 204, r.text
