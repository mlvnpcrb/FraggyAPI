import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Directory } from "@/components/directory";
import {
  api,
  ApiError,
  getFragrances,
  queryString,
  type Fragrance,
} from "@/lib/api";
import FragrancesPage from "@/app/fragrances/(directory)/page";
import BrandsPage from "@/app/brands/page";
import Home from "@/app/page";
import FragrancePage from "@/app/fragrances/[id]/page";
vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NOT_FOUND");
  },
}));

const brand = {
  id: "brand-uuid",
  name: "Nacre Workshop",
  slug: "nacre-workshop",
  synthetic: true,
};
const fragrance: Fragrance = {
  id: "fragrance-uuid",
  name: "Paper Horizon",
  slug: "paper-horizon",
  synthetic: true,
  brand,
  releases: [],
  releases_truncated: false,
};
const page = {
  data: [fragrance],
  pagination: { limit: 20, offset: 0, total: 21 },
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("public catalog integration", () => {
  it("renders API records, stable IDs, synthetic labels and pagination", () => {
    render(
      <Directory
        results={page}
        brands={[brand]}
        notes={[]}
        accords={[]}
        filters={{ q: "paper", brand: brand.slug }}
      />,
    );
    expect(screen.getByRole("link", { name: /Paper Horizon/ })).toHaveAttribute(
      "href",
      "/fragrances/fragrance-uuid",
    );
    expect(screen.getByText("Synthetic demo collection")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveAttribute("name", "q");
    expect(screen.getByLabelText("Filter by brand")).toHaveValue(
      "nacre-workshop",
    );
    expect(screen.getByRole("link", { name: "Next page" })).toHaveAttribute(
      "href",
      "/fragrances?q=paper&brand=nacre-workshop&offset=20",
    );
    expect(screen.getByRole("button", { name: "Search" })).toHaveAttribute(
      "type",
      "submit",
    );
  });
  it("renders an empty collection and reset link", () => {
    render(
      <Directory
        results={{ data: [], pagination: { limit: 20, offset: 0, total: 0 } }}
        brands={[]}
        notes={[]}
        accords={[]}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "No scents found" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Clear filters" })).toHaveAttribute(
      "href",
      "/fragrances",
    );
  });
  it("serializes repeated filters and excludes unrelated URL parameters", () => {
    expect(
      queryString({ notes: ["a", "b"], q: "% & rose", secret: "never" }),
    ).toBe("q=%25+%26+rose&notes=a&notes=b");
  });
  it("uses the configurable API URL with no cache and a timeout", async () => {
    vi.stubEnv("API_BASE_URL", "https://catalog.example/api/v1/");
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(page)));
    expect(await api("/fragrances", fetcher)).toEqual(page);
    expect(fetcher).toHaveBeenCalledWith(
      "https://catalog.example/api/v1/fragrances",
      expect.objectContaining({
        cache: "no-store",
        signal: expect.any(AbortSignal),
      }),
    );
  });
  it.each([404, 422, 500])("sanitizes API errors (%s)", async (status) => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response("private error", { status }));
    await expect(api("/fragrances", fetcher)).rejects.toMatchObject({ status });
    await expect(api("/fragrances", fetcher)).rejects.not.toThrow(
      "private error",
    );
  });
  it("maps connection failures to a safe unavailable error", async () => {
    await expect(
      api("/fragrances", vi.fn().mockRejectedValue(new Error("password"))),
    ).rejects.toEqual(new ApiError(503));
  });
  it("forwards search and filters through the typed client", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(page)));
    vi.stubGlobal("fetch", fetcher);
    expect(
      await getFragrances({ q: "paper", concentration: "eau_de_parfum" }),
    ).toEqual(page);
    expect(fetcher.mock.calls[0][0]).toContain(
      "/fragrances?q=paper&concentration=eau_de_parfum",
    );
  });
  it("renders the server directory from API responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation((url: string) =>
          Promise.resolve(
            new Response(
              JSON.stringify(
                url.includes("/fragrances?")
                  ? page
                  : { data: [brand], pagination: page.pagination },
              ),
            ),
          ),
        ),
    );
    render(
      await FragrancesPage({ searchParams: Promise.resolve({ q: "paper" }) }),
    );
    expect(
      screen.getByRole("heading", { name: "Paper Horizon" }),
    ).toBeInTheDocument();
  });
  it("renders the homepage from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(page))),
    );
    render(await Home());
    expect(
      screen.getByRole("heading", { name: "Paper Horizon" }),
    ).toBeInTheDocument();
  });
  it("renders API brands and demo labels", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ ...page, data: [brand] })),
        ),
    );
    render(await BrandsPage({ searchParams: Promise.resolve({}) }));
    expect(
      screen.getByRole("heading", { name: "Nacre Workshop" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Synthetic demo house")).toBeInTheDocument();
  });
});

describe("UUID detail integration", () => {
  const id = "00000000-0000-4000-8000-000000000001";
  it("renders release IDs and nullable public fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: {
              ...fragrance,
              id,
              releases: [
                {
                  id: "release-id",
                  concentration: null,
                  release_year: null,
                  notes: [],
                  accords: [],
                  synthetic: true,
                },
              ],
            },
          }),
        ),
      ),
    );
    render(await FragrancePage({ params: Promise.resolve({ id }) }));
    expect(
      screen.getByRole("heading", { name: "Paper Horizon" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Release year unknown")).toBeInTheDocument();
    expect(screen.getByText("Release ID: release-id")).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: /source/i }),
    ).not.toBeInTheDocument();
  });
  it("maps hidden or missing API resources to not found", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("", { status: 404 })),
    );
    await expect(
      FragrancePage({ params: Promise.resolve({ id }) }),
    ).rejects.toThrow("NOT_FOUND");
  });
  it("rejects malformed detail IDs before making a request", async () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    await expect(
      FragrancePage({ params: Promise.resolve({ id: "not-a-uuid" }) }),
    ).rejects.toThrow("NOT_FOUND");
    expect(fetcher).not.toHaveBeenCalled();
  });
});
