# PayFlow API

API REST de procesamiento de pagos — proyecto educativo para practicar hooks de Claude Code.

**Stack:** Python 3.12+, FastAPI, SQLite + aiosqlite, Pydantic v2, pytest

## Inicio rápido

```bash
# 1. Crear y activar el entorno virtual
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Instalar dependencias
pip install -e ".[dev]"

# 3. Ejecutar los tests
python -m pytest tests/ -v

# 4. Arrancar el servidor
python -m uvicorn app.main:app --reload
```

El servidor arranca en **http://localhost:8000**.

| Recurso | URL |
|---------|-----|
| Docs interactivas | http://localhost:8000/docs |
| Redoc | http://localhost:8000/redoc |
| Dashboard | http://localhost:8000/dashboard |
| Health | http://localhost:8000/health |

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado de la API |
| POST | `/merchants` | Crear merchant (devuelve api_key) |
| GET | `/merchants` | Listar merchants |
| GET | `/merchants/{id}` | Detalle de merchant |
| POST | `/payments` | Crear pago (`X-API-Key` requerido) |
| GET | `/payments` | Listar pagos del merchant autenticado |
| GET | `/payments/{id}` | Detalle de pago |
| PATCH | `/payments/{id}/status` | Cambiar estado del pago |

## Transiciones de estado válidas

```
pending → completed
pending → failed
completed → refunded
```

## Autenticación

Los endpoints de pagos requieren el header `X-API-Key` con la clave generada al crear el merchant (`pk_` + 32 hex chars).
