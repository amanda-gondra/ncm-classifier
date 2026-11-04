import { describe, expect, it, vi } from "vitest";

import { ApiError, getHealth, predict } from "@/lib/api/client";
import { API_URL } from "@/lib/config";
import { jsonResponse, predictionResponse } from "@/test/fixtures";

function stubFetch(implementation: () => Promise<Response>) {
  const fetchMock = vi.fn(implementation);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("predict", () => {
  it("sends one description in the single-item format", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(predictionResponse));

    await expect(predict(["Ureia"])).resolves.toEqual(predictionResponse);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_URL}/v1/predictions`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ description: "Ureia" });
  });

  it("sends several descriptions as a batch", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(predictionResponse));

    await predict(["Ureia", "Arame"]);

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ descriptions: ["Ureia", "Arame"] });
  });

  it("turns the API error body into an ApiError", async () => {
    stubFetch(async () =>
      jsonResponse(
        { error: { code: "rate_limited", message: "Muitas requisições.", request_id: "req-9" } },
        429,
        { "Retry-After": "30" },
      ),
    );

    const error = await predict(["Ureia"]).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 429,
      code: "rate_limited",
      message: "Muitas requisições.",
      requestId: "req-9",
      retryAfterSeconds: 30,
      isTemporary: false,
    });
  });

  it("prefers the first field detail of a validation error", async () => {
    stubFetch(async () =>
      jsonResponse(
        {
          error: {
            code: "validation_error",
            message: "Requisição inválida.",
            details: [{ field: "description", message: "Texto muito longo." }],
          },
        },
        422,
      ),
    );

    await expect(predict(["x"])).rejects.toMatchObject({ message: "Texto muito longo." });
  });

  it("reports a network failure as a temporary error", async () => {
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });

    const error = await predict(["Ureia"]).catch((caught: unknown) => caught);

    expect(error).toMatchObject({ status: null, code: "network_error", isTemporary: true });
  });

  it("lets a cancellation by the caller through", async () => {
    stubFetch(async () => {
      throw new DOMException("Aborted", "AbortError");
    });

    await expect(predict(["Ureia"])).rejects.toMatchObject({ name: "AbortError" });
  });
});

describe("getHealth", () => {
  it("reads the health body of a 503 while the model loads", async () => {
    const body = { status: "starting", model: { state: "loading", version: null } };
    stubFetch(async () => jsonResponse(body, 503));

    await expect(getHealth()).resolves.toEqual(body);
  });
});
