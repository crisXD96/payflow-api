"""Gestión de la conexión a SQLite y creación de tablas."""

from typing import AsyncGenerator

import aiosqlite

from app import config

# Se lee en cada conexión (no al importar), así los tests pueden sobrescribirlo.
DATABASE_URL = config.DATABASE_URL


async def _connect() -> aiosqlite.Connection:
    """Abre una conexión configurada con filas tipo dict y claves foráneas activas."""
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    # SQLite no aplica REFERENCES salvo que se active por conexión (no altera el schema).
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Proporciona una conexión a la base de datos como dependencia de FastAPI."""
    db = await _connect()
    try:
        yield db
    finally:
        await db.close()


async def create_tables() -> None:
    """Crea las tablas de la base de datos si no existen."""
    db = await _connect()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                email       TEXT NOT NULL UNIQUE,
                api_key     TEXT NOT NULL UNIQUE,
                status      TEXT NOT NULL DEFAULT 'active',
                created_at  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id              TEXT PRIMARY KEY,
                merchant_id     TEXT NOT NULL REFERENCES merchants(id),
                amount          REAL NOT NULL,
                currency        TEXT NOT NULL DEFAULT 'EUR',
                status          TEXT NOT NULL DEFAULT 'pending',
                description     TEXT,
                customer_email  TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
        """)
        await db.commit()
    finally:
        await db.close()
