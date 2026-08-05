# Backend — Indoor Positioning Platform

## Requisitos

- Python **3.11** o **3.12** (no usar 3.13+ — el stack ML tiene incompatibilidades en Windows)
- Base de datos SQLite (por defecto; cambiar a PostgreSQL en producción vía `.env`)

## Setup

```powershell
# 1. Clonar e ir al directorio
cd backend

# 2. Crear entorno virtual con la versión correcta de Python
py -3.12 -m venv .venv

# 3. Activar
.venv\Scripts\activate

# 4. Instalar el paquete en modo editable
pip install -e .

# 5. Copiar configuración
copy .env.example .env
```

## Base de datos

Se usa SQLite por defecto (archivo `./data/dev.db`). Las migraciones se
ejecutan automáticamente al iniciar el servidor.

```powershell
# Manual (si hace falta)
alembic upgrade head
```

El admin inicial se crea automáticamente en el primer inicio tomando
`ADMIN_EMAIL` y `ADMIN_PASSWORD` del `.env`. No requiere pasos extra.

## Ejecutar

```powershell
uvicorn app.main:app --reload --port 8000
```

Abrir `http://localhost:8000/docs` (Swagger UI).

## Tests

```powershell
python -m pytest tests/ -v
```

## Linting y tipos

```powershell
python -m ruff check app/ tests/
python -m mypy app/
```
