"""Boundary types for the image -> 3D asset library.

Every value that crosses a layer is a Pydantic model (AGENTS.md §3). The
`Asset` manifest is the durable record on B2 (`library/<id>/manifest.json`);
there is no database. Presigned URLs on artifacts are ephemeral and are filled
in at read time, never persisted in the manifest.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AssetStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class GenerationEngine(StrEnum):
    TRIPOSR = "triposr"
    HUNYUAN3D = "hunyuan3d"
    PROCEDURAL = "procedural"


class ArtifactKind(StrEnum):
    SOURCE = "source"
    MESH_GLB = "mesh_glb"
    MESH_OBJ = "mesh_obj"
    TEXTURE = "texture"
    PREVIEW = "preview"


# Finite UI choice — a Select on the create form, validated here too.
TEXTURE_RESOLUTIONS = (2048, 1024, 512)


class GenerationParams(BaseModel):
    engine: GenerationEngine = GenerationEngine.TRIPOSR
    texture_resolution: int = 1024
    remove_background: bool = True


class AssetArtifact(BaseModel):
    kind: ArtifactKind
    key: str
    size_bytes: int
    size_human: str
    content_type: str
    # Set for texture maps (the resolution of the map); None for mesh/preview.
    resolution: int | None = None
    # Presigned inline GET URL, populated at read time only (never persisted).
    url: str | None = None


class WriteAmplification(BaseModel):
    """The sample's headline lesson: one small input fans out into many larger
    B2 objects. `ratio` is output bytes / input bytes."""

    input_bytes: int = 0
    output_bytes: int = 0
    object_count: int = 0
    ratio: float = 0.0
    input_bytes_human: str = "0 B"
    output_bytes_human: str = "0 B"


class Asset(BaseModel):
    id: str  # content hash of the source image (sha256, first 16 hex)
    name: str
    tags: list[str] = Field(default_factory=list)
    status: AssetStatus = AssetStatus.PENDING
    params: GenerationParams = Field(default_factory=GenerationParams)
    input_key: str
    input_filename: str
    input_bytes: int = 0
    version: int = 1
    device_used: str | None = None
    generation_seconds: float | None = None
    artifacts: list[AssetArtifact] = Field(default_factory=list)
    write_amplification: WriteAmplification = Field(default_factory=WriteAmplification)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    # Live progress overlaid from the in-memory job registry at read time while
    # the run is pending/running; not persisted in the manifest.
    progress_message: str | None = None


class AssetCreateRequest(BaseModel):
    """Point the generator at an already-uploaded source image (the /generate
    form uploads it via the existing presign flow, then submits its key)."""

    input_key: str
    name: str | None = None
    engine: GenerationEngine = GenerationEngine.TRIPOSR
    texture_resolution: int = 1024
    remove_background: bool = True


class AssetUpdateRequest(BaseModel):
    name: str | None = None
    tags: list[str] | None = None


class RegenerateRequest(BaseModel):
    """Optionally change the engine/params on a re-run; bumps the version."""

    engine: GenerationEngine | None = None
    texture_resolution: int | None = None
    remove_background: bool | None = None


class ArtifactTypeUsage(BaseModel):
    count: int = 0
    bytes: int = 0
    bytes_human: str = "0 B"


class AssetStats(BaseModel):
    total_assets: int = 0
    total_objects: int = 0
    total_bytes: int = 0
    total_bytes_human: str = "0 B"
    input_bytes: int = 0
    output_bytes: int = 0
    output_bytes_human: str = "0 B"
    avg_objects_per_generation: float = 0.0
    amplification_ratio: float = 0.0
    by_artifact_type: dict[str, ArtifactTypeUsage] = Field(default_factory=dict)


class EngineInfo(BaseModel):
    name: GenerationEngine
    label: str
    description: str
    deployment: str  # always "local" for this sample
    device_requirement: str  # "any" | "gpu"
    is_default: bool = False
    available: bool = True
