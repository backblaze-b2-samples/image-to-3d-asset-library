"""Runtime device selection for local ML generation.

Hard rule (see the plan / parent standards): default to CPU and auto-detect the
first available of CUDA -> Apple MPS -> CPU. Never hard-require a GPU. torch is
imported lazily so this module (and the engines package) import without it.
"""

import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


def _mps_available(torch) -> bool:
    backend = getattr(torch.backends, "mps", None)
    return bool(backend is not None and backend.is_available())


def cuda_available() -> bool:
    """True only if a CUDA GPU is actually usable (used by the GPU-only engine
    to report availability without importing its heavy pipeline)."""
    try:
        import torch
    except Exception:
        return False
    return bool(torch.cuda.is_available())


def select_device(requested: str | None = None) -> str:
    """Resolve the device string. Honors an explicit cpu/cuda/mps request when
    that accelerator is actually available, otherwise auto-detects
    CUDA -> MPS -> CPU. Always falls back to CPU.

    Also sets ``PYTORCH_ENABLE_MPS_FALLBACK=1`` so any TripoSR op unsupported on
    Apple MPS transparently falls back to the CPU implementation instead of
    raising.
    """
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    import torch

    req = (requested or settings.generation_device or "auto").lower()
    if req == "cpu":
        return "cpu"
    if req == "cuda" and torch.cuda.is_available():
        return "cuda"
    if req == "mps" and _mps_available(torch):
        return "mps"
    # "auto", or a requested accelerator that isn't present: detect.
    if torch.cuda.is_available():
        return "cuda"
    if _mps_available(torch):
        return "mps"
    return "cpu"
