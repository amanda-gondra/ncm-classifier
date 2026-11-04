// What was measured and decided: the published results, the comparison with BERTimbau,
// how the data was built and what the model does not do. Numbers come from project-facts.
import { CheckCircle2, ExternalLink } from "lucide-react";

import { SectionHeading } from "@/components/landing/section-heading";
import { LINKS } from "@/lib/config";
import { formatDecimal, formatPercent } from "@/lib/format";
import {
  MODEL_COMPARISON,
  POSITIONS_IN_SCOPE,
  PUBLISHED_TEST,
  SECOND_TEST,
  TRAINING_ROWS,
  WITHOUT_SYNTHETIC_TOP1,
} from "@/lib/project-facts";

const COMPARISON_URL = `${LINKS.github}/blob/main/docs/experiments/model_comparison.md`;
const LIMITATIONS_URL = `${LINKS.github}#limitações`;

const speedup = Math.round(
  MODEL_COMPARISON.medianLatencyMs.bertimbau / MODEL_COMPARISON.medianLatencyMs.baseline,
);

const MODELS = [
  {
    name: "TF-IDF + regressão logística",
    role: "Em produção",
    top1: MODEL_COMPARISON.top1.baseline,
    latency: MODEL_COMPARISON.medianLatencyMs.baseline,
    disk: MODEL_COMPARISON.diskMb.baseline,
    chosen: true,
  },
  {
    name: "BERTimbau (fine-tuning)",
    role: "Experimento documentado",
    top1: MODEL_COMPARISON.top1.bertimbau,
    latency: MODEL_COMPARISON.medianLatencyMs.bertimbau,
    disk: MODEL_COMPARISON.diskMb.bertimbau,
    chosen: false,
  },
];

const TOTAL_TRAINING = TRAINING_ROWS.official + TRAINING_ROWS.real + TRAINING_ROWS.synthetic;

const DATA_ROWS = [
  { label: "Descrições oficiais da tabela NCM", value: TRAINING_ROWS.official },
  { label: "Descrições reais de anúncios e licitações", value: TRAINING_ROWS.real },
  { label: "Descrições sintéticas, escritas por LLM e marcadas", value: TRAINING_ROWS.synthetic },
];

const LIMITATIONS = [
  "Classifica a posição (4 dígitos), não o subitem de 8 dígitos da nota.",
  `Cobre ${POSITIONS_IN_SCOPE} posições do agro; um produto fora delas recebe a mais parecida.`,
  `Os testes somam ${MODEL_COMPARISON.pooledRows} descrições: diferenças de 2 a 3 pontos não são detectáveis.`,
  "Descrições de uma palavra, siglas e marcas ainda erram com mais frequência.",
];

export function ResultsSection() {
  return (
    <section id="resultados" aria-labelledby="results-section-title" className="border-b bg-muted/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-4 py-14">
        <SectionHeading titleId="results-section-title" eyebrow="Resultados" title="Medido em descrições reais, com testes congelados">
          <p>
            Os testes têm textos reais, rotulados à mão e congelados com checksum. Nenhum deles foi
            usado para treinar, calibrar ou escolher o modelo. No{" "}
            {SECOND_TEST.name} ({SECOND_TEST.rows} descrições), o acerto da 1ª sugestão foi de{" "}
            {formatPercent(SECOND_TEST.top1)}; no {PUBLISHED_TEST.name}, os casos aceitos sem revisão
            acertaram {formatPercent(PUBLISHED_TEST.acceptedTop1)}.
          </p>
        </SectionHeading>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <article className="flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-5">
            <h3 className="font-heading text-lg font-semibold">O modelo simples ganhou</h3>
            <p className="text-sm text-muted-foreground">
              Os dois modelos foram treinados e avaliados com o mesmo protocolo. Nas{" "}
              {MODEL_COMPARISON.pooledRows} descrições de teste, empataram; o mais simples responde
              cerca de {speedup} vezes mais rápido em CPU e foi para produção.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th scope="col" className="py-2 pr-3 font-medium">Modelo</th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">Acerto top-1</th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">Latência</th>
                    <th scope="col" className="hidden py-2 text-right font-medium sm:table-cell">Tamanho</th>
                  </tr>
                </thead>
                <tbody>
                  {MODELS.map((model) => (
                    <tr key={model.name} className="border-b last:border-0">
                      <th scope="row" className="py-2.5 pr-3 text-left font-normal">
                        <span className="flex items-center gap-1.5 font-medium">
                          {model.chosen && <CheckCircle2 aria-hidden className="size-4 text-primary" />}
                          {model.name}
                        </span>
                        <span className="text-xs text-muted-foreground">{model.role}</span>
                      </th>
                      <td className="py-2.5 pr-3 text-right tabular-nums">{formatPercent(model.top1)}</td>
                      <td className="py-2.5 pr-3 text-right tabular-nums">
                        {formatDecimal(model.latency, 1)} ms
                      </td>
                      <td className="hidden py-2.5 text-right tabular-nums sm:table-cell">
                        {formatDecimal(model.disk, 1)} MB
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">
              Latência mediana de uma descrição por vez, em CPU.{" "}
              <a href={COMPARISON_URL} target="_blank" rel="noopener noreferrer" className="underline underline-offset-3">
                Comparação completa
                <ExternalLink aria-hidden className="ml-0.5 inline size-3" />
                <span className="sr-only">(abre em nova aba)</span>
              </a>
            </p>
          </article>

          <article className="flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-5">
            <h3 className="font-heading text-lg font-semibold">
              {TOTAL_TRAINING} descrições de treino, de três fontes
            </h3>
            <ul className="flex flex-col gap-2 text-sm">
              {DATA_ROWS.map((row) => (
                <li key={row.label} className="flex items-baseline justify-between gap-4 border-b pb-2 last:border-0">
                  <span className="text-muted-foreground">{row.label}</span>
                  <span className="font-semibold tabular-nums">{row.value}</span>
                </li>
              ))}
            </ul>
            <p className="text-sm text-muted-foreground">
              Os sintéticos fizeram diferença: sem eles, o acerto da 1ª sugestão no{" "}
              {PUBLISHED_TEST.name} cai de {formatPercent(PUBLISHED_TEST.top1)} para{" "}
              {formatPercent(WITHOUT_SYNTHETIC_TOP1)}. O {SECOND_TEST.name} foi montado depois deles,
              para medir esse efeito sem viés.
            </p>
          </article>
        </div>

        <article className="flex flex-col gap-3 rounded-xl border bg-card p-5">
          <h3 className="font-heading text-lg font-semibold">Limitações conhecidas</h3>
          <ul className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
            {LIMITATIONS.map((item) => (
              <li key={item} className="flex gap-2">
                <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
                {item}
              </li>
            ))}
          </ul>
          <a
            href={LIMITATIONS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="w-fit text-sm underline underline-offset-3"
          >
            Todas as limitações no README
            <span className="sr-only">(abre em nova aba)</span>
          </a>
        </article>
      </div>
    </section>
  );
}
