// Fonts for the share image, the same families as the page (Geist and Geist Mono, from the
// official `geist` package, SIL Open Font License). Read once, at build time.
import { readFile } from "node:fs/promises";
import { join } from "node:path";

const FONT_DIR = join(process.cwd(), "node_modules", "geist", "dist", "fonts");

const FILES = [
  { name: "Geist", file: "geist-sans/Geist-Regular.ttf", weight: 400 },
  { name: "Geist", file: "geist-sans/Geist-Bold.ttf", weight: 700 },
  { name: "Geist Mono", file: "geist-mono/GeistMono-Bold.ttf", weight: 700 },
] as const;

export const shareFonts = Promise.all(
  FILES.map(async ({ name, file, weight }) => ({
    name,
    data: await readFile(join(FONT_DIR, file)),
    weight,
    style: "normal" as const,
  })),
);
