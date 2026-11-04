"use client";

// The interactive part of the page: API status, the form, the results and the model panel.
// The page itself is static HTML; everything here runs in the browser and calls the API.
import { useEffect, useState } from "react";

import { ModelInfo } from "@/components/model-info";
import { PredictionForm } from "@/components/prediction-form";
import { PredictionResults } from "@/components/prediction-results";
import { StatusBanner } from "@/components/status-banner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useApiStatus } from "@/hooks/use-api-status";
import {
  ApiError,
  getModelInfo,
  predict,
  type ModelInfo as ModelInfoData,
  type PredictionResponse,
} from "@/lib/api/client";

type Submission = { descriptions: string[]; response: PredictionResponse };

function toApiError(error: unknown): ApiError {
  return error instanceof ApiError
    ? error
    : new ApiError("Ocorreu um erro inesperado.", null, "unexpected_error");
}

export function ClassifierApp() {
  const { status, retry } = useApiStatus();
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);
  const [model, setModel] = useState<ModelInfoData | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "ready" || model) return;
    const controller = new AbortController();
    getModelInfo(controller.signal)
      .then((info) => {
        setModel(info);
        setModelError(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setModelError("Não foi possível carregar os dados do modelo.");
        }
      });
    return () => controller.abort();
  }, [status, model]);

  const handleSubmit = async (descriptions: string[]) => {
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
  };

  const announcement = pending
    ? "Classificando…"
    : submission
      ? `${submission.response.results.length} resultado(s) pronto(s).`
      : "";

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="flex min-w-0 flex-col gap-6">
        <StatusBanner status={status} onRetry={retry} />
        <PredictionForm
          onSubmit={(descriptions) => void handleSubmit(descriptions)}
          pending={pending}
          disabled={status !== "ready"}
        />
        {error && <ErrorAlert error={error} />}
        <p className="sr-only" aria-live="polite">
          {announcement}
        </p>
        {submission && (
          <PredictionResults descriptions={submission.descriptions} response={submission.response} />
        )}
      </div>
      <aside className="min-w-0">
        <ModelInfo model={model} error={modelError} />
      </aside>
    </div>
  );
}

function ErrorAlert({ error }: { error: ApiError }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Não foi possível classificar</AlertTitle>
      <AlertDescription>
        <p>
          {error.message}
          {error.retryAfterSeconds !== null &&
            ` Tente de novo em ${error.retryAfterSeconds} segundo(s).`}
        </p>
        {error.requestId && (
          <p className="text-xs">
            Código da requisição: <code>{error.requestId}</code>
          </p>
        )}
      </AlertDescription>
    </Alert>
  );
}
