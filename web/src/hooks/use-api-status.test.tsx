import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useApiStatus } from "@/hooks/use-api-status";
import { getHealth, type HealthResponse } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ getHealth: vi.fn() }));

const healthMock = vi.mocked(getHealth);

const health = (status: HealthResponse["status"]): HealthResponse => ({
  status,
  model: { state: status === "ok" ? "ready" : "loading", version: null },
});

describe("useApiStatus", () => {
  beforeEach(() => {
    healthMock.mockReset();
  });

  it("keeps polling while the server wakes up, until the model is ready", async () => {
    healthMock
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(health("starting"))
      .mockResolvedValue(health("ok"));

    const { result } = renderHook(() => useApiStatus(5, 10_000));

    expect(result.current.status).toBe("checking");
    await waitFor(() => expect(result.current.status).toBe("ready"));
    expect(healthMock).toHaveBeenCalledTimes(3);
  });

  it("gives up after the waiting time and can retry", async () => {
    healthMock.mockRejectedValue(new Error("offline"));

    const { result } = renderHook(() => useApiStatus(5, 0));

    await waitFor(() => expect(result.current.status).toBe("unavailable"));

    healthMock.mockResolvedValue(health("ok"));
    act(() => result.current.retry());

    await waitFor(() => expect(result.current.status).toBe("ready"));
  });

  it("reports a model that failed to load as unavailable", async () => {
    healthMock.mockResolvedValue(health("unavailable"));

    const { result } = renderHook(() => useApiStatus(5, 10_000));

    await waitFor(() => expect(result.current.status).toBe("unavailable"));
    expect(healthMock).toHaveBeenCalledTimes(1);
  });
});
