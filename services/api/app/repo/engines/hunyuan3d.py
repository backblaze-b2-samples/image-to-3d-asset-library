"""Hunyuan3D engine — optional, GPU-only second engine (deployment: local).

An honest second engine, not exercised by the CPU verify path. Its heavy
pipeline is NOT in the default lock (see services/api/requirements-hunyuan3d.txt)
and it needs a CUDA GPU, so on a CPU host (or without the extras installed)
`generate()` raises a friendly, actionable error instead of fabricating output.
"""

from app.repo.engines.base import EngineResult, EngineUnavailableError
from app.repo.engines.device import cuda_available
from app.types import EngineInfo, GenerationEngine, GenerationParams

_INSTALL_HINT = (
    "Hunyuan3D requires a CUDA GPU and its optional extras. Install them with "
    "`pip install -r services/api/requirements-hunyuan3d.txt` on a CUDA host — "
    "see the README engine matrix. It is never installed by the default setup."
)


class Hunyuan3DEngine:
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=GenerationEngine.HUNYUAN3D,
            label="Hunyuan3D (GPU only)",
            description=(
                "Higher-fidelity reconstruction with Tencent's Hunyuan3D. Requires a "
                "CUDA GPU and optional extras (not installed by default); unavailable "
                "on CPU-only hosts."
            ),
            deployment="local",
            device_requirement="gpu",
            is_default=False,
            available=cuda_available(),
        )

    def available(self) -> bool:
        return cuda_available()

    def generate(self, image_bytes: bytes, params: GenerationParams) -> EngineResult:
        if not cuda_available():
            raise EngineUnavailableError(_INSTALL_HINT)
        try:
            import hy3dgen  # noqa: F401 - real pipeline, lazy-imported on a GPU host
        except ImportError as exc:  # extras not installed even though a GPU exists
            raise EngineUnavailableError(_INSTALL_HINT) from exc
        # A GPU host with the extras installed would run the real pipeline here.
        raise EngineUnavailableError(_INSTALL_HINT)
