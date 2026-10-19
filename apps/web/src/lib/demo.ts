/** Server-side, original-only public DTO snapshot. No database or network calls. */
import snapshot from "@/demo/catalog.json";
import {
  ApiError,
  concentrations,
  type Fragrance,
  type NamedEntity,
} from "./api";

const catalog = snapshot as {
  fragrances: Fragrance[];
  brands: NamedEntity[];
  notes: NamedEntity[];
  accords: NamedEntity[];
};
const invalid = () => {
  throw new ApiError(422);
};
function integer(
  params: URLSearchParams,
  key: string,
  fallback: number,
  min: number,
  max: number,
) {
  const value = params.get(key);
  if (value === null) return fallback;
  if (!/^\d+$/.test(value)) return invalid();
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < min || number > max)
    return invalid();
  return number;
}
function page<T>(data: T[], params: URLSearchParams) {
  const limit = integer(params, "limit", 20, 1, 50);
  const offset = integer(params, "offset", 0, 0, 10000);
  return {
    data: data.slice(offset, offset + limit),
    pagination: { limit, offset, total: data.length },
  };
}
export function demoMediaPath(id: string, preset: string): string | null {
  if (!["display", "thumb"].includes(preset)) return null;
  const images = catalog.fragrances.flatMap((f) => [
    ...(f.images ?? []),
    ...f.releases.flatMap((r) => [
      ...(r.images ?? []),
      ...(r.variant_images ?? []).flatMap((v) => v.images ?? []),
    ]),
  ]);
  return images.some((image) => image.id === id)
    ? `/demo-media/${id}/${preset}.webp`
    : null;
}
export function demoResponse(path: string): unknown {
  if (!path.startsWith("/") || path.startsWith("//")) throw new ApiError(404);
  const url = new URL(path, "https://demo.invalid");
  const params = url.searchParams;
  const detail = /^\/fragrances\/([a-f0-9-]{36})$/i.exec(url.pathname);
  if (detail) {
    const fragrance = catalog.fragrances.find((f) => f.id === detail[1]);
    if (!fragrance) throw new ApiError(404);
    return { data: fragrance };
  }
  if (["/brands", "/notes", "/accords"].includes(url.pathname)) {
    const key = url.pathname.slice(1) as "brands" | "notes" | "accords";
    return page(catalog[key], params);
  }
  if (url.pathname !== "/fragrances") throw new ApiError(404);
  const q = (params.get("q") ?? "").trim().toLocaleLowerCase("en");
  if (q.length > 120) return invalid();
  const concentration = params.get("concentration");
  if (concentration && !concentrations.includes(concentration))
    return invalid();
  const year = params.has("year")
    ? integer(params, "year", 0, 1000, 2999)
    : null;
  const sort = params.get("sort") ?? "relevance";
  if (!["relevance", "name", "name_desc"].includes(sort)) return invalid();
  const notes = params.getAll("notes");
  const accords = params.getAll("accords");
  const brand = params.get("brand");
  const data = catalog.fragrances.filter(
    (f) =>
      (!q || `${f.name} ${f.brand.name}`.toLocaleLowerCase("en").includes(q)) &&
      (!brand || f.brand.slug === brand || f.brand.id === brand) &&
      ((!concentration && year === null && !notes.length && !accords.length) ||
        f.releases.some(
          (r) =>
            (!concentration || r.concentration === concentration) &&
            (year === null || r.release_year === year) &&
            notes.every((id) => r.notes.some((n) => n.id === id)) &&
            accords.every((id) => r.accords.some((a) => a.id === id)),
        )),
  );
  // Stable lexical demo search, not the PostgreSQL relevance-ranking algorithm.
  data.sort(
    (a, b) =>
      (a.name.localeCompare(b.name, "en") || a.id.localeCompare(b.id)) *
      (sort === "name_desc" ? -1 : 1),
  );
  return page(data, params);
}
