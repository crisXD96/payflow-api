"""Tests para el CRUD de merchants."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_merchant(client: AsyncClient) -> None:
    """Crear un merchant devuelve 201 y una api_key con prefijo pk_."""
    resp = await client.post(
        "/merchants",
        json={"name": "Mi Tienda", "email": "tienda@example.com"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Mi Tienda"
    assert data["email"] == "tienda@example.com"
    assert data["api_key"].startswith("pk_")
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_merchant(client: AsyncClient) -> None:
    """Crear dos merchants con el mismo email devuelve 409."""
    payload = {"name": "Dup", "email": "dup@example.com"}
    r1 = await client.post("/merchants", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/merchants", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_merchants(client: AsyncClient, merchant: dict) -> None:
    """Listar merchants devuelve al menos el merchant creado."""
    resp = await client.get("/merchants")
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()]
    assert merchant["id"] in ids


@pytest.mark.asyncio
async def test_get_merchant_by_id(client: AsyncClient, merchant: dict) -> None:
    """Obtener un merchant por ID devuelve los datos correctos."""
    resp = await client.get(f"/merchants/{merchant['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == merchant["id"]


@pytest.mark.asyncio
async def test_get_merchant_not_found(client: AsyncClient) -> None:
    """Solicitar un merchant inexistente devuelve 404."""
    resp = await client.get("/merchants/no-existe")
    assert resp.status_code == 404
