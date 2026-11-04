# Interface web do NCM Classifier

Site estático (Next.js + TypeScript + Tailwind + shadcn/ui) que apresenta o projeto e chama a
[API do NCM Classifier](../docs/api.md). Publicado no GitHub Pages:
**https://amanda-gondra.github.io/ncm-classifier/**.

A página não tem servidor próprio nem segredos: é HTML, CSS e JavaScript gerados por
`next build` (`output: "export"`).

## O que a página mostra e de onde vem cada coisa

| Parte | Origem |
|---|---|
| Topo, faixa de diferenciais, como funciona, resultados, arquitetura | conteúdo estático; números em `src/lib/project-facts.ts` |
| Exemplo do topo ("Ureia agrícola, pacote 1 kg") | resposta real da API, gravada em `src/lib/sample-prediction.ts` |
| Demonstração: sugestões, confiança, revisão manual, regra 31.05 | API, ao vivo |
| Painel "Sobre o modelo" | API (`GET /v1/model`), ao vivo |
| Imagem de compartilhamento (`/og-image.png`) e ícone (`/icon.png`) | gerados no build, com os mesmos números e o mesmo exemplo |

Os números estáticos não são digitados à mão sem conferência: `src/lib/project-facts.test.ts`
compara cada um com os relatórios versionados do repositório (`reports/baseline_v1.json`,
`reports/comparison/*.json`, `positions.json`) e falha se algum divergir. O mesmo teste confere
que o exemplo gravado usa as descrições oficiais do catálogo.

O topo mostra um resultado mesmo com a API dormindo; a demonstração mostra
"A API está acordando…" e tenta de novo sozinha até o modelo ficar pronto.

## Desenvolvimento

Requer Node 24.

```bash
cd web
npm ci
npm run dev        # http://localhost:3000
```

Por padrão a página chama a API publicada na Render. Para usar uma API local:

```bash
# terminal 1, na raiz do repositório
ALLOWED_ORIGINS=http://localhost:3000 uvicorn ncm_classifier.api.main:create_app --factory --port 8000

# terminal 2, em web/
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Verificações

```bash
npm run lint        # ESLint
npm run typecheck   # tipos de rota do Next + tsc
npm test            # Vitest + Testing Library, incluindo os números da página
npm run build       # gera o site estático em out/
```

## Contrato com a API

Os tipos TypeScript (`src/lib/api/schema.d.ts`) são gerados do esquema OpenAPI da API, então
uma mudança no contrato aparece como erro de tipo, não como bug no navegador:

```bash
python scripts/export_openapi.py   # na raiz: atualiza web/openapi.json
npm run gen:api                    # em web/: atualiza schema.d.ts
```

A CI falha se `openapi.json` ou `schema.d.ts` ficarem desatualizados.

## Material de divulgação

As capturas e o GIF de [`docs/media/`](../docs/media/README.md) são tirados do site publicado,
chamando a API real:

```bash
cd web
node scripts/capture-media.mjs           # capturas + quadros do GIF em ../docs/media
cd ..
python scripts/build_demo_gif.py         # monta docs/media/demo.gif (Pillow, extra "analysis")
```

O script usa o Edge ou o Chrome já instalados (ou `BROWSER_PATH`) por meio do `playwright-core`,
que não baixa navegador.

## Publicação

O workflow [`pages.yml`](../.github/workflows/pages.yml) testa, gera o site com o
`basePath` do Pages (`/ncm-classifier`) e publica a cada push em `main` que altere `web/`.
A origem `https://amanda-gondra.github.io` está em `ALLOWED_ORIGINS` no `render.yaml`, para o
navegador poder chamar a API.
