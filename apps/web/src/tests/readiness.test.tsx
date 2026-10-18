import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ErrorPage from "@/app/error";
import Home from "@/app/page";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("uses the current Next retry callback so recovery refetches server data", () => {
  const retry = vi.fn();
  render(
    <ErrorPage error={new Error("PRIVATE_SERVER_DETAIL")} retry={retry} />,
  );
  expect(screen.queryByText(/PRIVATE_SERVER_DETAIL/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(retry).toHaveBeenCalledOnce();
});
it("keeps homepage source credits outside the positioned hero artwork", async () => {
  const credit = {
    id: "original-fixture",
    provider: "Original fictional workshop",
    text: "Original fixture metadata",
    source_url: "https://example.invalid/fixture",
    license_name: "Original fixture permission",
    license_url: "https://example.invalid/permission",
    copyright_holder: null,
    placement: "adjacent_record",
    modification_disclosure_required: false,
    modification_disclosure: null,
    redistribution_conditions: [],
    last_verified: "2026-10-19",
    fields: ["name"],
  };
  const fragrance = {
    id: "12345678-1234-4234-8234-123456789abc",
    name: "Original Fixture",
    slug: "original-fixture",
    synthetic: true,
    brand: {
      id: "brand",
      name: "Original House",
      slug: "original-house",
      synthetic: true,
    },
    releases: [],
    releases_truncated: false,
    attributions: [credit],
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: [fragrance],
          pagination: { limit: 4, offset: 0, total: 1 },
        }),
        { headers: { "Content-Type": "application/json" } },
      ),
    ),
  );
  const { container } = render(await Home());
  const feature = container.querySelector(".hero-feature");
  expect(feature?.querySelector(".source-credits")).toBeInTheDocument();
  expect(container.querySelector(".hero-art .source-credits")).toBeNull();
});
