import { AssetDetail } from "@/components/assets/asset-detail";

export default async function AssetDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="animate-fade-in">
      <AssetDetail id={id} />
    </div>
  );
}
