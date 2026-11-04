# Interface web do NCM Classifier

Site estático (Next.js + TypeScript + Tailwind + shadcn/ui) que apresenta o projeto e chama a
[API do NCM Classifier](../docs/api.md). Publicado no GitHub Pages:
**https://amanda-gondra.github.io/ncm-classifier/**.

A página não tem servidor próprio nem segredos: é HTML, CSS e JavaScript gerados por
`next build` (`output: "export"`).

## O que a página mostra e de onde vem cada coisa

| Parte | Origem |
|---|---|
| Textos, números do topo, como funciona, resultados, infraestrutura | conteúdo estático; números em `src/lib/project-facts.ts` |
| "Experimente agora" (topo) e demonstração | API, ao vivo; o estado da API é verificado uma vez para a página toda |
| "Detalhes do modelo e métricas" | API (`GET /v1/model`), ao vivo |
| Imagem de compartilhamento (`/og-image.png`) e ícone (`/icon.png`) | gerados no build; a imagem usa uma resposta real gravada em `src/lib/sample-prediction.ts` |

Os números estáticos não são digitados à mão sem conferência: `src/lib/project-facts.test.ts`
compara cada um com os relatórios versionados do repositório (`reports/baseline_v1.json`,
`reports/comparison/*.json`, `positions.json`) e falha se algum divergir. O mesmo teste confere
que o exemplo gravado usa as descrições oficiais do catálogo.

Com a API dormindo, o topo e a demonstração avisam que o servidor está acordando e tentam de
novo sozinhos até o modelo ficar pronto; os botões de classificar só são liberados nessa hora.

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
