"""Modelos Pydantic para requests y responses de la API."""

from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.currencies import ACTIVE_CURRENCIES, minor_units

# ---------------------------------------------------------------------------
# Merchants
# ---------------------------------------------------------------------------

MerchantName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class MerchantCreate(BaseModel):
    """Datos necesarios para crear un nuevo merchant."""
    name: MerchantName
    email: EmailStr


class MerchantPublic(BaseModel):
    """Datos públicos de un merchant. Nunca incluye la API key."""
    id: str
    name: str
    email: str
    status: Literal["active", "suspended"]
    created_at: datetime


class MerchantResponse(MerchantPublic):
    """Merchant con su API key: solo se devuelve al crearlo o al autenticarse."""
    api_key: str


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

PaymentStatus = Literal["pending", "completed", "failed", "refunded"]

VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending":   ["completed", "failed"],
    "completed": ["refunded"],
    "failed":    [],
    "refunded":  [],
}

MAX_AMOUNT = 1_000_000_000


class PaymentCreate(BaseModel):
    """Datos necesarios para crear un nuevo pago."""
    amount: float = Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    currency: str = "EUR"
    description: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]] = None
    customer_email: Optional[EmailStr] = None

    @field_validator("currency")
    @classmethod
    def currency_iso_code(cls, v: str) -> str:
        """Normaliza la moneda a mayúsculas y exige un código ISO 4217 en circulación."""
        code = v.strip().upper()
        if code not in ACTIVE_CURRENCIES:
            raise ValueError("La moneda debe ser un código ISO 4217 en circulación (p. ej. EUR)")
        return code

    @model_validator(mode="after")
    def amount_fits_currency_decimals(self) -> "PaymentCreate":
        """Rechaza importes con más decimales de los que admite su moneda (EUR 2, JPY 0, BHD 3)."""
        digits = minor_units(self.currency)
        scaled = self.amount * 10**digits
        if abs(scaled - round(scaled)) > 1e-6:
            raise PydanticCustomError(
                "amount_decimals",
                "{currency} admite como máximo {digits} decimales",
                {"currency": self.currency, "digits": digits},
            )
        return self

    @field_validator("description")
    @classmethod
    def empty_description_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Una descripción vacía o solo con espacios se guarda como nula."""
        return v or None


class PaymentStatusUpdate(BaseModel):
    """Payload para actualizar el estado de un pago."""
    status: PaymentStatus


class PaymentResponse(BaseModel):
    """Representación completa de un pago en las respuestas."""
    id: str
    merchant_id: str
    amount: float
    currency: str
    status: PaymentStatus
    description: Optional[str]
    customer_email: Optional[str]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Respuesta del endpoint de health check."""
    status: str
    version: str
    timestamp: datetime
