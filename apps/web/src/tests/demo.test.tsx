import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { existsSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import mediaHashes from "@/demo/media-hashes.json";
import { join } from "node:path";
import { api, ApiError, type Fragrance, type Page } from "@/lib/api";
import { demoResponse, demoMediaPath } from "@/lib/demo";
import { isDemoMode } from "@/lib/demo-mode";
import { GET } from "@/app/media/[id]/[preset]/route";
import RootLayout from "@/app/layout";
import catalog from "@/demo/catalog.json";
vi.mock("@/components/providers", () => ({
  Providers: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("@/components/navigation", () => ({ Navigation: () => <nav /> }));

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  cleanup();
});
const listing = (query = "") =>
  demoResponse(`/fragrances?${query}`) as Page<Fragrance>;
describe("explicit self-contained Vercel demo", () => {
  it("contains exactly the 100 original fictional fragrances and no private evidence", () => {
    expect(listing().pagination.total).toBe(100);
    expect(catalog.brands).toHaveLength(10);
    const text = JSON.stringify(catalog);
    expect(text).not.toMatch(
      /"synthetic":false|"evidence"|"reviewer"|"payload"|postgresql|CONTACT_EMAIL/,
    );
    expect(
      catalog.fragrances.every(
        (f) =>
          f.synthetic &&
          f.brand.synthetic &&
          f.releases.every((r) => r.synthetic),
      ),
    ).toBe(true);
  });
  it("serves the demo even with an unreachable API without any fetch", async () => {
    vi.stubEnv("FRAGGY_DEMO_MODE", "synthetic");
    vi.stubEnv("API_BASE_URL", "http://127.0.0.1:1/unreachable");
    const fetcher = vi.fn();
    expect(
      (await api<Page<Fragrance>>("/fragrances", fetcher)).pagination.total,
    ).toBe(100);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("keeps the normal FastAPI path and never falls back on API failure", async () => {
    vi.stubEnv("FRAGGY_DEMO_MODE", "");
    const fetcher = vi.fn().mockRejectedValue(new Error("private failure"));
    await expect(api("/fragrances", fetcher)).rejects.toEqual(
      new ApiError(503),
    );
    expect(fetcher).toHaveBeenCalledOnce();
  });
  it("rejects misspelled deployment mode instead of silently enabling fixtures", () => {
    vi.stubEnv("FRAGGY_DEMO_MODE", "true");
    expect(isDemoMode).toThrow("Invalid FRAGGY_DEMO_MODE");
  });
  it("searches fictional fragrance and brand names and supports empty results", () => {
    const f = catalog.fragrances[0];
    expect(
      listing(`q=${encodeURIComponent(f.name)}`).data.some(
        (item) => item.id === f.id,
      ),
    ).toBe(true);
    expect(
      listing(`q=${encodeURIComponent(f.brand.name)}`).pagination.total,
    ).toBe(10);
    expect(listing("q=no-such-fictional-scent").pagination.total).toBe(0);
  });
  it("filters brand, concentration, year, notes and accords on a matching release", () => {
    const f = catalog.fragrances[0];
    const r = f.releases[0];
    const params = new URLSearchParams({
      brand: f.brand.slug,
      concentration: r.concentration!,
      year: String(r.release_year),
      notes: r.notes[0].id,
      accords: r.accords[0].id,
    });
    const data = listing(params.toString()).data;
    expect(data.some((item) => item.id === f.id)).toBe(true);
    expect(
      data.every(
        (item) =>
          item.brand.id === f.brand.id &&
          item.releases.some(
            (release) =>
              release.concentration === r.concentration &&
              release.release_year === r.release_year &&
              release.notes.some((n) => n.id === r.notes[0].id) &&
              release.accords.some((a) => a.id === r.accords[0].id),
          ),
      ),
    ).toBe(true);
    expect(listing("notes=unknown").pagination.total).toBe(0);
  });
  it("sorts and paginates without overlapping or dropping entries", () => {
    const first = listing("sort=name&limit=50");
    const second = listing("sort=name&limit=50&offset=50");
    expect(new Set([...first.data, ...second.data].map((f) => f.id)).size).toBe(
      100,
    );
    expect(listing("sort=name_desc&limit=1").data[0].id).toBe(
      second.data.at(-1)?.id,
    );
  });
  it.each([
    "limit=0",
    "limit=9999",
    "offset=-1",
    "year=NaN",
    "concentration=bad",
    "sort=bad",
  ])("rejects malformed or unbounded filters: %s", (query) => {
    expect(() => listing(query)).toThrow(ApiError);
  });
  it("serves exact details and lookup lists, denying unknown paths and IDs", () => {
    const f = catalog.fragrances[0];
    expect(demoResponse(`/fragrances/${f.id}`)).toEqual({ data: f });
    expect(demoResponse("/notes?limit=50")).toMatchObject({
      pagination: { total: 24 },
    });
    expect(demoResponse("/accords?limit=50")).toMatchObject({
      pagination: { total: 8 },
    });
    expect(() =>
      demoResponse("/fragrances/00000000-0000-0000-0000-000000000000"),
    ).toThrow(ApiError);
    expect(() => demoResponse("//evil.example/fragrances")).toThrow(ApiError);
    expect(() => demoResponse("/admin")).toThrow(ApiError);
  });
  it("serves only bundled original WebP images and thumbnails, retaining credits", async () => {
    vi.stubEnv("FRAGGY_DEMO_MODE", "synthetic");
    const f = catalog.fragrances.find((item) => item.primary_image)!;
    const image = f.primary_image!;
    for (const preset of ["display", "thumb"]) {
      const path = demoMediaPath(image.id, preset)!;
      const file = join(process.cwd(), "public", path);
      expect(existsSync(file)).toBe(true);
      expect(readFileSync(file).subarray(8, 12).toString()).toBe("WEBP");
      const response = await GET(
        new Request("https://preview.vercel.app/media/fixture"),
        { params: Promise.resolve({ id: image.id, preset }) },
      );
      expect(response.headers.get("location")).toBe(path);
    }
    expect(image.attribution.text).toContain("Original fictional");
    expect(demoMediaPath("../private", "display")).toBeNull();
    const missing = await GET(
      new Request("https://preview.vercel.app/media/fixture"),
      { params: Promise.resolve({ id: image.id, preset: "raw" }) },
    );
    expect(missing.status).toBe(404);
  });
  it("preserves the content hashes of all eight original WebP assets", () => {
    expect(Object.keys(mediaHashes)).toHaveLength(8);
    for (const [file, hash] of Object.entries(mediaHashes)) {
      const bytes = readFileSync(
        join(process.cwd(), "public/demo-media", file),
      );
      expect(createHash("sha256").update(bytes).digest("hex")).toBe(hash);
    }
  });
  it("labels every demo page read-only and fictional", () => {
    vi.stubEnv("FRAGGY_DEMO_MODE", "synthetic");
    // Render the layout's body children to avoid nesting html/body in jsdom.
    const layout = RootLayout({ children: <p>Catalog</p> });
    render(layout.props.children.props.children);
    expect(screen.getByLabelText("Read-only demo")).toHaveTextContent(
      "100 invented fragrances",
    );
  });
});
