import { proxyMedia } from "@/lib/media";
export const dynamic = "force-dynamic";
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string; preset: string }> },
) {
  const { id, preset } = await params;
  return proxyMedia(
    id,
    preset,
    process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1",
  );
}
