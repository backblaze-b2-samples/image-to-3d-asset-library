<!-- last_verified: 2026-08-10 -->
# Image to 3D Asset Library

Turn a single image into a 3D mesh, texture maps, and a preview render — all
stored in **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-image-to-3d-asset-library)**
as a versioned, content-addressed asset library. You upload a source image; a
local open-source engine (**TripoSR**, MIT) reconstructs a 3D mesh; the app
writes the mesh (GLB/OBJ), multi-resolution texture maps, and a dark preview
render to B2, keyed by the input's content hash for dedup and versioning.
Downstream consumers fetch every artifact via presigned S3 URLs — **the bucket
is the 3D asset library.**

It runs entirely on local, open-source models with **B2 credentials only — no
second API key and no per-generation cost.** GPU is optional: generation
auto-detects CUDA → Apple MPS → CPU and always falls back to CPU.

> **The headline lesson: write amplification.** One small input image fans out
> into many larger B2 objects — a mesh, several texture maps, a preview, and a
> manifest. A bulk asset library fills a bucket fast, and B2's flat per-GB
> pricing is exactly the point.

Built on the Backblaze [vibe-coding-starter-kit](https://www.backblaze.com/cloud-storage/b2-ai-integrations?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-image-to-3d-asset-library)
foundation (Next.js 16 + FastAPI), so it ships with a full dashboard UI, a
bucket file browser, direct-to-B2 upload, and the checked-in
[local OpenAPI contract](docs/api/openapi.json).

## What it looks like

Screenshots are captured per release. Locally, the app has four purpose-built
screens:

- **Dashboard** (`/`) — asset count, total B2 objects written, storage used, and
  the aggregate input→output **amplification ratio**, plus storage-by-artifact
  breakdown and recent generations.
- **Generate** (`/generate`) — upload a source image, pick an engine and
  settings, and start a reconstruction.
- **Library** (`/library`) — a grid of generated assets, and a per-asset detail
  page with an **in-browser 3D viewer**, artifact table, and write-amplification
  breakdown.
- **Files** (`/files`) — the full-bucket explorer (browse everything in B2, not
  just this app's output).

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.12, and a free
**[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-image-to-3d-asset-library)**.
The default install is CPU-only and works on macOS (Apple Silicon), Linux, and
WSL2 — no CUDA required. (Native Windows isn't supported; the dev scripts use
POSIX shell and `services/api/.venv/bin/*` paths — use WSL2.)

The first TripoSR generation downloads the public `stabilityai/TripoSR` weights
(~1.6 GB) from the Hugging Face Hub and caches them; no weights are downloaded
at install or in CI. Prefer a zero-download first run? Pick the **Demo
(procedural, no model)** engine.

**1. Setup**

```bash
pnpm run setup
```

Copies `.env.example` to `.env` (only if missing), installs workspace
dependencies from `pnpm-lock.yaml`, creates `services/api/.venv`, and installs
the committed Python 3.12 resolution from `services/api/requirements.lock`. Safe
to rerun.

> Use the `pnpm run` form: `setup` (like `doctor`) is a built-in pnpm command
> before pnpm 11, so bare `pnpm setup` would run pnpm's own command.

**2. Add your B2 credentials**

Open `.env` and fill in the standardized B2 variables. Create a bucket and a
`Read and Write` application key in the
[B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-image-to-3d-asset-library):

- `B2_APPLICATION_KEY_ID` ← the key's **keyID**
- `B2_APPLICATION_KEY` ← the key's **applicationKey** *(shown once)*
- `B2_BUCKET_NAME` ← your bucket's unique name
- `B2_REGION` ← your bucket's region, e.g. `us-west-004` (the S3 endpoint is
  **derived** from it: `https://s3.<region>.backblazeb2.com`)

`B2_PUBLIC_URL_BASE` is optional — leave it commented for a private bucket; the
app serves every mesh, texture, and preview via presigned URLs.

**3. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000` (Swagger UI at
`localhost:8000/docs`). Open **Generate**, drop in an image, and watch the mesh,
textures, and preview land in your bucket. `pnpm dev` runs `pnpm run doctor`
first to catch setup gotchas.

### Serving the 3D viewer from B2

The in-browser viewer (`@google/model-viewer`) fetches the GLB from a presigned
B2 URL, which is a cross-origin request. Allow your web origin GET/HEAD on the
bucket once per deployed origin:

```bash
services/api/.venv/bin/python services/api/scripts/setup_b2_cors.py --origin http://localhost:3000 --apply
```

## How it works

```
Source image ──(presigned PUT)──▶ B2 (uploads/)
      │
      ▼  POST /assets  (sha256 → asset id; dedup)
Local engine (TripoSR) reconstructs a vertex-colored mesh
      │
      ▼  server-side writes
B2  library/<hash>/
       manifest.json      ← the durable asset record (B2 is the only datastore)
       source.<ext>       ← the input, copied into the asset prefix
       mesh.glb, mesh.obj ← the reconstructed mesh
       texture_2048.png … ← multi-resolution maps (the write-amp fan-out)
       preview.png        ← dark, single-subject card thumbnail
      │
      ▼  presigned GET (inline)
model-viewer, artifact downloads, downstream consumers
```

The asset id is the source image's content hash, so re-uploading the same image
with the same engine + settings **dedups** to the same prefix; **Regenerate**
re-runs inference and bumps the asset version.

## Engine matrix

| Engine | Default | Deployment | Device | Notes |
|--------|:-------:|-----------|--------|-------|
| **TripoSR** | ✅ | local | CPU / CUDA / MPS (autodetect) | MIT. The core engine. Weights download once from the HF Hub. Vendored + patched to use PyMCubes on CPU (no `torchmcubes`, no OpenGL) — see `services/api/vendor/triposr/PROVENANCE.md`. |
| **Hunyuan3D** | — | local | CUDA **only** | Optional, higher fidelity. Not in the default lock; install `services/api/requirements-hunyuan3d.txt` on a GPU host. Raises a friendly error on a CPU host. |
| **Demo (procedural)** | — | local | any (no ML) | Instant, no model download — builds a real height-field mesh from the image. Great for a first run and used by CI. |

## Write amplification (the lesson)

Every generation turns one small image into a handful of larger B2 objects. The
dashboard aggregates this across your whole library — total objects written,
total storage, average objects per generation, and the **output-bytes ÷
input-bytes ratio** — and each asset's detail page shows its own breakdown. This
is the point of the sample: bulk 3D pipelines are write-heavy, and B2's flat
per-GB pricing makes durable, versioned artifact storage cheap.

## When to use

Use this as a template or reference when you are building a game / AR-XR / 3D
content pipeline that runs **bulk image-to-3D reconstruction** and needs durable,
versioned, shared storage for every artifact — with a real, working example of
local OSS inference writing content-addressed objects to Backblaze B2 over the
S3-compatible API.

## When not to use

Don't expect a hosted SaaS or a production 3D service. There is no managed
hosting, no user accounts, authentication, tenant isolation, or billing. Mesh
quality is bounded by the open-source engines (single-image reconstruction is
approximate). You own the product-specific security, operations, and support
decisions for anything you adapt.

## B2 surface (S3-compatible only)

All storage goes through boto3 in the `repo/` layer with a custom user agent —
**no b2-native API**. `put_object` (uploads + generated artifacts + manifest),
`get_object` (hashing/inference input + manifests), `head_object`,
`list_objects_v2` (bucket explorer, library listing, stats), `delete_objects`
(prefix-scoped asset delete), and `generate_presigned_url` (inline GET for the
viewer + downloads, PUT for the direct upload).

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm run setup` | Idempotently copy `.env.example` to `.env` only if missing, install workspace dependencies, create the backend venv, and install the locked API dependencies |
| `pnpm run doctor` | Preflight environment check (also runs automatically before `pnpm dev`) |
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm contract:export` | Export deterministic FastAPI OpenAPI JSON to `docs/api/openapi.json` |
| `pnpm contract:check` | Verify the checked-in OpenAPI artifact and frontend API client route registry |
| `pnpm check:agent-docs` | Validate agent shims, command docs, CI claims, and `.env` ignore coverage |
| `pnpm verify` | Credential-free canonical non-live pre-PR suite — runs `check:agent-docs`, `verify:api`, then `verify:web` |
| `pnpm verify:api` | Backend half: API lint, API tests, structure tests |
| `pnpm verify:web` | Frontend half: web lint, web unit tests, web typecheck + build |
| `pnpm verify:full` | `pnpm run doctor`, then `pnpm verify`, then Playwright E2E; requires populated `.env`, local server/browser permission, port 3000 free, and Chromium installed |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:web` | Run frontend unit tests (vitest) |
| `pnpm test:api` | Run backend tests |
| `pnpm test:live:b2` | Opt-in real B2 connectivity test; requires `RUN_LIVE_B2_TESTS=1` and non-production credentials |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright E2E smoke tests (run `pnpm --filter @image-to-3d-asset-library/web exec playwright install chromium` once first) |

Run `pnpm run setup` once before local development and after pulling dependency
changes. If you add a Node dependency, run `pnpm install` to refresh
`pnpm-lock.yaml`; for an API dependency, follow the reviewed refresh workflow in
[docs/dev-workflows.md](docs/dev-workflows.md#python-dependency-updates). Run
`pnpm verify` before opening a PR (it needs `services/api/.venv` from setup),
and `pnpm verify:full` when you can start the local app stack and browser tests.
`pnpm verify` needs neither B2 credentials nor a browser; the backend tests use
a fake engine and never download model weights.

## Deploying to Vercel

This app deploys to Vercel as **one project** using Vercel
[Services](https://vercel.com/docs/services): the Next.js web app and the
FastAPI API build from the same repo and share a single origin — web at `/`, API
under `/api`. One click, one project, no CORS between them and no wiring two URLs
together.

[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Fimage-to-3d-asset-library&project-name=image-to-3d-asset-library&env=B2_APPLICATION_KEY_ID,B2_APPLICATION_KEY,B2_BUCKET_NAME,B2_REGION&envDescription=B2%20credentials%2C%20bucket%2C%20and%20region&envLink=https%3A%2F%2Fgithub.com%2Fbackblaze-b2-samples%2Fimage-to-3d-asset-library%2Fblob%2Fmain%2Finfra%2Fvercel%2FREADME.md)

Set the four B2 variables. The web app reaches the API at the same-origin `/api`
automatically (no `NEXT_PUBLIC_API_URL` needed). Note: TripoSR reconstruction is
CPU/GPU-heavy and long-running — Vercel serverless functions are a poor fit for
the generation step, so treat the button as a preview of the UI/bucket surface
and run generation on a machine you control (local, or a GPU host for
Hunyuan3D). The bucket must allow your deploy origin in its CORS (GET/HEAD for
the viewer, PUT for uploads — see `services/api/scripts/setup_b2_cors.py`). Full
variable classification, the two-Project alternative, and rollback live in the
[Vercel delivery contract](infra/vercel/README.md). Deploying is a
human-approved action — nothing here performs one for you.

## Agent-First Architecture

[AGENTS.md](AGENTS.md) is the single source of truth for coding agents:
repository layout, the strict `types → config → repo → service → runtime`
layering, commands, and conventions. Architecture is enforced **mechanically**
— structural tests keep `boto3` in `repo/`, forbid backward imports, and cap
authored `app/` Python files at 300 lines (the vendored TripoSR model lives
outside `app/`, under `services/api/vendor/`). External engines are wrapped as
`repo/engines/` adapters; heavy ML imports are lazy, inside `generate()`.

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
services/api/      FastAPI backend (types/config/repo/service/runtime)
  app/repo/engines/  mesh-generation adapters (TripoSR, Hunyuan3D, procedural)
  vendor/triposr/    vendored, MIT-licensed TripoSR model code (+ PROVENANCE.md)
packages/shared/   Shared TypeScript types (mirror the Pydantic models)
docs/              System of record (features, workflows, security, reliability)
```

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/asset-generation.md](docs/features/asset-generation.md) | Engines, device autodetect, dedup/versioning, write amplification |
| [docs/features/asset-library.md](docs/features/asset-library.md) | Library explorer, 3D viewer, presigned serving |
| [docs/features/dashboard.md](docs/features/dashboard.md) | Asset-library metrics |
| [docs/features/](docs/features/) | Kept file browser, upload, metadata docs |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/api/openapi.json](docs/api/openapi.json) | Checked contract for the local FastAPI API |
| [infra/vercel/README.md](infra/vercel/README.md) | Vercel deployment contract |

## FAQ

**What is the Image to 3D Asset Library?**
A full-stack sample (Next.js 16 + FastAPI) that reconstructs a 3D mesh, textures,
and a preview from a single image with a local open-source engine (TripoSR) and
stores every artifact in Backblaze B2 as a versioned, content-addressed library.

**Does it need a GPU or an API key?**
Neither. It runs on B2 credentials only, with no external model provider. TripoSR
is CPU-capable and auto-detects a CUDA/MPS GPU when present. Hunyuan3D is an
optional GPU-only extra.

**How much does a generation cost?**
$0 in external API fees — the models run on your machine. Your only cost is B2
storage for the artifacts, which is the write-amplification lesson the dashboard
makes concrete.

**Where do the model weights come from?**
`stabilityai/TripoSR` (MIT) downloads once from the Hugging Face Hub on the first
real run and is cached. No weights are downloaded at install or in CI.

**Why is the mesh vertex-colored instead of UV-textured?**
The upstream TripoSR texture bake needs OpenGL (`moderngl`/`xatlas`), which isn't
available on a headless CPU install, so this sample exports a vertex-colored GLB
and derives multi-resolution preview/texture maps by rendering with matplotlib
and downsampling with Pillow. See `services/api/vendor/triposr/PROVENANCE.md`.

**Do I have to use Backblaze B2?**
Yes — B2 (via the S3-compatible API) is the datastore this sample is built
around. You supply your own bucket and application key at setup.

**Is it really built for AI coding agents?**
Yes. [AGENTS.md](AGENTS.md) is the single source of truth and the boundaries are
enforced by tests and lints, so an agent can read the repo and start contributing.

**Where do I get help or report bugs?**
Report repository defects through
[GitHub Issues](https://github.com/backblaze-b2-samples/image-to-3d-asset-library/issues).
For B2 account, billing, or API help, use
[Backblaze Support](https://www.backblaze.com/help?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-image-to-3d-asset-library).

## Maintenance and support

Backblaze maintains this open-source sample to help developers build on B2.
Production use is possible with caution and requires your own validation. Report
defects through
[GitHub Issues](https://github.com/backblaze-b2-samples/image-to-3d-asset-library/issues);
for B2 account, billing, service, or API help, use
[Backblaze Support](https://www.backblaze.com/help?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-image-to-3d-asset-library).
This sample is not covered by the Backblaze service level agreement.

## Contributing

Start with [AGENTS.md](AGENTS.md) — everything else is discoverable from there.
For local commit hooks, follow [the pre-commit workflow](docs/dev-workflows.md#pre-commit).

## License

MIT License - see [LICENSE](LICENSE) for details. The vendored TripoSR code under
`services/api/vendor/triposr/` is also MIT (upstream license included there).
