"""Mesh-generation engine contract (the external 'SDK', wrapped in repo/).

An engine turns one source image into a 3D mesh plus derived artifacts. Heavy
ML imports (torch, the vendored TripoSR) MUST stay inside `generate()` so that
importing this package never loads them — the app boots and the hermetic tests
run without torch, and no model weights are downloaded at import/CI time.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.types import EngineInfo, GenerationParams


class EngineError(Exception):
    """Generation failed for a reason worth surfacing to the user."""


class EngineUnavailableError(EngineError):
    """The selected engine cannot run here (e.g. a GPU-only engine on CPU, or an
    optional extra that isn't installed). Carries a friendly, actionable message
    — it never fabricates a result to hide the missing capability."""


@dataclass
class EngineResult:
    """Everything one generation produced, as bytes ready to write to B2."""

    glb_bytes: bytes
    preview_png: bytes
    texture_maps: dict[int, bytes] = field(default_factory=dict)
    obj_bytes: bytes | None = None
    # Free-form run telemetry (device_used, vertices, faces, seconds, ...).
    stats: dict = field(default_factory=dict)


@runtime_checkable
class MeshEngine(Protocol):
    def info(self) -> EngineInfo: ...

    def available(self) -> bool:
        """True if this engine can run in the current environment (e.g. a
        GPU-only engine returns False on a CPU-only host)."""
        ...

    def generate(self, image_bytes: bytes, params: GenerationParams) -> EngineResult:
        """Reconstruct a mesh from `image_bytes`. Blocking + CPU/GPU-bound; run
        it off the event loop (see repo/jobs.py). Raises on failure."""
        ...
