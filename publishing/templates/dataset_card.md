---
language: pt
license: other
license_name: mixed-official-cc-by-4.0
pretty_name: NCM Classifier — parte pública do treino
task_categories:
  - text-classification
tags:
  - ncm
  - classificacao-fiscal
  - agronegocio
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files: data/train_public-v1.parquet
---

# NCM Classifier — dataset (parte pública do treino)

## Objetivo

Exemplos de descrições de produtos agropecuários rotulados com a posição NCM (4 dígitos),
usados para treinar o [`$model_repo`](https://huggingface.co/$model_repo).

Esta é a **parte redistribuível** do treino: **$rows linhas** de um total de $full_rows
($full_sources).

## Escopo

$scope_table

**Tabela NCM:** $ncm_version.

## Fontes

| source_type | O que é | Redistribuição |
|---|---|---|
| `ncm_official` | Texto da própria tabela NCM: a descrição da posição e de cada subitem relevante, usando a posição de 4 dígitos como rótulo | Ato oficial, publicado pelo governo (Siscomex/Classif). A Lei 9.610/98, art. 8º, IV, exclui atos oficiais da proteção autoral. A NCM deriva do Sistema Harmonizado, cuja nomenclatura a Organização Mundial das Aduanas declara ser de sua propriedade intelectual. Publicado aqui com atribuição, para pesquisa e ensino; **essa ressalva de direitos é uma limitação conhecida**. |
| `synthetic` | Descrições escritas por um LLM (`llm:claude-opus-5.5`) no estilo de anúncios e notas, e revisadas uma a uma | CC BY 4.0 |

**Não incluídos:**
- descrições de anúncios e catálogos de terceiros (Mercado Livre, MF Rural, Magazine Luiza e
  outros), por serem textos de terceiros sem autorização de redistribuição;
- os dois testes congelados, para não comprometer a avaliação.

## Construção

1. **Escopo:** 37 posições escolhidas do agro.
2. **Exemplos oficiais:** o texto de cada posição e de cada subitem, ignorando níveis genéricos
   ("Outros").
3. **Exemplos sintéticos:** descrições por posição no estilo de anúncios e notas, com unidades e
   abreviações comuns, cada uma revisada antes de entrar.
4. **Limpeza contra vazamento:** foram removidas as quase-duplicatas dos testes (Jaccard de
   5-gramas de caracteres ≥ 0,8), os conflitos de rótulo e as repetições. A conferência de
   quase-duplicatas foi refeita na exportação deste arquivo.

## Estrutura

`data/train_public-v1.parquet`:

| Coluna | Tipo | Descrição |
|---|---|---|
| `example_id` | string | id estável (`ncm-…` oficial, `s…` sintético) |
| `text` | string | descrição do produto |
| `position` | string | posição NCM de 4 dígitos (rótulo) |
| `chapter` | string | capítulo NCM (2 primeiros dígitos) |
| `source_type` | string | `ncm_official` ou `synthetic` |
| `source_ref` | string | código NCM de origem ou identificação do gerador |

**Valores ausentes:** nenhum. Todas as colunas estão preenchidas em todas as linhas.

## Distribuição por capítulo

$distribution_table

$positions posições presentes. Contagens por posição em `stats/`.

## Exemplos

$examples_table

## Revisão

Cada linha foi revisada por uma pessoa antes de entrar no treino. A rotulagem segue o texto legal
das posições, com estas convenções:

- **Adubos sem embalagem declarada:** contam como granel (mais de 10 kg), e não como 31.05.
- **Sal:** sal mineral para animais é 23.09; sal comum é 25.01.

## Limitações

- **Parte do treino:** este arquivo, sozinho, não reproduz o modelo publicado. As 241
  descrições de anúncios não estão aqui.
- **Texto oficial é formal:** ele é bem diferente das descrições comerciais reais.
- **Viés dos sintéticos:** eles refletem o estilo do gerador, mesmo revisados. Foram escritos
  depois de o primeiro teste existir.
- **Classes pequenas:** de 14 a algumas dezenas de linhas por posição, somando todas as fontes.

## Licença

- `synthetic`: **CC BY 4.0** (atribuição: Amanda Gondra, NCM Classifier).
- `ncm_official`: texto de ato oficial brasileiro, reproduzido com atribuição (fonte: Siscomex,
  $ncm_version), com a ressalva sobre o Sistema Harmonizado descrita em *Fontes*.
- Este documento não é parecer jurídico.

## Versão

$version, gerado em $date a partir do código em [$github]($github). Hashes dos arquivos em
`manifest.json`.
