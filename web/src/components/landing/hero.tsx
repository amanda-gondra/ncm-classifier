// First screen: what the project does, three verified results and a real answer of the
// API recorded in advance, so the visitor sees the output before typing anything.
import { ArrowRight, ExternalLink, History } from "lucide-react";

import { ResultCard } from "@/components/prediction-results";
import { buttonVariants } from "@/components/ui/button";
import { LINKS } from "@/lib/config";
import { formatPercent } from "@/lib/format";
import { POSITIONS_IN_SCOPE, PUBLISHED_TEST } from "@/lib/project-facts";
import {
  SAMPLE_DESCRIPTION,
  SAMPLE_MODEL_VERSION,
  SAMPLE_RECORDED_ON,
  SAMPLE_RESULT,
} from "@/lib/sample-prediction";
import { cn } from "@/lib/utils";

const STATS = [
  { value: formatPercent(PUBLISHED_TEST.top1), label: "de acerto na 1ª sugestão" },
  { value: formatPercent(PUBLISHED_TEST.top3), label: "com a posição certa entre as 3 sugestões" },
  { value: String(POSITIONS_IN_SCOPE), label: "posições NCM do agronegócio" },
];

function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

export function Hero() {
  return (
    <section
      id="inicio"
      aria-labelledby="hero-title"
      className="border-b bg-linear-to-b from-secondary/70 to-background"
    >
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 md:py-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)] lg:items-center">
        <div className="flex flex-col gap-6">
          <p className="w-fit rounded-full border border-primary/20 bg-background/70 px-3 py-1 text-xs font-medium text-secondary-foreground">
            Projeto open source · licença MIT
          </p>
          <h1
            id="hero-title"
            className="font-heading text-3xl leading-tight font-bold tracking-tight text-balance sm:text-4xl lg:text-[2.75rem]"
          >
            Classificação NCM de produtos agropecuários com{" "}
            <span className="text-primary">inteligência artificial</span>
          </h1>
          <p className="max-w-xl text-base text-pretty text-muted-foreground sm:text-lg">
            Digite a descrição comercial de um produto, como ela aparece num anúncio ou numa nota
            fiscal, e receba as 3 posições NCM mais prováveis, com confiança calibrada e o aviso de
            quando vale revisar manualmente.
          </p>

          <div className="flex flex-col gap-3">
            <dl className="grid grid-cols-3 gap-3 sm:gap-6">
              {STATS.map((stat) => (
                <div key={stat.label} className="flex flex-col gap-1 border-l-2 border-primary/40 pl-3">
                  <dt className="order-2 text-xs leading-snug text-muted-foreground sm:text-sm">
                    {stat.label}
                  </dt>
                  <dd className="order-1 font-heading text-2xl font-bold tabular-nums sm:text-3xl">
                    {stat.value}
                  </dd>
                </div>
              ))}
            </dl>
            <p className="text-xs text-muted-foreground">
              Modelo publicado {SAMPLE_MODEL_VERSION}, avaliado em {PUBLISHED_TEST.rows} descrições
              reais que ele nunca viu no treino ({PUBLISHED_TEST.name}).
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <a href="#demonstracao" className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-base")}>
              Testar a demonstração
              <ArrowRight data-icon="inline-end" aria-hidden />
            </a>
            <a
              href={LINKS.github}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-11 px-5 text-base")}
            >
              Ver o código no GitHub
              <ExternalLink data-icon="inline-end" aria-hidden />
              <span className="sr-only">(abre em nova aba)</span>
            </a>
          </div>
        </div>

        <figure className="flex flex-col gap-3">
          <div className="rounded-2xl border bg-background p-3 shadow-sm sm:p-4">
            <p className="mb-3 rounded-lg border bg-muted px-3 py-2 text-sm">
              <span className="text-muted-foreground">Descrição: </span>
              {SAMPLE_DESCRIPTION}
            </p>
            <ResultCard description="Resposta da API" result={SAMPLE_RESULT} compact />
          </div>
          <figcaption className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <History aria-hidden className="size-3.5" />
            Resposta real da API, gravada em {formatDate(SAMPLE_RECORDED_ON)} com o modelo{" "}
            {SAMPLE_MODEL_VERSION}.
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
