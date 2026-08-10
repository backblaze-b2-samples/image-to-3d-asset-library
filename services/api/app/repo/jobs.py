"""Module-local, in-memory registry for the *live* generation run.

Durable status is the B2 manifest (`repo/manifest.py`); this registry only
tracks the in-flight run so `GET /assets/{id}` can report live progress while a
mesh is being reconstructed, and keeps the (blocking, CPU/GPU-bound) generation
off the event loop.

Single worker on purpose: local ML generation is memory-heavy, so runs are
serialized rather than thrashing the machine. Stdlib only — no boto3, no
service imports (the service passes the job body in as a callable).
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="asset-gen")
_lock = Lock()


@dataclass
class JobProgress:
    status: str = "pending"
    processed: int = 0
    total: int = 0
    message: str = ""


_jobs: dict[str, JobProgress] = {}


def register(asset_id: str, total: int, message: str = "Queued") -> None:
    with _lock:
        _jobs[asset_id] = JobProgress(
            status="pending", processed=0, total=total, message=message
        )


def update(
    asset_id: str,
    *,
    status: str | None = None,
    processed: int | None = None,
    total: int | None = None,
    message: str | None = None,
) -> None:
    with _lock:
        job = _jobs.get(asset_id)
        if job is None:
            job = JobProgress()
            _jobs[asset_id] = job
        if status is not None:
            job.status = status
        if processed is not None:
            job.processed = processed
        if total is not None:
            job.total = total
        if message is not None:
            job.message = message


def get(asset_id: str) -> JobProgress | None:
    with _lock:
        job = _jobs.get(asset_id)
        return JobProgress(**vars(job)) if job is not None else None


def clear(asset_id: str) -> None:
    with _lock:
        _jobs.pop(asset_id, None)


def submit(asset_id: str, run: Callable[[], None]) -> None:
    """Run `run()` on the single background worker. Exceptions are logged (the
    job body is responsible for recording failure in the manifest)."""

    def _wrapped() -> None:
        try:
            run()
        except Exception:
            logger.exception("Asset generation worker crashed for %s", asset_id)

    _executor.submit(_wrapped)


def _reset_state() -> None:
    """Test helper: forget all tracked jobs."""
    with _lock:
        _jobs.clear()
