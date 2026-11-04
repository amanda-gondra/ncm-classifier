// Favicon, generated at build time as /icon.png: the sprout of the header on the brand
// green. A route named with the extension keeps the .png in the static export, so GitHub
// Pages serves it as image/png.
import { ImageResponse } from "next/og";

import { BRAND, SproutGlyph } from "@/lib/brand";

export const dynamic = "force-static";

export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "100%",
          height: "100%",
          borderRadius: 14,
          background: BRAND.green,
        }}
      >
        <SproutGlyph size={40} color="white" />
      </div>
    ),
    { width: 64, height: 64 },
  );
}
