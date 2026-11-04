import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ModelInfo } from "@/components/model-info";
import type { ModelInfo as ModelInfoData } from "@/lib/api/client";

// Shape of GET /v1/model; the numbers are test values, not the published metrics.
const interval = (value: number, low: number, high: number) => ({ value, low, high });

const model: ModelInfoData = {
  name: "ncm-classifier",
  version: "v0.1.0",
  repo_id: "AmandaGondra/ncm-classifier",
  revision: "v0.1.0",
  architecture: "test_architecture",
  scope: {
    level: "position",
    ncm_table: "Tabela de teste",
    legal_act: "Ato de teste",
    positions: [
      { ncm: "3102", formatted: "31.02", official_description: "Descrição de teste A." },
      { ncm: "7313", formatted: "73.13", official_description: "Descrição de teste B." },
    ],
  },
  metrics: [
    {
      test_set: "test_v1",
      rows: 100,
      top1: interval(0.9, 0.85, 0.95),
      top3: interval(0.99, 0.97, 1),
      macro_f1: interval(0.88, 0.8, 0.93),
      ece: 0.0753,
      review_rate: interval(0.1, 0.05, 0.15),
      accepted_top1: null,
    },
  ],
  calibration: {
    method: "temperature scaling",
    temperature: 0.4012,
    review_threshold: 0.65,
    review_target_accuracy: 0.95,
    fitted_on: "out-of-fold",
  },
  rule_3105: { id: "rule", description: "Regra de teste.", limit_kg: 10, target: "3105" },
  release: {
    version: "v0.1.0",
    date: "2026-11-03",
    code_commit: "a03a54f1d0973966b0babc8fb846e681197b07e2",
    github: "https://github.com/amanda-gondra/ncm-classifier",
  },
  disclaimer: "Aviso de teste.",
};

describe("ModelInfo", () => {
  it("shows the metrics with their intervals in Brazilian format", () => {
    render(<ModelInfo model={model} error={null} />);

    expect(screen.getByText("Sugere 2 posições NCM de 4 dígitos", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("90,0%")).toBeInTheDocument();
    expect(screen.getByText("85,0% a 95,0%")).toBeInTheDocument();
    expect(screen.getByText("0,075")).toBeInTheDocument();
    expect(screen.getByText("temperature scaling, T = 0,40")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "a03a54f" })).toHaveAttribute(
      "href",
      "https://github.com/amanda-gondra/ncm-classifier/commit/a03a54f1d0973966b0babc8fb846e681197b07e2",
    );
  });

  it("explains when the model data could not be loaded", () => {
    render(<ModelInfo model={null} error="Não foi possível carregar os dados do modelo." />);

    expect(screen.getByText("Não foi possível carregar os dados do modelo.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Código no GitHub/ })).toBeInTheDocument();
  });
});
