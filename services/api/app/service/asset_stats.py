"""Aggregate write-amplification metrics for the dashboard.

Kept in its own module so `service/assets.py` stays under the 300-line ceiling.
Pure function over the manifest list — no I/O.
"""

from app.types import ArtifactKind, ArtifactTypeUsage, Asset, AssetStats
from app.types.formatting import humanize_bytes


def compute_stats(assets: list[Asset]) -> AssetStats:
    generations = [a for a in assets if a.artifacts]

    total_objects = 0
    input_bytes = 0
    total_bytes = 0
    by_type: dict[str, ArtifactTypeUsage] = {}

    for asset in generations:
        total_objects += asset.write_amplification.object_count or (
            len(asset.artifacts) + 1
        )
        input_bytes += asset.input_bytes
        for artifact in asset.artifacts:
            total_bytes += artifact.size_bytes
            usage = by_type.setdefault(artifact.kind.value, ArtifactTypeUsage())
            usage.count += 1
            usage.bytes += artifact.size_bytes

    for usage in by_type.values():
        usage.bytes_human = humanize_bytes(usage.bytes)

    # Source-artifact bytes equal the input bytes; everything else is output.
    source_usage = by_type.get(ArtifactKind.SOURCE.value)
    source_bytes = source_usage.bytes if source_usage else 0
    output_bytes = max(total_bytes - source_bytes, 0)
    ratio = round(output_bytes / input_bytes, 2) if input_bytes > 0 else 0.0
    avg_objects = round(total_objects / len(generations), 2) if generations else 0.0

    return AssetStats(
        total_assets=len(assets),
        total_objects=total_objects,
        total_bytes=total_bytes,
        total_bytes_human=humanize_bytes(total_bytes),
        input_bytes=input_bytes,
        output_bytes=output_bytes,
        output_bytes_human=humanize_bytes(output_bytes),
        avg_objects_per_generation=avg_objects,
        amplification_ratio=ratio,
        by_artifact_type=by_type,
    )
