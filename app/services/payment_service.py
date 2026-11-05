"""Lógica de negocio para la gestión de pagos."""

import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import HTTPException

from app.models import PaymentCreate, PaymentResponse, PaymentStatus, VALID_TRANSITIONS


def _row_to_payment(row: aiosqlite.Row) -> PaymentResponse:
    """Convierte una fila de SQLite en un objeto PaymentResponse."""
    return PaymentResponse.model_validate(dict(row))


async def create_payment(
    db: aiosqlite.Connection, merchant_id: str, data: PaymentCreate
) -> PaymentResponse:
    """Crea un nuevo pago asociado a un merchant."""
    payment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """
        INSERT INTO payments
            (id, merchant_id, amount, currency, status, description, customer_email, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            payment_id,
            merchant_id,
            data.amount,
            data.currency,
            data.description,
            data.customer_email,
            now,
            now,
        ),
    )
    await db.commit()

    return await get_payment(db, payment_id, merchant_id)


async def list_payments(
    db: aiosqlite.Connection, merchant_id: str
) -> list[PaymentResponse]:
    """Devuelve todos los pagos de un merchant ordenados por fecha descendente."""
    async with db.execute(
        "SELECT * FROM payments WHERE merchant_id = ? ORDER BY created_at DESC",
        (merchant_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_payment(r) for r in rows]


async def get_payment(
    db: aiosqlite.Connection, payment_id: str, merchant_id: str
) -> PaymentResponse:
    """Obtiene un pago por ID validando que pertenece al merchant."""
    async with db.execute(
        "SELECT * FROM payments WHERE id = ? AND merchant_id = ?",
        (payment_id, merchant_id),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    return _row_to_payment(row)


async def update_payment_status(
    db: aiosqlite.Connection,
    payment_id: str,
    merchant_id: str,
    new_status: PaymentStatus,
) -> PaymentResponse:
    """Actualiza el estado de un pago validando que la transición sea permitida."""
    payment = await get_payment(db, payment_id, merchant_id)

    allowed = VALID_TRANSITIONS.get(payment.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Transición inválida: '{payment.status}' → '{new_status}'. "
                f"Transiciones permitidas desde '{payment.status}': {allowed or 'ninguna'}"
            ),
        )

    # Actualización condicional: solo aplica si el estado no cambió desde la lectura.
    # Evita que dos peticiones concurrentes (p. ej. completar y fallar) se pisen.
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        "UPDATE payments SET status = ?, updated_at = ? "
        "WHERE id = ? AND merchant_id = ? AND status = ?",
        (new_status, now, payment_id, merchant_id, payment.status),
    )
    await db.commit()

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=409,
            detail="El pago cambió de estado mientras se procesaba la petición. Vuelve a intentarlo.",
        )

    return await get_payment(db, payment_id, merchant_id)
