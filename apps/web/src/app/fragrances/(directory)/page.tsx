import { Directory } from "@/components/directory";
import {
  api,
  getBrands,
  getFragrances,
  type Filters,
  type NamedEntity,
  type Page,
} from "@/lib/api";
export const metadata = { title: "Fragrances" };
export const dynamic = "force-dynamic";
export default async function FragrancesPage({
  searchParams,
}: {
  searchParams: Promise<Filters>;
}) {
  const filters = await searchParams;
  const [results, brands, notes, accords] = await Promise.all([
    getFragrances(filters),
    getBrands(),
    api<Page<NamedEntity>>("/notes?limit=50"),
    api<Page<NamedEntity>>("/accords?limit=50"),
  ]);
  return (
    <section className="shell section directory-page">
      <p className="eyebrow">THE COLLECTION</p>
      <h1>
        Find your next <em>feeling.</em>
      </h1>
      <p className="page-intro">
        From familiar comforts to unexpected discoveries. Explore the public
        scent library.
      </p>
      <Directory
        results={results}
        brands={brands.data}
        notes={notes.data}
        accords={accords.data}
        filters={filters}
      />
    </section>
  );
}
