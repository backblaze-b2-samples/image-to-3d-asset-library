<!-- last_verified: 2026-08-10 -->
# Feature: 3D Asset Library

## Purpose
Browse the generated 3D assets scoped to the `library/` prefix, view each mesh
in the browser, and download every artifact — the B2 bucket *is* the versioned
asset library.

## Used By
- UI: `/library` (grid), `/library/[id]` (detail + 3D viewer)
- API: `GET /assets`, `GET /assets/{id}`, `PATCH /assets/{id}`, `DELETE /assets/{id}`

## Core Functions
- `apps/web/src/components/assets/asset-grid.tsx` / `asset-card.tsx` — library grid
- `apps/web/src/components/assets/asset-detail.tsx` — detail (viewer, artifacts, metadata)
- `apps/web/src/components/assets/asset-3d-viewer.tsx` — `@google/model-viewer` wrapper
- `apps/web/src/components/assets/asset-actions.tsx` — edit / delete / regenerate
- `apps/web/src/components/assets/write-amp-panel.tsx` — per-asset amplification
- `apps/web/src/lib/queries.ts` — `useAssets`, `useAsset` (polls while generating), `useUpdateAsset`, `useDeleteAsset`
- `services/api/app/repo/asset_store.py` — `presign_inline`, `delete_prefix`, `list_prefix_objects`
- `services/api/app/repo/manifest.py` — `list_manifests`, `load_manifest`

## Canonical Files
- Serving adapter: `services/api/app/repo/asset_store.py`
- Detail component: `apps/web/src/components/assets/asset-detail.tsx`

## Inputs
- `id`: str — asset content hash (from the URL)
- Edit: `name` (free text), `tags` (free-text chips)

## Outputs
- `GET /assets` → `Asset[]` (grid; preview presigned)
- `GET /assets/{id}` → `Asset` (all artifacts presigned inline)
- `DELETE /assets/{id}` → removes the entire `library/<id>/` prefix from B2

## Flow
- `/library` renders a card grid from `useAssets()`; each card shows the preview,
  status, engine, object count, and size
- `/library/[id]` presigns every artifact and renders the GLB in an in-browser
  3D viewer, an artifact table with download links, generation metadata, and the
  write-amplification breakdown
- Edit updates the manifest (name/tags); Delete removes the B2 prefix; Regenerate
  re-runs inference (see [asset-generation.md](asset-generation.md))

## Serving meshes to the browser
`@google/model-viewer` fetches the GLB from a **presigned, inline-disposition**
B2 URL — a cross-origin request. The bucket must allow the web origin GET/HEAD:
run `services/api/scripts/setup_b2_cors.py --origin <web-origin> --apply` once
per deployed origin (it also covers the uploader's PUT). Local-dev fallback: an
API proxy GET could stream the object same-origin — documented, not the default.

## Edge Cases
- Asset still generating → detail page shows progress and auto-refreshes (2s poll)
- Failed asset → detail shows the recorded engine error
- Deleted asset → follow-up read is 404; the card disappears after invalidation
- Viewer can't load (missing bucket CORS) → the viewer surface stays blank;
  configure CORS as above

## UX States
- Grid: skeletons → cards; empty state with a "Generate" CTA
- Detail: skeleton → viewer/artifacts; failed/pending states handled inline

## Verification
- Test files: `services/api/tests/test_assets.py` (list/get/update/delete/regenerate)
- Required cases: list + preview url, get + all urls, update name/tags, prefix delete, 404
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Image → 3D Generation](asset-generation.md)
- [File Browser](file-browser.md) — the kept full-bucket explorer
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
