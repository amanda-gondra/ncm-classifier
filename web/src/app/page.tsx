import { ClassifierApp } from "@/components/classifier-app";
import { LINKS } from "@/lib/config";

export default function Home() {
  return (
    <>
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8">
          <h1 className="font-heading text-2xl font-semibold tracking-tight">Classificador NCM</h1>
          <p className="max-w-2xl text-muted-foreground">
            Digite a descrição de um produto e veja as posições NCM (4 dígitos) mais prováveis,
            com confiança calibrada e o aviso de quando vale revisar manualmente.
          </p>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <ClassifierApp />
      </main>

      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-muted-foreground">
          <p>
            Ferramenta de demonstração. As sugestões não substituem a análise de um profissional
            nem a consulta à tabela NCM vigente.
          </p>
          <p>
            Projeto de portfólio de Amanda Gondra ·{" "}
            <a href={LINKS.github} className="underline underline-offset-3">
              código-fonte
            </a>
          </p>
        </div>
      </footer>
    </>
  );
}
