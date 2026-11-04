// Checks the form input against the API limits before sending it, so the person gets
// immediate feedback. The API validates every request again; this is a convenience.
import { MAX_BATCH_SIZE, MAX_TEXT_LENGTH } from "@/lib/config";
import { splitLines } from "@/lib/format";

export type InputMode = "single" | "batch";

export type ValidationResult =
  | { ok: true; descriptions: string[] }
  | { ok: false; message: string };

// Counts Unicode code points, as Python's len() does on the API side.
export function textLength(text: string): number {
  return [...text].length;
}

export function validateDescriptions(mode: InputMode, text: string): ValidationResult {
  const descriptions = mode === "single" ? [text.trim()].filter(Boolean) : splitLines(text);

  if (descriptions.length === 0) {
    return {
      ok: false,
      message:
        mode === "single"
          ? "Digite a descrição de um produto."
          : "Digite ao menos uma descrição, uma por linha.",
    };
  }
  if (descriptions.length > MAX_BATCH_SIZE) {
    return {
      ok: false,
      message: `Envie no máximo ${MAX_BATCH_SIZE} descrições por vez (há ${descriptions.length}).`,
    };
  }
  const tooLong = descriptions.findIndex((item) => textLength(item) > MAX_TEXT_LENGTH);
  if (tooLong !== -1) {
    return {
      ok: false,
      message:
        mode === "single"
          ? `A descrição passa de ${MAX_TEXT_LENGTH} caracteres.`
          : `A descrição nº ${tooLong + 1} passa de ${MAX_TEXT_LENGTH} caracteres.`,
    };
  }
  return { ok: true, descriptions };
}
