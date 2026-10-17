import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { Fragrance } from "@/lib/mock-data";
import { Bottle } from "./bottle";
export function FragranceCard({ fragrance: f }: { fragrance: Fragrance }) {
  return (
    <Link href={`/fragrances/${f.slug}`} className="fragrance-card group">
      <div className="card-art">
        <span className="family-tag">{f.family}</span>
        <Bottle color={f.color} accent={f.accent} name={f.name} />
        <span className="card-arrow">
          <ArrowUpRight size={18} />
        </span>
      </div>
      <div className="card-info">
        <p className="eyebrow">{f.brand}</p>
        <h3>{f.name}</h3>
        <p className="muted">
          {f.concentration} <span>·</span> {f.year}
        </p>
      </div>
    </Link>
  );
}
