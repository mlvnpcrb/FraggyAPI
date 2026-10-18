import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { BottleImage } from "@/components/bottle-image";
import { FragranceCard } from "@/components/fragrance-card";
import { mediaPath, proxyMedia } from "@/lib/media";
import type { BottleImage as ImageMetadata, Fragrance } from "@/lib/api";

const id = "12345678-1234-4234-8234-123456789abc";
const image: ImageMetadata = {
  id,
  url: `/api/v1/media/${id}/display`,
  thumbnail_url: `/api/v1/media/${id}/thumb`,
  width: 800,
  height: 1000,
  thumbnail_width: 256,
  thumbnail_height: 320,
  alt: "Original fictional amber bottle",
  role: "primary",
  source_id: "original-artwork",
  source_url: "https://example.invalid/artwork",
  synthetic: true,
  attribution: {
    id: "image-credit",
    provider: "Fictional artist",
    text: "Original fictional artwork",
    source_url: "https://example.invalid/artwork",
    license_name: "Fictional image permission",
    license_url: "https://example.invalid/permission",
    copyright_holder: "Fictional artist",
    placement: "adjacent_record",
    modification_disclosure_required: true,
    modification_disclosure: "Converted to WebP and resized.",
    redistribution_conditions: [],
    last_verified: "2026-10-19",
    fields: ["image"],
  },
};
const fragrance: Fragrance = {
  id,
  name: "Fictional Orbit",
  slug: "fictional-orbit",
  synthetic: true,
  brand: {
    id,
    name: "Invented House",
    slug: "invented-house",
    synthetic: true,
  },
  releases: [],
  releases_truncated: false,
  primary_image: image,
  images: [image],
};
afterEach(cleanup);

describe("rights-aware bottle images", () => {
  it("renders responsive, lazy, accessible same-origin images", () => {
    render(<BottleImage image={image} name="Fictional Orbit" large />);
    const rendered = screen.getByRole("img", { name: image.alt });
    expect(rendered).toHaveAttribute("src", `/media/${id}/display`);
    expect(rendered).toHaveAttribute("loading", "lazy");
    expect(rendered).toHaveAttribute("width", "800");
    expect(rendered).toHaveAttribute("height", "1000");
    expect(rendered.getAttribute("srcset")).toContain(
      `/media/${id}/thumb 256w`,
    );
    expect(rendered.getAttribute("sizes")).toContain("480px");
  });
  it("uses a labelled original placeholder for absent images and old API responses", () => {
    render(<BottleImage name="Fictional Orbit" />);
    expect(
      screen.getByRole("img", { name: /unavailable/ }),
    ).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
  it("falls back on broken or revoked image delivery", () => {
    render(<BottleImage image={image} name="Fictional Orbit" />);
    fireEvent.error(screen.getByRole("img", { name: image.alt }));
    expect(
      screen.getByRole("img", { name: /unavailable/ }),
    ).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
  it.each([
    "https://retailer.invalid/image.jpg",
    "//images.invalid/test.png",
    "javascript:alert(1)",
    `/api/v1/media/${id}/display?token=private`,
    "/api/v1/media/../../private/display",
  ])("rejects image URLs outside approved delivery: %s", (url) => {
    render(<BottleImage image={{ ...image, url }} name="Fictional Orbit" />);
    expect(document.querySelector("img")).toBeNull();
  });
  it("keeps image credit, copyright and license outside the product link", () => {
    render(<FragranceCard fragrance={fragrance} />);
    expect(screen.getByText("Fictional artist")).toBeInTheDocument();
    expect(screen.getByText(/Converted to WebP/)).toBeInTheDocument();
    const credit = screen.getByRole("link", {
      name: "Fictional image permission",
    });
    expect(credit.closest("a")?.parentElement?.closest("a")).toBeNull();
  });
  it("rejects malformed dimensions and mismatched asset identifiers", () => {
    expect(mediaPath({ ...image, width: 0 }, "display")).toBeNull();
    expect(mediaPath({ ...image, id: "../secret" }, "display")).toBeNull();
    expect(mediaPath({ ...image, height: 50000 }, "display")).toBeNull();
  });
});

describe("revocable image proxy", () => {
  it("fetches only a constant backend route without caching or redirects", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(new Uint8Array([1, 2, 3]), {
        headers: { "Content-Type": "image/webp" },
      }),
    );
    const response = await proxyMedia(
      id,
      "thumb",
      "http://backend.invalid/api/v1",
      fetcher,
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(fetcher).toHaveBeenCalledWith(
      `http://backend.invalid/api/v1/media/${id}/thumb`,
      expect.objectContaining({ cache: "no-store", redirect: "error" }),
    );
  });
  it.each([
    ["../private", "display"],
    [id, "https://images.invalid"],
    [id, "../../private"],
  ])(
    "rejects invalid route parameters without network access",
    async (identity, preset) => {
      const fetcher = vi.fn();
      expect(
        (
          await proxyMedia(
            identity,
            preset,
            "http://backend.invalid/api/v1",
            fetcher,
          )
        ).status,
      ).toBe(404);
      expect(fetcher).not.toHaveBeenCalled();
    },
  );
  it.each([
    new Response(null, { status: 404 }),
    new Response("<svg/>", { headers: { "Content-Type": "image/svg+xml" } }),
    new Response(new Uint8Array(5 * 1024 * 1024 + 1), {
      headers: { "Content-Type": "image/webp" },
    }),
  ])("refuses missing, untrusted or oversized bodies", async (response) => {
    expect(
      (
        await proxyMedia(
          id,
          "display",
          "http://backend.invalid/api/v1",
          vi.fn().mockResolvedValue(response),
        )
      ).status,
    ).toBe(404);
  });
  it("handles backend outage without exposing errors", async () => {
    const response = await proxyMedia(
      id,
      "display",
      "http://backend.invalid/api/v1",
      vi.fn().mockRejectedValue(new Error("PRIVATE")),
    );
    expect(response.status).toBe(404);
    expect(await response.text()).toBe("");
  });
});
