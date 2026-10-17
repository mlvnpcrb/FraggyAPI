import type { CSSProperties } from "react";
export function Bottle({
  color,
  accent,
  name,
  large = false,
}: {
  color: string;
  accent: string;
  name: string;
  large?: boolean;
}) {
  return (
    <div
      className={`bottle-stage ${large ? "bottle-large" : ""}`}
      style={
        { "--bottle-color": color, "--bottle-accent": accent } as CSSProperties
      }
      aria-hidden="true"
    >
      <div className="bottle-shadow" />
      <div className="bottle">
        <div className="bottle-cap" />
        <div className="bottle-neck" />
        <div className="bottle-body">
          <div className="bottle-label">
            <span>F / A</span>
            <strong>{name}</strong>
            <small>AN IMAGINED SCENT</small>
          </div>
        </div>
      </div>
    </div>
  );
}
