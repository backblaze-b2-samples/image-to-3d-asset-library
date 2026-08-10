<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Generate (`/generate`) — upload a source image, choose an engine + settings
  - Library (`/library`, `/library/[id]`) — asset grid + detail with an
    in-browser 3D viewer (`@google/model-viewer`), artifact table, and
    write-amplification breakdown
  - Dashboard (`/`) — asset-library metrics (objects written, storage,
    amplification ratio, storage-by-artifact, recent generations)
  - Files (`/files`) + Upload (`/upload`) — the kept full-bucket explorer +
    direct-to-B2 uploader
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - Image → 3D generation via `repo/engines/` adapters (TripoSR default,
    Hunyuan3D GPU-only, procedural demo); heavy ML imports are lazy
  - The B2 bucket is the versioned, content-addressed 3D asset library
    (`library/<hash>/manifest.json` is the durable record — no database)
  - Kept file upload/listing/deletion, metadata extraction, `/health`,
    `/metrics`, structured JSON logging
  - B2 S3 integration via boto3 (S3-compatible API only)
- **services/api/vendor/triposr/** — vendored MIT TripoSR model code, OUTSIDE
  `app/`, patched for CPU (PyMCubes, no OpenGL bake) — see its PROVENANCE.md
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (including the `Asset` models)
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (asset.py, files.py, upload.py, …)
    config/                Settings loaded from environment
    repo/                  Data access: b2_client, asset_store, manifest, jobs
      engines/             Mesh-generation adapters (base, device, render,
                           triposr, hunyuan3d, procedural) — lazy ML imports
    service/               Business logic (assets, asset_stats, upload, files)
    runtime/               FastAPI route handlers (assets, files, upload, …)
  vendor/triposr/          Vendored MIT TripoSR model code (outside app/)
  tests/                   pytest tests (structural + integration + hermetic assets)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. The versioned per-service configs and the human-approved
  staging/production contract live in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  - Source uploads land under `uploads/` (kept direct-upload flow)
  - The 3D asset library lives under `library/<content-hash>/`:
    `manifest.json` (the durable `Asset` record), `source.<ext>`, `mesh.glb`,
    `mesh.obj`, `texture_<res>.png…`, `preview.png`
  - Listing/stats via `list_objects_v2`; asset delete via prefix-scoped
    `delete_objects`; no application database

## External Services

- **Backblaze B2 S3 API** — object storage, retrieval, deletion, presigned URLs
- **Hugging Face Hub** — one-time download of the public `stabilityai/TripoSR`
  weights on the first real TripoSR run (cached; never at install/CI). No model
  provider API and no second key — B2 credentials only.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Generate**: Browser uploads the source via the presigned PUT flow, then
  `POST /assets` (`input_key`, engine, settings) -> service hashes the input
  (sha256 → asset id, dedup), writes a `pending` manifest, and submits the run
  to the single-worker registry (`repo/jobs.py`, off the event loop) -> the
  engine reconstructs the mesh -> service writes artifacts to `library/<id>/`
  and finalizes the manifest `complete`. The detail page polls
  `GET /assets/{id}` (manifest overlaid with live progress).
- **Browse/read**: `GET /assets` (library grid; preview presigned) and
  `GET /assets/{id}` (detail; every artifact presigned inline for the viewer).
- **Serve mesh**: model-viewer fetches the GLB from a presigned inline B2 URL
  (bucket CORS must allow GET/HEAD from the web origin).
- **Edit / Delete / Regenerate**: `PATCH /assets/{id}` (name/tags → manifest),
  `DELETE /assets/{id}` (prefix-scoped `delete_objects` of `library/<id>/`),
  `POST /assets/{id}/regenerate` (re-run; bumps version).
- **Stats**: `GET /assets/stats` aggregates write-amplification for the dashboard.
- **Upload / List / Download / Delete (files)**: the kept starter flows over
  the full bucket (`/upload`, `/files`).

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Asset routes: `services/api/app/runtime/assets.py`
- Asset orchestration: `services/api/app/service/assets.py` (+ `asset_stats.py`, `assets_hash.py`)
- Engine adapters: `services/api/app/repo/engines/` (`base`, `device`, `render`, `triposr`, `hunyuan3d`, `procedural`)
- B2 asset access (repo layer): `services/api/app/repo/asset_store.py`, `manifest.py`, `jobs.py`
- Vendored TripoSR model: `services/api/vendor/triposr/` (+ PROVENANCE.md)
- Pydantic models: `services/api/app/types/` (`asset.py`, `files.py`, `upload.py`, `stats.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`; hermetic asset tests: `tests/test_assets.py`
- OpenAPI contract: `docs/api/openapi.json`
- Frontend API client + hooks: `apps/web/src/lib/api-client.ts`, `queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Image → 3D Generation](docs/features/asset-generation.md)
- [3D Asset Library](docs/features/asset-library.md)
- [Dashboard](docs/features/dashboard.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
