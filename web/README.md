# Interface web do NCM Classifier

Site estático (Next.js + TypeScript + Tailwind + shadcn/ui) que chama a
[API do NCM Classifier](../docs/api.md). Publicado no GitHub Pages:
**https://amanda-gondra.github.io/ncm-classifier/**.

A página não tem servidor próprio nem segredos: é HTML, CSS e JavaScript gerados por
`next build` (`output: "export"`). Tudo o que ela mostra vem da API: sugestões, confiança,
alerta de revisão, regra 31.05, métricas do modelo e aviso fiscal.

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
npm test            # Vitest + Testing Library
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

## Publicação

O workflow [`pages.yml`](../.github/workflows/pages.yml) testa, gera o site com o
`basePath` do Pages (`/ncm-classifier`) e publica a cada push em `main` que altere `web/`.
A origem `https://amanda-gondra.github.io` precisa estar em `ALLOWED_ORIGINS` na Render para
o navegador poder chamar a API.

No plano gratuito da Render a API dorme após 15 minutos sem uso; a página mostra
"A API está acordando…" e tenta de novo sozinha até o modelo ficar pronto.
