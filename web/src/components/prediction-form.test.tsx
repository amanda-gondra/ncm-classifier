import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PredictionForm } from "@/components/prediction-form";
import { EXAMPLES } from "@/lib/config";

function renderForm(props: Partial<Parameters<typeof PredictionForm>[0]> = {}) {
  const onSubmit = vi.fn();
  render(<PredictionForm onSubmit={onSubmit} pending={false} disabled={false} {...props} />);
  return { onSubmit, user: userEvent.setup() };
}

describe("PredictionForm", () => {
  it("submits one trimmed description", async () => {
    const { onSubmit, user } = renderForm();

    await user.type(screen.getByLabelText("Descrição do produto"), "  Ureia agrícola ");
    await user.click(screen.getByRole("button", { name: "Classificar" }));

    expect(onSubmit).toHaveBeenCalledWith(["Ureia agrícola"]);
  });

  it("shows the validation message instead of submitting empty text", async () => {
    const { onSubmit, user } = renderForm();

    await user.click(screen.getByRole("button", { name: "Classificar" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Digite a descrição de um produto.");
    expect(screen.getByLabelText("Descrição do produto")).toHaveAttribute("aria-invalid", "true");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a batch with one description per line", async () => {
    const { onSubmit, user } = renderForm();

    await user.click(screen.getByRole("tab", { name: "Várias descrições" }));
    const field = screen.getByLabelText(/uma por linha/);
    await user.type(field, "Ureia{enter}{enter}Arame farpado");
    await user.click(screen.getByRole("button", { name: "Classificar" }));

    expect(onSubmit).toHaveBeenCalledWith(["Ureia", "Arame farpado"]);
  });

  it("fills the field with a clicked example", async () => {
    const { user } = renderForm();

    await user.click(screen.getByRole("button", { name: EXAMPLES[0] }));

    expect(screen.getByLabelText("Descrição do produto")).toHaveValue(EXAMPLES[0]);
  });

  it("disables submission while the API is not ready", () => {
    renderForm({ disabled: true });

    expect(screen.getByRole("button", { name: "Classificar" })).toBeDisabled();
    expect(screen.getByText("Aguarde a API ficar pronta.")).toBeInTheDocument();
  });
});
