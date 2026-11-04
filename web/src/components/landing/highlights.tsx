// Four short reasons to trust the result, right below the first screen.
import { FileCheck2, Scale, ShieldCheck, Wheat } from "lucide-react";

const ITEMS = [
  {
    icon: FileCheck2,
    title: "Tabela NCM oficial",
    text: "Descrições e códigos da tabela vigente do Classif, Portal Único Siscomex.",
  },
  {
    icon: Scale,
    title: "Sabe quando não sabe",
    text: "Confiança calibrada e aviso de revisão manual quando ela fica abaixo do limiar.",
  },
  {
    icon: Wheat,
    title: "Feito para o agro",
    text: "Adubos, sementes, rações, defensivos, cercas, animais, máquinas e mais.",
  },
  {
    icon: ShieldCheck,
    title: "Transparente e reproduzível",
    text: "Código, dataset, métricas e decisões públicos, com testes congelados.",
  },
];

export function Highlights() {
  return (
    <section aria-label="Diferenciais" className="border-b">
      <ul className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:grid-cols-2 lg:grid-cols-4">
        {ITEMS.map(({ icon: Icon, title, text }) => (
          <li key={title} className="flex gap-3">
            <span
              aria-hidden
              className="flex size-10 shrink-0 items-center justify-center rounded-full bg-secondary text-primary"
            >
              <Icon className="size-5" />
            </span>
            <div className="flex flex-col gap-0.5">
              <h2 className="text-sm font-semibold">{title}</h2>
              <p className="text-sm text-muted-foreground">{text}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
