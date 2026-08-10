"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useDropzone } from "react-dropzone";
import { z } from "zod";
import { toast } from "sonner";
import { ImageIcon, Loader2, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { uploadFile } from "@/lib/api-client";
import { useCreateAsset, useEngines } from "@/lib/queries";
import { TEXTURE_RESOLUTIONS } from "@image-to-3d-asset-library/shared";

const schema = z.object({
  name: z.string().max(80).optional(),
  engine: z.enum(["triposr", "hunyuan3d", "procedural"]),
  texture_resolution: z.enum(["2048", "1024", "512"]),
  remove_background: z.boolean(),
});
type FormValues = z.infer<typeof schema>;

export function GenerateForm() {
  const router = useRouter();
  const { data: engines = [] } = useEngines();
  const createAsset = useCreateAsset();

  const [inputKey, setInputKey] = useState<string | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    // Safe defaults for a sound first run (guidance only — no autofill button).
    defaultValues: {
      name: "",
      engine: "triposr",
      texture_resolution: "1024",
      remove_background: true,
    },
  });

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0];
    if (!file) return;
    setPreviewSrc(URL.createObjectURL(file));
    setFileName(file.name);
    setInputKey(null);
    setUploading(true);
    try {
      const stored = await uploadFile(file);
      setInputKey(stored.key);
      toast.success("Source image uploaded to B2");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
      setPreviewSrc(null);
      setFileName(null);
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".png", ".jpg", ".jpeg", ".webp"] },
    maxFiles: 1,
    multiple: false,
    disabled: uploading || createAsset.isPending,
  });

  const onSubmit = (values: FormValues) => {
    if (!inputKey) {
      toast.error("Add a source image first");
      return;
    }
    createAsset.mutate(
      {
        input_key: inputKey,
        name: values.name?.trim() || undefined,
        engine: values.engine,
        texture_resolution: Number(values.texture_resolution),
        remove_background: values.remove_background,
      },
      {
        onSuccess: (asset) => {
          toast.success("Generation started");
          router.push(`/library/${asset.id}`);
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Failed to start"),
      },
    );
  };

  const nameStem = fileName ? fileName.replace(/\.[^.]+$/, "") : "my-asset";

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Source image</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <div
              {...getRootProps()}
              className={[
                "flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed p-6 text-center transition-colors",
                isDragActive
                  ? "border-primary bg-[var(--accent-subtle)]"
                  : "border-border hover:border-primary/60 hover:bg-muted/60",
              ].join(" ")}
            >
              <input {...getInputProps()} aria-label="Choose a source image" />
              {previewSrc ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={previewSrc}
                  alt="Selected source"
                  className="max-h-48 rounded-md object-contain"
                />
              ) : (
                <div className="flex flex-col items-center gap-2 text-muted-foreground">
                  <ImageIcon className="h-8 w-8" aria-hidden />
                  <p className="text-sm font-medium text-foreground">
                    Drop an image or click to browse
                  </p>
                  <p className="text-xs">
                    A single, well-lit subject on a plain background works best.
                    PNG, JPG, or WebP.
                  </p>
                </div>
              )}
            </div>
            {uploading && (
              <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Uploading to B2…
              </p>
            )}
            {inputKey && !uploading && (
              <p className="mt-3 text-xs text-[var(--success)]">
                Ready: {inputKey}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Generation settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 p-5">
            <FormField
              control={form.control}
              name="engine"
              render={({ field }) => {
                const selected = engines.find((e) => e.name === field.value);
                return (
                  <FormItem>
                    <FormLabel>Engine</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger className="w-full sm:w-80">
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {(engines.length > 0
                          ? engines.map((e) => ({
                              value: e.name,
                              label:
                                e.label +
                                (e.device_requirement === "gpu" && !e.available
                                  ? " — GPU required"
                                  : ""),
                            }))
                          : [
                              { value: "triposr", label: "TripoSR (local, MIT)" },
                              { value: "hunyuan3d", label: "Hunyuan3D (GPU only)" },
                              { value: "procedural", label: "Demo (procedural, no model)" },
                            ]
                        ).map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      {selected?.description ??
                        "TripoSR (default) runs locally on CPU or GPU. Hunyuan3D needs a CUDA GPU. Demo builds a placeholder mesh with no model download."}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                );
              }}
            />

            <FormField
              control={form.control}
              name="texture_resolution"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Texture resolution</FormLabel>
                  <FormControl>
                    <RadioGroup
                      onValueChange={field.onChange}
                      value={field.value}
                      className="flex gap-6"
                    >
                      {TEXTURE_RESOLUTIONS.map((res) => (
                        <label
                          key={res}
                          className="flex items-center gap-2 text-sm cursor-pointer"
                        >
                          <RadioGroupItem value={String(res)} />
                          {res}px
                        </label>
                      ))}
                    </RadioGroup>
                  </FormControl>
                  <FormDescription>
                    1024 is a good default. Higher resolution writes larger
                    texture maps to B2 (more write amplification).
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="remove_background"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-md border border-border p-3">
                  <div className="space-y-0.5">
                    <FormLabel>Remove background</FormLabel>
                    <FormDescription>
                      Recommended. Isolates the subject before reconstruction for
                      a cleaner mesh.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name (optional)</FormLabel>
                  <FormControl>
                    <Input placeholder={nameStem} {...field} />
                  </FormControl>
                  <FormDescription>
                    Defaults to the image filename if left blank.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button
            type="submit"
            disabled={!inputKey || uploading || createAsset.isPending}
          >
            {createAsset.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Wand2 className="h-4 w-4" />
            )}
            Generate 3D asset
          </Button>
        </div>
      </form>
    </Form>
  );
}
