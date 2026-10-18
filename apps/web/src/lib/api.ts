/** Public DTOs only. Imported by server components; no database settings here. */
export type NamedEntity = {
  id: string;
  name: string;
  slug: string;
  synthetic: boolean;
};
export type Release = {
  id: string;
  concentration: string | null;
  release_year: number | null;
  notes: NamedEntity[];
  accords: NamedEntity[];
  synthetic: boolean;
};
export type Fragrance = NamedEntity & {
  brand: NamedEntity;
  releases: Release[];
  releases_truncated: boolean;
};
export type Page<T> = {
  data: T[];
  pagination: { limit: number; offset: number; total: number };
};
export class ApiError extends Error {
  constructor(public status: number) {
    super(
      status === 422 || status === 400
        ? "Please check your search and filters."
        : "The catalog is temporarily unavailable. Please try again.",
    );
  }
}
export const concentrations = [
  "parfum",
  "extrait_de_parfum",
  "eau_de_parfum",
  "eau_de_toilette",
  "eau_de_cologne",
  "eau_fraiche",
  "oil",
  "other",
];
export function label(value: string | null) {
  return value ? value.replaceAll("_", " ") : "Not specified";
}
export type Filters = Record<string, string | string[] | undefined>;
const permitted = [
  "q",
  "brand",
  "concentration",
  "year",
  "notes",
  "accords",
  "sort",
  "limit",
  "offset",
];
export function queryString(filters: Filters): string {
  const result = new URLSearchParams();
  for (const key of permitted) {
    const value = filters[key];
    for (const item of Array.isArray(value) ? value : [value]) {
      if (item !== undefined && item !== "") result.append(key, item);
    }
  }
  return result.toString();
}
export async function api<T>(
  path: string,
  fetcher: typeof fetch = fetch,
): Promise<T> {
  const base = process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1";
  try {
    const response = await fetcher(`${base.replace(/\/$/, "")}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new ApiError(response.status);
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(503);
  }
}
export async function getFragrances(filters: Filters = {}) {
  return api<Page<Fragrance>>(`/fragrances?${queryString(filters)}`);
}
export async function getFragrance(id: string) {
  return api<{ data: Fragrance }>(`/fragrances/${encodeURIComponent(id)}`);
}
export async function getBrands() {
  return api<Page<NamedEntity>>("/brands?limit=50");
}
