import { proxyMedia } from "@/lib/media";
import { isDemoMode } from "@/lib/demo-mode";
export const dynamic = "force-dynamic";
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string; preset: string }> },
) {
  const { id, preset } = await params;
  if (isDemoMode()) {
    const { demoMediaPath } = await import("@/lib/demo");
    const path = demoMediaPath(id, preset);
    return path
      ? new Response(null, {
          status: 307,
          headers: { Location: path, "Cache-Control": "no-store" },
        })
      : new Response(null, { status: 404 });
  }
  return proxyMedia(
    id,
    preset,
    process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1",
  );
}
