"use client";

// Sends descriptions to the API and keeps the last answer, the error and the loading state.
// Shared by the classifier at the top of the page and the full demonstration.
import { useCallback, useState } from "react";

import { useSharedApiStatus } from "@/components/api-status-provider";
import { ApiError, predict, type PredictionResponse } from "@/lib/api/client";

export type Submission = { descriptions: string[]; response: PredictionResponse };

function toApiError(error: unknown): ApiError {
  return error instanceof ApiError
    ? error
    : new ApiError("Ocorreu um erro inesperado.", null, "unexpected_error");
}

export function usePrediction() {
  const { retry } = useSharedApiStatus();
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  const submit = useCallback(
    async (descriptions: string[]) => {
      setPending(true);
      setError(null);
      try {
        const response = await predict(descriptions);
        setSubmission({ descriptions, response });
      } catch (caught) {
        const apiError = toApiError(caught);
        setError(apiError);
        // The server may have gone back to sleep: show the waking state again.
        if (apiError.isTemporary) retry();
      } finally {
        setPending(false);
      }
    },
    [retry],
  );

  return { submission, error, pending, submit };
}
