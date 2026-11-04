// The full demonstration: batch input, API state and the model details.
import { ClassifierApp } from "@/components/classifier-app";
import { SectionHeading } from "@/components/landing/section-heading";

export function DemoSection() {
  return (
    <section id="demonstracao" aria-labelledby="demo-title" className="border-y bg-muted/40">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-16">
        <SectionHeading titleId="demo-title" eyebrow="Demonstração" title="Teste com a sua descrição">
          <p>Uma descrição ou várias de uma vez, com até 3 sugestões, confiança e aviso de revisão.</p>
        </SectionHeading>
        <ClassifierApp />
      </div>
    </section>
  );
}
