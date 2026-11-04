// Footer: project summary, page sections, external resources, author and the fiscal notice.
import { BrandMark } from "@/components/landing/brand-mark";
import { SECTIONS } from "@/components/landing/site-header";
import { LINKS } from "@/lib/config";

const RESOURCES = [
  { href: LINKS.github, label: "Código no GitHub" },
  { href: LINKS.model, label: "Modelo no Hugging Face" },
  { href: LINKS.dataset, label: "Dataset no Hugging Face" },
  { href: LINKS.apiDocs, label: "Documentação da API" },
];

const AUTHOR = [
  { href: "https://github.com/amanda-gondra", label: "GitHub" },
  { href: "https://huggingface.co/AmandaGondra", label: "Hugging Face" },
];

const linkClass = "text-white/75 transition-colors hover:text-white";

function ExternalItem({ href, label }: { href: string; label: string }) {
  return (
    <li>
      <a href={href} target="_blank" rel="noopener noreferrer" className={linkClass}>
        {label}
        <span className="sr-only"> (abre em nova aba)</span>
      </a>
    </li>
  );
}

export function SiteFooter() {
  return (
    <footer className="bg-brand-deep text-white">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 md:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))]">
        <div className="flex flex-col gap-3">
          <span className="flex items-center gap-2.5">
            <BrandMark className="bg-white/15" />
            <span className="font-heading font-semibold">NCM Classifier</span>
          </span>
          <p className="max-w-xs text-sm text-white/75">
            Inteligência artificial aplicada à classificação fiscal de produtos agropecuários.
          </p>
        </div>

        <nav aria-label="Seções da página" className="flex flex-col gap-3 text-sm">
          <h2 className="font-semibold">Projeto</h2>
          <ul className="flex flex-col gap-2">
            {SECTIONS.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`} className={linkClass}>
                  {section.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex flex-col gap-3 text-sm">
          <h2 className="font-semibold">Recursos</h2>
          <ul className="flex flex-col gap-2">
            {RESOURCES.map((item) => (
              <ExternalItem key={item.href} {...item} />
            ))}
          </ul>
        </div>

        <div className="flex flex-col gap-3 text-sm">
          <h2 className="font-semibold">Amanda Gondra</h2>
          <ul className="flex flex-col gap-2">
            {AUTHOR.map((item) => (
              <ExternalItem key={item.href} {...item} />
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-white/15">
        <p className="mx-auto max-w-6xl px-4 py-5 text-xs text-white/70">
          Projeto de demonstração, código sob licença MIT. As sugestões não substituem a análise de
          um profissional habilitado nem a consulta à tabela NCM vigente.
        </p>
      </div>
    </footer>
  );
}
