// One card per description: the ranked NCM positions with their calibrated confidence,
// plus the flags the API returns (manual review, rule 31.05). The first suggestion is
// highlighted; the other two stay fully visible for comparison.
import { CircleCheck, Scale, TriangleAlert } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { PredictionResponse, PredictionResult, Suggestion } from "@/lib/api/client";
import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

type Props = {
  descriptions: string[];
  response: PredictionResponse;
};

export function PredictionResults({ descriptions, response }: Props) {
  return (
    <section aria-labelledby="results-title" className="flex flex-col gap-4">
      <h3 id="results-title" className="font-heading text-lg font-semibold">
        Resultados da classificação
      </h3>
      <ol className="flex flex-col gap-4">
        {response.results.map((result) => (
          <li key={result.index}>
            <ResultCard description={descriptions[result.index] ?? ""} result={result} />
          </li>
        ))}
      </ol>
      <Alert>
        <Scale aria-hidden />
        <AlertDescription>{response.disclaimer}</AlertDescription>
      </Alert>
      <p className="text-xs text-muted-foreground">
        Modelo {response.model_version} · requisição <code>{response.request_id}</code>
      </p>
    </section>
  );
}

type ResultCardProps = {
  description: string;
  result: PredictionResult;
  // Shortens the official descriptions to two lines (the full text stays in the title).
  compact?: boolean;
};

export function ResultCard({ description, result, compact = false }: ResultCardProps) {
  return (
    <Card>
      <CardHeader className="gap-2">
        <CardTitle className="break-words">{description}</CardTitle>
        <ResultFlags result={result} />
      </CardHeader>
      <CardContent>
        <ol className="flex flex-col gap-2">
          {result.predictions.map((suggestion) => (
            <SuggestionRow key={suggestion.rank} suggestion={suggestion} compact={compact} />
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

function ResultFlags({ result }: { result: PredictionResult }) {
  return (
    <div className="flex flex-wrap gap-2">
      {result.requires_manual_review ? (
        <Badge className="bg-warning text-warning-foreground">
          <TriangleAlert data-icon="inline-start" aria-hidden />
          Revisão manual recomendada
        </Badge>
      ) : (
        <Badge variant="secondary">
          <CircleCheck data-icon="inline-start" aria-hidden />
          Confiança acima do limiar de revisão
        </Badge>
      )}
      {result.rule_3105_applied && (
        <Badge variant="outline" title="Adubo do Capítulo 31 em embalagem de até 10 kg">
          Regra 31.05 aplicada
        </Badge>
      )}
    </div>
  );
}

function SuggestionRow({ suggestion, compact }: { suggestion: Suggestion; compact: boolean }) {
  const isTop = suggestion.rank === 1;
  return (
    <li
      className={cn(
        "grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 rounded-lg border p-3",
        isTop ? "border-primary/40 bg-secondary/60" : "border-border",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "flex size-7 items-center justify-center rounded-full text-sm font-semibold tabular-nums",
          isTop ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
        )}
      >
        {suggestion.rank}
      </span>
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="font-mono text-base font-semibold">
            <span className="sr-only">{suggestion.rank}ª sugestão: </span>
            {suggestion.formatted}
          </span>
          {isTop && <Badge>Mais provável</Badge>}
        </div>
        <p
          className={cn("text-sm text-muted-foreground", compact && "line-clamp-2")}
          title={compact ? suggestion.official_description : undefined}
        >
          {suggestion.official_description}
        </p>
      </div>
      <div className="col-start-2 flex items-center gap-3">
        <Progress
          value={Math.round(suggestion.confidence * 100)}
          aria-label={`Confiança da sugestão ${suggestion.rank}`}
          className={cn(
            "flex-1",
            !isTop && "[&_[data-slot=progress-indicator]]:bg-muted-foreground/50",
          )}
        />
        <span className="w-14 text-right text-sm font-medium tabular-nums">
          {formatPercent(suggestion.confidence)}
        </span>
      </div>
    </li>
  );
}
