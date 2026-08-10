export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Image -> 3D asset library ------------------------------------------
// Hand-written mirror of the Pydantic models in services/api/app/types/asset.py.
// Keep in sync (see docs/dev-workflows.md — payload shapes are synced by hand).

export type AssetStatus = "pending" | "running" | "complete" | "failed";
export type GenerationEngine = "triposr" | "hunyuan3d" | "procedural";
export type ArtifactKind =
  | "source"
  | "mesh_glb"
  | "mesh_obj"
  | "texture"
  | "preview";

/** Finite create-form choices for texture resolution (largest first). */
export const TEXTURE_RESOLUTIONS = [2048, 1024, 512] as const;

export interface GenerationParams {
  engine: GenerationEngine;
  texture_resolution: number;
  remove_background: boolean;
}

export interface AssetArtifact {
  kind: ArtifactKind;
  key: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  resolution: number | null;
  url: string | null;
}

export interface WriteAmplification {
  input_bytes: number;
  output_bytes: number;
  object_count: number;
  ratio: number;
  input_bytes_human: string;
  output_bytes_human: string;
}

export interface Asset {
  id: string;
  name: string;
  tags: string[];
  status: AssetStatus;
  params: GenerationParams;
  input_key: string;
  input_filename: string;
  input_bytes: number;
  version: number;
  device_used: string | null;
  generation_seconds: number | null;
  artifacts: AssetArtifact[];
  write_amplification: WriteAmplification;
  error: string | null;
  created_at: string;
  updated_at: string;
  progress_message: string | null;
}

export interface AssetCreateRequest {
  input_key: string;
  name?: string;
  engine: GenerationEngine;
  texture_resolution: number;
  remove_background: boolean;
}

export interface AssetUpdateRequest {
  name?: string;
  tags?: string[];
}

export interface RegenerateRequest {
  engine?: GenerationEngine;
  texture_resolution?: number;
  remove_background?: boolean;
}

export interface ArtifactTypeUsage {
  count: number;
  bytes: number;
  bytes_human: string;
}

export interface AssetStats {
  total_assets: number;
  total_objects: number;
  total_bytes: number;
  total_bytes_human: string;
  input_bytes: number;
  output_bytes: number;
  output_bytes_human: string;
  avg_objects_per_generation: number;
  amplification_ratio: number;
  by_artifact_type: Record<string, ArtifactTypeUsage>;
}

export interface EngineInfo {
  name: GenerationEngine;
  label: string;
  description: string;
  deployment: string;
  device_requirement: string;
  is_default: boolean;
  available: boolean;
}
