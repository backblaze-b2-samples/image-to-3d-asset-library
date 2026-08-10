# Vendored: TripoSR (`tsr` package)

This directory contains the upstream **TripoSR** model code, vendored verbatim
except for two small, documented local patches. It lives under
`services/api/vendor/` — **outside** `services/api/app/` — on purpose: it is
third-party code, so it is exempt from our authored-code lint and the
`<300-line` structural test (which only scans `app/`).

## Source

- Repository: https://github.com/VAST-AI-Research/TripoSR
- Branch: `main`
- Files vendored: the `tsr/` Python package (`system.py`, `utils.py`,
  `models/**`) plus the upstream MIT `LICENSE`.
- License: MIT (see `LICENSE` in this directory). Model weights
  (`stabilityai/TripoSR`) are downloaded from the Hugging Face Hub at first run
  and are governed by their own model license — no weights are vendored here.

## Local patches (the only changes to upstream)

1. **PyMCubes instead of `torchmcubes`** — `tsr/models/isosurface.py`.
   Upstream imports `torchmcubes`, a CUDA C++ extension that fails to build on a
   macOS/CPU install. We replaced that import with a tiny
   `torchmcubes`-compatible `marching_cubes` shim backed by
   [PyMCubes](https://pypi.org/project/PyMCubes/) (`mcubes`), a dependency-light
   pure-CPU marching-cubes implementation. Same iso-level and axis handling; it
   just converts NumPy `(vertices, triangles)` back to the torch tensors the
   caller expects.

2. **No moderngl texture bake** — `tsr/bake_texture.py` was **removed**.
   Upstream's optional UV texture bake depends on `moderngl` (OpenGL) and
   `xatlas`, neither of which is available on a headless CPU install. This
   sample exports a **vertex-colored** GLB (via `extract_mesh(..., has_vertex_color=True)`)
   and derives multi-resolution preview/texture maps by rendering with
   matplotlib + downsampling with Pillow (see `app/repo/engines/render.py`). The
   upstream `requirements.txt` (which pinned `torchmcubes`, `moderngl`, and
   `xatlas`) was also removed; this sample's Python deps live in
   `services/api/requirements.txt`.

## How it is loaded

`app/repo/engines/triposr.py` adds this directory to `sys.path` and imports
`tsr.system.TSR` **lazily, inside `generate()`** — so importing the app (and
running the hermetic test suite) never loads torch or the model code, and never
downloads weights.
