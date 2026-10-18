import { SourceCredits } from "./source-credits";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { label, type Fragrance } from "@/lib/api";
import { BottleImage } from "./bottle-image";
export function FragranceCard({ fragrance: f }: { fragrance: Fragrance }) {
  return (
    <article>
      <Link href={`/fragrances/${f.id}`} className="fragrance-card group">
        <div className="card-art">
          <span className="family-tag">
            {f.synthetic ? "Synthetic demo" : "Discovery"}
          </span>
          <BottleImage image={f.primary_image} name={f.name} />
          <span className="card-arrow">
            <ArrowUpRight size={18} />
          </span>
        </div>
        <div className="card-info">
          <p className="eyebrow">{f.brand.name}</p>
          <h3>{f.name}</h3>
          <p className="muted">
            {label(f.releases[0]?.concentration ?? null)} <span>·</span>{" "}
            {f.releases[0]?.release_year ?? "Year unknown"}
          </p>
        </div>
      </Link>
      <SourceCredits credits={f.attributions} />
      {f.primary_image && (
        <SourceCredits credits={[f.primary_image.attribution]} />
      )}
    </article>
  );
}
