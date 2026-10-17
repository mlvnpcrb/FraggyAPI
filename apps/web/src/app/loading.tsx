export default function Loading() {
  return (
    <div className="shell section" role="status">
      <span className="eyebrow">Opening the collection…</span>
      <div className="skeleton-heading" />
      <div className="fragrance-grid">
        {[1, 2, 3].map((n) => (
          <div className="skeleton-card" key={n} />
        ))}
      </div>
    </div>
  );
}
