import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PredictionResults } from "@/components/prediction-results";
import { DISCLAIMER, predictionResponse } from "@/test/fixtures";

function renderResults() {
  render(
    <PredictionResults descriptions={["Adubo NPK 1 kg", "Arame farpado"]} response={predictionResponse} />,
  );
  const card = (title: string) =>
    within(screen.getByText(title).closest("[data-slot=card]") as HTMLElement);
  return { first: card("Adubo NPK 1 kg"), second: card("Arame farpado") };
}

describe("PredictionResults", () => {
  it("renders one card per description with its ranked positions", () => {
    const { first, second } = renderResults();

    // The rank is read out by screen readers right before the code: "1ª sugestão: 31.05".
    const code = (scope: typeof first, rank: number) =>
      scope.getByText(`${rank}ª sugestão:`, { exact: false }).parentElement;

    expect(code(first, 1)).toHaveTextContent("1ª sugestão: 31.05");
    expect(code(first, 2)).toHaveTextContent("2ª sugestão: 31.02");
    expect(first.getByText("90,0%")).toBeInTheDocument();
    expect(first.getAllByRole("progressbar")).toHaveLength(2);
    expect(code(second, 1)).toHaveTextContent("1ª sugestão: 73.13");
    expect(second.getByText("50,0%")).toBeInTheDocument();
  });

  it("highlights only the first suggestion", () => {
    const { first, second } = renderResults();

    expect(first.getAllByText("Mais provável")).toHaveLength(1);
    expect(second.getAllByText("Mais provável")).toHaveLength(1);
  });

  it("shows the review and rule 31.05 flags returned by the API", () => {
    const { first, second } = renderResults();

    expect(first.getByText("Regra 31.05 aplicada")).toBeInTheDocument();
    expect(first.getByText("Confiança acima do limiar de revisão")).toBeInTheDocument();
    expect(second.getByText("Revisão manual recomendada")).toBeInTheDocument();
    expect(second.queryByText("Regra 31.05 aplicada")).not.toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument();
    expect(screen.getByText("req-123")).toBeInTheDocument();
  });
});
