"""Fixtures compartidas para los tests de PayFlow."""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Apuntar la DB a un archivo temporal ANTES de importar la app
TEST_DB = "test_payflow.db"
os.environ.setdefault("PAYFLOW_DB", TEST_DB)

# Parchear DATABASE_URL antes de que se importe la app
import app.database as _db_module
_db_module.DATABASE_URL = TEST_DB

from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    """Crea las tablas antes de cada test y las borra al terminar."""
    from app.database import create_tables
    await create_tables()
    yield
    # Limpiar tablas entre tests para independencia
    import aiosqlite
    async with aiosqlite.connect(TEST_DB) as db:
        await db.execute("DELETE FROM payments")
        await db.execute("DELETE FROM merchants")
        await db.commit()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Cliente HTTP asíncrono conectado a la app de test."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def merchant(client: AsyncClient) -> dict:
    """Crea un merchant de prueba y devuelve su respuesta JSON."""
    resp = await client.post(
        "/merchants",
        json={"name": "Tienda Test", "email": "test@example.com"},
    )
    assert resp.status_code == 201
    return resp.json()
