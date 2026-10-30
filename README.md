# NCM Classifier

Sugere os códigos NCM mais prováveis a partir da descrição comercial de um produto do agronegócio, como ela aparece numa nota fiscal.

```
"ADUBO NPK 20-05-20 SC 50KG"  →  top-3 posições NCM, com confiança calibrada
```

> **Status:** em desenvolvimento. As métricas serão publicadas aqui somente depois dos experimentos executados.

> **Aviso:** é uma ferramenta de apoio. A sugestão não substitui a decisão de classificação fiscal, que é responsabilidade de quem emite a nota.

## Por que este projeto

Toda NF-e exige o código NCM de cada produto, escolhido entre milhares de opções. Lojas agropecuárias e produtores costumam errar ou perder tempo nessa escolha. Este projeto investiga até onde um modelo de linguagem em português consegue ajudar, medindo o resultado com rigor.

## Escopo atual

- Produtos do agronegócio: animais e produtos animais, sementes e grãos, rações, adubos, defensivos, ferramentas e cercas, máquinas e peças.
- Classificação no nível de **posição (4 dígitos)**. O nível de 8 dígitos é uma evolução planejada.
- Fonte dos códigos: tabela NCM oficial do Classif (Portal Único Siscomex), com a versão registrada.

## Abordagem

| Etapa | Status |
| --- | --- |
| Normalização de texto compartilhada entre treino e inferência | feito |
| Tabela NCM oficial e dataset rotulado | em andamento |
| Baseline: TF-IDF + regressão logística | planejado |
| Modelo principal: fine-tuning do BERTimbau | planejado |
| Avaliação: top-1, top-3, F1 macro, calibração, análise de erros | planejado |
| API FastAPI (`POST /classify`) e demo no Hugging Face Spaces | planejado |

## Como rodar

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Estrutura

```
src/ncm_classifier/
├── text/         normalização de texto (treino e inferência)
├── data/         tabela NCM, montagem e divisão do dataset
├── models/       baseline e BERTimbau
├── evaluation/   métricas, calibração e análise de erros
├── inference/    carrega o modelo e devolve o top-3
└── api/          FastAPI
```

Decisões de arquitetura ficam em [`docs/adr/`](docs/adr/).

## Licença

MIT
