"""Procedural 'fast demo' engine (deployment: local, NO ML).

Deterministically turns the source image into a real 3D mesh: the image's
luminance becomes a height field and its colors become vertex colors, so the
same image always yields the same mesh. Instant, dependency-light (trimesh +
Pillow + numpy), and downloads nothing — this is the zero-friction first-run
option and the honest 'Demo (procedural, no model)' engine in the UI. It never
replaces TripoSR as the default.
"""

import hashlib
import io

from app.config import settings
from app.repo.engines import render
from app.repo.engines.base import EngineResult
from app.types import EngineInfo, GenerationEngine, GenerationParams

_GRID = 48  # heightfield resolution; ~4.4k faces — renders instantly


class ProceduralEngine:
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=GenerationEngine.PROCEDURAL,
            label="Demo (procedural, no model)",
            description=(
                "Instant, no-ML placeholder: builds a real height-field mesh from "
                "the image's brightness and colors. No model download — ideal for a "
                "first run or CI. Not a substitute for a learned reconstruction."
            ),
            deployment="local",
            device_requirement="any",
            is_default=False,
            available=True,
        )

    def available(self) -> bool:
        return True

    def generate(self, image_bytes: bytes, params: GenerationParams) -> EngineResult:
        import numpy as np
        import trimesh
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        small = img.resize((_GRID, _GRID), Image.LANCZOS)
        rgb = np.asarray(small, dtype=float) / 255.0
        gray = rgb.mean(axis=2)

        xs, ys = np.meshgrid(
            np.linspace(-1.0, 1.0, _GRID), np.linspace(-1.0, 1.0, _GRID)
        )
        z = (gray - gray.mean()) * 0.6
        verts = np.stack([xs.ravel(), ys.ravel(), z.ravel()], axis=1)

        faces = []
        for i in range(_GRID - 1):
            for j in range(_GRID - 1):
                a = i * _GRID + j
                b, c, d = a + 1, a + _GRID, a + _GRID + 1
                faces.append([a, b, d])
                faces.append([a, d, c])
        faces = np.asarray(faces)

        colors = (rgb.reshape(-1, 3) * 255).astype(np.uint8)
        vcolors = np.concatenate(
            [colors, np.full((len(colors), 1), 255, dtype=np.uint8)], axis=1
        )
        mesh = trimesh.Trimesh(
            vertices=verts, faces=faces, vertex_colors=vcolors, process=False
        )

        glb = mesh.export(file_type="glb")
        obj = mesh.export(file_type="obj")
        if isinstance(obj, str):
            obj = obj.encode("utf-8")

        seed = int.from_bytes(hashlib.sha256(image_bytes).digest()[:4], "big")
        base = render.render_mesh_png(glb, params.texture_resolution, seed=seed)
        maps = render.multi_resolution_maps(
            base, render.resolution_ladder(params.texture_resolution)
        )
        preview = render.downsample_png(base, settings.preview_thumbnail_size)

        return EngineResult(
            glb_bytes=glb,
            preview_png=preview,
            texture_maps=maps,
            obj_bytes=obj,
            stats={
                "engine": "procedural",
                "device_used": "cpu",
                "vertices": len(verts),
                "faces": len(faces),
            },
        )
