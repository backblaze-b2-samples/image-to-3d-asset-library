import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AssetStatus } from "@image-to-3d-asset-library/shared";

const LABELS: Record<AssetStatus, string> = {
  pending: "Queued",
  running: "Generating",
  complete: "Complete",
  failed: "Failed",
};

const VARIANTS: Record<AssetStatus, "default" | "secondary" | "outline" | "destructive"> = {
  pending: "outline",
  running: "secondary",
  complete: "default",
  failed: "destructive",
};

export function AssetStatusBadge({ status }: { status: AssetStatus }) {
  const active = status === "pending" || status === "running";
  return (
    <Badge variant={VARIANTS[status]} className="gap-1">
      {active && <Loader2 className="h-3 w-3 animate-spin" aria-hidden />}
      {LABELS[status]}
    </Badge>
  );
}
