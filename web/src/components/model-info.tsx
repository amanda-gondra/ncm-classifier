// What the model is and how well it did on the frozen test sets, exactly as the API
// reports it (/v1/model). Intervals are 95% bootstrap confidence intervals.
import { ExternalLink } from "lucide-react";
import type { ReactNode } from "react";

import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import type { ModelInfo as ModelInfoData, TestMetrics } from "@/lib/api/client";
import { LINKS } from "@/lib/config";
import { formatDecimal, formatPercent, formatRange } from "@/lib/format";

type Props = {
  model: ModelInfoData | null;
  error: string | null;
};

type Interval = TestMetrics["top1"];

// Point value on top, its 95% interval below in smaller text.
function IntervalCell({ interval }: { interval: Interval | null }) {
  if (!interval) return <>—</>;
  return (
    <>
      <span className="font-medium">{formatPercent(interval.value)}</span>
      <span className="block text-xs text-muted-foreground">{formatRange(interval)}</span>
    </>
  );
}

const METRIC_ROWS: { label: string; render: (metrics: TestMetrics) => ReactNode }[] = [
  { label: "Acerto top-1", render: (m) => <IntervalCell interval={m.top1} /> },
  { label: "Acerto top-3", render: (m) => <IntervalCell interval={m.top3} /> },
  { label: "F1 macro", render: (m) => <IntervalCell interval={m.macro_f1} /> },
  { label: "Enviados à revisão", render: (m) => <IntervalCell interval={m.review_rate} /> },
  {
    label: "Acerto top-1 sem revisão",
    render: (m) => <IntervalCell interval={m.accepted_top1} />,
  },
  { label: "ECE (erro de calibração)", render: (m) => formatDecimal(m.ece, 3) },
];

const EXTERNAL_LINKS = [
  { href: LINKS.github, label: "Código no GitHub" },
  { href: LINKS.model, label: "Modelo no Hugging Face" },
  { href: LINKS.dataset, label: "Dataset no Hugging Face" },
  { href: LINKS.apiDocs, label: "Documentação da API" },
];

export function ModelInfo({ model, error }: Props) {
  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted-foreground">
        {model
          ? `${model.name} ${model.version} · ${model.architecture} · dados lidos da API (GET /v1/model)`
          : "Dados publicados pela API."}
      </p>
      {model ? <ModelDetails model={model} /> : <ModelPlaceholder error={error} />}
      <Separator />
      <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          {EXTERNAL_LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 underline underline-offset-3 hover:text-foreground"
              >
                {link.label}
                <ExternalLink aria-hidden className="size-3.5" />
                <span className="sr-only">(abre em nova aba)</span>
              </a>
            </li>
          ))}
      </ul>
    </div>
  );
}

function ModelPlaceholder({ error }: { error: string | null }) {
  if (error) return <p className="text-sm text-muted-foreground">{error}</p>;
  return (
    <div className="flex flex-col gap-2" aria-hidden>
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

function ModelDetails({ model }: { model: ModelInfoData }) {
  const { scope, calibration, rule_3105: rule, release } = model;
  return (
    <>
      <p className="text-sm">
        Sugere {scope.positions.length} posições NCM de 4 dígitos ({scope.ncm_table},{" "}
        {scope.legal_act}).
      </p>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {model.metrics.map((metrics) => (
        <div key={metrics.test_set} className="min-w-0 overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="mb-1 text-left text-xs text-muted-foreground">
              Teste congelado <code>{metrics.test_set}</code> · {metrics.rows} linhas · IC 95%
            </caption>
            <tbody>
              {METRIC_ROWS.map((row) => (
                <tr key={row.label} className="border-b last:border-0">
                  <th scope="row" className="py-1 pr-3 text-left font-normal text-muted-foreground">
                    {row.label}
                  </th>
                  <td className="py-1 text-right tabular-nums">{row.render(metrics)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <dl className="grid min-w-0 grid-cols-[auto_1fr] content-start gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Calibração</dt>
        <dd>
          {calibration.method}, T = {formatDecimal(calibration.temperature, 2)}
        </dd>
        <dt className="text-muted-foreground">Revisão</dt>
        <dd>
          confiança abaixo de {formatPercent(calibration.review_threshold)} (meta de{" "}
          {formatPercent(calibration.review_target_accuracy)} de acerto)
        </dd>
        <dt className="text-muted-foreground">Regra 31.05</dt>
        <dd>{rule.description}</dd>
        <dt className="text-muted-foreground">Versão</dt>
        <dd>
          {release.version} de {release.date} ·{" "}
          <a
            href={`${release.github}/commit/${release.code_commit}`}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono underline underline-offset-3"
          >
            {release.code_commit.slice(0, 7)}
          </a>
        </dd>
      </dl>

      <details className="min-w-0 text-sm">
        <summary className="cursor-pointer font-medium">Posições cobertas</summary>
        <ul className="mt-2 flex max-h-64 flex-col gap-1 overflow-y-auto">
          {scope.positions.map((position) => (
            <li key={position.ncm}>
              <span className="font-mono">{position.formatted}</span>{" "}
              <span className="text-muted-foreground">{position.official_description}</span>
            </li>
          ))}
        </ul>
      </details>
      </div>
    </>
  );
}
