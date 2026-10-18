import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { SourceCredits } from "@/components/source-credits";
import { FragranceCard } from "@/components/fragrance-card";
import { Directory } from "@/components/directory";
import FragrancePage from "@/app/fragrances/[id]/page";
import BrandsPage from "@/app/brands/page";
import type { Attribution, Fragrance } from "@/lib/api";

const credit: Attribution = {
  id: "credit-one",
  provider: "Fictional Workshop",
  text: "Original invented data.",
  source_url: "https://example.invalid/workshop",
  license_name: "Fictional permission",
  license_url: "https://example.invalid/permission",
  copyright_holder: "Fictional Workshop",
  placement: "adjacent_record",
  modification_disclosure_required: true,
  modification_disclosure: "Names normalized by FraggyAPI.",
  redistribution_conditions: [],
  last_verified: "2026-10-18",
  fields: ["/name"],
};
const brand = {
  id: "house-id",
  name: "Invented House",
  slug: "invented-house",
  synthetic: true,
  attributions: [credit],
};
const fragrance: Fragrance = {
  id: "12345678-1234-4234-8234-123456789abc",
  name: "Fictional Stars",
  slug: "fictional-stars",
  synthetic: true,
  brand,
  releases: [],
  releases_truncated: false,
  attributions: [credit],
};
const page = {
  data: [fragrance],
  pagination: { limit: 20, offset: 0, total: 1 },
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("public attribution", () => {
  it("renders accessible provider, license, copyright and modification credits", () => {
    render(<SourceCredits credits={[credit]} />);
    expect(
      screen.getByRole("region", { name: "Source credits" }),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Fictional permission" });
    expect(link).toHaveAttribute("href", credit.license_url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(
      screen.getByText(credit.modification_disclosure!),
    ).toBeInTheDocument();
    expect(screen.getByText(/© Fictional Workshop/)).toBeInTheDocument();
  });
  it("renders multiple sources and omits empty credit sections", () => {
    const { rerender, container } = render(<SourceCredits />);
    expect(container).toBeEmptyDOMElement();
    rerender(
      <SourceCredits
        credits={[
          credit,
          { ...credit, id: "two", provider: "Second Provider" },
        ]}
      />,
    );
    expect(screen.getByText("Second Provider")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    rerender(<SourceCredits credits={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
  it.each([
    "javascript:alert(1)",
    "data:text/html,x",
    "//evil.example",
    "https://user:pass@example.com",
    "https://example.com/?token=x",
  ])("rejects unsafe transport links: %s", (url) => {
    render(
      <SourceCredits
        credits={[{ ...credit, source_url: url, license_url: url }]}
      />,
    );
    expect(screen.queryAllByRole("link")).toHaveLength(0);
  });
  it("escapes text and keeps source links outside fragrance navigation", () => {
    const { container } = render(
      <FragranceCard
        fragrance={{
          ...fragrance,
          attributions: [{ ...credit, text: "<script>alert(1)</script>" }],
        }}
      />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("a a")).toBeNull();
    expect(
      screen.getByRole("region", { name: "Source credits" }),
    ).toHaveTextContent("<script>alert(1)</script>");
  });
  it("displays filter metadata credits even with no matching fragrances", () => {
    render(
      <Directory
        results={{ ...page, data: [] }}
        brands={[brand]}
        notes={[]}
        accords={[]}
      />,
    );
    expect(screen.getByText("Fictional Workshop")).toBeInTheDocument();
    expect(screen.getByText("No scents found")).toBeInTheDocument();
  });
  it("renders API attribution on the fragrance detail page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ data: fragrance }),
      }),
    );
    render(
      await FragrancePage({ params: Promise.resolve({ id: fragrance.id }) }),
    );
    expect(
      screen.getByRole("region", { name: "Source credits" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Source credits" }),
    ).toHaveTextContent(credit.text);
  });
  it("renders API attribution on brand pages without nested links", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ...page, data: [brand] }),
      }),
    );
    const { container } = render(
      await BrandsPage({ searchParams: Promise.resolve({}) }),
    );
    expect(
      screen.getByRole("region", { name: "Source credits" }),
    ).toHaveTextContent(credit.text);
    expect(container.querySelector("a a")).toBeNull();
  });
});
