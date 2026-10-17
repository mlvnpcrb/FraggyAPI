import { Directory } from "@/components/directory";
export const metadata = { title: "Fragrances" };
export default async function FragrancesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; brand?: string }>;
}) {
  const params = await searchParams;
  const query = typeof params.q === "string" ? params.q : "";
  const brand = typeof params.brand === "string" ? params.brand : "";
  return (
    <section className="shell section directory-page">
      <p className="eyebrow">THE COLLECTION</p>
      <h1>
        Find your next <em>feeling.</em>
      </h1>
      <p className="page-intro">
        From familiar comforts to unexpected discoveries. Explore our imagined
        scent library.
      </p>
      <Directory
        key={`${query}:${brand}`}
        initialQuery={query}
        initialBrand={brand}
      />
    </section>
  );
}
