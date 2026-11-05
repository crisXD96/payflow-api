"""Router para el CRUD de merchants."""

from fastapi import APIRouter, Depends

import aiosqlite

from app.database import get_db
from app.models import MerchantCreate, MerchantPublic, MerchantResponse
from app.services import merchant_service

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.post("", response_model=MerchantResponse, status_code=201)
async def create_merchant(
    data: MerchantCreate,
    db: aiosqlite.Connection = Depends(get_db),
) -> MerchantResponse:
    """Crea un nuevo merchant y devuelve su API key (única vez que se expone)."""
    return await merchant_service.create_merchant(db, data)


@router.get("", response_model=list[MerchantPublic])
async def list_merchants(
    db: aiosqlite.Connection = Depends(get_db),
) -> list[MerchantPublic]:
    """Devuelve la lista de todos los merchants, sin API keys."""
    return await merchant_service.list_merchants(db)


@router.get("/{merchant_id}", response_model=MerchantPublic)
async def get_merchant(
    merchant_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> MerchantPublic:
    """Devuelve el detalle de un merchant por su ID, sin API key."""
    return await merchant_service.get_merchant(db, merchant_id)
