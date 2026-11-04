// Sticky header: project name, links to the sections of this page and the main actions.
// On small screens the section links are hidden (the page scrolls through them anyway);
// the call to action stays.
import { ArrowRight, ExternalLink } from "lucide-react";

import { BrandMark } from "@/components/landing/brand-mark";
import { buttonVariants } from "@/components/ui/button";
import { LINKS } from "@/lib/config";
import { cn } from "@/lib/utils";

export const SECTIONS = [
  { id: "como-funciona", label: "Como funciona" },
  { id: "demonstracao", label: "Demonstração" },
  { id: "resultados", label: "Resultados" },
  { id: "arquitetura", label: "Arquitetura" },
] as const;

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
        <a href="#inicio" className="flex items-center gap-2.5" aria-label="NCM Classifier, início">
          <BrandMark />
          <span className="flex flex-col leading-tight">
            <span className="font-heading font-semibold">NCM Classifier</span>
            <span className="hidden text-xs text-muted-foreground sm:block">
              IA para classificação fiscal no agro
            </span>
          </span>
        </a>

        <nav aria-label="Seções" className="ml-4 hidden lg:block">
          <ul className="flex items-center gap-6 text-sm">
            {SECTIONS.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  {section.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <a
            href={LINKS.github}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(buttonVariants({ variant: "outline", size: "lg" }), "hidden sm:inline-flex")}
          >
            GitHub
            <ExternalLink data-icon="inline-end" aria-hidden />
            <span className="sr-only">(abre em nova aba)</span>
          </a>
          <a href="#demonstracao" className={buttonVariants({ size: "lg" })}>
            Testar agora
            <ArrowRight data-icon="inline-end" aria-hidden />
          </a>
        </div>
      </div>
    </header>
  );
}
