import type { NextConfig } from "next";

const config: NextConfig = {
  poweredByHeader: false,
  // On Vercel the catch-all rewrite to the web service sends /_next/image to the app, which answers 404.
  images: { unoptimized: true },
};

export default config;
