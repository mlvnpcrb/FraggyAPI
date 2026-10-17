import Link from "next/link";
import { Button } from "@/components/ui/button";
export default function NotFound() {
  return (
    <section className="shell section empty-state">
      <p className="eyebrow">404 / A SCENT UNKNOWN</p>
      <h1>A little off the trail.</h1>
      <p>We couldn’t find that fragrance or page.</p>
      <Button asChild>
        <Link href="/fragrances">Explore the collection</Link>
      </Button>
    </section>
  );
}
