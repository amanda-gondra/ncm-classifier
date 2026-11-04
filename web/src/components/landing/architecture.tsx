// How the pieces connect, with the technologies of each one, plus the quality checks.
import { ArrowDown, ArrowRight, Boxes, Globe, Server } from "lucide-react";
import { Fragment } from "react";

import { SectionHeading } from "@/components/landing/section-heading";
import { LINKS } from "@/lib/config";

const STAGES = [
  {
    icon: Boxes,
    title: "Hugging Face Hub",
    text: "Modelo v0.1.0 em formato skops, com calibração e cartão do modelo; dataset v1.0.0.",
    tech: ["scikit-learn", "skops", "Python"],
    href: LINKS.model,
    linkLabel: "Ver o modelo",
  },
  {
    icon: Server,
    title: "API de classificação",
    text: "Baixa o modelo numa versão fixa e responde em JSON, com validação, limite de taxa e CORS fechado.",
    tech: ["FastAPI", "Pydantic", "Docker", "Render"],
    href: LINKS.apiDocs,
    linkLabel: "Documentação da API",
  },
  {
    icon: Globe,
    title: "Este site",
    text: "Página estática que chama a API; os tipos vêm do esquema OpenAPI, então o contrato é verificado.",
    tech: ["Next.js", "TypeScript", "Tailwind CSS", "GitHub Pages"],
    href: LINKS.github,
    linkLabel: "Código-fonte",
  },
];

const CHECKS = [
  "ruff e mypy no Python",
  "pytest com cobertura mínima de 90% na API",
  "ESLint, TypeScript e Vitest no site",
  "Números da página conferidos contra os relatórios",
];

export function Architecture() {
  return (
    <section id="arquitetura" aria-labelledby="architecture-title" className="border-b">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-4 py-14">
        <SectionHeading titleId="architecture-title" eyebrow="Arquitetura" title="Do modelo publicado à página, sem custo">
          <p>
            Cada parte roda num serviço gratuito e pode ser verificada por qualquer pessoa: o modelo é
            público, a API documenta o próprio contrato e o código está no GitHub.
          </p>
        </SectionHeading>

        <ol className="flex flex-col items-stretch gap-3 lg:flex-row">
          {STAGES.map(({ icon: Icon, title, text, tech, href, linkLabel }, index) => (
            <Fragment key={title}>
              {index > 0 && (
                <li aria-hidden className="flex items-center justify-center text-muted-foreground">
                  <ArrowDown className="size-5 lg:hidden" />
                  <ArrowRight className="hidden size-5 lg:block" />
                </li>
              )}
              <li className="flex flex-1 flex-col gap-3 rounded-xl border bg-card p-5">
                <span className="flex items-center gap-2">
                  <Icon aria-hidden className="size-5 text-primary" />
                  <h3 className="font-semibold">{title}</h3>
                </span>
                <p className="text-sm text-muted-foreground">{text}</p>
                <ul className="flex flex-wrap gap-1.5" aria-label="Tecnologias">
                  {tech.map((name) => (
                    <li key={name} className="rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
                      {name}
                    </li>
                  ))}
                </ul>
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-auto w-fit text-sm font-medium text-primary underline underline-offset-3"
                >
                  {linkLabel}
                  <span className="sr-only">(abre em nova aba)</span>
                </a>
              </li>
            </Fragment>
          ))}
        </ol>

        <div className="flex flex-col gap-3 rounded-xl border border-dashed p-5">
          <h3 className="font-semibold">Verificado a cada mudança</h3>
          <ul className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
            {CHECKS.map((check) => (
              <li key={check} className="flex gap-2">
                <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
                {check}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
