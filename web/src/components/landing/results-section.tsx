// The published results in one short table, plus one line on the model comparison.
// Everything else (intervals, test_v2, calibration) is in the demonstration's details block.
import { ArrowRight, CircleCheck, Gauge, Info, ListChecks, Scale, Target } from "lucide-react";

import { SectionHeading } from "@/components/landing/section-heading";
import { LINKS } from "@/lib/config";
import { formatDecimal, formatPercent } from "@/lib/format";
import { MODEL_COMPARISON, PUBLISHED_TEST } from "@/lib/project-facts";

const COMPARISON_URL = `${LINKS.github}/blob/main/docs/experiments/model_comparison.md`;

const speedup = Math.round(
  MODEL_COMPARISON.medianLatencyMs.bertimbau / MODEL_COMPARISON.medianLatencyMs.baseline,
);

const ROWS = [
  { icon: Target, metric: "Acerto top-1", value: formatPercent(PUBLISHED_TEST.top1), note: "A 1ª sugestão é a posição correta" },
  { icon: ListChecks, metric: "Acerto top-3", value: formatPercent(PUBLISHED_TEST.top3), note: "A posição correta está entre as 3" },
  { icon: Scale, metric: "F1 macro", value: formatDecimal(PUBLISHED_TEST.macroF1, 3), note: "Equilíbrio entre todas as posições" },
  { icon: Gauge, metric: "Erro de calibração", value: formatDecimal(PUBLISHED_TEST.ece, 3), note: "Quanto menor, mais a confiança reflete o acerto" },
  { icon: CircleCheck, metric: "Acerto sem revisão", value: formatPercent(PUBLISHED_TEST.acceptedTop1), note: "Nos casos que não pediram revisão manual" },
];

export function ResultsSection() {
  return (
    <section id="resultados" aria-labelledby="results-section-title" className="bg-muted/60">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-8 px-4 py-16">
        <SectionHeading
          titleId="results-section-title"
          eyebrow="Resultados"
          title="Resultados da avaliação"
          centered
        >
          <p>Medidos em descrições reais que o modelo nunca viu.</p>
        </SectionHeading>

        <div className="w-full overflow-hidden rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/70 text-left text-muted-foreground">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">Métrica</th>
                <th scope="col" className="px-4 py-3 text-right font-medium sm:text-left">Resultado</th>
                <th scope="col" className="hidden px-4 py-3 font-medium sm:table-cell">O que significa</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(({ icon: Icon, metric, value, note }) => (
                <tr key={metric} className="border-t">
                  <th scope="row" className="px-4 py-3 text-left font-medium">
                    <span className="flex items-center gap-2.5">
                      <Icon aria-hidden className="size-5 shrink-0 text-primary" />
                      {metric}
                    </span>
                  </th>
                  <td className="px-4 py-3 text-right text-base font-semibold tabular-nums sm:text-left">{value}</td>
                  <td className="hidden px-4 py-3 text-muted-foreground sm:table-cell">{note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="flex max-w-2xl items-start gap-2 text-center text-sm text-muted-foreground sm:items-center">
          <Info aria-hidden className="mt-0.5 size-4 shrink-0 text-primary sm:mt-0" />
          Teste congelado {PUBLISHED_TEST.name}, com {PUBLISHED_TEST.rows} descrições reais. O
          segundo teste e os intervalos de confiança estão nos detalhes da demonstração.
        </p>

        <a
          href={COMPARISON_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="group flex w-full items-center justify-between gap-4 rounded-xl border bg-card p-4 text-sm transition-colors hover:border-primary/40"
        >
          <span>
            <span className="font-semibold">O BERTimbau também foi testado e empatou.</span>{" "}
            <span className="text-muted-foreground">
              O modelo mais simples, cerca de {speedup} vezes mais rápido, foi para produção.
            </span>
          </span>
          <span className="flex shrink-0 items-center gap-1 font-medium text-primary">
            Ver comparação
            <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-0.5" />
            <span className="sr-only">(abre em nova aba)</span>
          </span>
        </a>
      </div>
    </section>
  );
}
