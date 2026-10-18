import Link from "next/link";
import { Search } from "lucide-react";
import {
  concentrations,
  label,
  queryString,
  type Filters,
  type Fragrance,
  type NamedEntity,
  type Page,
} from "@/lib/api";
import { FragranceCard } from "./fragrance-card";
import { Button } from "./ui/button";
export function Directory({
  results,
  brands,
  notes,
  accords,
  filters = {},
}: {
  results: Page<Fragrance>;
  brands: NamedEntity[];
  notes: NamedEntity[];
  accords: NamedEntity[];
  filters?: Filters;
}) {
  const value = (key: string) => {
    const v = filters[key];
    return Array.isArray(v) ? v[0] : v || "";
  };
  const { total, limit, offset } = results.pagination;
  return (
    <>
      <form
        key={queryString(filters)}
        action="/fragrances"
        className="filter-bar"
      >
        <div className="search-input">
          <Search size={19} aria-hidden="true" />
          <input
            type="search"
            name="q"
            aria-label="Search fragrances"
            placeholder="Search fragrance or brand…"
            defaultValue={value("q")}
            maxLength={120}
          />
        </div>
        <div className="select-filters">
          <select
            name="brand"
            aria-label="Filter by brand"
            defaultValue={value("brand")}
          >
            <option value="">All brands</option>
            {brands.map((b) => (
              <option key={b.id} value={b.slug}>
                {b.name}
              </option>
            ))}
          </select>
          <select
            name="concentration"
            aria-label="Filter by concentration"
            defaultValue={value("concentration")}
          >
            <option value="">All concentrations</option>
            {concentrations.map((c) => (
              <option key={c} value={c}>
                {label(c)}
              </option>
            ))}
          </select>
          <input
            name="year"
            type="number"
            min="1000"
            max="2999"
            aria-label="Release year"
            placeholder="Year"
            defaultValue={value("year")}
          />
          <select
            name="notes"
            aria-label="Filter by note"
            defaultValue={value("notes")}
          >
            <option value="">All notes</option>
            {notes.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
          <select
            name="accords"
            aria-label="Filter by accord"
            defaultValue={value("accords")}
          >
            <option value="">All accords</option>
            {accords.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
          <select
            name="sort"
            aria-label="Sort fragrances"
            defaultValue={value("sort") || "relevance"}
          >
            <option value="relevance">Relevance</option>
            <option value="name">Name A–Z</option>
            <option value="name_desc">Name Z–A</option>
          </select>
          <Button type="submit">Search</Button>
        </div>
      </form>
      <div className="results-caption">
        <p aria-live="polite">
          {total} {total === 1 ? "fragrance" : "fragrances"}
        </p>
        <span>
          {results.data.some((f) => f.synthetic)
            ? "Synthetic demo collection"
            : "Public catalog"}
        </span>
      </div>
      {results.data.length ? (
        <div className="fragrance-grid">
          {results.data.map((f) => (
            <FragranceCard key={f.id} fragrance={f} />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Search size={28} />
          <h2>No scents found</h2>
          <p>
            Try another search or clear your filters to explore the collection.
          </p>
          <Button asChild variant="outline">
            <Link href="/fragrances">Clear filters</Link>
          </Button>
        </div>
      )}
      <nav className="catalog-pagination" aria-label="Catalog pagination">
        {offset > 0 && (
          <Link
            href={`/fragrances?${queryString({ ...filters, offset: String(Math.max(0, offset - limit)) })}`}
          >
            Previous page
          </Link>
        )}
        {offset + limit < total && offset + limit <= 10000 && (
          <Link
            href={`/fragrances?${queryString({ ...filters, offset: String(offset + limit) })}`}
          >
            Next page
          </Link>
        )}
      </nav>
    </>
  );
}
