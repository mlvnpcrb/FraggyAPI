import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Directory } from "@/components/directory";
import { filterFragrances } from "@/lib/mock-data";

describe("synthetic directory", () => {
  it("combines normalized text, brand and concentration filters", () => {
    expect(
      filterFragrances("  CEDAR  ", "Maison Aube", "Eau de Parfum").map(
        (f) => f.slug,
      ),
    ).toEqual(["santal-no-04"]);
    expect(filterFragrances("", "Atelier Vert", "Eau de Parfum")).toHaveLength(
      0,
    );
  });
  it("filters interactively and resets an empty state", async () => {
    const user = userEvent.setup();
    render(<Directory />);
    expect(screen.getByText("6 fragrances")).toBeInTheDocument();
    await user.selectOptions(
      screen.getByLabelText("Filter by brand"),
      "Maison Aube",
    );
    expect(screen.getByText("2 fragrances")).toBeInTheDocument();
    await user.selectOptions(
      screen.getByLabelText("Filter by concentration"),
      "Eau de Parfum",
    );
    expect(
      screen.getByRole("heading", { name: "Santal No. 04" }),
    ).toBeInTheDocument();
    await user.type(screen.getByRole("searchbox"), "nonexistent");
    expect(
      screen.getByRole("heading", { name: "No scents found" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByText("6 fragrances")).toBeInTheDocument();
  });
  it("links cards to detail pages", () => {
    render(<Directory initialQuery="figue" />);
    expect(screen.getByRole("link", { name: /Figue Sauvage/ })).toHaveAttribute(
      "href",
      "/fragrances/figue-sauvage",
    );
  });
});
