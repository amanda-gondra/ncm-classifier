// First screen: what the project does, three verified results and the live classifier.
import { ArrowRight, BarChart3, ExternalLink, ListChecks, Sprout, Target } from "lucide-react";

import { QuickClassifier } from "@/components/quick-classifier";
import { buttonVariants } from "@/components/ui/button";
import { LINKS } from "@/lib/config";
import { formatPercent } from "@/lib/format";
import { POSITIONS_IN_SCOPE, PUBLISHED_TEST } from "@/lib/project-facts";
import { cn } from "@/lib/utils";

const STATS = [
  { icon: Target, value: formatPercent(PUBLISHED_TEST.top1), label: "acerto na 1ª sugestão" },
  { icon: ListChecks, value: formatPercent(PUBLISHED_TEST.top3), label: "acerto entre as 3" },
  { icon: BarChart3, value: String(POSITIONS_IN_SCOPE), label: "posições NCM do agro" },
];

export function Hero() {
  return (
    <section id="inicio" aria-labelledby="hero-title" className="bg-linear-to-b from-secondary/60 to-background">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-4 py-12 md:py-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:items-start lg:pt-20">
        <div className="flex min-w-0 flex-col gap-6">
          <p className="flex w-fit items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
            <Sprout aria-hidden className="size-3.5" />
            IA aplicada ao agronegócio
          </p>
          <h1
            id="hero-title"
            className="font-heading text-3xl leading-tight font-bold tracking-tight text-balance sm:text-4xl lg:text-[2.75rem]"
          >
            Classificação NCM de produtos agropecuários com{" "}
            <span className="text-primary">inteligência artificial</span>
          </h1>
          <p className="max-w-lg text-base text-pretty text-muted-foreground sm:text-lg">
            Digite a descrição de um produto e receba as 3 posições NCM mais prováveis, com a
            confiança de cada uma.
          </p>

          <div className="flex flex-col gap-2">
            <dl className="grid grid-cols-3 gap-2 sm:gap-3">
              {STATS.map(({ icon: Icon, value, label }) => (
                <div key={label} className="flex flex-col gap-1 rounded-xl border bg-card p-3 sm:flex-row sm:items-center sm:gap-3 sm:p-4">
                  <Icon aria-hidden className="size-5 shrink-0 text-primary sm:size-6" />
                  <div className="flex flex-col">
                    <dt className="order-2 text-xs leading-snug text-muted-foreground">{label}</dt>
                    <dd className="order-1 font-heading text-xl font-bold tabular-nums sm:text-2xl">{value}</dd>
                  </div>
                </div>
              ))}
            </dl>
            <p className="text-xs text-muted-foreground">
              Avaliado em {PUBLISHED_TEST.rows} descrições reais, nunca usadas no treino.
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

        <QuickClassifier />
      </div>
    </section>
  );
}
