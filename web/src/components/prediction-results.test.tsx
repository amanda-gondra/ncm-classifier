import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PredictionResults } from "@/components/prediction-results";
import { DISCLAIMER, predictionResponse } from "@/test/fixtures";

describe("PredictionResults", () => {
  it("renders one card per description with its ranked positions", () => {
    render(
      <PredictionResults
        descriptions={["Adubo NPK 1 kg", "Arame farpado"]}
        response={predictionResponse}
      />,
    );

    const first = screen.getByText("Adubo NPK 1 kg").closest("[data-slot=card]") as HTMLElement;
    const second = screen.getByText("Arame farpado").closest("[data-slot=card]") as HTMLElement;

    expect(within(first).getByText("31.05")).toBeInTheDocument();
    expect(within(first).getByText("31.02")).toBeInTheDocument();
    expect(within(first).getByText("90,0%")).toBeInTheDocument();
    expect(within(second).getByText("73.13")).toBeInTheDocument();
    expect(within(second).getByText("50,0%")).toBeInTheDocument();
    expect(within(first).getAllByRole("progressbar")).toHaveLength(2);
  });

  it("shows the review and rule 31.05 flags returned by the API", () => {
    render(
      <PredictionResults
        descriptions={["Adubo NPK 1 kg", "Arame farpado"]}
        response={predictionResponse}
      />,
    );

    expect(screen.getByText("Regra 31.05 aplicada")).toBeInTheDocument();
    expect(screen.getByText("Regra de teste da posição 31.05.")).toBeInTheDocument();
    expect(screen.getByText("Revisão manual recomendada")).toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument();
    expect(screen.getByText("req-123")).toBeInTheDocument();
  });
});
