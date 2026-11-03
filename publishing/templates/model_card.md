---
language: pt
license: mit
library_name: sklearn
pipeline_tag: text-classification
tags:
  - ncm
  - classificacao-fiscal
  - agronegocio
  - scikit-learn
  - skops
  - tfidf
datasets:
  - $dataset_repo
---

# NCM Classifier — sugestão de posição NCM para produtos do agro

> **Aviso.** Este modelo dá **sugestões**, não decisões fiscais. A responsabilidade pela
> classificação fiscal permanece com quem emite a nota. Na dúvida, consulte um profissional
> habilitado.

## Identificação

| | |
|---|---|
| Modelo | `$repo_id` |
| Versão | $version (publicado em $date) |
| Autora | Amanda Gondra |
| Arquitetura | TF-IDF (palavras 1–2 e caracteres 3–5) + regressão logística com classes balanceadas, calibração por temperatura e regra legal da posição 31.05 |
| Modelo pré-treinado | nenhum (treinado do zero com scikit-learn $sklearn) |
| Código | [$github]($github), commit `$commit` |
| Formato | `model.skops` (sem pickle) |

## Descrição

A partir da descrição comercial de um produto agropecuário ("Ureia agrícola saco 50 kg",
"Arame farpado 500 m"), o modelo sugere as **três posições NCM mais prováveis** (4 dígitos),
com a confiança calibrada da primeira. Quando a confiança fica abaixo de um limiar, marca a
sugestão para **revisão manual**.

O problema: quem vende para o produtor rural precisa informar a NCM na nota fiscal, e as
descrições comerciais raramente usam a linguagem da tabela.

Etapas da inferência, iguais às da avaliação:

1. **Normalização do texto:** minúsculas, sem acentos, fórmulas NPK, unidades e abreviações
   padronizadas.
2. **Probabilidades** da regressão logística.
3. **Calibração por temperatura:** `softmax(log p / T)`, com T = $temperature.
4. **Regra 31.05**, do texto legal da posição: mercadorias do Capítulo 31 em embalagens de até
   10 kg vão para a 31.05.
5. **Três sugestões e revisão:** volta o top-3; a sugestão vai para revisão quando a confiança
   final for menor que $threshold.

## Uso pretendido

- **Público:** quem emite nota de produtos agropecuários (lojas, revendas, cooperativas) e quer
  um ponto de partida para a classificação. Também serve como exemplo de engenharia de ML.
- **Cenários:** sugerir a NCM numa tela de cadastro de produtos; triar descrições para revisão.
- **Fora do uso pretendido:** decidir a NCM sem revisão humana; produtos fora das posições
  abaixo; classificação em 8 dígitos (subitem).

Posições cobertas (nível de posição, 4 dígitos):

$scope_table

## Dados de treinamento

- **Linhas:** $train_rows ($train_sources).
- **Fontes:**
  - descrições comerciais reais de anúncios e catálogos;
  - descrições da própria tabela NCM oficial;
  - descrições sintéticas, geradas com um LLM e revisadas uma a uma.
- **Rotulagem:** feita à mão, com a regra legal anotada em cada linha. A fonte comprova a
  descrição, não a classificação.
- **Pré-processamento:** a normalização descrita acima. Quase-duplicatas dos testes foram
  removidas do treino (Jaccard de 5-gramas de caracteres ≥ 0,8), e nenhuma fonte do treino
  coincide com uma fonte de teste.
- **Dados sintéticos:** foram escritos depois do primeiro teste (test_v1) existir. Por isso foi
  criado um segundo teste independente (test_v2); nele, o ganho dos sintéticos foi menor, mas
  se manteve.
- **Versão dos dados:** SHA-256 do arquivo de treino `$train_sha`.
- **Parte publicada:** só as linhas oficiais e sintéticas estão em
  [`$dataset_repo`](https://huggingface.co/datasets/$dataset_repo). As descrições de anúncios
  não são redistribuídas.

## Avaliação

### Protocolo

- **Escolha do C:** validação cruzada estratificada em 5 dobras no treino (impressão digital
  das dobras: `$folds_sha`). C = $best_c, macro F1 médio de $cv_f1.
- **Calibração:** temperatura e limiar de revisão ajustados nas probabilidades fora da dobra do
  treino. Fora da dobra: $oof_review enviado para revisão e $oof_accepted de top-1 nos aceitos.
- **Testes:** dois testes **congelados** e escritos à mão antes do treino, com checksum,
  nunca usados para treino ou escolha:
  - `test_v1`: 146 linhas, todas as 37 posições;
  - `test_v2`: 74 linhas, de fontes novas.
- **Intervalos:** bootstrap com 1000 reamostragens, intervalo percentil de 95%, semente 0.

### Resultados (calibrado + regra 31.05)

$metrics_table

As métricas macro tiram a média sobre as posições presentes em cada teste. ECE é o erro de
calibração da confiança do top-1, em 10 faixas.

### Por capítulo

Linhas, acerto da posição e acerto do capítulo (os dois primeiros dígitos):

$chapter_table

### Comparação com BERTimbau

Um fine-tuning do BERTimbau, com os mesmos dados, dobras, calibração e regra, empatou na
qualidade: o top-1 dos dois testes juntos foi igual, e o intervalo da diferença pareada vai de
−3,6 a +4,1 pontos. Ele custa ~50× mais por previsão em CPU. Os detalhes e o modelo estão em
[`$bertimbau_repo`](https://huggingface.co/$bertimbau_repo).

## Como usar

```bash
pip install -r requirements.txt   # instala o pacote ncm-classifier na versão $version
```

```python
from huggingface_hub import snapshot_download
from ncm_classifier.inference.predictor import NcmPredictor

path = snapshot_download("$repo_id", revision="$version")
predictor = NcmPredictor.from_directory(path)

for prediction in predictor.predict(["Ureia agrícola, pacote 1 kg"]):
    print(prediction.to_dict())
```

Cada resultado traz:

- `suggestions`: três posições, da mais provável para a menos provável, com a probabilidade
  calibrada de cada uma. Leia como "provavelmente a primeira; confira as outras duas se a
  descrição for ambígua".
- `confidence`: probabilidade calibrada da primeira sugestão.
- `needs_review`: `true` quando a confiança está abaixo do limiar. Nesse caso, a sugestão deve
  ser conferida por uma pessoa.
- `rule_31_05`: `true` quando a regra da embalagem de até 10 kg mudou a sugestão.

O carregador só aceita, além do scikit-learn e do NumPy, a função de normalização do próprio
projeto. Qualquer outro tipo no arquivo faz o carregamento falhar.

## Limitações e riscos

- **O modelo dá sugestões, não decisões fiscais.** Ele pode errar, inclusive com confiança alta.
- **A responsabilidade pela classificação fiscal permanece com quem emite a nota.** A revisão
  por um profissional habilitado pode ser necessária.
- **A qualidade depende da descrição.** Textos curtos ("Chocadeira"), siglas ("TSP") e marcas
  sem contexto erram mais.
- **Composição e aplicação mudam a NCM.** Por exemplo, sal mineral é 23.09 e sal comum é 25.01;
  adubos dependem da composição e da embalagem. Produtos assim podem exigir análise técnica.
- **Embalagem não declarada:** quando o texto não diz o peso, o rótulo segue a convenção de
  granel (mais de 10 kg). A regra 31.05 só lê pesos escritos em grafias reconhecidas ("5 kg",
  "500 g"); grafias como "5k" passam sem a regra.
- **A tabela NCM muda.** O escopo segue a tabela vigente em 30/10/2026 (Resolução Gecex
  nº 926/2026).
- **Testes pequenos.** Com 220 linhas, os intervalos de confiança são largos.
- **Escopo restrito:** 37 posições, nível de 4 dígitos. Fora delas, o modelo sempre sugere uma
  das 37, mesmo que nenhuma sirva.

## Licença

- **Código e modelo:** MIT.
- **Dados:** o treino inclui descrições de anúncios de terceiros, que não são redistribuídas.
  O modelo guarda delas apenas estatísticas de palavras e trechos curtos. A parte publicada dos
  dados tem licença própria, descrita no
  [dataset card](https://huggingface.co/datasets/$dataset_repo).
- Este documento não é parecer jurídico.
