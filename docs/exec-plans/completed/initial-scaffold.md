# Build plan — `image-to-3d-asset-library`

Source of truth for the starter: `.claude/scratch/vcsk-1155e1f1-1c20-4a49-a16c-979721e2fb16/`
(vibe-coding-starter-kit, cloned fresh in Phase 0). All keep/trim/add deltas below
are computed against that tree. Parent standards: `../CLAUDE.md` (S3-only, custom
user agent, standardized `B2_*` env vars). Starter contract: the clone's `AGENTS.md`.

---

## 1. Purpose

`image-to-3d-asset-library` is a B2 sample for game/AR-XR/3D content pipelines that run
**bulk image-to-3D reconstruction** and need durable shared storage for every artifact a
generation produces. A user uploads a source image; a local open-source engine (**TripoSR**,
MIT, the default) reconstructs a 3D mesh; the app writes the mesh, multi-resolution texture
maps, and a preview render to Backblaze B2, keyed by the input's content hash for dedup and
versioning. Downstream consumers fetch assets via presigned S3 URLs — the bucket **is** the
versioned 3D asset library. The sample's headline lesson is **write amplification**: one small
input image fans out into many larger B2 objects, so a bulk asset library fills a bucket fast,
and B2's flat per-GB pricing is the point. It runs on local OSS with **B2 credentials only —
no second API key**.

## 2. Architecture delta from vibe-coding-starter-kit

The starter is the ceiling. Strip what this app doesn't need; keep the starter contract
(UI kit, `/design`, `/files` bucket explorer, `/upload`, sidebar) intact; add the 3D-asset
surface. Every kept file that isn't listed under *trim* stays as-is.

### KEEP (do not strip / rename / restyle)
- **UI kit** `apps/web/src/components/ui/**` (shadcn primitives) — never edit generated files;
  restyle only via tokens in `apps/web/src/app/globals.css`.
- **`/design`** reference page and its `components/design/**`.
- **Bucket explorer (NON-NEGOTIABLE KEEP)** — `/files` route, `apps/web/src/app/files/`,
  `apps/web/src/components/files/`, its API routes (`runtime/files.py`, `service/files.py`),
  the full-bucket listing cache (`repo/list_cache.py`), and the **Files** sidebar entry. This
  is the full-bucket browse and is never removable.
- **Upload** — `/upload` route, `apps/web/src/app/upload/`, `components/upload/**`, the
  presigned-direct-upload flow (`runtime/upload.py`, `service/upload.py`, `repo/b2_upload.py`),
  and the **Upload** sidebar entry. Kept as the generic uploader; the new "New Asset" flow
  reuses this presign path for the source image (see §4).
- **Settings** — `/settings`, `components/settings/**` (also the **form-UX exemplar**, §4),
  `danger-zone.tsx`.
- **Metadata extraction** — `service/metadata.py` + `/files-by-key/detail`; still powers the
  file browser's detail panel. Keep feature + doc.
- **Backend spine** — layered `types → config → repo → service → runtime`; middleware order
  in `main.py`; health/metrics/ratelimit; structured JSON logging; OpenAPI contract machinery
  (`contract:export/check`, `test_openapi_contract.py`, `api-contract.test.ts`); the
  `check:agent-docs` harness and all its gates.
- **Sidebar nav** (Dashboard, Upload, Files, Settings, + Design reference link) — extend, don't remove.

### TRIM (remove / replace)
- **Dashboard body only** — the starter's file-centric dashboard (`apps/web/src/components/
  dashboard/stats-cards.tsx`, `upload-chart.tsx`, `recent-uploads-table.tsx`) is the one screen
  the starter contract says to *rewrite per app*. Replace its **contents** with asset-library
  metrics (§4). Keep the `/` route, the layout, and the `runtime→service→repo`+TanStack-Query
  data path. (Do not delete the components wholesale before their replacements exist — swap contents.)
- Nothing else is trimmed. The starter is lean; every other kept file earns its place.

### ADD (new for this sample)
- **Backend `repo/engines/`** — mesh-generation adapters (external "SDK" wrapped in repo/, per
  AGENTS "all external APIs wrapped in repo/ adapters"):
  - `engines/base.py` — `MeshEngine` protocol + `EngineResult` (glb bytes, optional obj bytes,
    `texture_maps: dict[int,bytes]` keyed by resolution, `preview_png` bytes, `stats`).
  - `engines/device.py` — device autodetect **CUDA → MPS → CPU** (hard rule), `GENERATION_DEVICE`
    env override (`auto|cpu|cuda|mps`). Sets `PYTORCH_ENABLE_MPS_FALLBACK=1`; note TripoSR ops may
    be unsupported on MPS and fall back to CPU.
  - `engines/render.py` — **headless** preview render + texture derivation. Load mesh with
    `trimesh`; render preview PNG with **matplotlib** (no OpenGL/moderngl/pyglet — headless-safe);
    derive multi-resolution texture/preview maps by downsampling (Pillow). Force a dark, single-
    subject framing suitable for a card thumbnail.
  - `engines/triposr.py` — **default engine (core, deployment: local)**. Lazy-imports torch +
    the vendored TripoSR model inside `generate()`; loads `stabilityai/TripoSR` weights via
    `huggingface_hub` on first run (cached; NOT downloaded at install/CI); extracts the mesh with
    **PyMCubes** (NOT `torchmcubes` — CUDA-only build fails on macOS CPU); exports a vertex-colored
    GLB (NO moderngl texture bake). Device from `engines/device.py`.
  - `engines/hunyuan3d.py` — **optional, GPU-only (deployment: local)**. Lazy-imports the Hunyuan3D
    pipeline (NOT in the default lock — see §deps); raises a friendly "Hunyuan3D requires a CUDA GPU
    and its optional extras — see README" on non-CUDA / not-installed. Honest second engine; not
    exercised by CPU verify.
  - `engines/procedural.py` — **"Fast demo" engine (deployment: local, no ML)**. Deterministically
    turns an input image into a real mesh via `trimesh` primitives (dependency-light, instant, no
    model download). This is the engine **unit tests use** and a selectable UI option labeled
    "Demo (procedural, no model)". It never replaces TripoSR as the default; it exists for a
    zero-friction first run and CI.
  - `engines/__init__.py` — `get_engine(name)` registry + `ENGINES` metadata list (name, label,
    `deployment`, `device_requirement`, `is_default`).
  - **Vendored TripoSR** lives at `services/api/vendor/triposr/` (OUTSIDE `services/api/app/` so the
    `<300-line` structural test never scans it), with upstream `LICENSE` (MIT) + a `PROVENANCE.md`
    noting the source commit and the two local patches (PyMCubes marching cubes; no moderngl bake).
    The adapter adds `vendor/` to `sys.path` or imports it as a package. *(Builder may instead pin a
    CPU-installable TripoSR source; the hard constraint is: default install pulls NO CUDA/torchmcubes/
    moderngl dep and imports cleanly on macOS arm64 CPU, with all heavy imports lazy inside `generate()`.)*
- **Backend `repo/manifest.py`** — read/write `library/<hash>/manifest.json` on B2 (B2 is the sole
  datastore; no DB). Asset persistence lives in the manifest.
- **Backend `repo/asset_store.py`** (or extend `b2_client.py`) — `get_object_bytes(key)` (download
  input for hashing + inference, and manifests), `delete_prefix(prefix)` (list + `delete_objects`
  batch to remove all of `library/<hash>/`), reusing the existing client + list cache.
- **Backend `repo/jobs.py`** — module-local in-memory job registry (a `dict` + `threading.Lock`
  + a `ThreadPoolExecutor(max_workers=1)`), mirroring the starter's module-local counter/list_cache
  pattern. Durable status is the manifest; the registry tracks the *live* run for progress polling
  and keeps generation off the event loop.
- **Backend `service/assets.py`** — orchestration: `create_asset` (validate input under `inputs/`,
  download bytes, sha256 → asset id, **dedup**: if a complete manifest for the same engine+params
  exists, return it; else write `pending` manifest + submit job), the job body (`running` → run
  engine → upload artifacts + finalize manifest `complete`/`failed`), `list_assets` (list `library/`
  prefixes, read manifests), `get_asset`, `update_asset` (patch name/tags in manifest),
  `delete_asset` (delete the asset's B2 prefix), `regenerate_asset` (re-run; bumps `version`),
  `asset_stats` (aggregate write-amplification). Calls repo only; returns Pydantic types.
- **Backend `runtime/assets.py`** — routes (all call service, never repo):
  `POST /assets`, `GET /assets`, `GET /assets/{id}`, `PATCH /assets/{id}`, `DELETE /assets/{id}`,
  `POST /assets/{id}/regenerate`, `GET /assets/stats`. Live status folds into `GET /assets/{id}`
  (manifest overlaid with registry progress). Register the router in `main.py` and re-export
  `docs/api/openapi.json`.
- **Backend `types/asset.py`** — `Asset`, `AssetArtifact`, `AssetStatus` (enum), `GenerationEngine`
  (enum), `GenerationParams`, `WriteAmplification`, `AssetCreateRequest`, `AssetUpdateRequest`,
  `AssetStats`, `EngineInfo`. All boundary data typed (no raw dicts across layers).
- **Frontend routes / components**:
  - `/library` — **sample-specific asset explorer (REQUIRED ADD)** scoped to the `library/` prefix:
    a grid of generated assets as cards (preview thumbnail, name, engine, status badge, artifact
    count, total size). Distinct from `/files` (which stays the full-bucket browse).
  - `/library/[id]` — **asset detail**: in-browser 3D viewer (`@google/model-viewer`, dynamic
    `ssr:false`, GLB via presigned inline URL), artifact table (kind, size, download), generation
    metadata (engine, device, timings), **write-amplification breakdown**, and the **edit / delete /
    regenerate** actions.
  - `/generate` — **New Asset (CREATE) form** (§4 form-UX rules): pick/upload source image, choose
    engine + params, submit. On success routes to the new asset's detail page (which polls status).
  - `components/assets/**` — asset-card, asset-grid, asset-3d-viewer (model-viewer wrapper),
    write-amp panel, generate-form, asset-actions (edit dialog, delete AlertDialog, regenerate).
  - Sidebar: add **Library** (icon e.g. `Boxes`) and **Generate** (`Sparkles`/`Wand2`) to `navItems`.
  - Dashboard rewrite (see §4).
- **Frontend data layer** — extend `apps/web/src/lib/api-client.ts` (`API_CLIENT_ROUTES` + fns),
  `apps/web/src/lib/queries.ts` (`useAssets`, `useAsset` w/ `refetchInterval` while `pending|running`,
  `useAssetStats`, `useCreateAsset`, `useUpdateAsset`, `useDeleteAsset`, `useRegenerateAsset`),
  `packages/shared/src/types.ts` (mirror the new Pydantic models). No bare `useEffect+fetch`.

## 3. B2 surface (S3-compatible only — no b2-native)

All via boto3 in `repo/` with the custom user agent. No b2-native API anywhere.
- `put_object` — input image (existing presign path), and server-side writes of mesh(.glb/.obj),
  texture maps, preview render, and `manifest.json`.
- `get_object` — download input for hashing + inference; read manifests.
- `head_object` — artifact/file metadata.
- `list_objects_v2` — bucket explorer, `library/` asset listing, stats (shared listing cache).
- `delete_object` / `delete_objects` — delete an asset's whole prefix.
- `generate_presigned_url` (GET) — serve meshes/textures/previews; **inline** disposition for the
  GLB so `model-viewer` can fetch it. Direct browser GET requires bucket CORS to allow GET/HEAD from
  the web origin (same mechanism the presigned PUT already needs — extend `scripts/setup_b2_cors.py`
  / docs to include GET+HEAD). Local-dev fallback: an API proxy GET (documented, not the default).
- `generate_presigned_url` (PUT) — existing presigned direct upload for the source image.

Key layout on B2: `inputs/<name>` (source images, via existing upload) and
`library/<sha256>/{manifest.json, mesh.glb, mesh.obj?, texture_<res>.png…, preview.png}`
(+ `runs/<version>/…` on regenerate). Generation outputs are written server-side with explicit
content types and **do not** pass through the upload allow-list, so `ALLOWED_TYPES` needs no change
(GLB/OBJ are never client-uploaded).

## 4. Key features (seed README + `docs/features/*` stubs)

Every feature is **`deployment: local`** — heavy work runs on-device; **no external API provider,
no external key, B2 credentials only**. Per `api-provider-selection.md`: the sample's whole point is
an on-device capability (TripoSR), so LOCAL is the default with GPU autodetect (CUDA→MPS→CPU);
estimated per-run external cost **$0**.

1. **Image → 3D generation** — TripoSR (default, local, MIT, CPU-capable w/ GPU autodetect);
   Hunyuan3D (optional, GPU-only extra); Procedural demo (no-ML, instant). `deployment: local`.
2. **B2 3D asset library** — every input, mesh, texture set, and preview render stored on B2,
   keyed by input content hash (dedup + versioning). `deployment: local`.
3. **Write-amplification dashboard** — objects & bytes written per generation and the aggregate
   input→output amplification ratio; storage by artifact type. `deployment: local`.
4. **In-browser 3D viewer** — `@google/model-viewer` renders the generated GLB from a presigned B2
   URL. `deployment: local`.
5. **Dual explorer** — kept full-bucket **Files** browser + added sample-scoped **Library**
   explorer. `deployment: local`.

### Primary entity — lifecycle (UI completeness)
**Entity: `Asset`** (one generated 3D model + its B2 artifacts, id = input content hash). All five
verbs are user-accessible and MUST be built — **`omitted_ui_verbs` is empty**:
- **create** — `/generate` form → `POST /assets` (uploads/points at the input, runs generation).
- **read** — `/library` grid + `/library/[id]` detail (3D viewer, artifacts, metadata).
- **edit** — asset detail: rename + edit tags → `PATCH /assets/{id}` (edits the manifest; editing the
  mesh geometry is out of scope — metadata is the honest edit verb here).
- **delete** — asset detail (and card) → `DELETE /assets/{id}` with an AlertDialog confirm; removes
  the asset's entire B2 prefix.
- **run** — asset detail "Regenerate" → `POST /assets/{id}/regenerate` (re-runs inference, optionally
  a different engine/params; bumps `version`).

### Form UX conventions
- **CREATE (`/generate`)** — model on `components/settings/settings-form.tsx` (Select + RadioGroup +
  FormDescription).
  - `engine` → **Select** (finite): TripoSR (default) / Hunyuan3D (GPU) / Demo (procedural).
    FormDescription explains each and the GPU requirement.
  - `texture_resolution` → **Select/RadioGroup** (finite): 2048 / 1024 (default) / 512.
  - `remove_background` → **Switch** (default on), with a one-line hint.
  - `name` → free text (open-ended; free text is correct here), optional.
  - source image → dropzone / picker (a resource selector, not a finite-value field).
  - Safe defaults surfaced as placeholder / FormDescription guidance for a sound first run
    (guidance only — **no autofill button**).
- **EDIT (asset detail)** — opens pre-filled; name = free text, tags = free-text chips; selector rule
  applies to any finite field (none here beyond what create covers). No create-only default hints.

### Dashboard rewrite (asset-library metrics)
Stat cards: total assets, total B2 objects written, total storage, **avg objects per generation** +
**amplification ratio (output bytes ÷ input bytes)**. Chart: storage growth or write-amp breakdown by
artifact type. Table: recent generations (name, engine, status, artifact count, size). All via
`GET /assets/stats` through `runtime→service→repo` + a TanStack-Query hook. Update `docs/features/dashboard.md`.

## 5. Doc transforms
- **Rewrite**: `README.md` (identity, quick start, generation flow, write-amp story, engine matrix
  incl. Hunyuan3D GPU extras, screenshots placeholder). Order for humans (global pref): quick start +
  visual proof early; deploy/governance lower; **keep a When-to-use / FAQ** (AEO). `ARCHITECTURE.md`
  (components: engines/ + assets service + library; data flows: generate→store→serve; data stores:
  `library/` + `inputs/`). `docs/features/dashboard.md` (asset metrics). `docs/app-workflows.md`
  (generate → store → browse journey).
- **Add stubs**: `docs/features/asset-generation.md` (engines, device autodetect, dedup/versioning,
  write amplification), `docs/features/asset-library.md` (Library explorer + 3D viewer + serving).
- **Keep**: `docs/features/file-browser.md`, `file-upload.md`, `metadata-extraction.md`, SECURITY,
  RELIABILITY, dev-workflows (update env-var names + any new engine setup notes).
- **AGENTS.md + shims**: keep agent-sized; add the two new features to the Doc Map / Core Features
  lists and note the `repo/engines/` adapter + `services/api/vendor/` boundary. Keep `CLAUDE.md`,
  `GEMINI.md`, `.github/copilot-instructions.md` as thin pointers.
- Move this plan to `docs/exec-plans/completed/initial-scaffold.md` on PASS (Phase 5).

## 6. Rename table (every identity surface)

| Kind | From (starter) | To |
|---|---|---|
| kebab slug | `vibe-coding-starter-kit` | `image-to-3d-asset-library` |
| Display / Title | `Vibe Coding Starter Kit` | `Image to 3D Asset Library` |
| `APP_NAME` (`apps/web/src/lib/app-config.ts`, **only** literal per branding gate) | `"Vibe Coding Starter Kit"` | `"Image to 3D Asset Library"` |
| `APP_DESCRIPTION` | file-mgmt template blurb | image→3D asset library on B2 blurb |
| `main.py` `API_TITLE` (**must equal** `${APP_NAME} API`) | `Vibe Coding Starter Kit API` | `Image to 3D Asset Library API` |
| `main.py` `API_DESCRIPTION` | mentions old name | must mention `Image to 3D Asset Library` |
| `docs/api/openapi.json` `info.title`/`description` | old | re-export via `pnpm contract:export` |
| root `package.json` `name` | `vibe-coding-starter-kit` | `image-to-3d-asset-library` |
| workspace pkg | `@vibe-coding-starter-kit/web` | `@image-to-3d-asset-library/web` |
| workspace pkg | `@vibe-coding-starter-kit/shared` | `@image-to-3d-asset-library/shared` |
| all `--filter` refs (root `package.json` scripts), `pnpm-workspace.yaml`, `apps/web/package.json`, `packages/shared/package.json`, and every `from "@vibe-coding-starter-kit/shared"` import (e.g. `queries.ts`) | old scope | new scope |
| `services/api/pyproject.toml` `[project].name` | old | `image-to-3d-asset-library-api` |
| **B2 attribution token** (branding gate: ONE value across every `user_agent_extra=` in `services/api/**/*.py` and every `utm_content=` in README/docs/`apps/web/src`/`scripts`) | `b2ai-oss-start` | `image-to-3d-asset-library` |
| infra/CI display strings referencing the old slug | `vibe-coding-starter-kit` | new slug (service names `web`/`api` stay) |

## 7. B2 env-var standardization → parent Standard #3 (REQUIRED)

Parent `../CLAUDE.md` mandates `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`,
`B2_REGION`, `B2_PUBLIC_URL_BASE`, and calls deviations defects. The starter deviates
(`B2_KEY_ID`, `B2_ENDPOINT`, `B2_PUBLIC_URL`, no `B2_REGION`). Rename to the standard (mechanical
sweep; does **not** touch the `check:agent-docs` gates, which key off `user_agent_extra`/`utm_content`,
`.env.example` existence, and gitignore — not var names):

| Starter env / attr | Standard #3 env / attr | Note |
|---|---|---|
| `B2_KEY_ID` / `b2_key_id` | `B2_APPLICATION_KEY_ID` / `b2_application_key_id` | |
| `B2_APPLICATION_KEY` / `b2_application_key` | *(unchanged)* | |
| `B2_BUCKET_NAME` / `b2_bucket_name` | *(unchanged)* | |
| `B2_ENDPOINT` / `b2_endpoint` | `B2_REGION` / `b2_region` (default `us-west-004`) | `get_s3_client` derives `endpoint_url = f"https://s3.{b2_region}.backblazeb2.com"`; keep an **optional** `B2_ENDPOINT` override (empty→derive) so custom endpoints still work |
| `B2_PUBLIC_URL` / `b2_public_url` | `B2_PUBLIC_URL_BASE` / `b2_public_url_base` | optional; empty default |

Sweep every reference: `services/api/app/config/settings.py`, `services/api/main.py`
(`REQUIRED_B2_SETTINGS` env names + `PLACEHOLDER_VALUES`), `services/api/app/repo/b2_client.py`
(endpoint construction), `.env.example` (new names + region example + refreshed placeholders),
`services/api/live_tests/`, `services/api/tests/**` + `conftest.py` (any env the tests set),
`scripts/*.mjs` + `services/api/scripts/*.py` (if they name env vars), `infra/**`, and docs
(README, ARCHITECTURE, SECURITY, dev-workflows). Grep `B2_KEY_ID|B2_ENDPOINT|B2_PUBLIC_URL|
b2_key_id|b2_endpoint|b2_public_url` to find them all. Run `pnpm run setup` then `pnpm verify:api`
to catch any missed reference.

## 8. Python dependencies (default install = CPU-installable, no CUDA/OpenGL)

Add to `services/api/requirements.txt` (lower-bound pins) and regenerate `requirements.lock` per
`docs/dev-workflows.md#python-dependency-updates`. Everything below installs on macOS arm64 CPU:
`torch` (CPU wheel), `numpy<2` (ML-ecosystem compat — see prior samples), `trimesh`, `PyMCubes`,
`huggingface_hub`, `safetensors`, `einops`, `omegaconf`, `matplotlib`, `rembg` **or** a lighter
`Pillow`-based background trim (rembg pulls onnxruntime — acceptable but pin it), plus existing
`Pillow`. **Do NOT add** `torchmcubes`, `moderngl`, `xatlas`, `pyglet`, or the Hunyuan3D CUDA
rasterizers to the default lock. Provide `services/api/requirements-hunyuan3d.txt` (optional, GPU
host only) for Hunyuan3D — lazy-imported, documented in the README, never installed by default/CI.
Pin decisively (unpinned torch/hf is a known false-green that breaks clean installs).

**Tests must not run the ML models or download weights.** Unit tests default to the `procedural`
engine and/or monkeypatch `get_engine`; assert dedup, write-amp math, manifest read/write,
delete-prefix, key validation, and all `/assets` routes with a **fake engine** returning tiny
deterministic bytes. `torch`/TripoSR are imported only inside `generate()`, so importing the repo
layer (and running CI) never pulls them.

## 9. Standards & gates the builder must satisfy before finishing
- S3-only; custom `user_agent_extra` on the single B2 client; Standard #3 env vars (§7).
- Layering intact (no boto3 outside `repo/`; no backward imports; routes call service not repo;
  authored `app/**` Python < 300 lines — vendored TripoSR lives OUTSIDE `app/`).
- Every route change re-exports `docs/api/openapi.json`; backend-only routes (none expected — all
  `/assets` routes are frontend-consumed) else go in `SERVER_ONLY_OPERATIONS`.
- `packages/shared` types mirror the Pydantic models; frontend imports `APP_NAME` (no stray literal).
- Tests added for every new behavior; docs updated in the same change.
- `pnpm run setup` succeeds, then **`pnpm verify` is green** (check:agent-docs → verify:api →
  verify:web). This is the definition of a clean build.
