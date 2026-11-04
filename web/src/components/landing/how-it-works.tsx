// Three steps, in plain words. The model details stay in the demonstration's details block.
import { ArrowDown, ArrowRight, CircleCheck, Cpu, FileText } from "lucide-react";
import { Fragment } from "react";

import { SectionHeading } from "@/components/landing/section-heading";

const STEPS = [
  { icon: FileText, title: "Descreva o produto", text: "Como no anúncio ou na nota." },
  { icon: Cpu, title: "O modelo analisa o texto", text: "Palavras, siglas, pesos e fórmulas." },
  { icon: CircleCheck, title: "Receba as 3 sugestões", text: "Com confiança e aviso de revisão." },
];

export function HowItWorks() {
  return (
    <section id="como-funciona" aria-labelledby="how-title">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-10 px-4 py-16">
        <SectionHeading titleId="how-title" eyebrow="Como funciona" title="Do texto à classificação, em segundos" centered />
        <ol className="flex w-full max-w-4xl flex-col items-center gap-4 md:flex-row md:items-start md:justify-between">
          {STEPS.map(({ icon: Icon, title, text }, index) => (
            <Fragment key={title}>
              {index > 0 && (
                <li aria-hidden className="flex items-center text-muted-foreground/60 md:mt-6">
                  <ArrowDown className="size-5 md:hidden" />
                  <ArrowRight className="hidden size-6 md:block" />
                </li>
              )}
              <li className="flex max-w-56 flex-col items-center gap-3 text-center">
                <span aria-hidden className="flex size-14 items-center justify-center rounded-2xl bg-secondary text-primary">
                  <Icon className="size-7" />
                </span>
                <h3 className="font-semibold">
                  {index + 1}. {title}
                </h3>
                <p className="text-sm text-muted-foreground">{text}</p>
              </li>
            </Fragment>
          ))}
        </ol>
      </div>
    </section>
  );
}
