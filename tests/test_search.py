from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.anyio
async def test_search_filters(auth_client_a):
    # создадим несколько объявлений от пользователя A
    ads = [
        {"title": "Продам RTX 4090", "description": "Новая", "price": "2500.00", "author": "Alice"},
        {"title": "Куплю RTX", "description": "Ищу 3080/3090", "price": "1200.00", "author": "Bob"},
        {"title": "Продам велосипед", "description": "Горный", "price": "300.00", "author": "Alice"},
    ]

    created_ids: list[int] = []
    for a in ads:
        r = await auth_client_a.post("/advertisement", json=a)
        assert r.status_code == 201, r.text
        created_ids.append(r.json()["id"])

    # q (общий поиск)
    r = await auth_client_a.get("/advertisement", params={"q": "rtx"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) >= 2
    assert any("rtx" in it["title"].lower() for it in items)

    # author filter
    r = await auth_client_a.get("/advertisement", params={"author": "Alice"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) >= 2
    assert all("alice" in it["author"].lower() for it in items)

    # price range (Decimal сравнение, без float)
    r = await auth_client_a.get("/advertisement", params={"price_from": "1000", "price_to": "2600"})
    assert r.status_code == 200, r.text
    items = r.json()

    low = Decimal("1000")
    high = Decimal("2600")
    assert all(low <= Decimal(it["price"]) <= high for it in items)

    # cleanup (удаление своих объявлений)
    for ad_id in created_ids:
        r = await auth_client_a.delete(f"/advertisement/{ad_id}")
        assert r.status_code == 204, r.text
