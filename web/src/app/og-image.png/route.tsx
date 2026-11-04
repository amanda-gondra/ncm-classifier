// Share image shown when the link is posted on LinkedIn and other networks, generated at
// build time as /og-image.png from the same verified facts and recorded API answer as the
// page. layout.tsx points the Open Graph and Twitter tags to it.
import { ImageResponse } from "next/og";

import { BRAND, SHARE_IMAGE, SproutGlyph } from "@/lib/brand";
import { formatPercent } from "@/lib/format";
import { POSITIONS_IN_SCOPE, PUBLISHED_TEST } from "@/lib/project-facts";
import { SAMPLE_DESCRIPTION, SAMPLE_RESULT } from "@/lib/sample-prediction";
import { shareFonts } from "@/lib/share-fonts";

export const dynamic = "force-static";

const { green: GREEN, deep: DEEP, pale: PALE } = BRAND;

const STATS = [
  { value: formatPercent(PUBLISHED_TEST.top1), label: "acerto na 1ª sugestão" },
  { value: formatPercent(PUBLISHED_TEST.top3), label: "certa entre as 3" },
  { value: String(POSITIONS_IN_SCOPE), label: "posições NCM do agro" },
];

export async function GET() {
  return new ImageResponse(
    (
      <div style={{ display: "flex", width: "100%", height: "100%", background: DEEP, color: "white", fontFamily: "Geist" }}>
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: 640, padding: 64 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ width: 56, height: 56, borderRadius: 14, background: GREEN, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <SproutGlyph size={34} color="white" />
              </div>
              <div style={{ fontSize: 34, fontWeight: 700 }}>NCM Classifier</div>
            </div>
            <div style={{ fontSize: 46, fontWeight: 700, lineHeight: 1.15 }}>
              Classificação NCM de produtos agropecuários com inteligência artificial
            </div>
          </div>
          <div style={{ display: "flex", gap: 36 }}>
            {STATS.map((stat) => (
              <div key={stat.label} style={{ display: "flex", flexDirection: "column", borderLeft: `4px solid ${PALE}`, paddingLeft: 14 }}>
                <div style={{ fontSize: 40, fontWeight: 700 }}>{stat.value}</div>
                <div style={{ fontSize: 20, color: "rgba(255,255,255,0.75)" }}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flex: 1, alignItems: "center", padding: "0 56px 0 0" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14, width: "100%", background: "white", color: DEEP, borderRadius: 24, padding: 28 }}>
            <div style={{ display: "flex", fontSize: 20, color: "#55665c" }}>Descrição do produto</div>
            <div style={{ display: "flex", fontSize: 26, fontWeight: 600, padding: "12px 16px", borderRadius: 12, background: "#f4f7f4" }}>
              {SAMPLE_DESCRIPTION}
            </div>
            {SAMPLE_RESULT.predictions.map((suggestion) => {
              const top = suggestion.rank === 1;
              return (
                <div
                  key={suggestion.rank}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    padding: "12px 16px",
                    borderRadius: 12,
                    border: `2px solid ${top ? GREEN : "#e2e8e3"}`,
                    background: top ? PALE : "white",
                  }}
                >
                  <div style={{ width: 34, height: 34, borderRadius: 17, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, fontWeight: 700, background: top ? GREEN : "#e9eeea", color: top ? "white" : "#55665c" }}>
                    {suggestion.rank}
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 700, fontFamily: "Geist Mono" }}>{suggestion.formatted}</div>
                  <div style={{ marginLeft: "auto", fontSize: 24, fontWeight: 600 }}>{formatPercent(suggestion.confidence)}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    ),
    { width: SHARE_IMAGE.width, height: SHARE_IMAGE.height, fonts: await shareFonts },
  );
}
