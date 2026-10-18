import type { BottleImage } from "./api";

const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
export function mediaPath(
  image: BottleImage,
  preset: "display" | "thumb",
): string | null {
  if (!uuid.test(image.id)) return null;
  const value = preset === "display" ? image.url : image.thumbnail_url;
  if (value !== `/api/v1/media/${image.id}/${preset}`) return null;
  if (
    !Number.isInteger(image.width) ||
    !Number.isInteger(image.height) ||
    image.width < 1 ||
    image.height < 1 ||
    image.width > 1200 ||
    image.height > 1200 ||
    !Number.isInteger(image.thumbnail_width) ||
    !Number.isInteger(image.thumbnail_height) ||
    image.thumbnail_width < 1 ||
    image.thumbnail_width > 320 ||
    image.thumbnail_height < 1 ||
    image.thumbnail_height > 320
  )
    return null;
  return `/media/${image.id}/${preset}`;
}

/** Server-only caller supplies a trusted deployment base. No remote image URLs. */
export async function proxyMedia(
  id: string,
  preset: string,
  base: string,
  fetcher: typeof fetch = fetch,
): Promise<Response> {
  const headers = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
  };
  const missing = () => new Response(null, { status: 404, headers });
  if (!uuid.test(id) || !["display", "thumb"].includes(preset))
    return missing();
  try {
    const response = await fetcher(`${base}/media/${id}/${preset}`, {
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(5000),
    });
    if (
      !response.ok ||
      response.headers.get("content-type")?.split(";", 1)[0] !== "image/webp" ||
      !response.body
    )
      return missing();
    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 5 * 1024 * 1024) {
          await reader.cancel();
          return missing();
        }
        chunks.push(value);
      }
    } finally {
      reader.releaseLock();
    }
    if (!size) return missing();
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return new Response(bytes, {
      headers: { ...headers, "Content-Type": "image/webp" },
    });
  } catch {
    return missing();
  }
}
