import type { Metadata } from "next";
import Link from "next/link";
import { Providers } from "@/components/providers";
import { Navigation } from "@/components/navigation";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "Fraggy — A world of scent", template: "%s | Fraggy" },
  description:
    "Explore a thoughtfully imagined fragrance collection. Synthetic demo data only.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <a href="#main" className="skip-link">
            Skip to content
          </a>
          <Navigation />
          <main id="main">{children}</main>
          <footer className="site-footer shell">
            <div>
              <Link href="/" className="wordmark">
                fraggy<span>®</span>
              </Link>
              <p>A little curiosity. A world of scent.</p>
            </div>
            <div>
              <p>An independent scent discovery catalog</p>
              <small>
                Synthetic entries are labeled. Original bottle illustrations.
              </small>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
