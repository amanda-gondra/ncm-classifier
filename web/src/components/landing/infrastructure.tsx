// Where each piece is published, one line each, with a link to check it.
import { ArrowRight, Boxes, Server, Workflow } from "lucide-react";

import { SectionHeading } from "@/components/landing/section-heading";
import { LINKS } from "@/lib/config";

const ITEMS = [
  {
    icon: Boxes,
    title: "Hugging Face",
    text: "Modelo e dataset publicados, com versão fixa e documentação.",
    href: LINKS.model,
    action: "Acessar",
  },
  {
    icon: Server,
    title: "API de classificação",
    text: "Serviço REST (FastAPI, Docker) que devolve as sugestões em JSON.",
    href: LINKS.apiDocs,
    action: "Ver documentação",
  },
  {
    icon: Workflow,
    title: "GitHub Actions",
    text: "Testes automáticos a cada mudança, publicação do site e monitoramento da API.",
    href: `${LINKS.github}/actions`,
    action: "Ver execuções",
  },
];

export function Infrastructure() {
  return (
    <section id="infraestrutura" aria-labelledby="infrastructure-title">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-8 px-4 py-16">
        <SectionHeading
          titleId="infrastructure-title"
          eyebrow="Infraestrutura"
          title="Publicação e infraestrutura"
          centered
        >
          <p>Modelo, dados e API abertos e reproduzíveis, sem custo de hospedagem.</p>
        </SectionHeading>

        <ul className="w-full divide-y rounded-xl border bg-card">
          {ITEMS.map(({ icon: Icon, title, text, href, action }) => (
            <li key={title}>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-4 p-4 transition-colors hover:bg-muted/50 sm:p-5"
              >
                <Icon aria-hidden className="size-8 shrink-0 text-primary" />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="font-semibold">{title}</span>
                  <span className="text-sm text-muted-foreground">{text}</span>
                </span>
                <span className="hidden shrink-0 items-center gap-1 text-sm font-medium text-primary sm:flex">
                  {action}
                  <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-0.5" />
                </span>
                <ArrowRight aria-hidden className="size-4 shrink-0 text-primary sm:hidden" />
                <span className="sr-only">(abre em nova aba)</span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
