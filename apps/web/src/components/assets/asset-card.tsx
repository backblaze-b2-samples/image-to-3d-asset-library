import Link from "next/link";
import { Box } from "lucide-react";
import { Card } from "@/components/ui/card";
import { AssetStatusBadge } from "./asset-status-badge";
import type { Asset } from "@image-to-3d-asset-library/shared";

function previewUrl(asset: Asset): string | null {
  return asset.artifacts.find((a) => a.kind === "preview")?.url ?? null;
}

export function AssetCard({ asset }: { asset: Asset }) {
  const preview = previewUrl(asset);
  const objectCount = asset.write_amplification.object_count;

  return (
    <Link href={`/library/${asset.id}`} className="group block">
      <Card className="card-hover overflow-hidden p-0">
        <div className="relative aspect-square w-full overflow-hidden bg-[#0c0e12]">
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={preview}
              alt={`Preview of ${asset.name}`}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-muted-foreground">
              <Box className="h-10 w-10" aria-hidden />
            </div>
          )}
          <div className="absolute left-2 top-2">
            <AssetStatusBadge status={asset.status} />
          </div>
        </div>
        <div className="space-y-1 p-3">
          <div className="truncate font-medium" title={asset.name}>
            {asset.name}
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="capitalize">{asset.params.engine}</span>
            <span className="tabular-nums">
              {asset.status === "complete"
                ? `${objectCount} objs · ${asset.write_amplification.output_bytes_human}`
                : asset.progress_message ?? "—"}
            </span>
          </div>
        </div>
      </Card>
    </Link>
  );
}
