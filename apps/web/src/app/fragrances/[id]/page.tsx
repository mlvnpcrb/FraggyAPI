import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { ApiError, getFragrance, label } from "@/lib/api";
import { Bottle } from "@/components/bottle";
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
          <Bottle color="#d3b994" accent="#695039" name={f.name} large />
          <span>ORIGINAL BOTTLE ILLUSTRATION</span>
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
                <small>Release ID: {r.id}</small>
              </section>
            ))}
          </div>
          {!f.releases.length && (
            <p>No public release information available.</p>
          )}
          {f.releases_truncated && <p>Showing the first 20 public releases.</p>}
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
