"""Tests de regresión para los bugs de validación y seguridad corregidos en el refactor."""

import pytest
from httpx import AsyncClient


def _auth(api_key: str) -> dict[str, str]:
    """Helper para construir el header de autenticación."""
    return {"X-API-Key": api_key}


async def _create_payment(client: AsyncClient, api_key: str, **body) -> dict:
    """Crea un pago válido y devuelve su JSON."""
    resp = await client.post("/payments", json={"amount": 10.0, **body}, headers=_auth(api_key))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Seguridad: la API key nunca se filtra fuera de la creación
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_merchants_does_not_expose_api_key(client: AsyncClient, merchant: dict) -> None:
    """GET /merchants es público: no debe devolver la API key de nadie."""
    resp = await client.get("/merchants")
    assert resp.status_code == 200
    assert all("api_key" not in m for m in resp.json())


@pytest.mark.asyncio
async def test_get_merchant_does_not_expose_api_key(client: AsyncClient, merchant: dict) -> None:
    """GET /merchants/{id} es público: no debe devolver la API key."""
    resp = await client.get(f"/merchants/{merchant['id']}")
    assert resp.status_code == 200
    assert "api_key" not in resp.json()


@pytest.mark.asyncio
async def test_cors_does_not_allow_credentials(client: AsyncClient) -> None:
    """CORS abierto, pero sin credenciales (la auth va por cabecera, no por cookies)."""
    resp = await client.options(
        "/health",
        headers={"Origin": "http://otro-sitio.example", "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-credentials") != "true"


@pytest.mark.asyncio
async def test_payment_of_other_merchant_is_not_found(client: AsyncClient, merchant: dict) -> None:
    """Un merchant no puede ver ni modificar pagos de otro merchant."""
    payment = await _create_payment(client, merchant["api_key"])
    other = (await client.post("/merchants", json={"name": "Otra", "email": "otra@example.com"})).json()

    resp = await client.get(f"/payments/{payment['id']}", headers=_auth(other["api_key"]))
    assert resp.status_code == 404
    resp = await client.patch(
        f"/payments/{payment['id']}/status", json={"status": "completed"}, headers=_auth(other["api_key"])
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Validación de merchants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
async def test_create_merchant_rejects_invalid_name(client: AsyncClient, name: str) -> None:
    """El nombre no puede estar vacío, ser solo espacios ni superar 120 caracteres."""
    resp = await client.post("/merchants", json={"name": name, "email": "n@example.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_merchant_trims_name(client: AsyncClient) -> None:
    """Los espacios alrededor del nombre se eliminan."""
    resp = await client.post("/merchants", json={"name": "  Mi Tienda  ", "email": "t@example.com"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Mi Tienda"


# ---------------------------------------------------------------------------
# Validación de pagos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("raw_amount", ["NaN", "Infinity", "-Infinity"])
async def test_create_payment_rejects_non_finite_amount(
    client: AsyncClient, merchant: dict, raw_amount: str
) -> None:
    """NaN provocaba un 500 (IntegrityError) e Infinity se guardaba: ahora ambos son 422."""
    resp = await client.post(
        "/payments",
        content=f'{{"amount": {raw_amount}}}',
        headers={**_auth(merchant["api_key"]), "Content-Type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [0, -5, 1_000_000_001])
async def test_create_payment_rejects_invalid_amount(
    client: AsyncClient, merchant: dict, amount: float
) -> None:
    """Importe > 0 y dentro del tope."""
    resp = await client.post("/payments", json={"amount": amount}, headers=_auth(merchant["api_key"]))
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("amount", "currency"),
    [(0.001, "EUR"), (19.999, "USD"), (15000.5, "JPY"), (100.1, "CLP"), (1.1255, "BHD")],
)
async def test_create_payment_rejects_too_many_decimals_for_currency(
    client: AsyncClient, merchant: dict, amount: float, currency: str
) -> None:
    """Los decimales se validan según la moneda (ISO 4217), no con un límite global."""
    resp = await client.post(
        "/payments", json={"amount": amount, "currency": currency}, headers=_auth(merchant["api_key"])
    )
    assert resp.status_code == 422
    assert f"{currency} admite como máximo" in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("amount", "currency"),
    [(0.01, "EUR"), (19.99, "USD"), (15000, "JPY"), (1.125, "BHD"), (0.5, "KWD")],
)
async def test_create_payment_accepts_valid_decimals_for_currency(
    client: AsyncClient, merchant: dict, amount: float, currency: str
) -> None:
    """Se aceptan 2 decimales en EUR/USD, 0 en JPY y 3 en BHD/KWD."""
    payment = await _create_payment(client, merchant["api_key"], amount=amount, currency=currency)
    assert payment["amount"] == amount
    assert payment["currency"] == currency


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["", "EU", "EURO", "12A", "€", "ZZZ", "XXX"])
async def test_create_payment_rejects_invalid_currency(
    client: AsyncClient, merchant: dict, currency: str
) -> None:
    """La moneda debe ser un código ISO 4217 de 3 letras."""
    resp = await client.post(
        "/payments", json={"amount": 10, "currency": currency}, headers=_auth(merchant["api_key"])
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_payment_normalizes_currency(client: AsyncClient, merchant: dict) -> None:
    """La moneda se normaliza a mayúsculas."""
    payment = await _create_payment(client, merchant["api_key"], currency=" mxn ")
    assert payment["currency"] == "MXN"


@pytest.mark.asyncio
async def test_create_payment_blank_description_is_null(client: AsyncClient, merchant: dict) -> None:
    """Una descripción solo con espacios se guarda como null."""
    payment = await _create_payment(client, merchant["api_key"], description="   ")
    assert payment["description"] is None


@pytest.mark.asyncio
async def test_create_payment_rejects_long_description(client: AsyncClient, merchant: dict) -> None:
    """La descripción admite como máximo 200 caracteres (igual que el dashboard)."""
    resp = await client.post(
        "/payments", json={"amount": 10, "description": "x" * 201}, headers=_auth(merchant["api_key"])
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Transiciones de estado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["pending", "completed", "failed", "refunded"])
async def test_refunded_is_terminal(client: AsyncClient, merchant: dict, target: str) -> None:
    """Desde refunded no hay transiciones posibles."""
    payment = await _create_payment(client, merchant["api_key"])
    headers = _auth(merchant["api_key"])
    url = f"/payments/{payment['id']}/status"
    assert (await client.patch(url, json={"status": "completed"}, headers=headers)).status_code == 200
    assert (await client.patch(url, json={"status": "refunded"}, headers=headers)).status_code == 200

    resp = await client.patch(url, json={"status": target}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_status_update_refreshes_updated_at(client: AsyncClient, merchant: dict) -> None:
    """Cambiar el estado actualiza updated_at y conserva created_at."""
    payment = await _create_payment(client, merchant["api_key"])
    resp = await client.patch(
        f"/payments/{payment['id']}/status", json={"status": "completed"}, headers=_auth(merchant["api_key"])
    )
    data = resp.json()
    assert data["created_at"] == payment["created_at"]
    assert data["updated_at"] >= payment["updated_at"]


@pytest.mark.asyncio
async def test_concurrent_status_change_returns_409(
    client: AsyncClient, merchant: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si otra petición cambia el estado entre la lectura y la escritura, no se pisa: 409."""
    from app.services import payment_service

    payment = await _create_payment(client, merchant["api_key"])
    headers = _auth(merchant["api_key"])
    url = f"/payments/{payment['id']}/status"
    # Otra petición marca el pago como fallido...
    assert (await client.patch(url, json={"status": "failed"}, headers=headers)).status_code == 200

    # ...pero esta petición leyó el pago cuando aún estaba pending (lectura obsoleta).
    real_get_payment = payment_service.get_payment
    calls = {"n": 0}

    async def stale_get_payment(db, payment_id, merchant_id):
        calls["n"] += 1
        current = await real_get_payment(db, payment_id, merchant_id)
        return current.model_copy(update={"status": "pending"}) if calls["n"] == 1 else current

    monkeypatch.setattr(payment_service, "get_payment", stale_get_payment)
    resp = await client.patch(url, json={"status": "completed"}, headers=headers)
    assert resp.status_code == 409

    monkeypatch.undo()
    final = await client.get(f"/payments/{payment['id']}", headers=headers)
    assert final.json()["status"] == "failed"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_is_served(client: AsyncClient) -> None:
    """El dashboard estático se sirve en /dashboard/."""
    resp = await client.get("/dashboard/")
    assert resp.status_code == 200
    assert "PayFlow" in resp.text
    # El navegador debe revalidar el HTML para no mostrar versiones viejas tras un despliegue.
    assert resp.headers["cache-control"] == "no-cache"


@pytest.mark.asyncio
async def test_root_redirects_to_dashboard(client: AsyncClient) -> None:
    """La raíz redirige al dashboard."""
    resp = await client.get("/")
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/dashboard/"
