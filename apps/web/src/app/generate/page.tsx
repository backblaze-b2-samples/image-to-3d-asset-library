import { GenerateForm } from "@/components/assets/generate-form";

export default function GeneratePage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Generate a 3D asset</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Upload a source image and reconstruct a 3D mesh, texture maps, and a
          preview render — all stored in your Backblaze B2 bucket, keyed by the
          image&apos;s content hash.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <GenerateForm />
      </div>
    </div>
  );
}
