"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

/**
 * In-browser 3D viewer for the generated GLB.
 *
 * `@google/model-viewer` registers a `<model-viewer>` custom element and pulls
 * in three.js, so it is imported dynamically INSIDE an effect (client-only) —
 * never at module top level — to keep it out of SSR/prerender and off the
 * initial bundle. Rendering the element via the DOM (not JSX) sidesteps the
 * custom-element typing dance and keeps `tsc`/`next build` clean.
 *
 * `src` is a presigned, inline-disposition B2 URL. Cross-origin fetch by the
 * viewer needs the bucket's CORS to allow GET/HEAD from the web origin — run
 * `services/api/scripts/setup_b2_cors.py` once per deployed origin (it also
 * covers the uploader's PUT). See docs/features/asset-library.md.
 */
export function Asset3DViewer({
  src,
  poster,
  alt,
}: {
  src: string;
  poster?: string | null;
  alt: string;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let element: HTMLElement | null = null;
    let cancelled = false;

    (async () => {
      await import("@google/model-viewer");
      if (cancelled || !hostRef.current) return;
      element = document.createElement("model-viewer");
      element.setAttribute("src", src);
      element.setAttribute("alt", alt);
      if (poster) element.setAttribute("poster", poster);
      element.setAttribute("camera-controls", "");
      element.setAttribute("auto-rotate", "");
      element.setAttribute("shadow-intensity", "1");
      element.setAttribute("exposure", "0.9");
      element.setAttribute("environment-image", "neutral");
      element.style.width = "100%";
      element.style.height = "100%";
      element.style.backgroundColor = "var(--muted)";
      hostRef.current.replaceChildren(element);
      setReady(true);
    })();

    return () => {
      cancelled = true;
      element?.remove();
    };
  }, [src, poster, alt]);

  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-lg border border-border bg-muted">
      <div ref={hostRef} className="h-full w-full" />
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden />
          <span className="sr-only">Loading 3D viewer</span>
        </div>
      )}
    </div>
  );
}
