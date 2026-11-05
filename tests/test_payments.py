"""Tests para el CRUD de pagos y las transiciones de estado."""

import pytest
from httpx import AsyncClient


def _auth(api_key: str) -> dict[str, str]:
    """Helper para construir el header de autenticación."""
    return {"X-API-Key": api_key}


@pytest.mark.asyncio
async def test_create_payment_with_valid_api_key(
    client: AsyncClient, merchant: dict
) -> None:
    """Crear un pago con api_key válida devuelve 201 y estado pending."""
    resp = await client.post(
        "/payments",
        json={"amount": 49.99, "currency": "EUR", "description": "Suscripción Pro"},
        headers=_auth(merchant["api_key"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["amount"] == 49.99
    assert data["merchant_id"] == merchant["id"]


@pytest.mark.asyncio
async def test_create_payment_without_api_key(client: AsyncClient) -> None:
    """Crear un pago sin api_key devuelve 422 (header requerido faltante)."""
    resp = await client.post(
        "/payments",
        json={"amount": 10.0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_payment_with_invalid_api_key(client: AsyncClient) -> None:
    """Crear un pago con api_key inválida devuelve 401."""
    resp = await client.post(
        "/payments",
        json={"amount": 10.0},
        headers=_auth("pk_invalida"),
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_payments(client: AsyncClient, merchant: dict) -> None:
    """Listar pagos devuelve únicamente los del merchant autenticado."""
    await client.post(
        "/payments",
        json={"amount": 20.0},
        headers=_auth(merchant["api_key"]),
    )
    resp = await client.get("/payments", headers=_auth(merchant["api_key"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_payment_detail(client: AsyncClient, merchant: dict) -> None:
    """Obtener el detalle de un pago existente devuelve 200."""
    create = await client.post(
        "/payments",
        json={"amount": 5.0},
        headers=_auth(merchant["api_key"]),
    )
    payment_id = create.json()["id"]
    resp = await client.get(f"/payments/{payment_id}", headers=_auth(merchant["api_key"]))
    assert resp.status_code == 200
    assert resp.json()["id"] == payment_id


@pytest.mark.asyncio
async def test_valid_status_transition_pending_to_completed(
    client: AsyncClient, merchant: dict
) -> None:
    """La transición pending → completed debe devolver 200."""
    create = await client.post(
        "/payments",
        json={"amount": 100.0},
        headers=_auth(merchant["api_key"]),
    )
    payment_id = create.json()["id"]
    resp = await client.patch(
        f"/payments/{payment_id}/status",
        json={"status": "completed"},
        headers=_auth(merchant["api_key"]),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_valid_status_transition_pending_to_failed(
    client: AsyncClient, merchant: dict
) -> None:
    """La transición pending → failed debe devolver 200."""
    create = await client.post(
        "/payments",
        json={"amount": 30.0},
        headers=_auth(merchant["api_key"]),
    )
    payment_id = create.json()["id"]
    resp = await client.patch(
        f"/payments/{payment_id}/status",
        json={"status": "failed"},
        headers=_auth(merchant["api_key"]),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_valid_status_transition_completed_to_refunded(
    client: AsyncClient, merchant: dict
) -> None:
    """La transición completed → refunded debe devolver 200."""
    create = await client.post(
        "/payments",
        json={"amount": 75.0},
        headers=_auth(merchant["api_key"]),
    )
    payment_id = create.json()["id"]
    await client.patch(
        f"/payments/{payment_id}/status",
        json={"status": "completed"},
        headers=_auth(merchant["api_key"]),
    )
    resp = await client.patch(
        f"/payments/{payment_id}/status",
        json={"status": "refunded"},
        headers=_auth(merchant["api_key"]),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"


@pytest.mark.asyncio
async def test_invalid_status_transition_failed_to_completed(
    client: AsyncClient, merchant: dict
) -> None:
    """La transición failed → completed debe devolver 400."""
    create = await client.post(
        "/payments",
        json={"amount": 50.0},
        headers=_auth(merchant["api_key"]),
    )
    payment_id = create.json()["id"]
    await client.patch(
        f"/payments/{payment_id}/status",
        json={"status": "failed"},
        headers=_auth(merchant["api_key"]),
    )
    resp = await client.patch(
        f"/payments/{payment_id}/status",
        json={"status": "completed"},
        headers=_auth(merchant["api_key"]),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_status_transition_pending_to_refunded(
    client: AsyncClient, merchant: dict
) -> None:
    """La transición pending → refunded debe devolver 400."""
    create = await client.post(
        "/payments",
        json={"amount": 60.0},
        headers=_auth(merchant["api_key"]),
    )
    payment_id = create.json()["id"]
    resp = await client.patch(
        f"/payments/{payment_id}/status",
        json={"status": "refunded"},
        headers=_auth(merchant["api_key"]),
    )
    assert resp.status_code == 400
