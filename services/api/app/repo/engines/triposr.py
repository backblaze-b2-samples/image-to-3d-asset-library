"""TripoSR engine — the default, core, local, MIT reconstruction (image -> 3D).

This is the sample's primary capability and it runs for real: it loads the
vendored TripoSR model (see services/api/vendor/triposr/, patched to use PyMCubes
on CPU) and the public `stabilityai/TripoSR` weights (downloaded from the Hugging
Face Hub on the FIRST real run only — never at install/CI), reconstructs a
vertex-colored mesh, exports GLB + OBJ, and derives a preview + multi-resolution
maps. No external API and no second key: B2 credentials only.

Every heavy import (torch, rembg, the vendored `tsr` package) is INSIDE
`generate()` / the cached loader, so importing this module never loads torch and
the hermetic test suite never touches it. Device is auto-detected CUDA -> MPS ->
CPU with a CPU fallback (see device.py).
"""

import functools
import io
import logging
import sys
import time
from pathlib import Path

from app.config import settings
from app.repo.engines import render
from app.repo.engines.base import EngineError, EngineResult
from app.repo.engines.device import select_device
from app.types import EngineInfo, GenerationEngine, GenerationParams

logger = logging.getLogger(__name__)

# services/api/vendor/triposr — repo/engines/triposr.py -> engines -> repo ->
# app -> api, then vendor/triposr.
_VENDOR_DIR = Path(__file__).resolve().parents[3] / "vendor" / "triposr"
_FOREGROUND_RATIO = 0.85
_CHUNK_SIZE = 8192


def _ensure_vendor_on_path() -> None:
    vendor = str(_VENDOR_DIR)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)


@functools.lru_cache(maxsize=1)
def _load_model(model_id: str, device: str):
    """Load + cache the TripoSR system on `device`. First call downloads the
    public weights via huggingface_hub; subsequent calls reuse the HF cache."""
    _ensure_vendor_on_path()
    from tsr.system import TSR

    logger.info("Loading TripoSR model=%s device=%s", model_id, device)
    model = TSR.from_pretrained(model_id, config_name="config.yaml", weight_name="model.ckpt")
    model.renderer.set_chunk_size(_CHUNK_SIZE)
    model.to(device)
    return model


def _preprocess(image_bytes: bytes, remove_bg: bool):
    import numpy as np
    from PIL import Image

    _ensure_vendor_on_path()
    img = Image.open(io.BytesIO(image_bytes))
    if not remove_bg:
        return img.convert("RGB")

    import rembg
    from tsr.utils import remove_background, resize_foreground

    img = remove_background(img, rembg.new_session())
    img = resize_foreground(img, _FOREGROUND_RATIO)
    arr = np.asarray(img).astype(np.float32) / 255.0
    if arr.shape[-1] == 4:  # composite over a neutral gray, as upstream does
        arr = arr[:, :, :3] * arr[:, :, 3:4] + 0.5 * (1.0 - arr[:, :, 3:4])
    return Image.fromarray((arr * 255.0).astype("uint8"))


class TripoSREngine:
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=GenerationEngine.TRIPOSR,
            label="TripoSR (local, MIT)",
            description=(
                "Default engine. Single-image 3D reconstruction with Stability AI's "
                "TripoSR, run locally. CPU-capable; auto-detects a CUDA/MPS GPU when "
                "present. Weights download once from the Hugging Face Hub."
            ),
            deployment="local",
            device_requirement="any",
            is_default=True,
            available=True,
        )

    def available(self) -> bool:
        return True

    def generate(self, image_bytes: bytes, params: GenerationParams) -> EngineResult:
        import torch

        device = select_device(settings.generation_device)
        model = _load_model(settings.triposr_model_id, device)
        image = _preprocess(image_bytes, params.remove_background)

        started = time.time()
        device_used = device
        try:
            mesh = self._reconstruct(model, image, device)
        except Exception:
            if device == "cpu":
                raise
            logger.warning("TripoSR failed on %s; retrying on CPU", device, exc_info=True)
            model = _load_model(settings.triposr_model_id, "cpu")
            mesh = self._reconstruct(model, image, "cpu")
            device_used = "cpu"

        glb = mesh.export(file_type="glb")
        obj = mesh.export(file_type="obj")
        if isinstance(obj, str):
            obj = obj.encode("utf-8")
        if not isinstance(glb, (bytes, bytearray)):
            raise EngineError("TripoSR GLB export did not return bytes")

        base = render.render_mesh_png(bytes(glb), params.texture_resolution)
        maps = render.multi_resolution_maps(
            base, render.resolution_ladder(params.texture_resolution)
        )
        preview = render.downsample_png(base, settings.preview_thumbnail_size)

        _ = torch  # torch import is what device selection + inference relied on
        return EngineResult(
            glb_bytes=bytes(glb),
            preview_png=preview,
            texture_maps=maps,
            obj_bytes=obj,
            stats={
                "engine": "triposr",
                "device_used": device_used,
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
                "generation_seconds": round(time.time() - started, 2),
                "mc_resolution": settings.triposr_mc_resolution,
            },
        )

    def _reconstruct(self, model, image, device: str):
        import torch

        with torch.no_grad():
            scene_codes = model([image], device=device)
            meshes = model.extract_mesh(
                scene_codes, True, resolution=settings.triposr_mc_resolution
            )
        return meshes[0]
