import { SourceCredits } from "@/components/source-credits";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { ApiError, getFragrance, label } from "@/lib/api";
import { BottleImage } from "@/components/bottle-image";
export const dynamic = "force-dynamic";
export default async function FragrancePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
  )
    notFound();
  const f = await getFragrance(id)
    .then((r) => r.data)
    .catch((e: unknown) => {
      if (e instanceof ApiError && e.status === 404) notFound();
      throw e;
    });
  return (
    <div className="shell section">
      <Link href="/fragrances" className="back-link">
        <ArrowLeft size={16} />
        Back to the collection
      </Link>
      <section className="detail-grid">
        <div className="detail-art">
          <BottleImage image={f.primary_image} name={f.name} large />
          {f.primary_image && (
            <SourceCredits credits={[f.primary_image.attribution]} />
          )}
        </div>
        <div className="detail-copy">
          <p className="eyebrow">{f.brand.name}</p>
          <h1>{f.name}</h1>
          {f.synthetic && (
            <p className="demo-note">
              Synthetic demo fragrance. Invented data; no affiliation to real
              perfume houses.
            </p>
          )}
          {!!f.images?.length && (
            <div className="image-gallery" aria-label="Fragrance image gallery">
              {f.images
                .filter((image) => image.id !== f.primary_image?.id)
                .map((image) => (
                  <figure key={image.id}>
                    <BottleImage image={image} name={f.name} />
                    <figcaption>
                      <SourceCredits credits={[image.attribution]} />
                    </figcaption>
                  </figure>
                ))}
            </div>
          )}
          <div className="note-pyramid">
            {f.releases.map((r) => (
              <section key={r.id}>
                <h2>{label(r.concentration)}</h2>
                <p>{r.release_year ?? "Release year unknown"}</p>
                <p>
                  Notes:{" "}
                  {r.notes.map((n) => n.name).join(" · ") || "Not published"}
                </p>
                <p>
                  Accords:{" "}
                  {r.accords.map((a) => a.name).join(" · ") || "Not published"}
                </p>
                {!!r.images?.length && (
                  <div
                    className="image-gallery"
                    aria-label={`${label(r.concentration)} images`}
                  >
                    {r.images.map((image) => (
                      <figure key={image.id}>
                        <BottleImage image={image} name={f.name} />
                        <figcaption>
                          <SourceCredits credits={[image.attribution]} />
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                )}
                {r.variant_images?.map((variant) => (
                  <div
                    key={variant.variant_id}
                    className="image-gallery"
                    aria-label="Bottle variant images"
                  >
                    {variant.images?.map((image) => (
                      <figure key={image.id}>
                        <BottleImage image={image} name={f.name} />
                        <figcaption>
                          <SourceCredits credits={[image.attribution]} />
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                ))}
                <small>Release ID: {r.id}</small>
              </section>
            ))}
          </div>
          {!f.releases.length && (
            <p>No public release information available.</p>
          )}
          {f.releases_truncated && <p>Showing the first 20 public releases.</p>}
          <SourceCredits credits={f.attributions} />
          <Link
            className="brand-link"
            href={`/fragrances?brand=${encodeURIComponent(f.brand.slug)}`}
          >
            Explore {f.brand.name}
          </Link>
        </div>
      </section>
    </div>
  );
}
