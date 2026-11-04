// Captures the screenshots and the GIF frames that present the project (docs/media/),
// from the running site and its real API: nothing on them is mocked.
//
// Usage (from web/):
//   node scripts/capture-media.mjs [--url <site>] [--out <dir>] [--text "<description>"]
// then, from the repository root, build the GIF from the frames:
//   python scripts/build_demo_gif.py
//
// Needs a Chromium-based browser already installed (Edge or Chrome); set BROWSER_PATH to
// use another one. playwright-core drives it and never downloads a browser.
import { existsSync } from "node:fs";
import { mkdir, rm, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";

import { chromium } from "playwright-core";

const { values: args } = parseArgs({
  options: {
    url: { type: "string", default: "https://amanda-gondra.github.io/ncm-classifier/" },
    out: { type: "string", default: "../docs/media" },
    text: { type: "string", default: "Adubo NPK 20-05-20 saco 50kg" },
  },
});

const OUT_DIR = resolve(args.out);
const FRAMES_DIR = join(OUT_DIR, "frames");
const API_READY_TIMEOUT_MS = 180_000; // the free API instance may need to wake up

const BROWSER_CANDIDATES = [
  process.env.BROWSER_PATH,
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

function findBrowser() {
  const path = BROWSER_CANDIDATES.find((candidate) => existsSync(candidate));
  if (!path) throw new Error("No Chromium browser found: set BROWSER_PATH.");
  return path;
}

async function openPage(browser, viewport, deviceScaleFactor, isMobile = false) {
  // Reduced motion turns off smooth scrolling, so each screenshot shows where it scrolled to.
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor,
    isMobile,
    hasTouch: isMobile,
    locale: "pt-BR",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto(args.url, { waitUntil: "networkidle" });
  return page;
}

async function waitForApi(page) {
  await page.getByText("API operacional").waitFor({ timeout: API_READY_TIMEOUT_MS });
}

// The classifier at the top of the page ("Experimente agora").
const quick = (page) => page.locator("#experimente");

async function classifyAtTop(page) {
  await quick(page).getByLabel("Descrição do produto").fill(args.text);
  await quick(page).getByRole("button", { name: "Classificar" }).click();
  await quick(page).locator("[data-slot=card]").waitFor();
}

// The full demonstration further down the page.
async function classifyInDemo(page) {
  const demo = page.locator("#demonstracao");
  await demo.getByLabel("Descrição do produto").fill(args.text);
  await demo.getByRole("button", { name: "Classificar" }).click();
  await demo.getByRole("heading", { name: "Resultados da classificação" }).waitFor();
}

async function captureScreenshots(browser) {
  const desktop = await openPage(browser, { width: 1280, height: 800 }, 2);
  await waitForApi(desktop);
  await desktop.evaluate(() => window.scrollTo(0, 0));
  await desktop.screenshot({ path: join(OUT_DIR, "home-desktop.png") });
  await classifyAtTop(desktop);
  await desktop.screenshot({ path: join(OUT_DIR, "home-result-desktop.png") });
  await classifyInDemo(desktop);
  await desktop.locator("#demonstracao").screenshot({ path: join(OUT_DIR, "demo-desktop.png") });
  await desktop.context().close();

  const mobile = await openPage(browser, { width: 390, height: 844 }, 3, true);
  await waitForApi(mobile);
  await mobile.evaluate(() => window.scrollTo(0, 0));
  await mobile.screenshot({ path: join(OUT_DIR, "home-mobile.png") });
  await classifyAtTop(mobile);
  await quick(mobile).evaluate((node) => node.scrollIntoView({ block: "start" }));
  await mobile.screenshot({ path: join(OUT_DIR, "result-mobile.png") });
  await mobile.context().close();
}

// Frames for the GIF: the first screen, typing in "Experimente agora", the answer.
async function captureFrames(browser) {
  await rm(FRAMES_DIR, { recursive: true, force: true });
  await mkdir(FRAMES_DIR, { recursive: true });
  const page = await openPage(browser, { width: 1200, height: 750 }, 1);
  await waitForApi(page);

  const frames = [];
  const shot = async (durationMs) => {
    const file = `frame-${String(frames.length).padStart(3, "0")}.png`;
    await page.screenshot({ path: join(FRAMES_DIR, file) });
    frames.push({ file, durationMs });
  };

  await page.evaluate(() => window.scrollTo(0, 0));
  await shot(1800);

  const field = quick(page).getByLabel("Descrição do produto");
  await field.click();
  for (let index = 1; index <= args.text.length; index += 2) {
    await field.fill(args.text.slice(0, index));
    await shot(90);
  }
  await field.fill(args.text);
  await shot(600);

  await quick(page).getByRole("button", { name: "Classificar" }).click();
  await quick(page).locator("[data-slot=card]").waitFor();
  await page.evaluate(() => window.scrollTo(0, 0));
  await shot(4500);

  await page.context().close();
  await writeFile(join(FRAMES_DIR, "frames.json"), JSON.stringify(frames, null, 2));
  return frames.length;
}

await mkdir(OUT_DIR, { recursive: true });
const browser = await chromium.launch({ executablePath: findBrowser() });
try {
  await captureScreenshots(browser);
  const frames = await captureFrames(browser);
  console.log(`Screenshots and ${frames} GIF frames saved in ${OUT_DIR}`);
} finally {
  await browser.close();
}
