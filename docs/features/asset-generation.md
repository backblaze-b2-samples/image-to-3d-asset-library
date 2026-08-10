<!-- last_verified: 2026-08-10 -->
# Feature: Image → 3D Generation

## Purpose
Reconstruct a 3D mesh, texture maps, and a preview render from a single source
image with a local open-source engine, and persist every artifact to Backblaze
B2 — content-addressed for dedup and versioning.

## Used By
- UI: `/generate` (create form), `/library/[id]` (Regenerate action)
- API: `POST /assets`, `POST /assets/{id}/regenerate`, `GET /assets/engines`
- Job: single-worker in-memory registry (`repo/jobs.py`) runs generation off the
  event loop; durable status is the B2 manifest

## Core Functions
- `services/api/app/service/assets.py` — `create_asset`, `regenerate_asset`, `_run_generation`, `_write_artifacts`, `_amplification`
- `services/api/app/service/assets_hash.py` — `short_content_hash` (sha256 → asset id)
- `services/api/app/repo/engines/` — `get_engine`, `list_engine_info`, and the engines:
  - `triposr.py` — default; loads the vendored TripoSR + public weights (lazy)
  - `hunyuan3d.py` — optional GPU-only; friendly error on CPU / when extras absent
  - `procedural.py` — no-ML height-field mesh; instant, no download
  - `device.py` — CUDA → MPS → CPU autodetect (never requires a GPU)
  - `render.py` — headless matplotlib preview + Pillow multi-resolution maps
- `services/api/app/repo/asset_store.py` / `manifest.py` — B2 writes + manifest

## Canonical Files
- Engine contract: `services/api/app/repo/engines/base.py`
- Default engine: `services/api/app/repo/engines/triposr.py`
- Vendored model: `services/api/vendor/triposr/` (+ `PROVENANCE.md`)

## Inputs
- `input_key`: str — an already-uploaded source image (from the presigned PUT flow)
- `engine`: `triposr | hunyuan3d | procedural` (Select, default TripoSR)
- `texture_resolution`: `2048 | 1024 | 512` (default 1024)
- `remove_background`: bool (default true)
- `name`: str (optional; defaults to the filename stem)

## Outputs
- `Asset` (manifest) at `library/<hash>/manifest.json`
- B2 objects: `source.<ext>`, `mesh.glb`, `mesh.obj`, `texture_<res>.png…`, `preview.png`
- `write_amplification`: input bytes, output bytes, object count, ratio

## Flow
- Upload the source (presigned PUT → `uploads/`), then `POST /assets`
- Service downloads the input, hashes it (sha256 → id), and **dedups**: a
  complete manifest for the same content + engine + params is returned as-is
- Otherwise a `pending` manifest is written and the run is submitted to the job
  registry; status advances `pending → running → complete|failed`
- The engine reconstructs the mesh (device autodetected); artifacts are written
  under `library/<id>/` and the manifest is finalized
- Regenerate re-runs (optionally different engine/params) and bumps `version`

## Edge Cases
- Missing/non-image `input_key` → 400
- Invalid `texture_resolution` → 400
- Hunyuan3D on a CPU host → the run fails with a friendly, actionable error
  recorded in the manifest (never fabricated output)
- MPS op unsupported by TripoSR → `PYTORCH_ENABLE_MPS_FALLBACK=1` + a CPU retry

## UX States
- Create form: dropzone + engine/resolution/background controls with safe-default hints
- Detail while generating: spinner + live progress message (polled every 2s)
- Failed: error surfaced on the detail page

## Verification
- Test files: `services/api/tests/test_assets.py` (fake engine, hermetic — no model download)
- Required cases: generate+complete, dedup, write-amp math, regenerate/version bump, engine catalog, input validation
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green; real TripoSR runs are exercised manually with weights, not in CI

## Related Docs
- [3D Asset Library](asset-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
