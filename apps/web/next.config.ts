import type { NextConfig } from "next";
const config: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return process.env.FRAGGY_DEMO_MODE === "synthetic"
      ? [
          {
            source: "/:path*",
            headers: [
              { key: "X-Robots-Tag", value: "noindex, nofollow, noarchive" },
              { key: "X-Content-Type-Options", value: "nosniff" },
            ],
          },
        ]
      : [];
  },
};
export default config;
