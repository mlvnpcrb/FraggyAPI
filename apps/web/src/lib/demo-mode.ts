/** Explicit deployment mode. Never enabled by an API error or NODE_ENV. */
export function isDemoMode(): boolean {
  const mode = process.env.FRAGGY_DEMO_MODE;
  if (mode && mode !== "synthetic")
    throw new Error("Invalid FRAGGY_DEMO_MODE; use synthetic or leave unset.");
  return mode === "synthetic";
}
