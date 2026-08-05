# Internav

Plataforma de posicionamiento indoor basado en huellas WiFi (fingerprinting).
Estima la posición dentro de un edificio a partir del escaneo de redes Wi-Fi,
con entrenamiento de modelos por piso y apps móviles Android.

## Módulos

| Directorio | Descripción |
|---|---|
| [`backend/`](backend/) | API REST (FastAPI) + pipeline de entrenamiento (KNN) + inferencia. Ver [`backend/README.md`](backend/README.md) |
| [`admin-portal/`](admin-portal/) | Portal web de administración (React + TypeScript + Vite): jerarquía, planos, grillas, campañas, datasets, modelos |
| [`android/`](android/) | Apps Android (Kotlin + Jetpack Compose): `:capture-app` (captura de huellas) y `:user-app` (posicionamiento) |
| [`spec/`](spec/) | Especificación del sistema (dominio, APIs, reglas de negocio) |
| `.github/workflows/` | CI/CD: backend, admin-portal y android |

## Cómo correr

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Swagger UI en `http://localhost:8000/docs`. El admin inicial se crea en el primer
arranque con `ADMIN_EMAIL` / `ADMIN_PASSWORD` del `.env`.

### Admin Portal

```powershell
cd admin-portal
npm install
npm run dev
```

### Android

```powershell
cd android
$env:JAVA_HOME="C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot"
.\gradlew.bat :capture-app:assembleDebug :user-app:assembleDebug
```

## Tests

```powershell
# Backend
cd backend && python -m pytest tests/ -v

# Admin Portal
cd admin-portal && npm run build

# Android
cd android && .\gradlew.bat :user-app:assembleDebug
```

## Documentación

- `spec/` — especificación completa del sistema.
- `PROGRESS.md` — estado del proyecto por fase y decisiones de implementación.
- `CHANGELOG.md` — historial de versiones.
