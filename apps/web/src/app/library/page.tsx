import Link from "next/link";
import { Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { AssetGrid } from "@/components/assets/asset-grid";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Library</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Every generated 3D asset in your B2 bucket, scoped to the{" "}
            <code>library/</code> prefix. Click an asset to open its 3D viewer,
            artifacts, and write-amplification breakdown.
          </p>
        </div>
        <Button asChild size="sm" className="h-8 shrink-0">
          <Link href="/generate">
            <Wand2 aria-hidden className="h-3.5 w-3.5" />
            Generate
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <AssetGrid />
      </div>
    </div>
  );
}
