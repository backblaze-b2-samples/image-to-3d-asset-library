import { ArrowRight, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WriteAmplification } from "@image-to-3d-asset-library/shared";

/**
 * The sample's headline lesson: one small input image fans out into many
 * larger B2 objects. This makes that concrete for a single asset.
 */
export function WriteAmpPanel({ amp }: { amp: WriteAmplification }) {
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <Layers className="h-4 w-4 text-muted-foreground" />
          Write amplification
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        <div className="flex items-center justify-center gap-4 text-center">
          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Input
            </div>
            <div className="stat-value">{amp.input_bytes_human}</div>
            <div className="text-xs text-muted-foreground">1 image</div>
          </div>
          <ArrowRight className="h-5 w-5 text-muted-foreground" aria-hidden />
          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Output
            </div>
            <div className="stat-value">{amp.output_bytes_human}</div>
            <div className="text-xs text-muted-foreground">
              {amp.object_count} B2 objects
            </div>
          </div>
        </div>
        <div className="mt-5 rounded-md border border-border bg-muted/30 p-3 text-center">
          <span className="text-sm text-muted-foreground">
            Amplification ratio
          </span>
          <div className="text-2xl font-semibold tabular-nums">
            {amp.ratio.toFixed(2)}×
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            output bytes ÷ input bytes — a bulk library fills a bucket fast, and
            B2&apos;s flat per-GB pricing is the point.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
