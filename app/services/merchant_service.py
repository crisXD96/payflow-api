"""Lógica de negocio para la gestión de merchants."""

import secrets
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import HTTPException

from app.models import MerchantCreate, MerchantPublic, MerchantResponse


_LOOKUP_QUERIES = {
    "id": "SELECT * FROM merchants WHERE id = ?",
    "api_key": "SELECT * FROM merchants WHERE api_key = ?",
}


async def _fetch_one(db: aiosqlite.Connection, column: str, value: str) -> aiosqlite.Row | None:
    """Busca un merchant por una columna única (id o api_key) con consultas fijas."""
    async with db.execute(_LOOKUP_QUERIES[column], (value,)) as cursor:
        return await cursor.fetchone()


async def create_merchant(db: aiosqlite.Connection, data: MerchantCreate) -> MerchantResponse:
    """Crea un nuevo merchant y le genera una API key única."""
    merchant_id = str(uuid.uuid4())
    api_key = "pk_" + secrets.token_hex(16)
    now = datetime.now(timezone.utc).isoformat()

    try:
        await db.execute(
            """
            INSERT INTO merchants (id, name, email, api_key, status, created_at)
            VALUES (?, ?, ?, ?, 'active', ?)
            """,
            (merchant_id, data.name, data.email, api_key, now),
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe un merchant con ese email")

    row = await _fetch_one(db, "id", merchant_id)
    return MerchantResponse.model_validate(dict(row))


async def list_merchants(db: aiosqlite.Connection) -> list[MerchantPublic]:
    """Devuelve todos los merchants (sin API keys) por fecha de creación descendente."""
    async with db.execute("SELECT * FROM merchants ORDER BY created_at DESC") as cursor:
        rows = await cursor.fetchall()
    return [MerchantPublic.model_validate(dict(r)) for r in rows]


async def get_merchant(db: aiosqlite.Connection, merchant_id: str) -> MerchantPublic:
    """Obtiene un merchant (sin API key) por su ID o lanza 404 si no existe."""
    row = await _fetch_one(db, "id", merchant_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Merchant no encontrado")
    return MerchantPublic.model_validate(dict(row))


async def get_merchant_by_api_key(db: aiosqlite.Connection, api_key: str) -> MerchantResponse:
    """Obtiene un merchant por su API key o lanza 401/403 si no es válida o está suspendido."""
    row = await _fetch_one(db, "api_key", api_key)
    if row is None:
        raise HTTPException(status_code=401, detail="API key inválida")
    if row["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Merchant suspendido")
    return MerchantResponse.model_validate(dict(row))
