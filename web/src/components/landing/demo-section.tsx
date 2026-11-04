// The live demonstration: the interactive part of the page, inside its own section.
import { ClassifierApp } from "@/components/classifier-app";
import { SectionHeading } from "@/components/landing/section-heading";

export function DemoSection() {
  return (
    <section id="demonstracao" aria-labelledby="demo-title" className="border-b bg-muted/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-14">
        <SectionHeading titleId="demo-title" eyebrow="Demonstração" title="Teste com a sua descrição">
          <p>
            Escreva o produto como ele aparece no anúncio ou na nota, ou escolha um exemplo. A API
            devolve as 3 posições mais prováveis com a descrição oficial de cada uma.
          </p>
        </SectionHeading>
        <ClassifierApp />
      </div>
    </section>
  );
}
