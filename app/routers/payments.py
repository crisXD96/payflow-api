"""Router para el CRUD de pagos."""

from fastapi import APIRouter, Depends, Header

import aiosqlite

from app.database import get_db
from app.models import MerchantResponse, PaymentCreate, PaymentResponse, PaymentStatusUpdate
from app.services import merchant_service, payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


async def _get_merchant_from_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: aiosqlite.Connection = Depends(get_db),
) -> MerchantResponse:
    """Dependencia: valida el header X-API-Key y devuelve el merchant autenticado."""
    return await merchant_service.get_merchant_by_api_key(db, x_api_key)


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(
    data: PaymentCreate,
    db: aiosqlite.Connection = Depends(get_db),
    merchant: MerchantResponse = Depends(_get_merchant_from_api_key),
) -> PaymentResponse:
    """Crea un nuevo pago para el merchant autenticado."""
    return await payment_service.create_payment(db, merchant.id, data)


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    db: aiosqlite.Connection = Depends(get_db),
    merchant: MerchantResponse = Depends(_get_merchant_from_api_key),
) -> list[PaymentResponse]:
    """Devuelve todos los pagos del merchant autenticado."""
    return await payment_service.list_payments(db, merchant.id)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    merchant: MerchantResponse = Depends(_get_merchant_from_api_key),
) -> PaymentResponse:
    """Devuelve el detalle de un pago del merchant autenticado."""
    return await payment_service.get_payment(db, payment_id, merchant.id)


@router.patch("/{payment_id}/status", response_model=PaymentResponse)
async def update_payment_status(
    payment_id: str,
    body: PaymentStatusUpdate,
    db: aiosqlite.Connection = Depends(get_db),
    merchant: MerchantResponse = Depends(_get_merchant_from_api_key),
) -> PaymentResponse:
    """Actualiza el estado de un pago. Las transiciones inválidas devuelven 400."""
    return await payment_service.update_payment_status(db, payment_id, merchant.id, body.status)
