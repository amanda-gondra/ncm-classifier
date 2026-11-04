// The problem, in the words of someone who issues invoices, and the five steps a
// description goes through, in the words of someone who builds models.
import { SectionHeading } from "@/components/landing/section-heading";

const STEPS = [
  {
    title: "Normalização do texto",
    text: "Minúsculas, acentos, abreviações e unidades padronizadas. A mesma função é usada no treino e na API.",
  },
  {
    title: "TF-IDF de palavras e caracteres",
    text: "Pedaços de palavras capturam siglas, erros de digitação e fórmulas como “20-05-20”.",
  },
  {
    title: "Regressão logística",
    text: "Um classificador linear dá uma probabilidade para cada uma das posições do escopo.",
  },
  {
    title: "Calibração e regra 31.05",
    text: "A temperatura ajusta as probabilidades à taxa real de acerto. Adubo em embalagem de até 10 kg vai para a 31.05.",
  },
  {
    title: "Limiar de revisão",
    text: "Abaixo de um limiar escolhido no treino, o caso é marcado para revisão manual.",
  },
];

export function HowItWorks() {
  return (
    <section id="como-funciona" aria-labelledby="how-title" className="border-b">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-4 py-14">
        <SectionHeading titleId="how-title" eyebrow="Como funciona" title="Da descrição do anúncio ao código da nota">
          <p>
            Toda NF-e exige o código NCM de cada produto, escolhido entre mais de 10 mil subitens da
            tabela oficial. Quem vende insumos e produtos agropecuários tem em mãos descrições como
            “ADUBO 20 5 20 SC 50KG”, que pouco se parecem com o texto legal. O NCM Classifier sugere a
            posição de 4 dígitos e diz quando a sugestão merece uma segunda olhada.
          </p>
        </SectionHeading>

        <ol className="grid gap-4 md:grid-cols-5">
          {STEPS.map((step, index) => (
            <li key={step.title} className="flex flex-col gap-2 rounded-xl border bg-card p-4">
              <span
                aria-hidden
                className="flex size-8 items-center justify-center rounded-full bg-secondary text-sm font-semibold text-primary"
              >
                {index + 1}
              </span>
              <h3 className="font-semibold">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
