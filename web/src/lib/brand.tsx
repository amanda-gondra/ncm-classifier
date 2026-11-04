// Brand values for the generated images (favicon and share image), which cannot read the
// CSS variables of the page. Hex equivalents of --primary, --brand-deep and --secondary.
export const BRAND = {
  green: "#1f6b3a",
  deep: "#173b26",
  pale: "#eaf5ec",
} as const;

// Share image served at /og-image.png (1200x630, the size LinkedIn and others expect).
export const SHARE_IMAGE = {
  path: "og-image.png",
  width: 1200,
  height: 630,
  alt: "NCM Classifier: sugere a posição NCM de produtos agropecuários a partir da descrição, com inteligência artificial",
} as const;

// Sprout icon from lucide (ISC license), the same one shown in the page header.
export function SproutGlyph({ size, color }: { size: number; color: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 9.536V7a4 4 0 0 1 4-4h1.5a.5.5 0 0 1 .5.5V5a4 4 0 0 1-4 4 4 4 0 0 0-4 4c0 2 1 3 1 5a5 5 0 0 1-1 3" />
      <path d="M4 9a5 5 0 0 1 8 4 5 5 0 0 1-8-4" />
      <path d="M5 21h14" />
    </svg>
  );
}
