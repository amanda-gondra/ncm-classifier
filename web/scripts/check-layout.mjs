// Checks the published page at phone and desktop widths: no horizontal scroll, every
// section present, share tags and images reachable. Read-only; prints one line per check.
//
// Usage (from web/): node scripts/check-layout.mjs [--url <site>]
import { existsSync } from "node:fs";
import { parseArgs } from "node:util";

import { chromium } from "playwright-core";

const { values: args } = parseArgs({
  options: { url: { type: "string", default: "https://amanda-gondra.github.io/ncm-classifier/" } },
});

const WIDTHS = [320, 360, 390, 768, 1280];
const SECTIONS = ["inicio", "como-funciona", "demonstracao", "resultados", "arquitetura"];
const browserPath = [
  process.env.BROWSER_PATH,
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].find((path) => path && existsSync(path));
if (!browserPath) throw new Error("No Chromium browser found: set BROWSER_PATH.");

let failures = 0;
const report = (ok, message) => {
  if (!ok) failures += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${message}`);
};

const browser = await chromium.launch({ executablePath: browserPath });
try {
  for (const width of WIDTHS) {
    const page = await browser.newPage({ viewport: { width, height: 800 } });
    await page.goto(args.url, { waitUntil: "networkidle" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    report(overflow <= 0, `${width}px: no horizontal scroll (${overflow}px extra)`);
    const missing = [];
    for (const id of SECTIONS) {
      if ((await page.locator(`#${id}`).count()) !== 1) missing.push(id);
    }
    report(missing.length === 0, `${width}px: sections present${missing.length ? ` (missing ${missing})` : ""}`);
    await page.close();
  }

  const page = await browser.newPage();
  await page.goto(args.url, { waitUntil: "networkidle" });
  const tags = await page.evaluate(() => ({
    image: document.querySelector('meta[property="og:image"]')?.getAttribute("content"),
    title: document.querySelector('meta[property="og:title"]')?.getAttribute("content"),
    icon: document.querySelector('link[rel="icon"]')?.getAttribute("href"),
  }));
  report(Boolean(tags.title), `og:title: ${tags.title}`);
  for (const [name, href] of [["og:image", tags.image], ["icon", tags.icon]]) {
    const response = href ? await page.request.get(new URL(href, args.url).toString()) : null;
    const type = response?.headers()["content-type"] ?? "-";
    report(response?.ok() === true && type.startsWith("image/png"), `${name} ${href} -> ${response?.status() ?? "-"} ${type}`);
  }
  await page.close();
} finally {
  await browser.close();
}
process.exitCode = failures ? 1 : 0;
