"""Punto de entrada de la aplicación FastAPI PayFlow."""

import math
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_NAME, APP_VERSION, FRONTEND_DIR
from app.database import create_tables
from app.routers import health, merchants, payments


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación: crea tablas al arrancar."""
    await create_tables()
    yield


app = FastAPI(
    title=APP_NAME,
    description="API REST de procesamiento de pagos - Proyecto educativo",
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS abierto (proyecto educativo). La autenticación va en la cabecera X-API-Key,
# no en cookies, así que no se permiten credenciales: con origen "*" + credenciales,
# Starlette refleja cualquier Origin y habilitaría peticiones con cookies desde cualquier web.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _json_safe(value: Any) -> Any:
    """Sustituye floats no finitos (NaN, ±Infinity) por texto: JSON estándar no los admite."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Igual que el handler por defecto (422 + detail), pero sin romper con NaN/Infinity.

    El handler por defecto repite el `input` recibido; si es NaN o Infinity, la
    serialización JSON falla y el cliente recibía un 500 en lugar de un 422.
    """
    return JSONResponse(status_code=422, content={"detail": _json_safe(jsonable_encoder(exc.errors()))})


# Routers
app.include_router(health.router)
app.include_router(merchants.router)
app.include_router(payments.router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirige la raíz al dashboard."""
    return RedirectResponse(url="/dashboard/")


class RevalidatingStaticFiles(StaticFiles):
    """StaticFiles que obliga al navegador a revalidar (ETag → 304) en cada carga.

    Sin esto, Chrome aplica caché heurística al HTML y tras un despliegue
    puede seguir mostrando un dashboard obsoleto.
    """

    async def get_response(self, path: str, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Frontend estático accesible en /dashboard (ruta absoluta: no depende del cwd)
app.mount("/dashboard", RevalidatingStaticFiles(directory=FRONTEND_DIR, html=True), name="dashboard")
