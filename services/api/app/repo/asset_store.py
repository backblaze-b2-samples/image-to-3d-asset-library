"""B2 object operations for the 3D asset library (S3-compatible API only).

boto3/botocore live only in repo/. This module reuses the shared, connection-
pooled S3 client from `b2_client` and adds the object ops the asset library
needs: writing generation artifacts, downloading the source image for hashing +
inference, presigning meshes/textures/previews for the browser, and deleting an
asset's entire `library/<id>/` prefix.
"""

import io

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import (
    _fetch_all_objects,
    _invalidate_list_cache,
    get_s3_client,
)


def put_bytes(key: str, data: bytes, content_type: str) -> int:
    """Write one object and return its byte length. Raises RuntimeError on S3
    failure. Invalidates the shared listing cache so the new object shows up in
    /files and the library immediately."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e
    _invalidate_list_cache()
    return len(data)


def get_bytes(key: str) -> bytes:
    """Download an object's full body. Raises RuntimeError on any S3 failure
    (including not-found — callers that must distinguish should head first)."""
    client = get_s3_client()
    try:
        resp = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return resp["Body"].read()
    except ClientError as e:
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e


def object_head(key: str) -> dict | None:
    """HEAD an object; return its metadata dict or None if it does not exist."""
    client = get_s3_client()
    try:
        return client.head_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise RuntimeError(f"B2 head failed for '{key}': {e}") from e


def presign_inline(key: str, expires_in: int = 900) -> str:
    """Presigned GET URL with an inline disposition, so `@google/model-viewer`
    and `<img>` render the object directly instead of downloading it. Raises
    RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.b2_bucket_name,
                "Key": key,
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def list_prefix_objects(prefix: str) -> list[dict]:
    """Every object under `prefix` (paginated). Used for stats + delete."""
    return _fetch_all_objects(prefix)


def delete_prefix(prefix: str) -> int:
    """Delete every object under `prefix` in batches (delete_objects caps at
    1000 keys/request). Prefix-scoped on purpose so an asset delete never
    touches another asset's or another app's data. Returns the count deleted.
    Raises RuntimeError on S3 failure."""
    if not prefix:
        raise ValueError("refusing to delete an empty prefix")
    keys = [obj["Key"] for obj in _fetch_all_objects(prefix)]
    if not keys:
        return 0
    client = get_s3_client()
    for i in range(0, len(keys), 1000):
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        try:
            client.delete_objects(
                Bucket=settings.b2_bucket_name, Delete={"Objects": batch}
            )
        except ClientError as e:
            raise RuntimeError(f"B2 delete_objects failed: {e}") from e
    _invalidate_list_cache()
    return len(keys)
