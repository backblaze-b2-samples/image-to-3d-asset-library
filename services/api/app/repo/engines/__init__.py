"""Mesh-generation engine registry.

Instantiating an engine is cheap — every heavy import (torch, trimesh,
matplotlib, the vendored TripoSR) lives inside `generate()`, so importing this
package never loads ML or triggers a model download. The service layer calls
`get_engine(...)`; tests monkeypatch it with a fake engine returning tiny
deterministic bytes so the suite stays hermetic and never runs a model.
"""

from app.repo.engines.base import (
    EngineError,
    EngineResult,
    EngineUnavailableError,
    MeshEngine,
)
from app.repo.engines.hunyuan3d import Hunyuan3DEngine
from app.repo.engines.procedural import ProceduralEngine
from app.repo.engines.triposr import TripoSREngine
from app.types import EngineInfo, GenerationEngine


class UnknownEngineError(EngineError):
    """Raised when an engine name has no registered adapter."""


# Order is the UI order (default first).
_REGISTRY: dict[GenerationEngine, MeshEngine] = {
    GenerationEngine.TRIPOSR: TripoSREngine(),
    GenerationEngine.HUNYUAN3D: Hunyuan3DEngine(),
    GenerationEngine.PROCEDURAL: ProceduralEngine(),
}


def get_engine(name: GenerationEngine | str) -> MeshEngine:
    key = name if isinstance(name, GenerationEngine) else GenerationEngine(name)
    engine = _REGISTRY.get(key)
    if engine is None:
        raise UnknownEngineError(f"Unknown generation engine: {name}")
    return engine


def list_engine_info() -> list[EngineInfo]:
    """Metadata for every engine (name, label, deployment, device requirement,
    default flag, current availability) — powers the create form's selector."""
    return [engine.info() for engine in _REGISTRY.values()]


__all__ = [
    "EngineError",
    "EngineInfo",
    "EngineResult",
    "EngineUnavailableError",
    "Hunyuan3DEngine",
    "MeshEngine",
    "ProceduralEngine",
    "TripoSREngine",
    "UnknownEngineError",
    "get_engine",
    "list_engine_info",
]
