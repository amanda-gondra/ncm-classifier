"use client";

// One shared view of the API state for the whole page, so the classifier at the top and the
// full demonstration below do not each poll /health on their own.
import { createContext, use, type ReactNode } from "react";

import { useApiStatus, type ApiStatus } from "@/hooks/use-api-status";

type ApiStatusValue = { status: ApiStatus; retry: () => void };

const ApiStatusContext = createContext<ApiStatusValue | null>(null);

export function ApiStatusProvider({ children }: { children: ReactNode }) {
  const value = useApiStatus();
  return <ApiStatusContext value={value}>{children}</ApiStatusContext>;
}

export function useSharedApiStatus(): ApiStatusValue {
  const value = use(ApiStatusContext);
  if (!value) throw new Error("useSharedApiStatus must be used inside ApiStatusProvider");
  return value;
}
