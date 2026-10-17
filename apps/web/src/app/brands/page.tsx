import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { brands, fragrances } from "@/lib/mock-data";
export const metadata = { title: "The houses" };
export default function BrandsPage() {
  return (
    <section className="shell section brands-page">
      <p className="eyebrow">THE PEOPLE BEHIND THE FEELING</p>
      <h1>
        Independent spirit.
        <br />
        <em>Imagined houses.</em>
      </h1>
      <p className="page-intro">
        Three fictional studios. Three different ways to see the world through
        scent.
      </p>
      <div className="brands-grid">
        {brands.map((brand, i) => (
          <Link
            href={`/fragrances?brand=${encodeURIComponent(brand)}`}
            key={brand}
            className="brand-card"
          >
            <span className="eyebrow">HOUSE / 0{i + 1}</span>
            <div className="brand-monogram" aria-hidden="true">
              {brand
                .split(" ")
                .map((w) => w[0])
                .join("")}
            </div>
            <h2>{brand}</h2>
            <p>
              {fragrances.filter((f) => f.brand === brand).length} imagined
              fragrances <ArrowUpRight size={18} />
            </p>
          </Link>
        ))}
      </div>
      <p className="demo-note">
        These brands are fictional demonstration data, with no affiliation to
        real perfume houses.
      </p>
    </section>
  );
}
