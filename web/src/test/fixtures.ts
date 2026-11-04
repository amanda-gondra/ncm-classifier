// Responses in the exact shape of the API contract, for component and client tests.
// Codes and descriptions come from the model's catalog (positions.json); the
// confidences are made up for the tests and are not model outputs.
import type { PredictionResponse } from "@/lib/api/client";

export const DISCLAIMER = "Texto de aviso de teste.";

export const predictionResponse: PredictionResponse = {
  request_id: "req-123",
  model_version: "v0.1.0",
  disclaimer: DISCLAIMER,
  results: [
    {
      index: 0,
      requires_manual_review: false,
      rule_3105_applied: true,
      applied_rule: "Regra de teste da posição 31.05.",
      predictions: [
        {
          rank: 1,
          ncm: "3105",
          level: "position",
          formatted: "31.05",
          official_description: "Adubos (fertilizantes) minerais ou químicos, que contenham dois ou três dos seguintes elementos fertilizantes: nitrogênio (azoto), fósforo e potássio; outros adubos (fertilizantes); produtos do presente Capítulo apresentados em tabletes ou formas semelhantes, ou ainda em embalagens de peso bruto não superior a 10 kg.",
          confidence: 0.9,
        },
        {
          rank: 2,
          ncm: "3102",
          level: "position",
          formatted: "31.02",
          official_description: "Adubos (fertilizantes) minerais ou químicos, nitrogenados (azotados).",
          confidence: 0.08,
        },
      ],
    },
    {
      index: 1,
      requires_manual_review: true,
      rule_3105_applied: false,
      applied_rule: null,
      predictions: [
        {
          rank: 1,
          ncm: "7313",
          level: "position",
          formatted: "73.13",
          official_description: "Arame farpado, de ferro ou aço; arames ou tiras, retorcidos, mesmo farpados, de ferro ou aço, do tipo utilizado em cercas.",
          confidence: 0.5,
        },
      ],
    },
  ],
};

export function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}
