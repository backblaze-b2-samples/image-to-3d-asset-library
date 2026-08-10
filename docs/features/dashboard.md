<!-- last_verified: 2026-08-10 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the 3D asset library and its write amplification —
how many assets exist, how many B2 objects and bytes they produced, and the
aggregate input→output amplification ratio.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /assets/stats`, `GET /assets`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (assets, B2 objects written, storage used, amplification ratio)
- `apps/web/src/components/dashboard/upload-chart.tsx` — `StorageBreakdownChart`, storage-by-artifact-type bar chart
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — `RecentGenerationsTable`, recent generations (name, engine, status, objects, size)
- `apps/web/src/lib/queries.ts` — `useAssetStats()`, `useAssets()`
- `services/api/app/runtime/assets.py` — `GET /assets/stats` handler
- `services/api/app/service/asset_stats.py` — `compute_stats()` aggregation

## Canonical Files
- Stats aggregation: `services/api/app/service/asset_stats.py`
- Dashboard cards: `apps/web/src/components/dashboard/stats-cards.tsx`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /assets/stats` → `AssetStats` (total_assets, total_objects, total_bytes(_human), input_bytes, output_bytes(_human), avg_objects_per_generation, amplification_ratio, by_artifact_type)
- `GET /assets` → `Asset[]` for the recent-generations table (newest first)

## Flow
- Page loads → `useAssetStats()` + `useAssets()` fire via TanStack Query
- Stat cards show total assets, total B2 objects written (with avg per
  generation), storage used, and the amplification ratio (output ÷ input bytes)
- The chart shows bytes written per artifact kind (source, mesh, textures,
  preview) — where the write amplification goes
- The table lists recent generations with a status badge; each row links to the
  asset detail page

## Edge Cases
- API unavailable → inline `ErrorState` with retry
- No assets yet → empty chart + empty table messages
- Assets mid-generation → counted in `total_assets`; their (empty) artifact sets
  don't inflate byte totals until they complete

## UX States
- Loading: `LoadingNotice` above the cards + skeletons for cards, chart, table
- Empty: "No artifacts yet" / "No generations yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_assets.py` (`test_stats_aggregate`), frontend build/typecheck
- Required cases: stats with assets, empty library, amplification math
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when the E2E/live prerequisites in [Dev Workflows](../dev-workflows.md#commands) are available
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Image → 3D Generation](asset-generation.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
