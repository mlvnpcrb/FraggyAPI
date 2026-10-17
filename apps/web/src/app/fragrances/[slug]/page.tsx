import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { fragrances } from "@/lib/mock-data";
import { Bottle } from "@/components/bottle";
import { FragranceCard } from "@/components/fragrance-card";
export function generateStaticParams() {
  return fragrances.map(({ slug }) => ({ slug }));
}
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return {
    title:
      fragrances.find((f) => f.slug === slug)?.name ?? "Fragrance not found",
  };
}
export default async function FragrancePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const f = fragrances.find((item) => item.slug === slug);
  if (!f) notFound();
  return (
    <div className="shell section">
      <Link href="/fragrances" className="back-link">
        <ArrowLeft size={16} />
        Back to the collection
      </Link>
      <section className="detail-grid">
        <div className="detail-art">
          <Bottle color={f.color} accent={f.accent} name={f.name} large />
          <span>ORIGINAL ILLUSTRATION · SYNTHETIC FRAGRANCE</span>
        </div>
        <div className="detail-copy">
          <p className="eyebrow">
            {f.brand} / {f.year}
          </p>
          <h1>{f.name}</h1>
          <p className="concentration">
            {f.concentration}
            <span>{f.family}</span>
          </p>
          <p className="detail-description">{f.description}</p>
          <div className="note-pyramid">
            {Object.entries(f.notes).map(([level, notes]) => (
              <div key={level}>
                <p className="eyebrow">{level} NOTES</p>
                <p>{notes.join(" · ")}</p>
              </div>
            ))}
          </div>
          <Link
            className="brand-link"
            href={`/fragrances?brand=${encodeURIComponent(f.brand)}`}
          >
            Explore {f.brand} <ArrowUpRight size={18} />
          </Link>
          <p className="demo-note">
            Fictional perfume. Notes and descriptions are invented; no ratings
            or licensed source content.
          </p>
        </div>
      </section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">KEEP YOUR CURIOSITY</p>
          <h2>Another direction</h2>
        </div>
      </div>
      <div className="fragrance-grid">
        {fragrances
          .filter((other) => other.slug !== slug)
          .slice(0, 3)
          .map((other) => (
            <FragranceCard key={other.slug} fragrance={other} />
          ))}
      </div>
    </div>
  );
}
