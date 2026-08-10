"""Image -> 3D asset orchestration.

Business logic only: it calls the repo layer (B2 + engines + the in-memory job
registry) and returns typed Pydantic models. boto3 stays in repo/; routes stay
thin. B2 is the sole datastore — the manifest at `library/<id>/manifest.json`
is the durable record, and one input image fans out into many B2 objects
(the write-amplification story).
"""

import contextlib
import logging
import mimetypes
import os
from datetime import UTC, datetime

from app.repo import asset_store, engines, jobs, manifest
from app.repo.engines.base import EngineResult
from app.service import asset_stats as stats_mod
from app.service.assets_hash import short_content_hash
from app.types import (
    TEXTURE_RESOLUTIONS,
    ArtifactKind,
    Asset,
    AssetArtifact,
    AssetCreateRequest,
    AssetStats,
    AssetStatus,
    AssetUpdateRequest,
    EngineInfo,
    GenerationEngine,
    GenerationParams,
    RegenerateRequest,
    WriteAmplification,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".jfif", ".bmp")


class AssetNotFoundError(Exception):
    def __init__(self, detail: str = "Asset not found"):
        self.detail = detail
        super().__init__(detail)


class AssetInputError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class AssetStateError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def list_engines() -> list[EngineInfo]:
    return engines.list_engine_info()


def _validate_params(engine: GenerationEngine, texture_resolution: int) -> GenerationParams:
    if texture_resolution not in TEXTURE_RESOLUTIONS:
        raise AssetInputError(
            f"texture_resolution must be one of {list(TEXTURE_RESOLUTIONS)}"
        )
    return GenerationParams(engine=engine, texture_resolution=texture_resolution)


def _load_source(input_key: str) -> tuple[bytes, str, str]:
    """Return (bytes, content_type, filename) for the source image, or raise
    AssetInputError if it is missing or not an image."""
    head = asset_store.object_head(input_key)
    if head is None:
        raise AssetInputError(f"Source image not found in bucket: '{input_key}'")
    filename = os.path.basename(input_key.rstrip("/")) or "source"
    content_type = head.get("ContentType") or mimetypes.guess_type(filename)[0] or ""
    is_image = content_type.startswith("image/") or filename.lower().endswith(_IMAGE_EXTS)
    if not is_image:
        raise AssetInputError("Source must be an image (jpg, png, webp, ...)")
    return asset_store.get_bytes(input_key), content_type or "image/png", filename


def create_asset(req: AssetCreateRequest) -> Asset:
    params = _validate_params(req.engine, req.texture_resolution)
    params.remove_background = req.remove_background
    data, content_type, filename = _load_source(req.input_key)
    asset_id = short_content_hash(data)

    existing = manifest.load_manifest(asset_id)
    if (
        existing is not None
        and existing.status == AssetStatus.COMPLETE
        and existing.params == params
    ):
        # Content + engine + params match a finished asset: dedup, don't re-run.
        return _with_all_urls(existing)

    now = datetime.now(UTC)
    version = existing.version if existing is not None else 1
    name = (req.name or "").strip() or os.path.splitext(filename)[0]
    asset = Asset(
        id=asset_id,
        name=name,
        params=params,
        input_key=req.input_key,
        input_filename=filename,
        input_bytes=len(data),
        version=version,
        status=AssetStatus.PENDING,
        created_at=existing.created_at if existing else now,
        updated_at=now,
        tags=existing.tags if existing else [],
    )
    _submit_generation(asset, content_type)
    # Return the freshest persisted state: pending in production (the async job
    # has not run yet, so no artifacts to presign), already complete under the
    # inline execution the tests use.
    return get_asset(asset.id)


def regenerate_asset(asset_id: str, req: RegenerateRequest) -> Asset:
    asset = _require(asset_id)
    if asset.status in (AssetStatus.PENDING, AssetStatus.RUNNING):
        raise AssetStateError("A generation for this asset is already running")
    engine = req.engine or asset.params.engine
    resolution = req.texture_resolution or asset.params.texture_resolution
    params = _validate_params(engine, resolution)
    params.remove_background = (
        req.remove_background
        if req.remove_background is not None
        else asset.params.remove_background
    )
    data, content_type, filename = _load_source(asset.input_key)
    asset.params = params
    asset.input_filename = filename
    asset.input_bytes = len(data)
    asset.version += 1
    asset.status = AssetStatus.PENDING
    asset.error = None
    asset.updated_at = datetime.now(UTC)
    _submit_generation(asset, content_type)
    return get_asset(asset.id)


def _submit_generation(asset: Asset, source_content_type: str) -> None:
    manifest.save_manifest(asset)
    jobs.register(asset.id, total=1, message="Queued")
    jobs.submit(asset.id, lambda: _run_generation(asset.id, source_content_type))


def _run_generation(asset_id: str, source_content_type: str) -> None:
    asset = manifest.load_manifest(asset_id)
    if asset is None:
        return
    asset.status = AssetStatus.RUNNING
    asset.updated_at = datetime.now(UTC)
    manifest.save_manifest(asset)
    jobs.update(asset_id, status="running", message="Reconstructing mesh")

    try:
        data = asset_store.get_bytes(asset.input_key)
        engine = engines.get_engine(asset.params.engine)
        result = engine.generate(data, asset.params)
        artifacts = _write_artifacts(asset, data, source_content_type, result)
        asset.artifacts = artifacts
        asset.device_used = result.stats.get("device_used")
        gen_s = result.stats.get("generation_seconds")
        asset.generation_seconds = float(gen_s) if gen_s is not None else None
        asset.write_amplification = _amplification(artifacts, len(data))
        asset.status = AssetStatus.COMPLETE
        asset.error = None
        jobs.update(asset_id, status="complete", processed=1, message="Complete")
    except Exception as exc:
        asset.status = AssetStatus.FAILED
        asset.error = str(exc)[:500]
        jobs.update(asset_id, status="failed", message=asset.error)
        logger.error("Asset generation failed: id=%s", asset_id, exc_info=True)
    finally:
        asset.updated_at = datetime.now(UTC)
        manifest.save_manifest(asset)


def _write_artifacts(
    asset: Asset, source_bytes: bytes, source_content_type: str, result: EngineResult
) -> list[AssetArtifact]:
    prefix = manifest.asset_prefix(asset.id)
    ext = os.path.splitext(asset.input_filename)[1].lower() or ".png"
    plan: list[tuple[ArtifactKind, str, bytes, str, int | None]] = [
        (ArtifactKind.SOURCE, f"{prefix}source{ext}", source_bytes, source_content_type, None),
        (ArtifactKind.MESH_GLB, f"{prefix}mesh.glb", result.glb_bytes, "model/gltf-binary", None),
        (ArtifactKind.PREVIEW, f"{prefix}preview.png", result.preview_png, "image/png", None),
    ]
    if result.obj_bytes:
        plan.append((ArtifactKind.MESH_OBJ, f"{prefix}mesh.obj", result.obj_bytes, "text/plain", None))
    for res, png in sorted(result.texture_maps.items(), reverse=True):
        plan.append((ArtifactKind.TEXTURE, f"{prefix}texture_{res}.png", png, "image/png", res))

    artifacts: list[AssetArtifact] = []
    for kind, key, data, ctype, resolution in plan:
        size = asset_store.put_bytes(key, bytes(data), ctype)
        artifacts.append(
            AssetArtifact(
                kind=kind,
                key=key,
                size_bytes=size,
                size_human=humanize_bytes(size),
                content_type=ctype,
                resolution=resolution,
            )
        )
    return artifacts


def _amplification(artifacts: list[AssetArtifact], input_bytes: int) -> WriteAmplification:
    output_bytes = sum(a.size_bytes for a in artifacts if a.kind != ArtifactKind.SOURCE)
    ratio = round(output_bytes / input_bytes, 2) if input_bytes > 0 else 0.0
    return WriteAmplification(
        input_bytes=input_bytes,
        output_bytes=output_bytes,
        object_count=len(artifacts) + 1,  # +1 for manifest.json
        ratio=ratio,
        input_bytes_human=humanize_bytes(input_bytes),
        output_bytes_human=humanize_bytes(output_bytes),
    )


def list_assets() -> list[Asset]:
    """Every asset, newest first, with only the preview presigned (cheap grid)."""
    return [_overlay(_with_preview_url(a)) for a in manifest.list_manifests()]


def get_asset(asset_id: str) -> Asset:
    return _overlay(_with_all_urls(_require(asset_id)))


def update_asset(asset_id: str, req: AssetUpdateRequest) -> Asset:
    asset = _require(asset_id)
    if req.name is not None:
        asset.name = req.name.strip()
    if req.tags is not None:
        asset.tags = [t.strip() for t in req.tags if t.strip()]
    asset.updated_at = datetime.now(UTC)
    manifest.save_manifest(asset)
    return _overlay(_with_all_urls(asset))


def delete_asset(asset_id: str) -> int:
    _require(asset_id)
    jobs.clear(asset_id)
    return asset_store.delete_prefix(manifest.asset_prefix(asset_id))


def asset_stats() -> AssetStats:
    return stats_mod.compute_stats(manifest.list_manifests())


def _require(asset_id: str) -> Asset:
    asset = manifest.load_manifest(asset_id)
    if asset is None:
        raise AssetNotFoundError()
    return asset


def _with_preview_url(asset: Asset) -> Asset:
    for artifact in asset.artifacts:
        if artifact.kind == ArtifactKind.PREVIEW:
            artifact.url = asset_store.presign_inline(artifact.key)
    return asset


def _with_all_urls(asset: Asset) -> Asset:
    for artifact in asset.artifacts:
        artifact.url = asset_store.presign_inline(artifact.key)
    return asset


def _overlay(asset: Asset) -> Asset:
    """Overlay live registry progress while a run is in flight (durable status
    still comes from the manifest for terminal states)."""
    progress = jobs.get(asset.id)
    if progress is not None and asset.status in (
        AssetStatus.PENDING,
        AssetStatus.RUNNING,
    ):
        with contextlib.suppress(ValueError):
            asset.status = AssetStatus(progress.status)
        asset.progress_message = progress.message or None
    return asset
