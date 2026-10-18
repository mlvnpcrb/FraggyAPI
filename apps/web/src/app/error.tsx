"use client";
import { Button } from "@/components/ui/button";
export default function ErrorPage({
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  return (
    <section className="shell section empty-state">
      <p className="eyebrow">A MOMENT OF PAUSE</p>
      <h1>Something went wrong.</h1>
      <p>We couldn’t open the collection. Please try again.</p>
      <Button onClick={retry}>Try again</Button>
    </section>
  );
}
