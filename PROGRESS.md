# Progreso del proyecto

## Estado actual

| Fase | Estado | Descripción |
|------|--------|-------------|
| 1 | ✅ | Domain + persistencia core (Organization, Site, Building, Floor) |
| 2 | ✅ | JWT + RBAC + CRUD REST jerarquía |
| 3 | ✅ | FloorPlan, Grid & Cell |
| 4 | ✅ | Campaign, Fingerprint & AccessPointObservation |
| 5 | ✅ | Dataset & DatasetCampaign |
| 6 | ✅ | ModelVersion (state machine, BR-004) |
| 7 | ✅ | Users API + Inference API |
| 8 | ✅ | Training Pipeline (KNN, evaluación, serialización, download) |
| 9 | ✅ | Configuration Management + Logging |
| 10 | ✅ | Domain Events + orquestación + Model Update Policy |
| 11 | ✅ | Testing faltante, edge cases, refinamiento backend |
| 12 | ✅ | Admin Portal (frontend): setup, routing, componentes, Map Editor |
| 13 | ✅ | Capture App (android/capture-app/): WiFi scanning, sync |
| 14 | ✅ | User App (android/user-app/): inferencia offline |
| 15 | ✅ | Testing integral, seguridad, CI/CD, deployment, release |

### Fase 2 — Detalle de lo implementado

**Auth API** (`app/api/routers/auth.py`)
- `POST /api/v1/auth/login` — autentica por email+bcrypt, devuelve access+refresh tokens
- `POST /api/v1/auth/refresh` — renueva access+refresh desde un refresh token válido

**Hierarchy API** (`app/api/routers/hierarchy.py`)
- CRUD completo (GET list, GET by id, POST create, PUT update, DELETE soft-delete) para Organization, Site, Building y Floor
- RBAC por endpoint:
  - Administrator: acceso completo (incluido DELETE)
  - Operator: lectura, creación y actualización (sin DELETE)
  - Viewer: solo lectura
- Envelope de respuesta estándar (`success/message/data/errors/metadata`)
- Códigos HTTP: 200, 201, 204, 400, 401, 403, 404, 409

**App entry point** (`app/main.py`)
- FastAPI app con lifespan: migraciones Alembic + bootstrap admin inicial
- CORS middleware
- Routers registrados bajo `/api/v1`

**Fixtures y config** (`app/api/dependencies.py`)
- `get_session`: commit automático al completar request, rollback en error
- `get_current_user`: decodifica JWT, valida usuario activo
- `require_roles`: factory de dependencia RBAC

**Tests de integración** (`tests/test_auth.py`, `tests/test_hierarchy_api.py`)
- 37 tests totales (7 domain/repos preexistentes + 8 auth + 22 hierarchy)
- Cobertura de login, refresh, RBAC, CRUD completo de 4 niveles, lifecycle completo, manejo de errores

### Fase 3 — Detalle de lo implementado

**FloorPlan API** (`app/api/routers/floor_plans.py`)
- `GET /api/v1/floors/{floor_id}/floor-plans` — lista versiones de un Floor
- `GET /api/v1/floor-plans/{id}` — obtiene un FloorPlan por ID
- `POST /api/v1/floors/{floor_id}/floor-plans` — crea nueva versión (desactiva la anterior, auto-incrementa versión)
- `DELETE /api/v1/floor-plans/{id}` — soft-delete (solo si no está activo)
- RBAC: POST/DELETE requieren Operator+; GET es público autenticado
- Regla BR-010: exactamente un FloorPlan activo por Floor; versiones históricas preservadas

**Grid API** (`app/api/routers/grids.py`)
- `GET /api/v1/floors/{floor_id}/grids` — lista grids de un Floor
- `GET /api/v1/grids/{id}` — obtiene un Grid por ID
- `POST /api/v1/floors/{floor_id}/grids` — genera grid (requiere FloorPlan activo; uno por Floor)
- `POST /api/v1/grids/{id}/regenerate` — regenera celdas (no permitido si está Locked)
- `POST /api/v1/grids/{id}/activate` — activa grid
- `POST /api/v1/grids/{id}/lock` — bloquea grid
- `POST /api/v1/grids/{id}/unlock` — desbloquea grid
- `GET /api/v1/grids/{id}/cells` — lista celdas
- `PUT /api/v1/cells/{id}/walkable` — actualiza walkable (bloqueado si hay campaña activa)
- `DELETE /api/v1/grids/{id}` — soft-delete (bloqueado si está activo)
- RBAC: POST/PUT/DELETE requieren Operator+; GET es público autenticado
- Estados de Grid: Draft → Active → Locked

**Application Services**
- `FloorPlanService` (`app/application/floor_plan_service.py`): upload con versioning, list_by_floor, get_active, soft_delete
- `GridService` (`app/application/grid_service.py`): generate, regenerate, activate, lock, unlock, update_walkable, soft_delete
- Generación de celdas: calcula rows/columns desde FloorPlan dimensions y cell_size
- Unicidad de celdas: row/column único por grid (restricción DB)
- Validación: walkable no modificable con campaña activa; grid no se puede borrar si está activo

**Persistence**
- ORM models: `FloorPlanModel`, `GridModel`, `CellModel` en `app/infrastructure/persistence/models.py`
- Mappers: `floor_plan_to_domain`, `grid_to_domain`, `cell_to_domain` en mappers.py
- Repos SQL: `SqlAlchemyFloorPlanRepository`, `SqlAlchemyGridRepository`, `SqlAlchemyCellRepository`
- Migración `20260727_0003_floorplan_grid_cell`: tablas floor_plans, grids, cells con FKs y unique constraints

**Dependencies & Router Registration**
- `get_floor_plan_service`, `get_grid_service` en `app/api/dependencies.py`
- Routers `floor_plans` y `grids` registrados en `app/main.py` y `tests/conftest.py`

**Tests de integración** (`tests/test_floor_plan_api.py`, `tests/test_grid_api.py`)
- 22 nuevos tests (8 FloorPlan + 14 Grid/Cell)
- 59 tests totales (15 domain/repos + 8 auth + 22 hierarchy + 8 floor plan + 6 grid)
- Cobertura: upload, versioning, list, get, delete (active/inactive), generate, regenerate, activate, lock/unlock, walkable update, constraints (one grid/floor, FloorPlan required, active grid protection)

### Fase 4 — Detalle de lo implementado

**Domain Entities**
- `Campaign` (`app/domain/entities/campaign.py`): state machine Draft→Ready→Collecting→Paused→Completed→Archived, `accepts_fingerprints` property, `transition_to` with audit timestamps
- `Fingerprint` (`app/domain/entities/fingerprint.py`): immutable after creation (version check), `observation_count` field
- `AccessPointObservation` (`app/domain/entities/access_point_observation.py`): RSSI -100..0 validation, frequency > 0, required bssid

**Campaign API** (`app/api/routers/campaigns.py`)
- `GET /api/v1/floors/{floor_id}/campaigns` — lista campañas de un Floor
- `GET /api/v1/campaigns/{id}` — obtiene una Campaign por ID
- `POST /api/v1/floors/{floor_id}/campaigns` — crea Campaign (Draft)
- `PATCH /api/v1/campaigns/{id}/start` — Draft → Ready
- `PATCH /api/v1/campaigns/{id}/begin-collecting` — Ready → Collecting (setea started_at)
- `PATCH /api/v1/campaigns/{id}/pause` — Collecting → Paused
- `PATCH /api/v1/campaigns/{id}/resume` — Paused → Collecting
- `PATCH /api/v1/campaigns/{id}/complete` — Collecting → Completed (setea finished_at)
- `PATCH /api/v1/campaigns/{id}/archive` — Completed → Archived
- `DELETE /api/v1/campaigns/{id}` — soft-delete (solo Draft o Archived)
- RBAC: POST/PATCH requieren Operator+; DELETE requiere Administrator

**Fingerprint API** (`app/api/routers/fingerprints.py`)
- `GET /api/v1/campaigns/{campaign_id}/fingerprints` — lista fingerprints de una Campaign
- `GET /api/v1/fingerprints/{id}` — obtiene Fingerprint con sus AccessPointObservations
- `POST /api/v1/campaigns/{campaign_id}/fingerprints` — crea Fingerprint con observaciones anidadas
- RBAC: POST requiere Operator+; GET es público autenticado
- Validaciones: campañas solo aceptan fingerprints en estado Collecting/Paused; se requiere al menos una observación; cell debe existir y estar activa

**Application Services**
- `CampaignService` (`app/application/campaign_service.py`): create, start, begin_collecting, pause, resume, complete, archive, soft_delete
- `FingerprintService` (`app/application/fingerprint_service.py`): create with nested observations, list_by_campaign, get_observations
- Campaign delete solo permitido en Draft o Archived

**Persistence**
- ORM models: `CampaignModel`, `FingerprintModel`, `AccessPointObservationModel` en `app/infrastructure/persistence/models.py`
- Mappers: `campaign_to_domain`, `fingerprint_to_domain`, `access_point_observation_to_domain` en mappers.py
- Repos SQL: `SqlAlchemyCampaignRepository`, `SqlAlchemyFingerprintRepository`, `SqlAlchemyAccessPointObservationRepository`
- Migración `20260727_0004_campaign_fingerprint_observation`: tablas campaigns, fingerprints, access_point_observations con FKs e índices

**Dependencies & Router Registration**
- `get_campaign_service`, `get_fingerprint_service` en `app/api/dependencies.py`
- Routers `campaigns` y `fingerprints` registrados en `app/main.py` y `tests/conftest.py`

**Tests de integración** (`tests/test_campaign_api.py`, `tests/test_fingerprint_api.py`)
- 15 nuevos tests (9 Campaign + 6 Fingerprint)
- 74 tests totales
- Cobertura: campaign CRUD, full lifecycle (Draft→Archived), invalid transitions, delete rules (Draft/Archived only), fingerprint create with observations, list fingerprints, get fingerprint with observations, empty observations rejected, non-collecting campaign rejected, fingerprint immutability

### Fase 5 — Detalle de lo implementado

**Domain Entities**
- `Dataset` (`app/domain/entities/dataset.py`): state machine Draft→Building→Ready→Archived, immutable after Ready, metadata: fingerprint_count, observation_count, floor_count
- `DatasetCampaign` (`app/domain/entities/dataset_campaign.py`): join entity linking Dataset to Campaign

**Dataset API** (`app/api/routers/datasets.py`)
- `GET /api/v1/datasets` — lista todos los datasets
- `GET /api/v1/datasets/{id}` — obtiene un Dataset por ID
- `POST /api/v1/datasets` — crea Dataset (Draft)
- `PATCH /api/v1/datasets/{id}/add-campaigns` — agrega campañas completadas al dataset
- `PATCH /api/v1/datasets/{id}/build` — transiciona Draft→Building→Ready, calcula metadata
- `PATCH /api/v1/datasets/{id}/archive` — transiciona Ready→Archived
- `DELETE /api/v1/datasets/{id}` — soft-delete (solo Draft o Archived)
- RBAC: POST/PATCH requieren Operator+; DELETE requiere Administrator
- Validaciones: solo campañas Completed pueden agregarse; no duplicados; dataset inmutable después de Ready

**Application Services**
- `DatasetService` (`app/application/dataset_service.py`): create, add_campaigns, build, archive, soft_delete
- Build: transiciona Draft→Building→Ready en una operación; calcula fingerprint_count y floor_count
- Add campaigns: valida Completed status, duplicados, y estado inmutable del Dataset

**Persistence**
- ORM models: `DatasetModel`, `DatasetCampaignModel` en `app/infrastructure/persistence/models.py`
- Mappers: `dataset_to_domain`, `dataset_campaign_to_domain` en mappers.py
- Repos SQL: `SqlAlchemyDatasetRepository`, `SqlAlchemyDatasetCampaignRepository`
- Migración `20260727_0005_dataset_dataset_campaign`: tablas datasets y dataset_campaigns con FKs y unique constraint

**Dependencies & Router Registration**
- `get_dataset_service` en `app/api/dependencies.py`
- Router `datasets` registrado en `app/main.py` y `tests/conftest.py`

**Tests de integración** (`tests/test_model_version_api.py`)
- 16 nuevos tests (create, list, get, list by floor, missing floor, mark ready, mark failed, invalid transition, publish, one published per floor, unpublish then publish new, archive ready, delete training, cannot delete published, cannot modify published, cannot modify archived)
- 103 tests totales
- Cobertura: model version CRUD, full lifecycle (Training→Failed/Ready→Published→Archived), state transition validation, one-published-per-floor enforcement, unpublish and re-publish flow, immutability (Published/Archived), delete rules

**Tests de integración** (`tests/test_user_api.py`, `tests/test_inference_api.py`)
- 16 nuevos tests (11 Users + 5 Inference)
- 119 tests totales
- Cobertura: user CRUD (list, get, create, duplicate, role, password, deactivate, activate, delete, admin protection, RBAC), inference (position estimation, no model, no observations, no match, auth required)

### Fase 11 — Detalle de lo implementado

**Domain Entity Edge-Case Tests** (`tests/test_core_domain.py`)
- Expansión de 5 tests a **55 tests** cubriendo todos los entities: Organization, Site, Building, Floor, FloorPlan, Grid, Cell, Campaign, Dataset, ModelVersion, AccessPointObservation, User, SoftDelete
- Cobertura: boundary values (RSSI -100..0, width/height/scale > 0), invalid inputs (bools en campos int, empty strings, whitespace-only), state-machine transitions (full lifecycle + invalid transitions), optional fields (description, address, metadata, organization_id)

**Service-Layer Unit Tests** (fake repositories, sin DB, rápidos)
- `test_floor_plan_service.py` (14 tests): CRUD, upload checksum/version/deactivate, soft delete rules (activo no borrable)
- `test_grid_service.py` (21 tests): CRUD, generate cell creation, regenerate, lock/unlock/activate, walkable updates, soft delete (activo no borrable, celdas en cascada)
- `test_user_service.py` (14 tests): CRUD, role/password updates, duplicate email (BusinessRuleViolation), activate/deactivate, soft delete admin protection
- `test_auth_service.py` (8 tests): ensure_initial_administrator (creates, exists, missing env vars), authenticate (success, wrong password, missing email, inactive user, deleted user)
- `test_inference_service.py` (9 tests): estimate_position success, empty observations error, no published model error, no fingerprints error, predicted cell not found, confidence=1 when all match same cell, model_version_id in result, top-5 candidates, inference_time_ms set

**Total: 161 tests de Fase 11**
- 50 domain entity (expansión)
- 14 floor_plan_service
- 21 grid_service
- 14 user_service
- 8 auth_service
- 9 inference_service

### Fase 12 — Detalle de lo implementado

**Scaffolding del proyecto** (`admin-portal/`)
- React 19 + TypeScript + Vite (template `react-ts`)
- Dependencias: `react-router-dom` (routing), `zustand` (estado UI)
- Directorios por capa: `pages/`, `features/`, `components/`, `hooks/`, `services/`, `stores/`, `utils/`, `types/`

**Infraestructura base**
- `types/index.ts` — interfaces TypeScript para todas las entidades del dominio (User, Organization, Site, Building, Floor, FloorPlan, Grid, Cell, Campaign, Dataset, ModelVersion, Fingerprint, AccessPointObservation) + ApiEnvelope genérico
- `services/api.ts` — API client con fetch nativo, auto-refresh de JWT en 401, métodos get/post/put/patch/delete/upload/login
- `stores/authStore.ts` — Zustand store: login, logout, user state
- `hooks/useAuth.ts` — hook de autenticación con helpers `isAuthenticated`, `isAdmin`, `isOperator`
- `hooks/useCrud.ts` — hook genérico CRUD con tipado (list, get, create, update, remove)
- `utils/format.ts` — formatDate, formatStatus

**Routing** (`App.tsx`)
- 12 rutas protegidas dentro de `<AppShell />` + ruta pública `/auth` + catch-all 404
- `ProtectedRoute` redirige a `/auth` si no autenticado; `PublicRoute` redirige a `/dashboard` si ya autenticado

**Layout**
- `AppShell` — sidebar + main content area (`<Outlet />`)
- `SideMenu` — navegación lateral con 10 enlaces + user email + logout button

**Shared Components** (12 componentes)
- `DataTable` — tabla genérica con columnas configurables, render personalizado, row click
- `Modal` — overlay modal con cierre por Escape/click fuera
- `ConfirmationDialog` — modal de confirmación con acción danger
- `Toast` — notificación auto-dismiss (4s) con tipos success/error/info
- `Pagination` — navegación de páginas (anterior/siguiente)
- `SearchBox` — input de búsqueda
- `Breadcrumb` — migas de pan con links
- `LoadingOverlay` — spinner de carga
- `ErrorView` — mensaje de error con botón retry

**Pages** (12 páginas)
- `LoginPage` — formulario de login con email+password, muestra errores
- `DashboardPage` — stats grid con conteos de todas las entidades
- `OrganizationListPage` — CRUD completo (list, create, edit, delete) con filtro de búsqueda
- `SiteListPage` — CRUD filtrado por `org_id` query param, breadcrumb jerárquico
- `BuildingListPage` — CRUD filtrado por `site_id`, breadcrumb jerárquico
- `FloorListPage` — CRUD filtrado por `building_id`, breadcrumb jerárquico
- `CampaignListPage` — listado con state machine (start, begin-collecting, pause, resume, complete, archive)
- `DatasetListPage` — listado con build/archive actions
- `GridListPage` — listado con generate, activate, lock, unlock, regenerate
- `ModelListPage` — listado con train, publish, unpublish, archive, delete actions
- `SettingsPage` — info de usuario y rol
- `NotFoundPage` — 404 con link al dashboard

**Verificación**
- `npm run build` — compilación exitosa (54 módulos, 271 KB JS + 0.74 KB CSS)
- `python -m pytest tests/...` — 188 tests backend continúan pasando
- Backend Ruff: All checks passed

### Fase 13 — Detalle de lo implementado

**Estructura del proyecto** (`android/`)
- Proyecto Gradle multi-módulo (Kotlin 2.1 + AGP 8.8 + Compose BOM 2025.04)
- `:shared` — módulo de librería con modelos, API client, Room DB, sync engine
- `:capture-app` — módulo de aplicación Capture App

**Shared module** (`:shared`)
- `model/Models.kt` — 18 data classes con serialización Gson (`@SerializedName` para snake_case): Organization, Site, Building, Floor, FloorPlan, Grid, Cell, Campaign, FingerprintRequest/Response, ObservationRequest/Response, LoginRequest/Response, RefreshRequest, TokenResponse, ApiEnvelope, PaginatedResponse
- `api/ApiService.kt` — Retrofit interface con 18 endpoints: login, refresh, list jerarquía, floor-plans, grids, cells, campaigns, campaign transitions (begin-collecting, pause, resume, complete), fingerprints CRUD
- `api/TokenInterceptor.kt` — OkHttp Interceptor con auto-refresh de JWT en 401 (thread-safe con `synchronized`)
- `api/ApiClient.kt` — Singleton de configuración Retrofit + OkHttp con logging, timeouts 15/30/30s
- `local/AppDatabase.kt` — Room database con entidad `PendingFingerprintEntity` (campaign_id, cell_id, device_id, captured_at, observations_json, status, retry_count, next_retry_at) y DAO completo (insert, update, markCompleted, markFailed, markUploading, deleteCompleted, queries por estado)
- `sync/SyncManager.kt` — sync queue offline-first: enqueue, upload con retry exponencial (5 máx, base 30s), manejo de 409/422 (descarta), estados Pending→Uploading→Completed/Failed
- `sync/SyncWorker.kt` — WorkManager CoroutineWorker con constraints de red, backoff exponencial, periodic cada 15 min; función helper `AppDatabase.getInstance(context)`

**Capture App** (`:capture-app`)

Arquitectura:
- Hilt DI (`@HiltAndroidApp`, `@AndroidEntryPoint`, `AppModule` con providers para AppDatabase, DAO, SyncManager)
- MVVM + Jetpack Compose + Navigation Compose

10 pantallas (Composables):
1. **LoginScreen** — server URL, email, password; inicializa ApiClient, login con JWT, navega a Organizations
2. **OrganizationSelectionScreen** — GET /organizations, LazyColumn con Cards
3. **SiteSelectionScreen** — GET /sites filtrado por orgId (PickerScreen reutilizable)
4. **BuildingSelectionScreen** — GET /buildings filtrado por siteId
5. **FloorSelectionScreen** — GET /floors filtrado por buildingId
6. **CampaignSelectionScreen** — GET /floors/{floorId}/campaigns, solo muestra Collecting/Paused; mensaje si no hay disponibles
7. **CellSelectionScreen** — GET grids activo + cells walkable; LazyVerticalGrid con celdas (row,col)
8. **CaptureScreen** — WiFi scan (WifiManager.startScan), muestra APs detectados (BSSID, SSID, RSSI, frequency), botón Save Offline → enqueue a Room + SyncManager
9. **ReviewScreen** — confirmación, muestra pending/completed count, opciones Capture Another / Done
10. **SyncStatusScreen** — lista fingerprints con estado (Pending/Uploading/Completed/Failed), botón Sync Now (Schedule WorkManager), iconos por estado

Navigation:
- `NavRoutes.kt` — 10 rutas con argumentos tipados (orgId, siteId, buildingId, floorId, campaignId, cellId, fingerprintId)
- `NavGraph.kt` — NavHost con 10 composable destinations, popUpTo en login y done

Componentes compartidos:
- `PickerScreen` — composable reutilizable con título, loading, error, retry, LazyColumn de Cards
- `CaptureAppTheme` — Material3 con color scheme azul (#2563EB)

Permisos (AndroidManifest): INTERNET, ACCESS_FINE_LOCATION, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE, ACCESS_NETWORK_STATE, POST_NOTIFICATIONS

Backend sin cambios — consume todos los endpoints existentes (auth, hierarchy, floor-plans, grids, cells, campaigns, fingerprints).

**Verificación**
- Backend Ruff: All checks passed
- Backend tests: 188 tests continúan pasando sin regresiones

### Fase 14 — Detalle de lo implementado

**User App** (`android/user-app/`)

Estructura del módulo:
- `build.gradle.kts` — Compose, Hilt, KSP, dependencias comparteidas (`:shared`)
- `proguard-rules.pro` — reglas para modelos Gson/Room
- `AndroidManifest.xml` — permisos WiFi, location, internet, notificaciones

Punto de entrada:
- `InternavUserApp.kt` — `@HiltAndroidApp` + `Configuration.Provider` para WorkManager con `HiltWorkerFactory`
- `MainActivity.kt` — `@AndroidEntryPoint` + Compose + `UserNavGraph`

DI (`di/AppModule.kt`):
- Provider para `AppDatabase` (Room, `internav_user_db`, `fallbackToDestructiveMigration`)
- Providers para DAOs (`CachedModelDao`, `CachedCellDao`)

Navegación (`navigation/`):
- `NavRoutes.kt` — 6 rutas: login, organizations, sites/{orgId}, buildings/{siteId}, floors/{buildingId}, positioning/{floorId}
- `NavGraph.kt` — NavHost con `popUpTo` en login, paso de argumentos tipados

Theme (`ui/theme/Theme.kt`):
- Material3 `lightColorScheme` con primary verde (#16A34A)

6 pantallas (Composables):
1. **LoginScreen** — email+password, loading, error, botón Sign In
2. **OrganizationSelectionScreen** — `@HiltViewModel` + LazyColumn de Cards, loading/error/empty states
3. **SiteSelectionScreen** — filtrado por orgId, loading/error/empty states
4. **BuildingSelectionScreen** — filtrado por siteId
5. **FloorSelectionScreen** — filtrado por buildingId
6. **PositioningScreen** — la más compleja: card con posición (cell, centro, confianza con color), Canvas con grid overlay (walkable/predicted cells), lista de APs escaneados

6 ViewModels:
- **LoginViewModel** — llama `ApiClient.getPublicService().login()`, almacena tokens via `ApiClient.tokenManager.updateTokens()`
- **OrganizationSelectionViewModel** — GET /organizations
- **SiteSelectionViewModel** — GET /sites?organization_id=
- **BuildingSelectionViewModel** — GET /buildings?site_id=
- **FloorSelectionViewModel** — GET /floors?building_id=
- **PositioningViewModel** — inicializa floor/grids/cells, carga modelo cacheado (Room) o vía API, build `InferenceEngine`, `startScanning()` lanza loop cada 2s con `WifiManager.scanResults`, `estimatePosition` cada scan

**Shared module** (`android/shared/`)

Modelos nuevos (`model/Models.kt`):
- `ModelUpdateResponse`, `ModelInfo`, `ModelResponse` — modelos de actualización
- `InferenceRequest`, `InferenceObservation`, `InferenceResponse`, `CandidateCell` — inferencia online
- `FeatureSchema` — esquema de features para el engine offline

Inference Engine (`inference/InferenceEngine.kt`):
- `InferenceEngine` — implementación nativa Kotlin de KNN con distancia euclidiana
- `ReferenceVector` — vector de referencia por celda (cellId, centerX, centerY, DoubleArray)
- `RssiObservation` — observación simple (bssid, rssi)
- `InferenceResult` — resultado (predictedCellId, centerX, centerY, confidence, candidates, time)
- Algoritmo: buildFeatureVector con normalización RSSI [0,1], euclideanDistance, top-K weighted voting, confidence = best_score / total_score
- Fallback: devuelve resultado vacío si no hay observaciones o referencias

Room cache (`local/AppDatabase.kt`):
- `CachedModelEntity` — tabla `cached_models`, PK floor_id, campos model_id/version/algorithm/checksum/paths/cellsJson
- `CachedCellEntity` — tabla `cached_cells`, PK id, campos grid/row/col/center_x/center_y/walkable/floor_id
- `CachedModelDao` — getModelForFloor, insertOrUpdate, deleteModelForFloor, getAllCachedModels
- `CachedCellDao` — getCellsForFloor, insertAll, deleteCellsForFloor
- `AppDatabase` versión 2 con las 3 entidades + DAOs

API endpoints nuevos (`api/ApiService.kt`):
- `GET /api/v1/floors/{floorId}` — getFloor
- `GET /api/v1/models/{modelId}` — getModel
- `listSites(orgId)`, `listBuildings(siteId)`, `listFloors(buildingId)` — query params opcionales (backward-compatible)

### Fixes de setup

**1. setuptools flat-layout**

`pip install -e .` fallaba con `"Multiple top-level packages discovered in a flat-layout: ['app', 'models', 'migrations']"`.

Solución: agregar `[build-system]` + `[tool.setuptools.packages.find]` con `include = ["app", "app.*"]`.

**2. Python 3.14 incompatible con ML stack**

`OverflowError: cannot convert longdouble infinity to integer` al importar numpy (aún 1.26.4) dentro de joblib en Windows. El bug es de numpy/scipy con Python 3.14, no se arregla con pinning.

Soluciones:
- `requires-python = ">=3.11,<3.13"` en `pyproject.toml`
- `numpy>=1.26,<2.3` — piso 1.26, techo <2.3 para evitar numpy 2.5+ (misma incompatibilidad)
- Se creó `backend/README.md` con instrucciones de setup que usan `py -3.12 -m venv`
- `AGENTS.md` documenta la advertencia y el comando exacto
- Revisión del resto de dependencias: rangos correctos (FastAPI, SQLAlchemy, alembic, bcrypt, joblib, pytest, ruff, mypy, httpx tienen upper bounds o son estables). Ninguna otra dependencia tiene rangos peligrosos.

### Fase 15 — Detalle de lo implementado

**CI/CD (GitHub Actions)**
- `.github/workflows/backend.yml` — lint (ruff check + format) + test (pytest --timeout=60) en Python 3.12
- `.github/workflows/admin-portal.yml` — lint (oxlint + prettier) + build (npm ci + npm run build) en Node 22
- `.github/workflows/android.yml` — lint (ktlintCheck + lint) + build (assembleDebug) con Gradle

**Code Quality (Admin Portal)**
- `.prettierrc` — configuración Prettier (semi, singleQuote, trailingComma, printWidth 100)
- CI valida formato con `npx prettier --check .`

**Deployment (Backend)**
- `backend/Dockerfile` — imagen Python 3.12-slim, instala el paquete, expone puerto 8000
- `backend/.dockerignore` — excluye .venv, __pycache__, .env, *.db, data/
- `docker-compose.yml` — servicio backend con build, ports, env_file, volúmenes data/models

**Seguridad (Backend)**
- `app/infrastructure/security/middleware.py` — `SecurityHeadersMiddleware` ASGI nativa (sin Starlette BaseHTTPMiddleware) que agrega:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 0`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- Registrada en `create_app()` después de CORS, TraceID y RequestLog middlewares

**Performance Testing Infrastructure**
- `pytest-timeout>=2.3` como dependencia dev
- Marcadores pytest: `integration` y `performance` configurados en `pyproject.toml`
- Tests se pueden filtrar: `-m "not integration"` para unit tests rápidos

**Changelog**
- `CHANGELOG.md` con entrada para v0.1.0

**Android**
- `.editorconfig` en `android/` con reglas para *.kt, *.xml, *.yml

**pyproject.toml**
- Migrado `[dependency-groups]` → `[project.optional-dependencies]` para compatibilidad con `pip install -e ".[dev]"`

**Verificación**
- Ruff: All checks passed
- Tests de integración (16) pasan con el nuevo middleware de seguridad

## Verificaciones realizadas

- `python -m ruff check app/ tests/`: All checks passed (con `--fix`).
- `python -m mypy app`: errores preexistentes en `core_hierarchy_service.py` (31) + empty-body en repos Protocol + structural subtyping en dependencies. Código nuevo sin errores únicos.
- Migraciones previas verificadas.
- **313 tests totales** (172 pre-existentes + 25 Fase 10 + 116 Fase 11).
- Todos los tests existentes (Fase 1-10) continúan pasando sin regresiones.

## Nota sobre datos de entrenamiento

**Importante:** Todos los datos utilizados para probar el training pipeline (Fase 8) son exclusivamente sintéticos, generados dentro de `tests/`. Las métricas reportadas por el modelo (accuracy, etc.) corresponden únicamente a estos datos de prueba sintéticos y **no representan validación productiva**. El modelo no ha sido entrenado ni evaluado con datos reales provenientes de campañas de campo. Esta nota se mantendrá hasta que se ejecute una validación con datos de producción reales.

## Decisiones de implementación documentadas

- Login por email (nunca username) — `spec/26_AUTHORIZATION.md`
- Admin inicial bootstrap desde `.env` (`ADMIN_EMAIL`, `ADMIN_PASSWORD`)
- Admin inicial puede existir sin Organization asignada
- RBAC MVP: Administrator (full), Operator (no delete), Viewer (read only)
- Contraseñas hasheadas con bcrypt, nunca en texto plano
- FloorPlan versioning: `fp_version` separado de `AuditableEntity.version` para evitar colisiones con `touch()`
- Grid state machine: Draft → Active → Locked; unlock restaura a Active (desde Locked) o Draft (desde Active)
- Un solo Grid por Floor (no solo activos): simplify la lógica de negocio evitando grids huérfanos
- Soft-delete de FloorPlan bypassa `touch()` para no incrementar `fp_version`
- Campaign state machine: Draft→Ready→Collecting→Paused→Completed→Archived (spec 35/17)
- Campaign delete solo en Draft o Archived (consistencia con estados finales)
- Fingerprint immutable after creation: check via version > 1 (created_at/updated_at are unreliable due to utc_now() called twice)
- Fingerprint requires ≥1 AccessPointObservation (spec 18/36)
- Fingerprint only accepts when Campaign is Collecting or Paused (spec 36)
- BSSID/SSID can be empty strings at domain level; API schemas can enforce stricter validation later
- Observation nested creation: fingerprints endpoint accepts `observations` array in request body
- Dataset state machine: Draft→Building→Ready→Archived (spec 38)
- Dataset is immutable after Ready (BR-005): add_campaigns blocked in Ready/Archived
- Dataset build: transitions Draft→Building→Ready in one operation
- Only Completed campaigns can be added to a Dataset
- No duplicate campaigns in a Dataset (unique constraint + domain check)
- Dataset delete only in Draft or Archived (same pattern as Campaign)
- Dataset metadata (fingerprint_count, floor_count) calculated from linked campaigns at build time
- ModelVersion ORM column `model_version` avoids collision with `AuditColumns.version` (same pattern as FloorPlan's `fp_version`)
- ModelVersion.floor_id stored alongside dataset_id for efficient "one published per floor" queries
- ModelVersion.publish enforces BR-004 via repository `has_published_on_floor` check
- ModelVersion.unpublish (Published→Archived) enables re-publishing a different model on the same floor
- Users API: Administrator-only for all user management operations (CRUD, role, password, activate/deactivate)
- Cannot delete Administrator users (BusinessRuleViolation)
- User email uniqueness enforced at service level (not DB constraint)
- Inference: RSSI similarity matching — for each fingerprint, compute sum of (1 - |query_rssi - fp_rssi|/100) per matching BSSID; rank cells by aggregated score
- Inference returns cell predictions, never coordinates; coordinates resolved from Cell metadata (center_x, center_y)
- Inference confidence: best_score / total_score across all matching cells
- FingerprintRepository.list_by_floor() joins with Campaigns table to filter by floor

### Fase 6 — Detalle de lo implementado

**Domain Entity**
- `ModelVersion` (`app/domain/entities/model_version.py`): state machine Training→Failed/Ready→Published→Archived, immutable after Published/Archived, `published_at` timestamp on publish
- States: Training, Failed, Ready, Published, Archived
- Fields: dataset_id, floor_id, algorithm, version, hyperparameters, metrics, training_time, checksum, published_at

**Business Rules Enforced**
- BR-004: Only one Published model per floor (enforced in publish via repository query)
- BR-006: Model versions are immutable after Published/Archived
- Algorithm is required (spec 18)

**Model API** (`app/api/routers/models.py`)
- `GET /api/v1/models` — lista todos los modelos
- `GET /api/v1/models/{id}` — obtiene un ModelVersion por ID
- `GET /api/v1/floors/{floor_id}/models` — lista modelos por Floor
- `POST /api/v1/models` — crea ModelVersion (Training)
- `PATCH /api/v1/models/{id}/mark-ready` — Training→Ready (con metrics, training_time, checksum)
- `PATCH /api/v1/models/{id}/mark-failed` — Training→Failed
- `PATCH /api/v1/models/{id}/publish` — Ready→Published (BR-004 enforced)
- `PATCH /api/v1/models/{id}/unpublish` — Published→Archived (permite publicar otro en el mismo Floor)
- `PATCH /api/v1/models/{id}/archive` — Ready/Published→Archived
- `DELETE /api/v1/models/{id}` — soft-delete (solo Training o Failed)
- RBAC: POST/PATCH requieren Operator+; DELETE y unpublish requieren Administrator

**Application Services**
- `ModelVersionService` (`app/application/model_version_service.py`): create, list_all, list_by_floor, list_by_dataset, mark_ready, mark_failed, publish, unpublish, archive, soft_delete
- Publish validation: only Ready→Published allowed; one published per floor enforced
- Immutability: blocked state transitions on Published/Archived

**Persistence**
- ORM: `ModelVersionModel` en `app/infrastructure/persistence/models.py` — column `model_version` (no colisiona con `AuditColumns.version`)
- Mapper: `model_version_to_domain` en mappers.py
- Repo: `SqlAlchemyModelVersionRepository` con `list_by_floor`, `list_by_dataset`, `has_published_on_floor`, `get_published_on_floor`
- Migración `20260727_0006_model_version`: tabla model_versions con FKs a datasets y floors, índices

**Dependencies & Router Registration**
- `get_model_version_service` en `app/api/dependencies.py`
- Router `models` registrado en `app/main.py` y `tests/conftest.py`

### Fase 7 — Detalle de lo implementado

#### 7A: Users API

**Application Service**
- `UserService` (`app/application/user_service.py`): list_all, get, create, update_role, update_password, deactivate, activate, soft_delete
- Validación: email único (BusinessRuleViolation), no se puede eliminar Administrator

**Users API** (`app/api/routers/users.py`)
- `GET /api/v1/users` — lista todos los usuarios
- `GET /api/v1/users/{id}` — obtiene un User por ID
- `POST /api/v1/users` — crea usuario (email, password, role, organization_id)
- `PATCH /api/v1/users/{id}/role` — actualiza rol
- `PATCH /api/v1/users/{id}/password` — actualiza contraseña
- `PATCH /api/v1/users/{id}/deactivate` — desactiva usuario
- `PATCH /api/v1/users/{id}/activate` — activa usuario
- `DELETE /api/v1/users/{id}` — soft-delete (no Administrator)
- RBAC: todos los endpoints requieren Administrator

**Persistence**
- `SqlAlchemyUserRepository.list_all()` añadido (ya existía el repo)
- `UserRepository.list_all()` añadido a la interfaz Protocol

**Tests** (`tests/test_user_api.py`)
- 11 tests: list, get, create, duplicate rejected, update role, update password, deactivate, activate, delete, cannot delete admin, requires admin role

#### 7B: Inference API

**Application Service**
- `InferenceService` (`app/application/inference_service.py`): estimate_position
- Algoritmo: similarity basada en RSSI matching (1 - |diff_rssi|/100) por BSSID
- Retorna: predicted_cell, center_x/y, confidence, candidate_cells (top 5), model_version_id, inference_time_ms
- Valida: observaciones ≥ 1, modelo Published en el Floor, fingerprints existentes

**Inference API** (`app/api/routers/inference.py`)
- `POST /api/v1/inference` — estima posición (floor_id + observations[])
- Input: `{floor_id, observations: [{bssid, ssid, rssi, frequency}]}`
- Output: `{predicted_cell_id, center_x, center_y, confidence, candidate_cells[], model_version_id, inference_time_ms}`
- RBAC: Operator+ (Administrator, Operator)
- La predicción retorna celdas, nunca coordenadas; coordenadas se resuelven desde Cell metadata

**Persistence**
- `FingerprintRepository.list_by_floor()` añadido (join con campaigns por floor_id)
- `SqlAlchemyFingerprintRepository.list_by_floor()` implementado

**Dependencies & Router Registration**
- `get_user_service`, `get_inference_service` en `app/api/dependencies.py`
- Routers `users` e `inference` registrados en `app/main.py` y `tests/conftest.py`

**Tests** (`tests/test_inference_api.py`)
- 5 tests: estimate position (match exitoso), no model, no observations, no match, requires auth

### Fase 8 — Detalle de lo implementado

**AI Layer** (`app/ai/`)
- `knn_model.py`: `KNNTrainer` — feature matrix building con normalización RSSI, entrenamiento KNN, predicción con confidence scores
- `evaluation.py`: `compute_metrics` — accuracy, macro F1, per-class precision/recall/F1, confusion matrix, top-3 accuracy, mean inference time
- `serialization.py`: `ModelArtifactStorage` — guarda/carga model.bin, metadata.json, feature_schema.json; checksum SHA-256
- `dataset_export.py`: `DatasetExportService` — exporta Dataset a formato training-ready (samples con observaciones + bssid_vocabulary)
- `training_pipeline.py`: `TrainingPipelineService` — orquesta el pipeline completo

**Training Pipeline** (`TrainingPipelineService.train()`)
- Dataset export → feature engineering → train/validation split (80/20, fallback full data si <5 samples) → KNN training → evaluación en validation set → serialización de artefactos → transición a Ready
- Feature engineering: normaliza BSSID, remueve duplicados, maneja APs faltantes (default 0), vectoriza observaciones, normaliza RSSI a [0,1]
- Metrics almacenadas: accuracy, macro_f1, top_3_accuracy, mean_inference_time_ms, per_class (precision, recall, f1_score), confusion matrix
- Artefactos: model.bin (joblib), metadata.json, feature_schema.json
- Eventos publicados: `TrainingStarted`, `ModelReady`

**API Endpoints** (`app/api/routers/models.py`)
- `POST /api/v1/models/{id}/train` — ejecuta training pipeline (200 OK, transiciona a Ready)
- `GET /api/v1/models/{id}/download` — descarga model.bin como application/octet-stream
- `ModelVersionService.train()` ya existente delega al `TrainingPipelineService`

**Dependencies** (`app/api/dependencies.py`)
- `get_training_pipeline_service()`: crea `TrainingPipelineService` con repositorios, `DatasetExportService` y `ModelArtifactStorage`
- `get_model_version_service()`: recibe `training_pipeline` opcional (inyectado en producción)

**Tests**
- `test_knn_model.py` (9 tests): build_feature_matrix shape/normalización/missing APs/empty, train con múltiples/single clase, predict labels/confidences/error antes de train
- `test_evaluation.py` (11 tests): top_k_accuracy perfecto/parcial/vacío, compute_metrics perfecto/sin matches/single class/top-3/inference time/empty/per-class
- `test_serialization.py` (9 tests): save/load model.bin + metadata + checksum + feature_schema, get_artifact_paths, delete_model
- `test_training_pipeline.py` (4 tests): train exitoso + metrics JSON parseable, 404 en modelo inexistente, download after train, RBAC sin auth
- Total: 33 tests nuevos

**Verificación**
- `python -m ruff check app/ tests/`: All checks passed
- 33 nuevos tests aprobados (4 unit test suites + 1 integration test suite)

### Fase 10 — Detalle de lo implementado

**Domain Events** (`app/domain/events.py`)
- `EventType` ya definía todos los tipos (9 en total: ORGANIZATION_CREATED, CAMPAIGN_STARTED, FINGERPRINT_CAPTURED, DATASET_BUILT, TRAINING_STARTED, TRAINING_COMPLETED, MODEL_READY, MODEL_PUBLISHED, MODEL_DOWNLOADED, INFERENCE_EXECUTED)
- Se agregó `TRAINING_COMPLETED` como nuevo tipo de evento

**Event Publications desde servicios:**
- `CoreHierarchyService.create_organization()` → publica `ORGANIZATION_CREATED` después de crear
- `CampaignService.begin_collecting()` → publica `CAMPAIGN_STARTED` al comenzar recolección
- `FingerprintService.create()` → publica `FINGERPRINT_CAPTURED` después de cada fingerprint
- `DatasetService.build()` → publica `DATASET_BUILT` después de construir el dataset
- `ModelVersionService.publish()` → publica `MODEL_PUBLISHED` después de publicar un modelo
- `TrainingPipelineService.train()` → publica `TRAINING_COMPLETED` adicional (ya tenía TRAINING_STARTED y MODEL_READY)

**Event Publications desde API routers:**
- `models.py` download endpoint → publica `MODEL_DOWNLOADED` al descargar modelo
- `inference.py` estimate_position endpoint → publica `INFERENCE_EXECUTED` después de inferencia

**Audit Event Listeners** (`app/infrastructure/events/audit_listeners.py`)
- `subscribe_audit_listeners()` suscribe audit log listeners para los 10 EventTypes
- Cada listener escribe al logger `audit.events` con información relevante del evento
- Se llama durante el lifespan de la aplicación en `main.py`

**ModelUpdateService** (`app/application/model_update_service.py`)
- `check_for_update(floor_id, current_model_version_id)` → retorna `{update_available, model}` con el último modelo publicado
- `get_published_model(floor_id)` → retorna el ModelVersion publicado o None
- Valida que el Floor exista (LookupError si no)
- Si el `current_model_version_id` coincide con el publicado, retorna `update_available: false`

**API Endpoint** (`app/api/routers/models.py`)
- `GET /api/v1/floors/{floor_id}/model-update` — verifica si hay un modelo nuevo disponible para un Floor
- RBAC: Operator+ (Administrator, Operator)
- Retorna `{update_available, model: {id, version, algorithm, checksum, published_at}}`

**Dependency** (`app/api/dependencies.py`)
- `get_model_update_service()`: crea ModelUpdateService con repositorios

**Tests** (`tests/test_domain_events.py`)
- 6 tests de publicación de eventos: organization_created, campaign_started, fingerprint_captured, dataset_built, model_published, multiple listeners
- 6 tests de ModelUpdateService: no published, returns update, current version matches, missing floor, get_published none, get_published returns
- 10 tests de audit listeners: subscribe wires all, cada tipo de evento genera audit log
- 3 tests de integración API: returns no update, returns update when published, requiere auth
- Total: 25 tests nuevos

**Verificación**
- `python -m ruff check app/ tests/`: All checks passed
- 25 nuevos tests aprobados (25/25)
- Tests existentes no afectados (publish, inference, campaign API tests pasan)

### Fase 9 — Detalle de lo implementado

**Configuration Management** (`app/config/settings.py`)
- Validación de `APP_ENV`: solo acepta `development`, `testing`, `production` — caso inválido lanza `ConfigurationError`
- Validación en producción: `JWT_SECRET_KEY` no puede ser el valor por defecto (`development-only-change-me`)
- `Settings` es frozen dataclass (inmutable)
- `.env.example` actualizado con `MODEL_STORAGE_PATH`

**Logging System** (`app/infrastructure/log/`)
- `setup.py`: `setup_logging(level)` configura logging root con formato `[%(trace_id)s]`, `TraceIDFilter` para inyectar trace_id en cada record, `get_audit_logger()` crea logger separado con prefijo `audit.` y sin propagación
- `middleware.py`: `TraceIDMiddleware` — asigna/genera `X-Trace-ID` por request, lo inyecta en el filtro global y lo devuelve en response headers; `RequestLogMiddleware` — logea método, path, status y duración de cada request
- `setup_logging()` llamado en `lifespan` de FastAPI con level según entorno

**Integración en servicios clave**
- `app/main.py`: `logger.critical` en error de configuración, audit log de startup/shutdown, middlewares registrados (TraceIDMiddleware, RequestLogMiddleware)
- `app/ai/training_pipeline.py` (`app.training`): logging de inicio y fin de training con accuracy y duración
- `app/application/inference_service.py` (`app.inference`): logging de inferencia con cell_id, confidence y duración; warning cuando no hay modelo publicado
- `app/application/auth_service.py` (`app.auth`): logging de login exitoso y fallido (con causa)

**Tests**
- `test_config.py` (9 tests): Settings default, env vars, entorno inválido, producción sin secret custom, env_file loading, frozen, VALID_ENVIRONMENTS
- `test_logging.py` (11 tests): TraceIDFilter (default, existing, global), get/set trace_id, setup_logging (level, handler), audit_logger, TraceIDMiddleware (generación y paso de trace_id)
- Total: 20 tests nuevos → 172 tests totales

**Verificación**
- `python -m ruff check app/ tests/`: All checks passed
- 20 nuevos tests aprobados

## Dockerización y cambios recientes (30 Jul 2026)

### JSON parse fix — endpoints devuelven array plano

**Problema:** Android esperaba `data` como `List<T>` pero los endpoints de listado devolvían `{items, total, page, page_size}`.

**Cambios en `backend/app/api/routers/hierarchy.py`:**
- `list_organizations`, `list_sites`, `list_buildings`, `list_floors` — cambiados de `success(data=_paginate(items, query))` a `success(data=[_entity_to_dict(i) for i in items])`
- `PageQuery` dependency removida de esos 4 endpoints
- El endpoint `list_campaigns` ya devolvía array plano

**Tests actualizados** (`tests/test_hierarchy_api.py`): 4 assertions cambiadas de `data["total"]` a `len(data)`.

### APK download endpoint

**Nuevo archivo:** `backend/app/api/routers/apk.py`
- `GET /apk` — sirve `capture-app-debug.apk` como descarga
- `GET /api/v1/health` — health check para Docker
- Path del APK configurable vía `APK_PATH` env var (default `/apk/capture-app-debug.apk`)

### Admin portal servido desde el backend

**Cambio en `backend/app/main.py`:**
- Se agregó `SPAStaticFiles` (subclase de `StaticFiles` con fallback a `index.html`) montado en `/`
- Se activa solo si `SERVE_ADMIN_PORTAL=true` y el directorio `/app/admin-portal-dist` existe
- Todas las rutas API (`/api/v1/*`) tienen prioridad sobre los archivos estáticos

**Cambio en `admin-portal/vite.config.ts`:**
- Ahora usa `defineConfig` con función para leer `VITE_API_PROXY_TARGET` del entorno
- En Docker, apunta a `http://backend:8000`

**Nuevo archivo:** `admin-portal/nginx.conf` — proxy reverso para producción

**Nuevo archivo:** `admin-portal/.dockerignore`

### Dockerfiles

**`backend/Dockerfile`** — multi-stage:
- `base`: python:3.12-slim, pip install con `.[dev]` + uvicorn added to pyproject.toml, COPY migrations/ y alembic.ini
- `development`: CMD con `--reload`
- `production`: CMD sin reload

**`admin-portal/Dockerfile`** — multi-stage:
- `build`: node:22-alpine, npm ci, npm run build
- `production`: nginx:alpine, sirve dist/
- `development`: node:22-alpine, npm run dev -- --host 0.0.0.0

### docker-compose.yml

- Backend con bind mounts para hot-reload + volumen APK + `SERVE_ADMIN_PORTAL=true`
- Frontend con bind mounts para HMR + `VITE_API_PROXY_TARGET=http://backend:8000`
- Volumen `./admin-portal/dist:/app/admin-portal-dist:ro` para servir admin portal desde backend

### Datos de prueba creados

Vía `POST /api/v1/...`:
1. Organization: **HSR**
2. Site: **Sotero** (bajo HSR)
3. Building: **Informatica** (bajo Sotero)
4. Floor: **Piso 2** (level 2, bajo Informatica)
5. Campaign: **Primera campanya** (bajo Piso 2)

### URLs accesibles

| Servicio | URL | Desde PC | Desde celular |
|---|---|---|---|
| Backend API | `http://localhost:8000` | ✅ | ❌ |
| Admin Portal | `http://localhost:8000/` | ✅ | ❌ |
| APK download | `http://localhost:8000/apk` | ✅ | ❌ |
| Via ngrok | `https://gear-glowing-unwary.ngrok-free.dev` | ✅ | ✅ |

### Flujo de trabajo

```bash
# Después de cambios en código (sin nuevas dependencias)
# bind mounts + --reload reflejan cambios automáticamente

# Después de nuevas dependencias o cambios en Dockerfile
docker-compose up -d --build

# Para nueva APK
cd android
./gradlew :capture-app:assembleDebug
# Descargar desde https://gear-glowing-unwary.ngrok-free.dev/apk
```

### Android — Navegación

- **PickerScreen**: agregado TopAppBar con flecha ← (atrás), ícono 🏠 (Home) y breadcrumb de ruta tipo `HSR > Sotero > Informatica`.
- **Todas las screens**: tienen botón atrás visible (excepto Login y Organizations por ser raíz) y Home para ir directo a Organizations.
- **Breadcrumbs dinámicos**: `NavState` singleton con `mutableStateListOf`. El NavGraph agrega crumbs al navegar adelante; el BackHandler + botón atrás las elimina al retroceder.
- **Home button**: limpia breadcrumbs y navega a Organizations con `popUpTo + inclusive` para backstack limpio.
- **Archivos modificados/creados**:
  - `navigation/NavState.kt` (nuevo)
  - `navigation/NavGraph.kt` (onBack/onHome/breadcrumbs en todas las rutas)
  - `ui/components/PickerScreen.kt` (TopAppBar + BackHandler + breadcrumb)
  - `ui/screens/OrganizationSelectionScreen.kt` (TopAppBar + breadcrumb)
  - `ui/screens/SiteSelectionScreen.kt` (onBack/onHome/breadcrumbs)
  - `ui/screens/BuildingSelectionScreen.kt` (ídem)
  - `ui/screens/FloorSelectionScreen.kt` (ídem)
  - `ui/screens/CampaignSelectionScreen.kt` (ídem)
  - `ui/screens/CellSelectionScreen.kt` (TopAppBar + BackHandler + breadcrumb)
  - `ui/screens/CaptureScreen.kt` (TopAppBar + BackHandler + breadcrumb)
  - `ui/screens/ReviewScreen.kt` (TopAppBar + Home + breadcrumb)
  - `ui/screens/SyncStatusScreen.kt` (TopAppBar + Home + breadcrumb)

### pyproject.toml

- Agregada dependencia `uvicorn>=0.34,<1.0` (antes solo en venv host)  

### Android — Fix sync offline + acceso a Sync Status (31 Jul 2026)

**Problema 1 — Sync Now dejaba todo en "Failed":**
`TokenManager` guardaba los tokens solo en memoria. Cuando WorkManager lanzaba el
`SyncWorker` en un proceso fresco (app muerta), no había token → 401 sin refresh
posible → `markFailed`.

**Fix:**
- `TokenManager` (en `shared/api/TokenInterceptor.kt`): ahora persiste/restaura
  `access_token`/`refresh_token` en SharedPreferences (`internav_prefs`), con
  `attach(context)`, `restoreFromPrefs()`, `persistLocked()` en `updateTokens`,
  y `clear()` que también borra prefs.
- `ApiClient.initialize(url, context)`: recibe Context, hace `tokenManager.attach(context)`;
  nuevo `isInitialized`.
- `InternavCaptureApp.onCreate()`: `initialize(savedUrl, this)` + `tokenManager.restoreFromPrefs()`.
- `SyncWorker.doWork()`: `ensureApiReady()` — si no está inicializado, inicializa
  desde `server_url` persistido y restaura tokens antes de sincronizar.
- `LoginScreen`: pasa context a `initialize()` (la persistencia ocurre vía `updateTokens`).

**Problema 2 — Sync Status inalcanzable salvo al guardar captura:**
- `OrganizationSelectionScreen`: nuevo ícono 🔄 en la TopAppBar que navega a `SYNC_STATUS`.
- `NavGraph`: `onSyncStatus` en la ruta `ORGANIZATIONS`.

**Problema 3 — "Sync scheduled" sin progreso visible:**
- `SyncStatusScreen`: `LaunchedEffect` que recarga la lista cada 2s mientras la
  pantalla está visible (polling liviano, sin dependencias nuevas), así se ven los
  estados Uploading → Completed/Failed en vivo.

**Build:**
- Java 25 instalado en la máquina rompía Gradle 8.12.1 (`IllegalArgumentException: 25`).
- Instalado Temurin JDK 21 (`C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot`);
  construir con `$env:JAVA_HOME` apuntando ahí. Wrapper quedó en 8.12.1.
- Compilar: `$env:JAVA_HOME="C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot"; .\gradlew capture-app:assembleDebug --no-daemon`

### Android — Permiso de ubicación en runtime + verificación de sync (31 Jul 2026)

**Runtime permission:**
- `CaptureScreen`: ahora usa `rememberLauncherForActivityResult(RequestPermission())`
  para pedir `ACCESS_FINE_LOCATION` al presionar "Scan WiFi" (antes solo mostraba error).
- Si se deniega, muestra error + botón "Open Settings" que abre los settings de la app.
- Filtro adicional en `performScan`: se descartan APs con `frequency <= 0` (evita 400 → Failed).

**Verificación end-to-end (sync funciona):**
- Confirmado vía API que las 4 capturas del usuario llegaron al backend
  (campaña "Primera campanya", status Collecting, `7f93a263-...`).
- Cada fingerprint tiene observaciones completas (ej: 10 APs con bssid/ssid/rssi/frequency).
- Nota: `GET /campaigns/{id}/fingerprints` no incluye observaciones (devuelve `[]`);
  el detalle `GET /fingerprints/{id}` sí las trae.

## Walkability real + grillas SVG (3 Ago 2026)

### Decisión de walkability (aprobada por usuario)

**Regla: `walkable = celda sin pixel no-blanco Y dentro del bbox de obstáculos`.**

- El algoritmo anterior usaba flood-fill desde los bordes para marcar el exterior,
  lo que asumía un contorno de edificio **cerrado**. Los planos reales (Piso 1/2)
  tienen vanos/puertas → el flood se colaba al interior y bloqueaba pasillos y salas.
- Se probó sellar puertas dilatando la barrera (k=2..10): no funcionó porque el
  contorno exterior del plano ni siquiera es un bucle cerrado.
- Solución: `_flood_exterior` reemplazado por `_obstacle_bbox` (bbox de la máscara
  de obstáculos **sin dilatar**). El bbox solo excluye el margen blanco del canvas;
  los vanos ya no importan. Limitación conocida: edificios en L pueden dejar
  concavidades interiores del bbox como walkable (corregible vía `PUT /cells/{id}/walkable`).

### Cambios en `backend/app/application/svg_analyzer.py`

- `_obstacle_bbox()` nuevo; `_flood_exterior()` eliminado.
- El bbox se calcula **antes** de `_dilate` (con la dilatada creaba muescas en las
  esquinas diagonales por la vecindad 4).
- Docstring del módulo actualizado.

### Cambios en `backend/tests/test_svg_analyzer.py`

- `test_doorway_does_not_flood_interior`: caja con vano en muro derecho (dos paths,
  sin `Z` — un `M` intermedio crea subpath nuevo y `Z` cierra en diagonal, artefacto SVG).

### Fix bug: `SqlAlchemyGridRepository.list_by_floor`

- No filtraba `GridModel.deleted_at.is_(None)` → tras `DELETE` (soft), el grid seguía
  listado y `GridService.generate` bloqueaba con "A floor can have only one grid".
- Añadido filtro de `deleted_at`. Test de regresión API: `test_generate_after_delete_grid`.

### Estado de datos reales (API)

- **Piso 1** (`a9777782-2c43-4e12-9166-b90b24d92f73`): plan SVG v1 activo (2000×3000),
  grid `e1bea51f-4ff7-4df4-af76-16e36883e97a` (cell 100, 600 celdas, **200 walkable**, Active).
- **Piso 2** (`bc41c259-bbe1-475a-8a80-79ec7510a79d`): plan SVG v2 activo (2000×3000),
  grid `fc7b84bc-c26f-4602-bb04-f494723950a1` (cell 100, 600 celdas, **149 walkable**, Active).
- El grid placeholder viejo (`7451805a-...`) quedó soft-deleted; sus 4 fingerprints/44
  observaciones fueron borradas físicamente por `backend/scripts/reset_floor.py`.
- `GET /floor-plans/{id}/image` sirve el SVG (200, `image/svg+xml`) para ambos pisos.

### Suite de tests

- **371 passed** (74s) tras los cambios (2 tests nuevos: `test_generate_after_delete_grid`,
  `test_doorway_does_not_flood_interior`).
- ruff/black limpios en archivos tocados (solo EXE002 preexistente).

### Pendiente / conocido

- `POST /grids/{id}/regenerate` **no recalcula walkability** (llama `_generate_cells`
  sin máscara → todas las celdas quedan walkable=True). Si se quiere que regenerate
  preserve el análisis, hay que pasarle la máscara del plan activo (no evaluado).
- El Map Editor del admin portal no expone el toggle de walkable (existe el endpoint
  `PUT /cells/{id}/walkable`).

## Grilla sobre plano en Admin Portal + Capture App (3 Ago 2026)

### Aprobación

Plan en 2 partes (Parte A Admin Portal, Parte B Capture App) aprobado por el
usuario ("Ambos", "Ver + editar").

### Parte A — Admin Portal (`admin-portal/`)

- **`src/pages/GridViewPage.tsx`** (nuevo): carga piso → plan activo + grid activa +
  celdas; `<img>` del plano (`/api/v1/floor-plans/{id}/image`) con overlay SVG
  `viewBox = plan.width×height` (rects por celda: verde traslúcido = walkable, gris =
  bloqueado; `title` con `(row,col)`). Cabecera con grid name/status/cell_size/plan
  version/total/walkable + leyenda. Click en celda (solo Operator/Admin) →
  `PUT /cells/{id}/walkable` + refresh local + Toast. Estados sin plan/sin grid/error.
- **`src/App.tsx`**: ruta `/floors/:floorId/grid` → `GridViewPage`.
- **`src/pages/FloorListPage.tsx`**: columna Actions siempre visible con botón "View"
  (todos los roles autenticados pueden ver); Edit/Delete siguen restringidos.
- **`src/pages/GridListPage.tsx`**: botón "View" (navega a `/floors/{floor_id}/grid`);
  modal Generate con checkbox **"Analyze walkability"** que envía
  `analyze_walkability: true` (hoy el portal generaba sin análisis).

### Parte B — Capture App (`android/`)

- **`shared/.../api/ApiService.kt`**: `@GET("api/v1/floor-plans/{floorId}/image")`
  `@Streaming downloadFloorPlanImage(...): Response<ResponseBody>` (sin Coil; se
  decodifica con `BitmapFactory`).
- **`capture-app/.../ui/components/CellMap.kt`** (nuevo): composable Canvas que dibuja
  el plano escalado + celdas (verde translúcido walkable / gris bloqueado / verde
  sólido + borde blanco la seleccionada) con detección de tap por celda
  (convierte px→coordenadas de plan).
- **`capture-app/.../ui/screens/CellSelectionScreen.kt`**: carga plan activo + imagen +
  todas las celdas; toggle **Map/List** (FilterChips). Mapa con celdas tappables en
  posición real (solo walkable seleccionan); la lista original de tarjetas `(row,col)`
  se mantiene.
- **`capture-app/.../navigation/NavRoutes.kt` / `NavGraph.kt`**: ruta `CAPTURE` pasa
  ahora `floorId` y `cellLabel` → `capture/{campaignId}/{floorId}/{cellId}/{cellLabel}`.
- **`capture-app/.../ui/screens/CaptureScreen.kt`**: mini-mapa (Box 180dp recortado,
  centrado) con la celda seleccionada resaltada; encabezado muestra
  `Cell: (row,col) | Sample: N` (antes UUID). El mapa es opcional (si falla la
  descarga, el flujo de captura sigue igual).

### Verificación (todo verde)

- `admin-portal`: `npm run build` OK (tsc + vite, 0 errores).
- `android`: `:capture-app:assembleDebug` y `compileDebugKotlin` BUILD SUCCESSFUL
  (APK generado); JAVA_HOME jdk-21.
- Backend sin cambios de código: suite completa **371 passed** (76s, única warning
  Starlette/httpx) — se ejecutó con `docker cp ./backend/tests` al contenedor vivo.
- Pendiente manual (no automatizable aquí): probar la UI en `localhost:8000`
  (admin@example.com / 123456) y reinstalar `capture-app-debug.apk`.

### Fix de 2 bugs detectados al probar la UI (3 Ago 2026, tarde)

1. **Deep links del SPA daban `{"detail":"Not Found"}`** (ej. `/grids`, `/floors/{id}/grid`).
   Causa: `SPAStaticFiles.get_response` capturaba `from fastapi import HTTPException`,
   pero en FastAPI 0.140 `fastapi.exceptions.HTTPException` ya **no** es la misma clase
   que `starlette.exceptions.HTTPException` que lanza `StaticFiles` → el `except` no
   capturaba el 404 y caía al handler de FastAPI. Fix en `backend/app/main.py`: importar
   `HTTPException as StarletteHTTPException` desde `starlette.exceptions` y capturarla.
   Verificado: `/grids` y `/floors/{id}/grid` → 200 (sirven index.html).
2. **Página Grids mostraba "Request failed"**: no existía `GET /api/v1/grids`
   (solo `GET /floors/{id}/grids`), pero `useCrud("/grids")` lo llama. Añadido:
   - `GridRepository.list_all()` (renombrado de `list` — un método `def list` sombrea
     el builtin en el cuerpo de la clase y rompe las anotaciones `list[Grid]` evaluadas;
     la convención del proyecto es `list_all`, ver `dataset_repository`).
   - `SqlAlchemyGridRepository.list_all()` (solo no-deleted, ordenado por created_at desc).
   - `GridService.list_all()`.
   - `@router.get("/grids")` en `backend/app/api/routers/grids.py` (antes de `/grids/{entity_id}`).
   - Test `test_list_all_grids` en `backend/tests/test_grid_api.py`.
   Verificado: `GET /api/v1/grids` → 200 con las 2 grids (Piso 1 y Piso 2).

Suite tras los fixes: **372 passed** (76s). ruff/black limpios en tocados
(solo EXE002 preexistente). Endpoints confirmados contra el contenedor vivo.

### Fix de sesión + edición de celdas (3 Ago 2026, noche)

1. **La sesión se cerraba al recargar la página.** Los tokens vivían en memoria
   (`api.ts`), el usuario en el store (sin persistir). Ahora:
   - `admin-portal/src/services/api.ts`: tokens persistidos en `localStorage`
     (`internav.auth.tokens`); se restauran al cargar el módulo y `refreshAccessToken`
     los re-persiste vía `setTokens`.
   - `admin-portal/src/stores/authStore.ts`: `user` hidratado desde `localStorage`
     (`internav.auth.user`) al crear el store; se guarda en login y se limpia en logout.
   - Tras recargar (Ctrl+F5) la sesión se mantiene; si el access token expiró, el flujo
     401→refresh sigue funcionando.
2. **El click en celdas no modificaba walkable** (solo parpadeaba la opacidad).
   Causa: `GridService.update_walkable` bloqueaba con 409 cuando `grid.status == ACTIVE`,
   pero **ambas grids reales son Active** → todo PUT daba `409 Conflict`.
   El spec (`17_ENTITY_CONTRACTS.md`) dice *"walkable immutable while Campaign is active"*.
   Fix en `backend/app/application/grid_service.py`: `GridService` recibe ahora
   `CampaignRepository` y `update_walkable` solo bloquea si
   `campaign_repo.has_active_on_floor(grid.floor_id)` (campaña Ready/Collecting).
   - `backend/app/api/dependencies.py`: `get_grid_service` pasa `SqlAlchemyCampaignRepository`.
   - Tests actualizados: `test_update_walkable_raises_if_grid_active` →
      `test_update_walkable_blocked_while_campaign_active` (grid Active + campaña Ready → 409)
     y nuevo `test_update_walkable_active_grid_allowed_without_campaign` (grid Active sin
     campaña → 200); en `test_grid_service.py` se añadió `FakeCampaignRepo` y tests
     equivalentes a nivel de servicio.

Verificación en vivo contra el contenedor:
- Piso 1 (grid Active, sin campañas): `PUT /cells/{id}/walkable` → **200** (toggle y revert OK).
- Piso 2 (grid Active, campaña `Collecting` "Primera campanya"): `PUT` → **409** (regla del spec).
- Bundle nuevo servido: `assets/index-ZFIogsGn.js`.
- Suite completa: **374 passed** (76s). black aplicado; ruff solo EXE002 preexistente.

### Rediseño Admin Portal + numeración de celdas (3 Ago 2026, noche)

**Causa raíz del "portal sin estructura":** `App.css` (494 líneas con las clases de
todos los componentes) **nunca se importaba** — el único CSS cargado era `index.css`
(46 líneas de tokens). El portal renderizaba sin estilos de componentes.

**Rediseño visual (CSS-only, sin dependencias nuevas):**
- `index.css`: tokens ampliados (spacing scale, radius, sombras, topbar/sidebar sizes).
- `App.css`: **reescritura completa** del design system (mantiene el contrato de clases
  existentes → todas las páginas heredan el estilo sin tocar su JSX). Ahora **importado
  en `main.tsx`**.
- Layout nuevo: sidebar oscura (brand "IP", secciones Overview/Management/Data/System,
  links activos, usuario + logout) + **topbar** (título de página + email/rol del user) +
  `main` con **`.container`** (max-width 1200px).
- **Cards** (`.card/.card-header/.card-body`) envolviendo las tablas de las 8 páginas de
  listado (Org/Site/Building/Floor/Grid/Campaign/Dataset/Model) + GridViewPage.
- Componentes pulidos vía CSS: botones (variants), formularios (focus/errores), DataTable
  (en card, hover, cabeceras), badges de estado (+ roles Administrator/Operator/Viewer),
  modal, toast, breadcrumb, paginación, búsqueda, login centrado con subtítulo,
  dashboard stat-cards.
- Verificación: `npm run build` OK; `npx prettier --write .` → todo el repo en estilo
  Prettier (CI green); `npx oxlint` 0 errores (10 warnings preexistentes de
  react-hooks/useCrud). Bundle nuevo servido: `index-BAoiDelj.js` + `index-D2J3MOox.css`.

**Numeración de celdas (#N computado, sin cambios de schema):**
- Fórmula determinística idéntica en admin y capture app:
  `nCols = max(column)+1`, `#N = row*nCols + column + 1` (1-based, fila-mayor).
- **Admin `GridViewPage.tsx`** (rework): tooltip `#N (row,col) walkable|blocked`; número
  SVG `<text>` centrado en cada celda (visible con `cell_size >= 40`); buscador
  **"Jump to cell #"** con resaltado naranja + `scrollIntoView`; toggle **Map/List** (la
  lista es una tabla `# | row | column | center | status | action`); leyenda con swatches
  y contadores en `.card`.
- **Capture App**:
  - `ui/utils/CellNumbering.kt` (nuevo): `cellNumber(cell, cells)` + `cellLabel` → `#N (row,col)`.
  - `CellMap.kt`: dibuja `#N` con `drawText`/`rememberTextMeasurer` cuando la celda
    renderizada es lo bastante grande (≥28px); el mini-mapa de captura queda limpio.
  - `CellSelectionScreen.kt`: items de lista y tap del mapa usan `cellLabel(cell, allCells)`.
  - `CaptureScreen.kt`: header `Cell: #N (row,col) | Sample: M`.
- Build Android: `:capture-app:assembleDebug` **BUILD SUCCESSFUL** (19s); APK
  `capture-app-debug.apk` regenerado (17.47 MB) → **reinstalar en el teléfono**.
- Nota: `ktlintCheck` NO existe en el proyecto (CI de Android preexistente rota — plugin
  ktlint no configurado); el código sigue el estilo del `.editorconfig`.

**Pendiente manual:** probar la UI en `localhost:8000` (Ctrl+F5) y reinstalar el APK.

### Fix: faltaba `GET /api/v1/campaigns` (3 Ago 2026, noche)

**Problema:** `/dashboard` y `/campaigns` del Admin Portal mostraban
`Unexpected token '<', "<!doctype " is not valid JSON`. Causa: no existía
`GET /api/v1/campaigns` (listar todas) — el router de campaigns solo tenía
`GET /floors/{floor_id}/campaigns` y `GET /campaigns/{id}`. La petición
`/api/v1/campaigns` no matcheaba ningún route y caía al mount SPA (`/`) → el
`SPAStaticFiles` servía `index.html` con 200 → `res.json()` fallaba. Afectaba a
Dashboard (`Promise.all` incluye `/campaigns?page_size=1`) y a CampaignListPage
(`useCrud("/campaigns")`), impidiendo completar la campaña del Piso 2.

**Fix (mismo patrón que `GET /grids`):**
- `app/repositories/campaign_repository.py`: `list_all()` en el protocol.
- `app/infrastructure/.../campaign_sqlalchemy_repository.py`: `list_all()`
  (solo no-deleted, `created_at desc`).
- `app/application/campaign_service.py`: `list_all()`.
- `app/api/routers/campaigns.py`: `@router.get("/campaigns")` (antes de
  `/campaigns/{campaign_id}`).
- Test `test_list_all_campaigns` en `tests/test_campaign_api.py`.

**Verificación:** `GET /api/v1/campaigns` → 200 con "Primera campanya"
(Collecting). Suite completa: **375 passed** (78s). black reformateó
`campaign_service.py`; ruff limpio; mypy sin errores nuevos (los reportados son
preexistentes: repos abstractos `...`, `dependencies.py`, tests sin anotaciones).

**Nota para el usuario:** el bloqueo de celdas del Piso 2 es la regla del spec
(campaña activa = Ready/Collecting en el piso → `PUT /cells/{id}/walkable` → 409
con mensaje claro en un toast). Para desbloquear: Admin → Campaigns → **Complete**
en "Primera campanya", editar celdas del Piso 2, y crear/arrancar campaña nueva.

## Mobile bundle + user-app real (4 Ago 2026)

### Backend: bundle JSON para inferencia offline en Android

El artefacto joblib/sklearn (`.bin`) NO es parseable en Android. Se decidió que el
backend sirva un **bundle JSON** de vectores de referencia + feature schema:

- `app/ai/training_pipeline.py`: `feature_schema` ahora incluye `classes`
  (train_info["classes"]).
- `app/ai/serialization.py`: nuevo `build_mobile_bundle(model_id)` →
  `{"feature_schema": {bssid_vocabulary, feature_count, normalization, missing_ap_value, classes},
    "references": [{cell_id, vector}]}` leyendo `_fit_X`/`_y` del joblib y mapeando
  labels vía `classes` (clases = **índice de clase**, no id de celda).
- `app/application/model_version_service.py` + `app/ai/training_pipeline.py`:
  `get_mobile_bundle()` (solo estados READY/PUBLISHED/ARCHIVED; TRAINING/FAILED → 409).
- `app/api/routers/models.py`: `GET /api/v1/models/{id}/mobile-bundle` → JSON compacto
  con header `X-Model-Checksum` = SHA-256 del body exacto, `Cache-Control: no-store`
  (usa `Request.app.state.model_version_service`; sin rol restringido).
- Tests en `tests/test_training_pipeline.py` (3 nuevos): bundle tras train (checksum
  SHA-256 del body OK; referencias ≥1; vector len == vocabulary; cell_id no nulo),
  409 antes de train, 404 modelo inexistente. Suite completa **378 passed** (80s);
  black/ruff limpios; tests re-corroborados tras black.
- Verificado en vivo: `GET /api/v1/campaigns` → 200 con "Primera campanya".

### Android user-app: fixes para que la inferencia funcione

Auditoría previa encontró que `ApiClient.initialize()` nunca se llamaba
(`baseUrl=""` → crash), `checkModelUpdate`/`downloadModel` nunca se usaban, el motor
se construía con `DoubleArray(0)` y `featureSchema = null`, `TokenManager` nunca se
restauraba, `stopScanning()` era no-op, y no había runtime permission de ubicación.

- `shared/.../api/ApiService.kt`: `@GET("api/v1/models/{modelId}/mobile-bundle")`
  `@Streaming downloadMobileBundle(...)`.
- `user-app/.../InternavUserApp.kt`: `onCreate` restaura `server_url` de
  `internav_prefs` + `ApiClient.initialize` + `tokenManager.restoreFromPrefs()`
  (patrón de capture-app).
- `user-app/.../LoginViewModel.kt`: estado `serverUrl` (default
  `http://10.0.2.2:8000`), `ApiClient.initialize(url, context)` antes del login,
  persistencia de `server_url` en prefs.
- `user-app/.../LoginScreen.kt`: campo **Server URL** (antes inexistente) + botón
  habilitado solo si no está en blanco.
- `user-app/.../PositioningViewModel.kt` (rework):
  - `initialize()`: grid activa (`status == "Active"`, no `lastOrNull`), cachea
    celdas en Room, guarda `gridCellSize`, luego `ensureEngine(floorId)`.
  - `ensureEngine()`: `checkModelUpdate(floorId)` → si hay versión nueva (o sin
    caché) descarga el bundle, valida SHA-256 con `X-Model-Checksum`, activa
    (construye `InferenceEngine` + escribe Room) o lanza error; si falla la red,
    rollback al bundle cacheado anterior.
  - `buildEngineFromBundle()`: parsea bundle con Gson, mapea `cell_id` → `Cell.id`
    de la grid activa, construye `InferenceEngine(referenceVectors, FeatureSchema, k=3)`.
  - `stopScanning()` real (cancela el `Job`); `startScanning()` reentrante.
  - `scanOnce()` en `Dispatchers.IO` con `WifiManager.scanResults` → top 30 APs.
- `user-app/.../PositioningScreen.kt`: runtime permission de ubicación
  (`rememberLauncherForActivityResult(RequestPermission())`, card con botón si se
  deniega), plano de fondo (`BitmapFactory` del `downloadFloorPlanImage`), celdas
  walkable/bloqueadas/predicha y marcador rojo en la posición estimada.
- Fixes de build: se eliminó `styles.xml` duplicado (el estilo ya vivía en
  `themes.xml` → "Duplicate resources"); `libs.hilt.work` faltaba en
  `user-app/build.gradle.kts` (HiltWorkerFactory no resolvía); `@HiltViewModel`
  sin import en `OrganizationSelectionViewModel`; smart-casts entre módulos en
  `LoginViewModel`/`PositioningScreen`/`SiteSelectionScreen`; parámetros
  `modelPath`/`schemaPath` obligatorios de `CachedModelEntity`.

### Build APK

`$env:JAVA_HOME="C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot";
.\gradlew :user-app:assembleDebug --no-daemon` → **BUILD SUCCESSFUL** (1m16s).
APK: `android/user-app/build/outputs/apk/debug/user-app-debug.apk` (18.1 MB).

### Pendiente manual

- Reinstalar `user-app-debug.apk` en el teléfono y probar el flujo completo.
- La inferencia de verdad necesita un modelo entrenado con datos reales (la campaña
  del Piso 2 sigue en Collecting → aún no hay dataset/modelo publicado en el entorno
  vivo para probar el bundle end-to-end).

### Fix: "Failed to decode floor plan" en capture-app (4 Ago 2026, tarde)

**Causa raíz:** los planos activos (Piso 1/2) se almacenan y sirven como **SVG**
(`GET /floor-plans/{id}/image` → `image/svg+xml`), pero Android decodificaba con
`BitmapFactory.decodeByteArray`, que no soporta SVG → `null` → error
"Failed to decode floor plan" en CellSelectionScreen / CaptureScreen.

**Solución (sin librerías nuevas ni cambios de backend):** renderizador SVG propio
en el módulo `:shared` usando `androidx.core.graphics.PathParser` (ya incluido vía
`androidx.core`, que está en el classpath de `:shared`):

- **`shared/.../graphics/SvgRenderer.kt`** (nuevo):
  - `decodeFloorPlanImage(bytes)`: intenta `BitmapFactory` primero (PNG/JPEG) y, si
    falla, rasteriza el SVG.
  - `renderSvg(bytes)`: parsea el XML con `XmlPullParser` (sin dependencias), lee
    `width/height`/`viewBox`, y dibuja en un `Bitmap` (ARGB, max dim 1024 preservando
    aspecto) los elementos `<path>` (vía `PathParser.createPathFromPathData` + drawPath)
    y `<rect>` (drawRect), respetando `fill`/`stroke` (hex `#RRGGBB`/`#RGB` y nombres
    `black`/`white`/etc., ignorando `none`). Trazo con grosor mínimo 1px para que los
    muros de 1 unidad sigan visibles al escalar.
- Los SVGs reales solo usan `<path>` + `<rect>` y comandos `C d H L M V Z` — todos
  soportados por `PathParser`.
- **Call sites actualizados** (reemplazan `BitmapFactory.decodeByteArray`):
  - `capture-app/.../CellSelectionScreen.kt` (mapa de selección de celdas).
  - `capture-app/.../CaptureScreen.kt` (mini-mapa de la captura).
  - `user-app/.../PositioningScreen.kt` (plano de fondo de posicionamiento).

**Build:** `:capture-app:assembleDebug :user-app:assembleDebug` → **BUILD SUCCESSFUL**
(1m14s). APKs regenerados:
- `android/capture-app/build/outputs/apk/debug/capture-app-debug.apk` (18.3 MB)
- `android/user-app/build/outputs/apk/debug/user-app-debug.apk` (18.2 MB)

**Pendiente manual:** reinstalar ambos APKs (el capture-app es el que fallaba).

## Regla de color capturas + user-app mapa de oficina (4 Ago 2026, noche)

### Capture-app: color del texto en la lista de celdas

Regla aprobada: interpolación gradual literal 0 (rojo) → 10 (verde), no por
umbrales. `0 = 0xCCDC2626`, `10+ = 0xCC16A34A`.

- `capture-app/.../ui/utils/CellNumbering.kt`: `cellCaptureColor(count)` + `lerp()`
  movidas desde `CellMap.kt` (ahora comparten constantes de color).
- `capture-app/.../ui/components/CellMap.kt`: importa `cellCaptureColor`; constantes
  `NUMBER_COLOR` y helper propios eliminados.
- `capture-app/.../ui/screens/CellSelectionScreen.kt`: el `Text(cellLabel(...))` de la
  vista lista ahora usa `color = cellCaptureColor(captureCounts[cell.id] ?: 0)`.

### User-app: pantalla de posicionamiento → mapa de oficina real

Decisiones aprobadas por el usuario:
- GPS: marcador azul aproximado SOBRE el plano aunque los planos no estén
  georreferenciados. Bounding box de la oficina: `minLat=-33.578876,
  maxLat=-33.578684, minLng=-70.578753, maxLng=-70.578674`.
- Orientación SVG (foto): **Norte = abajo del plano, Este = izquierda**.
  Fórmula: `x = (maxLng - lng) / span * width`, `y = (lat - minLat) / span * height`.
- Selección persistida: primera ejecución Org→Site→Building, luego se guarda y las
  siguientes abren el mapa directo.
- Modo manual "fijo hasta volver a Auto": si el usuario elige piso manualmente, el
  modelo no cambia de piso hasta que toque "Auto".

Implementación:
- `user-app/.../util/Prefs.kt` (nuevo): SharedPreferences `internav_prefs`, keys
  `KEY_LAST_ORG/SITE/BUILDING`, getters `lastBuildingId`/`lastSiteId`/`lastOrgId`.
- `user-app/.../location/OfficeGps.kt` (nuevo): `OfficeGpsBounds` +
  `gpsToPlan(lat, lng, planW, planH): PlanPoint` (mapping invertido por orientación).
- `user-app/.../navigation/NavRoutes.kt` y `NavGraph.kt`: `FLOORS`/`POSITIONING`
  reemplazados por `MAP = "map/{buildingId}"`. Login exitoso → si hay `lastBuildingId`
  va directo al mapa, si no a selección de organización; elegir edificio → mapa.
- `user-app/.../LoginScreen.kt`: navegación ahora con callback al NavGraph
  (login → map u organizations según prefs).
- Org/Site/BuildingSelectionScreen: persisten IDs (`Prefs.save*`) al hacer tap.
- `user-app/.../viewmodel/MapViewModel.kt` (nuevo): estado (floors, activeFloorId,
  floorPlan, cells, result, lastScan, `PositionSource.MODEL/GPS/NONE`, gpsPosition,
  autoFloor) + engine por piso; scan loop cada 2s; auto-floor elige la mayor
  confianza; fallback GPS vía `LocationManager` last-known; download de bundle con
  checksum SHA-256, caché en Room; carga del plano + imagen + celdas.
- `user-app/.../ui/screens/MapScreen.kt` (nuevo): FilterChips de piso ("Auto" + nombre
  de pisos), card de estado (Model/GPS/None + confianza + lat/lng/accuracy), Canvas del
  plano con zoom/pan (escala 1..5 + FAB reset), marcador azul GPS vía `gpsToPlan`,
  marcador rojo del modelo, lista de APs escaneados.
- `PositioningViewModel.kt` y `PositioningScreen.kt` eliminados (conflictos de
  redeclaración de `MobileBundle`/`MobileFeatureSchema`/`BundleReference` privadas en
  el mismo paquete; ya eran código muerto).

**Build:** `.\gradlew.bat assembleDebug` → **BUILD SUCCESSFUL** (20s). APKs:
- `android/capture-app/build/outputs/apk/debug/capture-app-debug.apk` (17.5 MB)
- `android/user-app/build/outputs/apk/debug/user-app-debug.apk` (17.4 MB)

Warnings no bloqueantes: `fallbackToDestructiveMigration` deprecated (AppModule),
`Divider` → `HorizontalDivider` (MapScreen.kt:293), `WifiManager.startScan`
deprecated (MapViewModel.kt:295).

**Pendiente manual:** reinstalar ambos APKs. En user-app, primera ejecución pasa por
Org→Site→Building y las siguientes abren el mapa directo (Auto + pisos); GPS usa
last-known location (no requiere Google Play Services).

### Calibración GPS→plano por ancla (4 Ago 2026, noche)

**Problema:** el mapeo por bounding box quedaba mal (el ancla caía en x≈4253, fuera del
plano de 2000 → clamp a 2000; la celda 126 real está en (550,650)).

**Intento de calibración por 2 puntos:** el usuario dio celda 470 (fila 23, col 9,
centro (950,2350)) con GPS (-33.578831, -70.578850), verificados en el backend. Las dos
celdas están a ~1746 unidades (~17 m) pero los GPS quedaron a **0.86 m** (4e-6° lat +
8e-6° lng) → ruido GPS indoor; con esos 2 puntos la escala da absurda (celda ~3 cm).
La segunda lectura **no sirve para escala**.

**Solución adoptada (escala real dada por el usuario):** *3.25 celdas = 2 metros* →
`UNITS_PER_METER = 100 * 3.25 / 2 = 162.5` (plano ≈ 12.3 × 18.5 m).

- `user-app/.../location/OfficeGps.kt` (rework): constantes `REF_LAT=-33.578835`,
  `REF_LNG=-70.578842`, `CALIBRATION_CELL_NUMBER=126`, escala real; `gpsToPlan(lat, lng,
  planW, planH, anchor)` lineal con origen en la referencia (Norte=abajo → y=(lat-lat0)*k,
  Este=izquierda → x=(lng0-lng)*k) y clamp a bounds; `findCellCenter(cells, cellNumber)`
  que busca la celda por número (`row*nCols+col+1`, `nCols=max(column)+1`). Se eliminó el
  objeto `OfficeGpsBounds`.
- `user-app/.../ui/screens/MapScreen.kt`: computa `gpsAnchor` desde `state.cells`
  (`remember`) y lo pasa a `gpsToPlan`; si la celda 126 no existe, no dibuja el marcador
  azul. Aplica igual a ambos pisos (planos idénticos).

**Build:** `.\gradlew.bat :user-app:assembleDebug` → **BUILD SUCCESSFUL** (6s). APK:
`android/user-app/build/outputs/apk/debug/user-app-debug.apk` (17.4 MB, 14:17).

### Fix user-app: marcador GPS en la esquina + scroll atascado (5 Ago 2026)

**Bug 1 — Marcador GPS se pegaba a la esquina superior izquierda.**
Causa raíz: `gpsToPlan` clampeaba x/y a los bordes del plano (`coerceIn`). La celda
ancla 126 está en (550,650), solo ~3-4 m del borde del plano (12×18 m); cualquier
fij GPS con error >~4 m (típico indoor, el usuario reportó precisión alta) caía
fuera y se pinnaba a (0,0). Además `MapViewModel` solo leía `getLastKnownLocation`
cada 5 s eligiendo por `loc.time` **sin filtrar por precisión** (podía ser una fij
stale o gruesa de red/torre).

Cambios:
- `user-app/.../location/OfficeGps.kt`: `gpsToPlan` ya **no clampea** (devuelve
  coordenadas crudas); nuevo helper `isInsidePlan(pt, planW, planH)`.
- `user-app/.../viewmodel/MapViewModel.kt`: GPS en vivo con `LocationListener` +
  `requestLocationUpdates` (GPS + NETWORK, `minTime=0`, `minDist=0`,
  `Looper.getMainLooper()`), guardado en campo `gpsListener`; `onLocationChanged`
  filtra con `isGoodFix` (accuracy 1..60 m, <30 s) y solo publica si la fij es
  más nueva que la actual; `bestLastKnownLocation` reescrito para preferir fij
  fresca + menor precisión (no solo la más reciente) y usarse como seed inicial
  (`isUsableSeed`: accuracy ≤80 m, <5 min); `stopGps()` hace `removeUpdates` +
  listener null. Constantes `MAX_LIVE_ACCURACY/MAX_LIVE_AGE_MS/MAX_SEED_*`.
- `user-app/.../ui/screens/MapScreen.kt`: calcula `gpsPlanPt` y `gpsOutside` en
  composición; el marcador azul solo se dibuja si la fij cae **dentro** del plano
  (decisión del usuario: "Ocultar + aviso"); si está fuera, la card muestra
  "GPS fuera del plano conocido" (rojo) manteniendo lat/lng/precisión visibles.

**Bug 2 — No se podía deslizar fuera del mapa (stuck arriba).**
Causa: el `Column` raíz de `MapScreen` no tenía scroll; el mapa con `aspectRatio`
(2000/3000) llenaba toda la altura y el `LazyColumn(fillMaxSize())` de APs quedaba
con espacio cero → contenido bajo el mapa inalcanzable.

Cambios en `MapScreen.kt`:
- Raíz: `Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState())`.
- `LazyColumn` de APs: `fillMaxSize()` → `heightIn(max = 240.dp)` (scroll anidado
  válido dentro del Column scrollable).

**Build:** `.\gradlew.bat :user-app:assembleDebug` → **BUILD SUCCESSFUL** (47s).
APK: `android/user-app/build/outputs/apk/debug/user-app-debug.apk`.

**Pendiente manual:** reinstalar `user-app-debug.apk` y verificar (1) el marcador
ya no se pinnea a la esquina (si la fij GPS es mala muestra el aviso "fuera del
plano") y (2) la página scrollea hasta la lista de APs. Nota: GPS indoor es
intrínsecamente impreciso (~5-15 m); la posición solo será confiable cerca de una
ventana o con un modelo WiFi entrenado con datos reales.

### Fix user-app: login 401 tras reinstalar la APK (5 Ago 2026)

**Síntoma:** tras reinstalar `user-app-debug.apk`, el login volvía a fallar con
`Login failed (401)`. Backend verificado OK vía LAN (`http://10.8.93.101:8000`) y
ngrok (`https://gear-glowing-unwary.ngrok-free.dev`): `/api/v1/health` → 200 y
`POST /auth/login` con `admin@example.com/123456` → 200 (token válido).

**Causa raíz (bug en la app):** `LoginScreen`/`LoginViewModel` no leían el
`server_url` persistido en `internav_prefs`. El campo siempre mostraba el default
`http://10.0.2.2:8000` (alias de emulador, no funciona en teléfono real). Al
reinstalar sobre la APK anterior (los datos persisten), `InternavUserApp.onCreate`
restauraba el URL bueno guardado, pero `login()` re-inicializaba con el valor del
campo (`10.0.2.2:8000`) → en la red corporativa `10.x.x.x` ese IP responde 401.

**Fix en `user-app/.../viewmodel/LoginViewModel.kt`:**
- `init`: pre-carga `serverUrl` desde prefs (`server_url`) si existe.
- Error de login ahora incluye la URL usada:
  `"Login failed (401) - URL: http://...` para diagnosticar el destino real.

**Build:** `.\gradlew.bat :user-app:assembleDebug` → **BUILD SUCCESSFUL** (17s).

**Pendiente manual:** reinstalar la APK. Si el teléfono está en el mismo WiFi que
el PC usar `http://10.8.93.101:8000`; si no, `https://gear-glowing-unwary.ngrok-free.dev`.
Credenciales verificadas: `admin@example.com` / `123456`.

### Fix user-app: 401 por autocompletado del teclado + default URL (5 Ago 2026)

**Síntoma:** tras reinstalar user-app, login daba 401 aunque capture-app (mismo
URL ngrok, mismas credenciales) entraba bien. Verificado que el código de login es
idéntico en ambas apps (mismo `:shared`, `getPublicService().login(LoginRequest)`),
y que el backend solo responde 401 por credenciales rechazadas.

**Causa raíz (confirmada por el usuario):** el **autocompletado del teclado del
teléfono** insertaba un espacio (o texto distinto) en el campo Email al tocar una
sugerencia → `get_by_email` no encontraba al usuario → 401. Escribiendo el email a
mano, entra sin problemas. Además el default `http://10.0.2.2:8000` (emulador)
confundía en teléfono real, y los prefs `internav_prefs` se borran al desinstalar
→ el campo no mostraba la URL ngrok guardada.

Cambios:
- `user-app/.../ui/screens/LoginScreen.kt`: campo Email con
  `KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next)`
  (teclado de email sin barra de sugerencias → elimina el espacio del autofill);
  campo Password con `KeyboardType.Password` + `ImeAction.Done`.
- `user-app/.../viewmodel/LoginViewModel.kt`:
  - Default de `serverUrl` → `https://gear-glowing-unwary.ngrok-free.dev`
    (decisión del usuario; el prefill por prefs sigue pisándolo si hay URL guardada).
  - `login()` normaliza el email: `email.trim().lowercase()`.
  - Error HTTP ahora parsea `errorBody()` → `detail` de FastAPI y muestra el email
    enviado con su longitud: `Login failed (401) - Invalid email or password.
    (email='admin@example.com', len=18)`. `len` distinto de 18 delata basura del
    autofill; si `len=18` y aún 401, el problema es el password (revisarlo con el ojito).

**Build:** `.\gradlew.bat :user-app:assembleDebug` → **BUILD SUCCESSFUL** (19s).

**Pendiente manual:** reinstalar `user-app-debug.apk`. La URL ya viene con el
default ngrok; escribir el email a mano (o con el teclado de email) y probar.

### Fix Admin Portal: "Create Campaign" daba "Request failed" (5 Ago 2026)

**Causa:** `CampaignListPage.handleCreate` posteaba a `POST /api/v1/campaigns`
(vía `crud.create`), pero el backend solo expone
`POST /api/v1/floors/{floor_id}/campaigns` (el floor va en la URL, no en el body).
El 405 devolvía `{"detail":"Method Not Allowed"}` sin `message` → el cliente
lanzaba el genérico `Request failed`. Verificado: `POST /api/v1/campaigns` → 405;
`POST /api/v1/floors/{id}/campaigns` → 201.

**Fix en `admin-portal/src/pages/CampaignListPage.tsx`:**
- `handleCreate` ahora usa `api.post('/floors/${formFloor}/campaigns', { name })`,
  muestra toast de éxito/error y refresca la lista (`crud.list()`).

Se auditó el resto de páginas: solo CampaignListPage tenía la URL incorrecta
(Grid/Dataset/Model/Org/Site/Building/Floor ya apuntaban bien).

**Build:** `npm run build` OK → bundle nuevo `index-BRoEtyxT.js` servido por el
backend (verificado: el HTML de `/` ya referencia el hash nuevo).

**Pendiente manual:** Ctrl+F5 en `localhost:8000/campaigns` y probar Create Campaign.

### Fix Admin Portal: Delete sin efecto + Train "Request failed" (5 Ago 2026)

**Bug 1 — Borrar dataset/modelo no actualizaba la UI (desaparecía al refrescar):**
Los endpoints DELETE (`/datasets/{id}`, `/models/{id}`, etc.) responden **204 sin
body**, pero `api.ts` hacía `res.json()` incondicional → lanzaba error → el
`.then()` que quita la fila (y cierra el diálogo) nunca corría. El server ya
había soft-deleteado → al refrescar, el item no aparecía.
- `admin-portal/src/services/api.ts`: `apiRequest` y `upload` ahora manejan
  body vacío/204 (`res.json().catch(() => null)`) y además exponen el campo
  `detail` de FastAPI (`json?.detail`) en el mensaje de error, para que los
  4xx/5xx muestren el motivo real y no el genérico "Request failed".
- Afecta a todos los deletes (org/site/building/floor/campaign/dataset/model).

**Bug 2 — Train daba "Request failed":**
`TrainingPipelineService.train` lanza `ValueError("No samples in dataset.
Cannot train.")` cuando el dataset no tiene fingerprints; `_handle_domain_errors`
de `models.py` mapeaba ValueError → 500 "Internal error." → portal mostraba
"Request failed". Además, con `get_session` (commit en éxito / **rollback en
excepción**), un "mark-failed tras excepción" se perdía y el modelo quedaba
atascado en `Training`.
- `backend/app/api/routers/models.py`: ValueError → **400** en
  `_handle_domain_errors`; el handler de `/train` devuelve **409** (JSONResponse,
  sin excepción) cuando el modelo terminó en `Failed`.
- `backend/app/application/model_version_service.py`: `train()` captura el error,
  transiciona el modelo a **Failed** y lo **retorna** (no re-lanza) para que el
  commit persista la transición; si el status no es Training, re-lanza.
- `backend/tests/test_training_pipeline.py`: nuevo test
  `test_train_empty_dataset_returns_409_and_marks_failed` (409 + status Failed).

**Bug 3 — Falta de UI para agregar campañas al Dataset (flujo roto):**
`DatasetListPage` no tenía forma de llamar a
`PATCH /datasets/{id}/add-campaigns` → sin campañas no se podía Build →
train siempre fallaba. Ahora hay botón **"Add Campaigns"** en datasets Draft
con un modal de checkboxes (solo campañas `Completed`) + toast de éxito/error.

**Verificación:**
- `npm run build` OK → bundle `index-DgcnV0vu.js` servido por el backend (verificado).
- Suite backend en contenedor: **378 passed** (1 warning Starlette). Ruff: solo
  EXE002 preexistente.
- En vivo: train con dataset sin muestras → **409** `"Training failed. Ensure the
  dataset is built and contains completed campaigns with fingerprints."` y el
  modelo queda `Failed`; DELETE 204 de modelo/dataset funcionando.

**Pendiente manual:** Ctrl+F5 en `localhost:8000`. Para entrenar un modelo real:
completar campaña(s) → Dataset → Add Campaigns → Build → Create Model → Train →
Publish. La campaña del Piso 2 ("Primera campanya") sigue Paused con 4 fingerprints
(insuficientes para un modelo útil; capturar más antes de completar).


