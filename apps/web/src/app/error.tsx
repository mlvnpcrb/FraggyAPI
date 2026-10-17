"use client";
import { Button } from "@/components/ui/button";
export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="shell section empty-state">
      <p className="eyebrow">A MOMENT OF PAUSE</p>
      <h1>Something went wrong.</h1>
      <p>We couldn’t open the collection. Please try again.</p>
      <Button onClick={reset}>Try again</Button>
    </section>
  );
}
