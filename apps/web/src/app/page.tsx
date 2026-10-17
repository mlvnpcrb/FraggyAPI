import Link from "next/link";
import { ArrowRight, ArrowDownRight, Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Bottle } from "@/components/bottle";
import { FragranceCard } from "@/components/fragrance-card";
import { fragrances } from "@/lib/mock-data";
export default function Home() {
  return (
    <>
      <section className="hero shell">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="tiny-dot" />
            THE ART OF FINDING YOUR SCENT
          </p>
          <h1>
            A world of scent.
            <br />
            <em>A little more you.</em>
          </h1>
          <p className="hero-description">
            Follow your curiosity. Explore notes, discover new houses, and find
            the fragrances that feel like your story.
          </p>
          <form action="/fragrances" className="hero-search">
            <Search size={20} aria-hidden="true" />
            <input
              name="q"
              type="search"
              aria-label="Search the collection"
              placeholder="A fragrance, a note, a feeling…"
            />
            <Button type="submit" size="icon" aria-label="Search">
              <ArrowRight size={20} />
            </Button>
          </form>
          <div className="hero-caption">
            <span>INDEPENDENT SPIRIT</span>
            <span>ENDLESS CURIOSITY</span>
          </div>
        </div>
        <div className="hero-art">
          <span className="art-corner">THE SCENT EDIT — 001</span>
          <div className="art-ring" />
          <Bottle color="#c9b58f" accent="#60503b" name="Santal No. 04" large />
          <div className="art-caption">
            <div>
              <p className="eyebrow">THE QUIET EXPRESSION</p>
              <h2>
                Less noise.
                <br />
                More feeling.
              </h2>
            </div>
            <Link
              href="/fragrances/santal-no-04"
              aria-label="Discover Santal No. 04"
            >
              <ArrowDownRight size={30} />
            </Link>
          </div>
        </div>
      </section>
      <div className="note-ribbon">
        <div className="shell">
          <Sparkles size={17} />
          <span>Every scent tells a story</span>
          <i>Woody</i>
          <span>·</span>
          <i>Floral</i>
          <span>·</span>
          <i>Fresh</i>
          <span>·</span>
          <i>Unexpected</i>
        </div>
      </div>
      <section className="section shell">
        <div className="section-heading">
          <div>
            <p className="eyebrow">A GOOD PLACE TO BEGIN</p>
            <h2>The discovery edit</h2>
          </div>
          <Button asChild variant="outline">
            <Link href="/fragrances">
              Explore all fragrances <ArrowRight size={17} />
            </Link>
          </Button>
        </div>
        <div className="fragrance-grid featured-grid">
          {fragrances.slice(0, 4).map((f) => (
            <FragranceCard key={f.slug} fragrance={f} />
          ))}
        </div>
      </section>
      <section className="editorial shell">
        <p className="eyebrow">FIND YOUR OWN WAY</p>
        <h2>
          Not just a fragrance.
          <br />
          <em>A feeling worth following.</em>
        </h2>
        <Button asChild>
          <Link href="/brands">
            Meet the imagined houses <ArrowRight size={17} />
          </Link>
        </Button>
        <p className="demo-note">
          An independent design study using fictional perfumes and original
          bottle illustrations.
        </p>
      </section>
    </>
  );
}
