import type { NextConfig } from "next";

// Static export: the site is plain HTML, CSS and JS served by GitHub Pages, and every call
// to the NCM Classifier API happens in the browser. No Next.js server runs anywhere.
//
// GitHub Pages serves the site under /<repository>, so the Pages workflow sets
// PAGES_BASE_PATH=/ncm-classifier; locally the site lives at the root.
const basePath = process.env.PAGES_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  // /ncm-classifier/ is served as /ncm-classifier/index.html by GitHub Pages.
  trailingSlash: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
