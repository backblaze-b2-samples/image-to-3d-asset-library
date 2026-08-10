"""Content-addressing for assets.

The asset id is the source image's content hash, so uploading the same image
twice maps to the same `library/<id>/` prefix — that is what makes the library
deduplicated and versioned.
"""

import hashlib

_HASH_LEN = 16  # first 16 hex chars of sha256: 64 bits, ample for dedup here


def short_content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:_HASH_LEN]
