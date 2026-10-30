# ADR 0001 — Escopo do MVP e hospedagem sem custo

- **Data:** 2026-10-30
- **Status:** aceita

## Contexto

O projeto tem 4 semanas de prazo, compartilhadas com outros projetos de portfólio, e precisa funcionar sem custo de infraestrutura.

## Decisões

1. **Classificar até a posição (4 dígitos).** Reduz o número de classes e a quantidade de exemplos necessária. O nível de 8 dígitos fica como evolução.
2. **Teste escrito à mão e congelado antes de qualquer treino.** É a referência de qualidade de todos os modelos.
3. **Exemplos gerados por LLM decididos por experimento.** O modelo é treinado com e sem esses exemplos; eles só ficam se melhorarem o resultado no teste manual.
4. **Dataset em Parquet, versionado no Hugging Face.** Sem banco de dados no MVP.
5. **Demo no Hugging Face Spaces (Gradio, plano gratuito com ZeroGPU).** A API FastAPI fica no repositório, testada e com Docker, rodando localmente.

## Consequências

- Custo de infraestrutura: zero.
- Frontend Next.js, PostgreSQL e deploy público da API ficam para depois do MVP.
- O README declara o nível de classificação e as limitações.
