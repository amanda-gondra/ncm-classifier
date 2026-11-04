import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { SHARE_IMAGE } from "@/lib/brand";
import { SITE_ORIGIN } from "@/lib/config";

// globals.css reads the fonts from --font-sans and --font-geist-mono.
const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const TITLE = "NCM Classifier · Classificação NCM de produtos agropecuários com IA";
const DESCRIPTION =
  "Sugere as 3 posições NCM mais prováveis a partir da descrição comercial de um produto do agro, com confiança calibrada e aviso de revisão manual. Projeto open source.";
// Base path of the published site (/ncm-classifier on GitHub Pages; empty locally).
const BASE_PATH = process.env.PAGES_BASE_PATH ?? "";

// Relative URLs below resolve against metadataBase, which already includes the base path.
const shareImage = {
  url: SHARE_IMAGE.path,
  width: SHARE_IMAGE.width,
  height: SHARE_IMAGE.height,
  alt: SHARE_IMAGE.alt,
  type: "image/png",
};

export const metadata: Metadata = {
  metadataBase: new URL(`${SITE_ORIGIN}${BASE_PATH}/`),
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "./" },
  icons: { icon: { url: `${BASE_PATH}/icon.png`, type: "image/png", sizes: "64x64" } },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    siteName: "NCM Classifier",
    title: TITLE,
    description: DESCRIPTION,
    url: "./",
    images: [shareImage],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: [shareImage],
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
