import type { Attribution } from "@/lib/api";

function safeLink(value: string): string | undefined {
  try {
    const url = new URL(value);
    if (
      url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      !url.search &&
      !/[\s\\]/.test(value)
    )
      return value;
  } catch {
    /* Untrusted transport values never become executable links. */
  }
  return undefined;
}

export function SourceCredits({ credits }: { credits?: Attribution[] }) {
  if (!credits?.length) return null;
  return (
    <section className="source-credits" aria-label="Source credits">
      <h2>Source credits</h2>
      <ul>
        {credits.map((credit) => (
          <li key={credit.id}>
            <p>
              <strong>{credit.provider}</strong> — {credit.text}
            </p>
            <p>
              <a
                href={safeLink(credit.source_url)}
                target="_blank"
                rel="noopener noreferrer"
              >
                Source
              </a>
              {" · "}
              <a
                href={safeLink(credit.license_url)}
                target="_blank"
                rel="noopener noreferrer"
              >
                {credit.license_name}
              </a>
            </p>
            {credit.copyright_holder && <p>© {credit.copyright_holder}</p>}
            {credit.modification_disclosure && (
              <p>{credit.modification_disclosure}</p>
            )}
            <small>Verified {credit.last_verified}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}
