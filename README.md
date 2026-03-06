# Lifecycle Policy Engine

A focused, home-grown platform for **ingest -> normalize -> policy -> evaluate -> report** lifecycle support tiers for OS and firmware components observed via runZero.

## Scope guard

This product is intentionally lightweight. It is **not**:

- a scanner
- a patch deployment tool
- a CMDB replacement
- a vulnerability platform
- an ITSM / ServiceNow workflow engine
- a topology or service-mapping product
- a multi-tenant SaaS
- a plugin marketplace
- a real-time streaming system

## What it does

- Pulls observed asset/component state from runZero Export API or local JSON/JSONL files
- Normalizes OS / BIOS / firmware-style observations into a small inventory model
- Applies lifecycle policies with deterministic precedence
- Produces auditable evaluation results and a compact React UI for reporting

## Repository layout

- `backend/` - FastAPI application, ingestion, policy engine, worker, tests
- `frontend/` - React + Vite + Tailwind UI
- `migrations/` - Alembic environment and initial schema migration
- `openapi.json` - exported FastAPI OpenAPI document

## Implemented architecture

### Backend

- Python 3.11+ (tested on 3.12)
- FastAPI + Uvicorn
- SQLAlchemy 2.0 async
- asyncpg for PostgreSQL
- Alembic migrations
- Pydantic v2 + pydantic-settings
- Lightweight scheduled ingestion worker loop (`backend/app/worker.py`)
- Minimal JWT auth with Admin / Viewer roles

### Frontend

- React + Vite + TypeScript
- Tailwind CSS
- Five pages:
  1. Dashboard
  2. Assets
  3. Asset Detail
  4. Policies
  5. Ingestion

## Data model

The required tables are implemented in the initial Alembic migration:

- `assets`
- `component_types`
- `observations`
- `policies`
- `evaluations`
- `ingestion_runs`
- `policy_audit_log`

## Policy matching precedence

Most specific matching policy wins:

1. `component + vendor + model + environment`
2. `component + vendor + model`
3. `component + asset_type + environment`
4. `component + asset_type`
5. `component + environment`
6. `component only`

Tie-breaks:

- latest `effective_from`
- deterministic by policy id

No match defaults to `Unsupported`.

## runZero integration

### Supported ingestion modes

1. **Scheduled/API pull** from runZero Export API using:
   - `GET /export/org/assets.json`
   - `GET /export/org/assets.jsonl` (preferred)
2. **Manual file upload** of local JSON / JSONL exports for development and testing

### Authentication

Use a runZero Export Token (`ET...`) in `RUNZERO_EXPORT_TOKEN`.

### Field mapping

The asset-centric runZero parser does **not** hardcode runZero export field names.

Update the mapping file here to adapt to your export shape without code changes:

- `backend/app/config/runzero_field_mapping.yaml`

The mapping controls:

- hostname / vendor / model / serial / IP / MAC extraction
- stable identifiers
- OS / BIOS / Firmware / NetworkOS / HypervisorOS / StorageOS / ApplianceFW version extraction
- observation timestamps

### Dummy service-centric parser

The canonical dummy export is checked in for tests here:

- `backend/app/tests/fixtures/dummy_service_export.json`

That parser groups service records by `service.address`, derives a single switch asset, extracts serial/MAC/IP identity, and creates an `OS` observation using `fp.os.version` or a deterministic `snmp.sysDesc` parse.

## Local development

### Prerequisites

- Python 3.11+
- Node 22+
- PostgreSQL 15+

### Backend

```bash
cp .env.example .env
python3 -m pip install -r backend/requirements.txt
alembic upgrade head
PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Worker (optional scheduled pull)

```bash
PYTHONPATH=backend python3 -m app.worker
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: `http://localhost:5173`
API docs: `http://localhost:8000/docs`

Default demo users:

- `admin / admin123!`
- `viewer / viewer123!`

Change these immediately for any real deployment.

## Docker / compose

```bash
cp .env.example .env
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- UI: `http://localhost:5173`
- Postgres: `localhost:5432`

## API highlights

Core endpoints:

- `GET /assets`
- `GET /assets/{id}`
- `GET /policies`
- `POST /policies`
- `PUT/PATCH /policies/{id}`
- `DELETE /policies/{id}`
- `POST /policies/import`
- `GET /evaluations`
- `POST /ingest/runzero`
- `POST /ingest/file`
- `GET /ingest/runs`
- `POST /evaluate`
- `POST /auth/token`

OpenAPI is available live from FastAPI and exported to `openapi.json`.

## CSV policy import

Expected header names:

```text
component_type_key,asset_type,vendor,model,environment,version,match_mode,lifecycle_tier,effective_from,effective_to,active,notes,created_by
```

## Testing

Run backend tests:

```bash
cd backend
python3 -m pytest app/tests -q
```

Implemented tests:

- policy matching precedence across all specificity layers
- dummy JSON ingestion producing one asset and one OS observation
- evaluation changes when policy data changes
- API flow for policy creation, ingest, evaluate, and query

## Notes on idempotency

Asset upsert prefers stable identifiers from runZero mappings. If no runZero asset id is available, it falls back to hostname + serial/MAC heuristics stored in `identifiers`.

Duplicate observations are avoided by the unique observation fingerprint and ingestion-side duplicate checks.

## Operational notes

- The worker only performs lightweight periodic runZero pulls.
- Evaluation is intentionally batch-oriented, not streaming.
- Policies are audited in `policy_audit_log` for create/update/delete operations.
- Conflict highlighting surfaces overlapping effective-dated rows with identical scope + version combinations.
