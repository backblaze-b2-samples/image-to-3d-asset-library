"""Read/write the durable Asset manifest on B2.

B2 is the sole datastore — there is no database. Each asset's record lives at
`library/<id>/manifest.json`; listing the library is listing the manifests.
boto3 stays in repo/; this module reuses the shared client from `b2_client`.
"""

import io

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import (
    _fetch_all_objects,
    _invalidate_list_cache,
    get_s3_client,
)
from app.types import Asset

_MANIFEST_NAME = "manifest.json"


def asset_prefix(asset_id: str) -> str:
    return f"{settings.library_prefix}{asset_id}/"


def manifest_key(asset_id: str) -> str:
    return f"{asset_prefix(asset_id)}{_MANIFEST_NAME}"


def save_manifest(asset: Asset) -> None:
    """Persist the asset record. Artifact `url`s are ephemeral, so they are
    stripped before writing (a stale presigned URL must never be persisted)."""
    to_store = asset.model_copy(deep=True)
    for artifact in to_store.artifacts:
        artifact.url = None
    to_store.progress_message = None
    body = to_store.model_dump_json().encode("utf-8")
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=manifest_key(asset.id),
            Body=io.BytesIO(body),
            ContentType="application/json",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 save_manifest failed for '{asset.id}': {e}") from e
    _invalidate_list_cache()


def load_manifest(asset_id: str) -> Asset | None:
    client = get_s3_client()
    try:
        resp = client.get_object(
            Bucket=settings.b2_bucket_name, Key=manifest_key(asset_id)
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 load_manifest failed for '{asset_id}': {e}") from e
    return Asset.model_validate_json(resp["Body"].read())


def list_manifests() -> list[Asset]:
    """Load every asset manifest under the library prefix, newest first."""
    assets: list[Asset] = []
    seen: set[str] = set()
    suffix = f"/{_MANIFEST_NAME}"
    for obj in _fetch_all_objects(settings.library_prefix):
        key = obj["Key"]
        if not key.endswith(suffix):
            continue
        asset_id = key[len(settings.library_prefix) : -len(suffix)]
        if asset_id in seen:
            continue
        seen.add(asset_id)
        asset = load_manifest(asset_id)
        if asset is not None:
            assets.append(asset)
    assets.sort(key=lambda a: a.created_at, reverse=True)
    return assets
