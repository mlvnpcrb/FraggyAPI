import { SourceCredits } from "@/components/source-credits";
import Link from "next/link";
import { api, type NamedEntity, type Page } from "@/lib/api";
export const metadata = { title: "The houses" };
export const dynamic = "force-dynamic";
export default async function BrandsPage({
  searchParams,
}: {
  searchParams: Promise<{ offset?: string }>;
}) {
  const { offset = "0" } = await searchParams;
  const brands = await api<Page<NamedEntity>>(
    `/brands?limit=20&offset=${encodeURIComponent(offset)}`,
  );
  return (
    <section className="shell section brands-page">
      <p className="eyebrow">THE PEOPLE BEHIND THE FEELING</p>
      <h1>
        Independent spirit.
        <br />
        <em>The houses.</em>
      </h1>
      <p className="page-intro">
        Explore the public catalog. Synthetic houses are marked as
        demonstrations.
      </p>
      <div className="brands-grid">
        {brands.data.map((brand, i) => (
          <article key={brand.id}>
            <Link
              href={`/fragrances?brand=${encodeURIComponent(brand.slug)}`}
              className="brand-card"
            >
              <span className="eyebrow">HOUSE / {i + 1}</span>
              <div className="brand-monogram" aria-hidden="true">
                {brand.name
                  .split(" ")
                  .map((w) => w[0])
                  .join("")}
              </div>
              <h2>{brand.name}</h2>
              <p>
                {brand.synthetic
                  ? "Synthetic demo house"
                  : "Explore fragrances"}
              </p>
            </Link>
            <SourceCredits credits={brand.attributions} />
          </article>
        ))}
      </div>
      {!brands.data.length && (
        <p className="empty-state">No public houses yet.</p>
      )}
      <nav aria-label="Brand pagination" className="catalog-pagination">
        {brands.pagination.offset > 0 && (
          <Link
            href={`/brands?offset=${Math.max(0, brands.pagination.offset - 20)}`}
          >
            Previous page
          </Link>
        )}
        {brands.pagination.offset + 20 < brands.pagination.total &&
          brands.pagination.offset + 20 <= 10000 && (
            <Link href={`/brands?offset=${brands.pagination.offset + 20}`}>
              Next page
            </Link>
          )}
      </nav>
    </section>
  );
}
