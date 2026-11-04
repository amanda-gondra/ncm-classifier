"use client";

// The full demonstration: the form (one description or a batch), the API state, the
// results and, closed by default, the model details read from /v1/model.
import { BarChart3, ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

import { useSharedApiStatus } from "@/components/api-status-provider";
import { ErrorAlert } from "@/components/error-alert";
import { ModelInfo } from "@/components/model-info";
import { PredictionForm } from "@/components/prediction-form";
import { PredictionResults } from "@/components/prediction-results";
import { StatusPanel } from "@/components/status-panel";
import { usePrediction } from "@/hooks/use-prediction";
import { getModelInfo, type ModelInfo as ModelInfoData } from "@/lib/api/client";

export function ClassifierApp() {
  const { status, retry } = useSharedApiStatus();
  const { submission, error, pending, submit } = usePrediction();
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

  const announcement = pending
    ? "Classificando…"
    : submission
      ? `${submission.response.results.length} resultado(s) pronto(s).`
      : "";

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex min-w-0 flex-col gap-6">
          <div className="rounded-xl border bg-card p-5">
            <PredictionForm
              onSubmit={(descriptions) => void submit(descriptions)}
              pending={pending}
              disabled={status !== "ready"}
            />
          </div>
          {error && <ErrorAlert error={error} />}
          <p className="sr-only" aria-live="polite">
            {announcement}
          </p>
          {submission && (
            <PredictionResults descriptions={submission.descriptions} response={submission.response} />
          )}
        </div>
        <div className="min-w-0">
          <StatusPanel status={status} modelVersion={model?.version ?? null} onRetry={retry} />
        </div>
      </div>

      <details className="group rounded-xl border bg-card">
        <summary className="flex cursor-pointer list-none items-center gap-4 p-5 [&::-webkit-details-marker]:hidden">
          <BarChart3 aria-hidden className="size-6 shrink-0 text-primary" />
          <span className="flex flex-1 flex-col">
            <span className="font-semibold">Detalhes do modelo e métricas</span>
            <span className="text-sm text-muted-foreground">
              Métricas com intervalo de confiança, calibração, regra 31.05 e posições cobertas.
            </span>
          </span>
          <ChevronDown aria-hidden className="size-5 shrink-0 transition-transform group-open:rotate-180" />
        </summary>
        <div className="border-t p-5">
          <ModelInfo model={model} error={modelError} />
        </div>
      </details>
    </div>
  );
}
