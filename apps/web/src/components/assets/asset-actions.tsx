"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil, RefreshCw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useDeleteAsset,
  useRegenerateAsset,
  useUpdateAsset,
} from "@/lib/queries";
import {
  TEXTURE_RESOLUTIONS,
  type Asset,
  type GenerationEngine,
} from "@image-to-3d-asset-library/shared";

export function AssetActions({ asset }: { asset: Asset }) {
  const busy = asset.status === "pending" || asset.status === "running";
  return (
    <div className="flex flex-wrap items-center gap-2">
      <EditAssetDialog asset={asset} />
      <RegenerateDialog asset={asset} disabled={busy} />
      <DeleteAssetDialog asset={asset} />
    </div>
  );
}

function EditAssetDialog({ asset }: { asset: Asset }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(asset.name);
  const [tagsText, setTagsText] = useState(asset.tags.join(", "));
  const update = useUpdateAsset(asset.id);

  const tags = tagsText
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const save = () => {
    update.mutate(
      { name: name.trim() || asset.name, tags },
      {
        onSuccess: () => {
          toast.success("Asset updated");
          setOpen(false);
        },
        onError: (e) => toast.error(e instanceof Error ? e.message : "Update failed"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Pencil className="h-3.5 w-3.5" /> Edit
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit asset</DialogTitle>
          <DialogDescription>
            Rename and tag this asset. Editing the mesh geometry is out of scope —
            metadata is the honest edit here. Changes update the manifest on B2.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="asset-name">Name</Label>
            <Input
              id="asset-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="asset-tags">Tags</Label>
            <Input
              id="asset-tags"
              value={tagsText}
              placeholder="prop, hero, low-poly"
              onChange={(e) => setTagsText(e.target.value)}
            />
            <div className="flex flex-wrap gap-1.5 pt-1">
              {tags.map((t) => (
                <Badge key={t} variant="secondary">
                  {t}
                </Badge>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RegenerateDialog({ asset, disabled }: { asset: Asset; disabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [engine, setEngine] = useState<GenerationEngine>(asset.params.engine);
  const [resolution, setResolution] = useState(String(asset.params.texture_resolution));
  const regenerate = useRegenerateAsset(asset.id);

  const run = () => {
    regenerate.mutate(
      { engine, texture_resolution: Number(resolution) },
      {
        onSuccess: () => {
          toast.success("Regeneration started");
          setOpen(false);
        },
        onError: (e) =>
          toast.error(e instanceof Error ? e.message : "Regenerate failed"),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        <RefreshCw className="h-3.5 w-3.5" /> Regenerate
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Regenerate asset</DialogTitle>
          <DialogDescription>
            Re-run reconstruction, optionally with a different engine or texture
            resolution. This bumps the asset version and overwrites its artifacts
            on B2.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Engine</Label>
            <Select value={engine} onValueChange={(v) => setEngine(v as GenerationEngine)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="triposr">TripoSR (local, MIT)</SelectItem>
                <SelectItem value="hunyuan3d">Hunyuan3D (GPU only)</SelectItem>
                <SelectItem value="procedural">Demo (procedural, no model)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Texture resolution</Label>
            <Select value={resolution} onValueChange={setResolution}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TEXTURE_RESOLUTIONS.map((r) => (
                  <SelectItem key={r} value={String(r)}>
                    {r}px
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={run} disabled={regenerate.isPending}>
            {regenerate.isPending ? "Starting…" : "Regenerate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteAssetDialog({ asset }: { asset: Asset }) {
  const router = useRouter();
  const del = useDeleteAsset();

  const confirm = () => {
    del.mutate(asset.id, {
      onSuccess: (res) => {
        toast.success(`Deleted asset (${res.objects_removed} B2 objects removed)`);
        router.push("/library");
      },
      onError: (e) => toast.error(e instanceof Error ? e.message : "Delete failed"),
    });
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this asset?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently removes the asset&apos;s entire{" "}
            <code>library/{asset.id}/</code> prefix from B2 — the mesh, textures,
            preview, and manifest. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={confirm} disabled={del.isPending}>
            {del.isPending ? "Deleting…" : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
