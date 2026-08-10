"use client";

import Link from "next/link";
import { ArrowLeft, Cpu, Download, ImageIcon, Loader2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useAsset } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import { Asset3DViewer } from "./asset-3d-viewer";
import { AssetActions } from "./asset-actions";
import { AssetStatusBadge } from "./asset-status-badge";
import { WriteAmpPanel } from "./write-amp-panel";
import type { Asset, AssetArtifact } from "@image-to-3d-asset-library/shared";

const KIND_LABELS: Record<string, string> = {
  source: "Source image",
  mesh_glb: "Mesh (GLB)",
  mesh_obj: "Mesh (OBJ)",
  texture: "Texture map",
  preview: "Preview render",
};

function artifact(asset: Asset, kind: string): AssetArtifact | undefined {
  return asset.artifacts.find((a) => a.kind === kind);
}

export function AssetDetail({ id }: { id: string }) {
  const { data: asset, isLoading, error, refetch } = useAsset(id);

  if (isLoading) {
    return <Skeleton className="h-96 w-full rounded-xl" />;
  }
  if (error || !asset) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const glb = artifact(asset, "mesh_glb");
  const preview = artifact(asset, "preview");
  const source = artifact(asset, "source");

  return (
    <div className="space-y-6">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <Link
            href="/library"
            className="mb-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Library
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="page-title truncate">{asset.name}</h1>
            <AssetStatusBadge status={asset.status} />
            <Badge variant="outline">v{asset.version}</Badge>
          </div>
          <p className="mt-1.5 font-mono text-xs text-muted-foreground">
            library/{asset.id}/
          </p>
        </div>
        <AssetActions asset={asset} />
      </div>

      {asset.status === "failed" && (
        <ErrorState
          title="Generation failed"
          description={asset.error ?? "The engine reported an error."}
        />
      )}

      {(asset.status === "pending" || asset.status === "running") && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
            <p className="text-sm font-medium">
              {asset.progress_message ?? "Reconstructing mesh…"}
            </p>
            <p className="text-xs text-muted-foreground">
              This page updates automatically when generation finishes.
            </p>
          </CardContent>
        </Card>
      )}

      {asset.status === "complete" && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            {glb?.url ? (
              <Asset3DViewer
                src={glb.url}
                poster={preview?.url}
                alt={`3D model of ${asset.name}`}
              />
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-sm text-muted-foreground">
                  Mesh artifact unavailable.
                </CardContent>
              </Card>
            )}
            {source?.url && (
              <Card>
                <CardHeader className="border-b border-border py-3 px-5">
                  <CardTitle className="card-title flex items-center gap-2 text-sm">
                    <ImageIcon className="h-4 w-4 text-muted-foreground" /> Source
                    image
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-5">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={source.url}
                    alt="Source"
                    className="mx-auto max-h-56 rounded-md object-contain"
                  />
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <WriteAmpPanel amp={asset.write_amplification} />

            <Card>
              <CardHeader className="border-b border-border py-4 px-5">
                <CardTitle className="card-title flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-muted-foreground" /> Generation
                </CardTitle>
              </CardHeader>
              <CardContent className="p-5 text-sm">
                <dl className="grid grid-cols-2 gap-y-2">
                  <dt className="text-muted-foreground">Engine</dt>
                  <dd className="text-right capitalize">{asset.params.engine}</dd>
                  <dt className="text-muted-foreground">Device</dt>
                  <dd className="text-right">{asset.device_used ?? "—"}</dd>
                  <dt className="text-muted-foreground">Texture size</dt>
                  <dd className="text-right tabular-nums">
                    {asset.params.texture_resolution}px
                  </dd>
                  <dt className="text-muted-foreground">BG removed</dt>
                  <dd className="text-right">
                    {asset.params.remove_background ? "Yes" : "No"}
                  </dd>
                  <dt className="text-muted-foreground">Time</dt>
                  <dd className="text-right tabular-nums">
                    {asset.generation_seconds !== null
                      ? `${asset.generation_seconds}s`
                      : "—"}
                  </dd>
                  <dt className="text-muted-foreground">Created</dt>
                  <dd className="text-right">{formatDate(asset.created_at)}</dd>
                </dl>
                {asset.tags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 border-t border-border pt-3">
                    {asset.tags.map((t) => (
                      <Badge key={t} variant="secondary">
                        {t}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-3">
            <Card>
              <CardHeader className="border-b border-border py-4 px-5">
                <CardTitle className="card-title">
                  B2 artifacts ({asset.artifacts.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40 hover:bg-muted/40">
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">
                        Artifact
                      </TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">
                        Resolution
                      </TableHead>
                      <TableHead className="text-xs uppercase tracking-wider text-muted-foreground">
                        Size
                      </TableHead>
                      <TableHead className="text-right text-xs uppercase tracking-wider text-muted-foreground">
                        Download
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {asset.artifacts.map((a) => (
                      <TableRow key={a.key}>
                        <TableCell className="font-medium">
                          {KIND_LABELS[a.kind] ?? a.kind}
                        </TableCell>
                        <TableCell className="text-muted-foreground tabular-nums">
                          {a.resolution ? `${a.resolution}px` : "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground tabular-nums">
                          {a.size_human}
                        </TableCell>
                        <TableCell className="text-right">
                          {a.url && (
                            <Button asChild variant="ghost" size="sm">
                              <a href={a.url} target="_blank" rel="noopener noreferrer">
                                <Download className="h-3.5 w-3.5" />
                              </a>
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
