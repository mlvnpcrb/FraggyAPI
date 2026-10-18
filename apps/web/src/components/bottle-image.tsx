"use client";
import { useState } from "react";
import type { BottleImage as ImageMetadata } from "@/lib/api";
import { mediaPath } from "@/lib/media";
import { Bottle } from "./bottle";

/** No Next optimizer cache: revocation must be checked on every image request. */
export function BottleImage({
  image,
  name,
  large = false,
}: {
  image?: ImageMetadata | null;
  name: string;
  large?: boolean;
}) {
  const [failed, setFailed] = useState<string | null>(null);
  const source =
    image && failed !== image.id ? mediaPath(image, "display") : null;
  const thumb = image ? mediaPath(image, "thumb") : null;
  if (!image || !source || !thumb)
    return (
      <div
        role="img"
        aria-label={`Bottle image unavailable for ${name}`}
        className="bottle-placeholder"
      >
        <Bottle color="#d3b994" accent="#695039" name={name} large={large} />
        <span className="image-placeholder-label">
          Bottle image unavailable
        </span>
      </div>
    );
  return (
    <div className={`approved-bottle ${large ? "approved-bottle-large" : ""}`}>
      {/* eslint-disable-next-line @next/next/no-img-element -- private, revocable same-origin delivery; no persistent optimizer cache */}
      <img
        src={source}
        srcSet={
          image.thumbnail_width < image.width
            ? `${thumb} ${image.thumbnail_width}w, ${source} ${image.width}w`
            : undefined
        }
        sizes={
          large
            ? "(max-width: 720px) 90vw, 480px"
            : "(max-width: 600px) 90vw, 320px"
        }
        width={image.width}
        height={image.height}
        alt={image.alt || `${name} bottle`}
        loading="lazy"
        decoding="async"
        onError={() => setFailed(image.id)}
      />
    </div>
  );
}
