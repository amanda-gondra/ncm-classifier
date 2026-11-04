// One card per description: the ranked NCM positions with their calibrated confidence,
// plus the flags the API returns (manual review, rule 31.05).
import { CircleCheck, Scale, TriangleAlert } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { PredictionResponse, PredictionResult } from "@/lib/api/client";
import { formatPercent } from "@/lib/format";

type Props = {
  descriptions: string[];
  response: PredictionResponse;
};

export function PredictionResults({ descriptions, response }: Props) {
  return (
    <section aria-labelledby="results-title" className="flex flex-col gap-4">
      <h2 id="results-title" className="font-heading text-lg font-semibold">
        Resultados
      </h2>
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

function ResultCard({ description, result }: { description: string; result: PredictionResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="break-words">{description}</CardTitle>
        <div className="flex flex-wrap gap-2">
          {result.requires_manual_review ? (
            <Badge variant="destructive">
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
            <Badge variant="outline">Regra 31.05 aplicada</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ol className="flex flex-col gap-3">
          {result.predictions.map((suggestion) => (
            <li key={suggestion.rank} className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              <span className="row-span-2 text-sm text-muted-foreground tabular-nums">
                {suggestion.rank}º
              </span>
              <div>
                <span className="font-mono font-semibold">{suggestion.formatted}</span>{" "}
                <span className="text-muted-foreground">{suggestion.official_description}</span>
              </div>
              <div className="flex items-center gap-3">
                <Progress
                  value={Math.round(suggestion.confidence * 100)}
                  aria-label={`Confiança da sugestão ${suggestion.rank}`}
                  className="flex-1"
                />
                <span className="w-14 text-right text-xs tabular-nums">
                  {formatPercent(suggestion.confidence)}
                </span>
              </div>
            </li>
          ))}
        </ol>
        {result.rule_3105_applied && result.applied_rule && (
          <p className="mt-3 text-xs text-muted-foreground">{result.applied_rule}</p>
        )}
      </CardContent>
    </Card>
  );
}
