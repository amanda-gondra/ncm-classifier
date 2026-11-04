"use client";

// "Experimente agora": the classifier at the top of the page. One description, an example
// in one click, the three suggestions right below. The full form is in the demonstration.
import { LoaderCircle, RotateCw, Sparkles } from "lucide-react";
import { useId, useState, type FormEvent } from "react";

import { useSharedApiStatus } from "@/components/api-status-provider";
import { ErrorAlert } from "@/components/error-alert";
import { BrandMark } from "@/components/landing/brand-mark";
import { ResultCard } from "@/components/prediction-results";
import { Button } from "@/components/ui/button";
import { usePrediction } from "@/hooks/use-prediction";
import { EXAMPLES } from "@/lib/config";
import { validateDescriptions } from "@/lib/validation";

const QUICK_EXAMPLES = EXAMPLES.slice(0, 3);

export function QuickClassifier() {
  const inputId = useId();
  const { status, retry } = useSharedApiStatus();
  const { submission, error, pending, submit } = usePrediction();
  const [text, setText] = useState("");
  const [validation, setValidation] = useState<string | null>(null);
  const ready = status === "ready";

  const classify = (value: string) => {
    const result = validateDescriptions("single", value);
    if (!result.ok) {
      setValidation(result.message);
      return;
    }
    setValidation(null);
    void submit(result.descriptions);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    classify(text);
  };

  const result = submission?.response.results[0];

  return (
    <div
      id="experimente"
      className="flex min-w-0 flex-col gap-5 rounded-2xl border bg-card p-5 shadow-lg shadow-primary/5 sm:p-6"
    >
      <div className="flex items-center gap-3">
        <BrandMark />
        <h2 className="font-heading text-lg font-semibold">Experimente agora</h2>
      </div>

      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-2 sm:flex-row">
        <label htmlFor={inputId} className="sr-only">
          Descrição do produto
        </label>
        <input
          id={inputId}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setValidation(null);
          }}
          placeholder="Ex.: Adubo NPK 20-05-20"
          aria-invalid={validation !== null || undefined}
          className="h-11 min-w-0 flex-1 rounded-lg border border-input bg-background px-3 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive"
        />
        <Button type="submit" size="lg" disabled={!ready || pending} className="h-11 px-5 text-base">
          {pending ? (
            <LoaderCircle data-icon="inline-start" className="animate-spin" aria-hidden />
          ) : (
            <Sparkles data-icon="inline-start" aria-hidden />
          )}
          {pending ? "Classificando…" : "Classificar"}
        </Button>
      </form>

      {validation && (
        <p role="alert" className="-mt-3 text-sm text-destructive">
          {validation}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {QUICK_EXAMPLES.map((example) => (
          <Button
            key={example}
            type="button"
            size="xs"
            variant="outline"
            disabled={!ready || pending}
            onClick={() => {
              setText(example);
              classify(example);
            }}
          >
            {example}
          </Button>
        ))}
      </div>

      <div aria-live="polite" className="flex flex-col gap-3">
        {status === "unavailable" ? (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted px-3 py-2 text-sm">
            <span>A API não respondeu.</span>
            <Button size="sm" variant="outline" onClick={retry}>
              <RotateCw data-icon="inline-start" aria-hidden />
              Tentar de novo
            </Button>
          </div>
        ) : !ready ? (
          <p className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
            <LoaderCircle aria-hidden className="size-4 shrink-0 animate-spin" />
            Acordando o servidor gratuito; pode levar até um minuto.
          </p>
        ) : null}

        {error && <ErrorAlert error={error} />}

        {result && submission ? (
          <ResultCard description={submission.descriptions[0] ?? ""} result={result} compact />
        ) : (
          !error && (
            <div className="flex flex-col items-center gap-3 py-6 text-center text-muted-foreground">
              <span aria-hidden className="flex size-14 items-center justify-center rounded-full bg-secondary text-primary">
                <Sparkles className="size-6" />
              </span>
              <p className="max-w-56 text-sm">Digite uma descrição e veja as 3 sugestões de NCM.</p>
            </div>
          )
        )}
      </div>
    </div>
  );
}
