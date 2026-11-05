"""Configuración central de la aplicación (sin secretos: todo es configurable por entorno)."""

import os
from pathlib import Path

APP_NAME = "PayFlow API"
APP_VERSION = "0.1.0"

# Raíz del proyecto: rutas independientes del directorio desde el que se lance uvicorn.
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Ruta del archivo SQLite; se puede sobrescribir con la variable de entorno PAYFLOW_DB.
DATABASE_URL = os.environ.get("PAYFLOW_DB", "payflow.db")
