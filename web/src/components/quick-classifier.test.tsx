import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QuickClassifier } from "@/components/quick-classifier";
import type { ApiStatus } from "@/hooks/use-api-status";
import { predict } from "@/lib/api/client";
import { EXAMPLES } from "@/lib/config";
import { predictionResponse } from "@/test/fixtures";

const status = vi.hoisted(() => ({ current: "ready" as ApiStatus, retry: vi.fn() }));

vi.mock("@/components/api-status-provider", () => ({
  useSharedApiStatus: () => ({ status: status.current, retry: status.retry }),
}));

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  predict: vi.fn(),
}));

const predictMock = vi.mocked(predict);

describe("QuickClassifier", () => {
  beforeEach(() => {
    status.current = "ready";
    predictMock.mockReset();
    predictMock.mockResolvedValue({ ...predictionResponse, results: [predictionResponse.results[0]] });
  });

  it("starts empty, then shows the three suggestions of the typed description", async () => {
    const user = userEvent.setup();
    render(<QuickClassifier />);

    expect(screen.getByText("Digite uma descrição e veja as 3 sugestões de NCM.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Descrição do produto"), "Adubo NPK 1 kg");
    await user.click(screen.getByRole("button", { name: "Classificar" }));

    expect(predictMock).toHaveBeenCalledWith(["Adubo NPK 1 kg"]);
    expect(await screen.findByText("Adubo NPK 1 kg")).toBeInTheDocument();
    expect(screen.getByText("Mais provável")).toBeInTheDocument();
    expect(screen.queryByText("Digite uma descrição e veja as 3 sugestões de NCM.")).not.toBeInTheDocument();
  });

  it("classifies an example in one click", async () => {
    const user = userEvent.setup();
    render(<QuickClassifier />);

    await user.click(screen.getByRole("button", { name: EXAMPLES[0] }));

    expect(predictMock).toHaveBeenCalledWith([EXAMPLES[0]]);
    expect(screen.getByLabelText("Descrição do produto")).toHaveValue(EXAMPLES[0]);
  });

  it("does not send an empty description", async () => {
    const user = userEvent.setup();
    render(<QuickClassifier />);

    await user.click(screen.getByRole("button", { name: "Classificar" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Digite a descrição de um produto.");
    expect(predictMock).not.toHaveBeenCalled();
  });

  it("says the server is waking up and waits before classifying", () => {
    status.current = "waking";
    render(<QuickClassifier />);

    expect(screen.getByText(/Acordando o servidor gratuito/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Classificar" })).toBeDisabled();
  });
});
