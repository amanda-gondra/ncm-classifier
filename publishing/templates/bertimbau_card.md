---
language: pt
license: mit
library_name: transformers
pipeline_tag: text-classification
base_model: neuralmind/bert-base-portuguese-cased
tags:
  - ncm
  - classificacao-fiscal
  - agronegocio
  - bert
  - experimento
---

# NCM Classifier — experimento com BERTimbau (não é o modelo principal)

> **Este é um experimento documentado.** O modelo recomendado para uso é
> [`$model_repo`](https://huggingface.co/$model_repo), que empatou com este na qualidade e é
> bem mais leve. **Sugestões, não decisões fiscais:** a responsabilidade pela classificação
> fiscal permanece com quem emite a nota.

## Identificação

| | |
|---|---|
| Modelo | `$repo_id` |
| Versão | $version (publicado em $date) |
| Autora | Amanda Gondra |
| Modelo pré-treinado | [`neuralmind/bert-base-portuguese-cased`](https://huggingface.co/neuralmind/bert-base-portuguese-cased), revisão `$revision` (licença MIT) |
| Treino | fine-tuning de classificação em 37 posições NCM, numa $gpu, em ~$minutes min |
| Código | [$github]($github) (`notebooks/bertimbau_finetuning_kaggle.py`) |

## Como foi treinado

- **Dados:** os mesmos do modelo principal (900 linhas), conferidos por SHA-256, e as mesmas
  5 dobras.
- **Escolha na validação cruzada:**
  - entrada `$best_mode` (o mesmo `normalize_text` do baseline);
  - $best_epoch épocas;
  - macro F1 médio de $cv_f1 fora da dobra.
- **Treino:** perda ponderada por classe, AdamW com learning rate 3e-5, warmup de 10%,
  batch 16, até 128 tokens, float16 na GPU, semente 0.
- **Calibração e revisão:** temperatura (T = $temperature) e limiar de revisão ajustados fora da
  dobra (`calibration.json`).
- **Regra 31.05:** a mesma do modelo principal, aplicada depois da calibração.

## Resultados nos testes congelados (calibrado + regra 31.05)

$metrics_table

Contra o modelo principal, com bootstrap pareado e teste de McNemar, nenhuma diferença de
top-1, top-3 ou macro F1 foi distinguível de zero. Em resumo:

- **A favor deste modelo:** probabilidades mais bem calibradas no test_v1 e menos casos
  enviados para revisão.
- **Contra:** mais erros com confiança alta e cerca de 50 vezes mais tempo por previsão em CPU.

A análise completa está em `docs/experiments/model_comparison.md`, no repositório do código.

## Como usar

```python
from huggingface_hub import snapshot_download
from ncm_classifier.models.bertimbau import load_model, predict_proba
from ncm_classifier.models.transformer_support import prepare_input

path = snapshot_download("$repo_id", revision="$version")
model, tokenizer, classes = load_model(path)
proba = predict_proba(
    model, tokenizer, prepare_input(["Ureia agrícola, pacote 1 kg"], "$best_mode"), 128
)
```

Estas são probabilidades **brutas**. Para chegar às sugestões avaliadas, aplique a temperatura de
`calibration.json` e a regra 31.05 (`ncm_classifier.rules.small_package`).

## Limitações

- Semente única: a variação entre sementes não foi medida.
- A época escolhida foi a última da grade testada.
- A calibração ajustada nas dobras não se transferiu bem para o modelo final. Ele ficou mais
  confiante, e a meta de 95% nos aceitos não se manteve no test_v2.
- Valem as mesmas limitações de escopo e de qualidade da descrição do modelo principal.

## Licença

MIT, como o modelo de origem. Os dados de treino incluem descrições de anúncios de terceiros,
que não são redistribuídas.
