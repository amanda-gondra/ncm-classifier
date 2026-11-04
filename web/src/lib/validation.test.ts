import { describe, expect, it } from "vitest";

import { MAX_BATCH_SIZE, MAX_TEXT_LENGTH } from "@/lib/config";
import { textLength, validateDescriptions } from "@/lib/validation";

describe("validateDescriptions", () => {
  it("trims a single description", () => {
    expect(validateDescriptions("single", "  Ureia agrícola  ")).toEqual({
      ok: true,
      descriptions: ["Ureia agrícola"],
    });
  });

  it("splits a batch into non-empty lines", () => {
    expect(validateDescriptions("batch", "Ureia\r\n\n  Adubo NPK \n")).toEqual({
      ok: true,
      descriptions: ["Ureia", "Adubo NPK"],
    });
  });

  it.each(["single", "batch"] as const)("rejects empty input in %s mode", (mode) => {
    expect(validateDescriptions(mode, " \n ").ok).toBe(false);
  });

  it("rejects a batch above the API limit", () => {
    const text = Array.from({ length: MAX_BATCH_SIZE + 1 }, (_, i) => `Produto ${i}`).join("\n");
    const result = validateDescriptions("batch", text);
    expect(result).toEqual({ ok: false, message: expect.stringContaining(`${MAX_BATCH_SIZE}`) });
  });

  it("points to the batch line that is too long", () => {
    const result = validateDescriptions("batch", `Ureia\n${"a".repeat(MAX_TEXT_LENGTH + 1)}`);
    expect(result).toEqual({ ok: false, message: expect.stringContaining("nº 2") });
  });

  it("accepts a description exactly at the limit", () => {
    expect(validateDescriptions("single", "a".repeat(MAX_TEXT_LENGTH)).ok).toBe(true);
  });
});

describe("textLength", () => {
  it("counts code points like Python's len()", () => {
    expect(textLength("ação")).toBe(4);
    expect(textLength("🌽")).toBe(1);
  });
});
