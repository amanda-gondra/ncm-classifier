# ADR 0003 — Escolha do modelo de produção

- **Data:** 2026-11-03
- **Status:** proposta, aguardando decisão da Amanda

## Contexto

Dois modelos foram avaliados com o mesmo protocolo (ADR 0002): os mesmos dados, as mesmas 5
dobras, a mesma calibração, a mesma regra 31.05, o mesmo limiar de revisão e as mesmas
métricas.

- `baseline_v1`: TF-IDF + regressão logística.
- `bertimbau_v1`: BERTimbau Base, fine-tuning no Kaggle.

A comparação completa está em `docs/experiments/model_comparison.md`.

## Evidência resumida

| | Baseline | BERTimbau |
|---|---|---|
| top-1, testes juntos (220 linhas) | 0,9455 | 0,9455 |
| Diferença pareada de top-1 (B − A), testes juntos | — | 0,0 pt [−3,6; +4,1], McNemar p = 1,00 |
| Diferença pareada de top-1, fora da dobra (900 linhas) | — | +0,7 pt [−1,3; +2,8], McNemar p = 0,59 |
| ECE calibrado, test_v1 / test_v2 | 0,075 / 0,062 | 0,014 / 0,057 |
| Vai para revisão, test_v1 / test_v2 | 11,0% / 13,5% | 2,1% / 4,1% |
| Erros aceitos sem revisão (220 linhas) | 2 | 8 |
| Latência mediana, um texto, CPU | 1,3 ms | 63,1 ms |
| Memória / disco | 96 MB / 7,3 MB | 655 MB / 436,5 MB |
| Retreino | CPU, minutos | GPU (Kaggle) |

## Decisão proposta

**Baseline em produção (API e Space); BERTimbau mantido como experimento documentado e
reproduzível.**

A qualidade medida não distingue os dois modelos. Com o limiar de revisão, o baseline comete
menos erros sem pedir revisão, e custa uma fração para servir e manter. O BERTimbau só seria
preferível se o custo da revisão humana pesasse mais do que esses pontos, ou se um teste maior
mostrasse ganho consistente.

## Alternativas

1. **BERTimbau em produção:** menos revisão, ao custo de ~50× de latência, 4× mais erros aceitos
   nestes testes e retreino com GPU.
2. **Os dois lado a lado no Space, baseline na API:** útil para demonstração, com o dobro do
   trabalho de publicação.

## Consequências (se aprovada)

- A API (etapa 8) e o Space (etapa 9) carregam `models/baseline_v1.joblib`, sem PyTorch.
- O modelo BERTimbau vai para o Hugging Face como experimento, com o model card apontando esta
  comparação.
- Ficam registrados para o futuro: um test_v3 maior, várias sementes do BERTimbau e uma versão da
  regra 31.05 que não infle a confiança (seção C da comparação).
