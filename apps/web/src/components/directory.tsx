"use client";
import { useState } from "react";
import { Search, SlidersHorizontal, X } from "lucide-react";
import { brands, concentrations, filterFragrances } from "@/lib/mock-data";
import { FragranceCard } from "./fragrance-card";
import { Button } from "./ui/button";
export function Directory({
  initialQuery = "",
  initialBrand = "",
}: {
  initialQuery?: string;
  initialBrand?: string;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [brand, setBrand] = useState(initialBrand);
  const [concentration, setConcentration] = useState("");
  const results = filterFragrances(query, brand, concentration);
  function reset() {
    setQuery("");
    setBrand("");
    setConcentration("");
  }
  return (
    <>
      <div className="filter-bar">
        <div className="search-input">
          <Search size={19} />
          <input
            type="search"
            aria-label="Search fragrances"
            placeholder="Search by fragrance, brand or note…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="select-filters">
          <SlidersHorizontal size={18} aria-hidden="true" />
          <select
            aria-label="Filter by brand"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
          >
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </select>
          <select
            aria-label="Filter by concentration"
            value={concentration}
            onChange={(e) => setConcentration(e.target.value)}
          >
            <option value="">All concentrations</option>
            {concentrations.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="results-caption">
        <p aria-live="polite">
          {results.length} {results.length === 1 ? "fragrance" : "fragrances"}
        </p>
        <span>Synthetic collection</span>
      </div>
      {results.length ? (
        <div className="fragrance-grid">
          {results.map((f) => (
            <FragranceCard key={f.slug} fragrance={f} />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Search size={28} />
          <h2>No scents found</h2>
          <p>
            Try another note or clear your filters to explore the collection.
          </p>
          <Button variant="outline" onClick={reset}>
            <X size={16} />
            Clear filters
          </Button>
        </div>
      )}
    </>
  );
}
