// A real answer of the published API, recorded so the top of the page can show a result
// at once, even while the free API instance is asleep. Not edited: values as returned.
//
// Request: POST https://ncm-classifier-api.onrender.com/v1/predictions on 2026-11-04,
// body {"descriptions": [...]} with the examples in EXAMPLES; this is the first result.
import type { PredictionResult } from "@/lib/api/client";

export const SAMPLE_RECORDED_ON = "2026-11-04";
export const SAMPLE_MODEL_VERSION = "v0.1.0";
export const SAMPLE_DESCRIPTION = "Ureia agrícola, pacote 1 kg";

export const SAMPLE_RESULT: PredictionResult = {
  index: 0,
  predictions: [
    {
      rank: 1,
      ncm: "3105",
      level: "position",
      formatted: "31.05",
      official_description:
        "Adubos (fertilizantes) minerais ou químicos, que contenham dois ou três dos seguintes elementos fertilizantes: nitrogênio (azoto), fósforo e potássio; outros adubos (fertilizantes); produtos do presente Capítulo apresentados em tabletes ou formas semelhantes, ou ainda em embalagens de peso bruto não superior a 10 kg.",
      confidence: 0.991143,
    },
    {
      rank: 2,
      ncm: "8716",
      level: "position",
      formatted: "87.16",
      official_description:
        "Reboques e semirreboques, para quaisquer veículos; outros veículos não autopropulsados; suas partes.",
      confidence: 0.003118,
    },
    {
      rank: 3,
      ncm: "8424",
      level: "position",
      formatted: "84.24",
      official_description:
        "Aparelhos mecânicos (mesmo manuais) para projetar, dispersar ou pulverizar líquidos ou pós; extintores, mesmo carregados; pistolas aerográficas e aparelhos semelhantes; máquinas e aparelhos de jato de areia, de jato de vapor e aparelhos de jato semelhantes.",
      confidence: 0.001091,
    },
  ],
  requires_manual_review: false,
  rule_3105_applied: true,
  applied_rule: "ncm-3105-small-package",
};
