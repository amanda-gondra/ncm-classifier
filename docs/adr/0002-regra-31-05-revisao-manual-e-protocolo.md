# ADR 0002 — Regra da 31.05, revisão manual e protocolo comum de avaliação

- **Data:** 2026-11-03
- **Status:** aceita

## Contexto

### O erro v045

No primeiro teste do baseline no `test_v2`, a linha **v045** ("Superfosfato Simples 1kg")
foi classificada em **31.03** (adubos fosfatados) com confiança calibrada de 1,0.

O texto da posição 31.05 inclui "mercadorias do presente Capítulo apresentadas em tabletes ou
formas semelhantes, ou ainda em embalagens com peso bruto não superior a 10 kg". Por isso,
qualquer mercadoria do Capítulo 31 em embalagem de até 10 kg é 31.05, e não a posição do
produto a granel.

Um classificador de texto não faz essa comparação de forma confiável: para ele, "1kg" é um
pedaço de texto, não um número menor que 10.

### Etapas 5 e 6

A etapa 5 (BERTimbau) exige que os dois modelos usem os mesmos dados, a mesma validação, a
mesma calibração, a mesma regra 31.05 e as mesmas métricas. A auditoria encontrou três lacunas:

1. não há conjunto de validação fixo: o baseline escolhe o `C` e calibra por validação cruzada
   de 5 dobras no treino;
2. não havia regra de revisão manual;
3. precisão, recall, métricas por capítulo e matriz de confusão não eram calculadas.

## Decisões

1. **Regra 31.05 depois do modelo** (`rules/small_package.py`). Ela só age quando:
   - o texto declara pelo menos um peso e todos são de até 10 kg;
   - a primeira sugestão do modelo é do Capítulo 31.

   Nesse caso, toda a probabilidade do Capítulo 31 passa para a 31.05. Isso muda o ranking e a
   confiança; os outros capítulos não mudam. Volumes ("1 L") não contam como peso bruto.

2. **Revisão manual por limiar de confiança** (`evaluation/review.py`).
   - Uma sugestão vai para revisão quando a confiança final (calibrada e depois da regra) fica
     abaixo de um limiar.
   - O limiar é ajustado nas probabilidades fora da dobra do treino: é a menor confiança para a
     qual os aceitos acertam pelo menos 95%.
   - Se nenhum limiar atinge a meta, tudo vai para revisão.

   Meta de 95% escolhida pela Amanda.

3. **Protocolo comum** (`evaluation/protocol.py` e `evaluation/report.py`).
   - Todos os modelos usam as mesmas 5 dobras estratificadas (semente 0), conferidas por uma
     impressão digital de cada par linha-dobra.
   - Cada modelo só entrega probabilidades brutas. A temperatura, a regra 31.05, o limiar de
     revisão e todas as métricas vêm do mesmo código.
   - Validação por essas 5 dobras escolhida pela Amanda, em vez de separar 15% do treino.

4. **Métricas acrescentadas sem mudar as anteriores:** precisão e recall macro (com o mesmo
   bootstrap), métricas por capítulo, pares de confusão e um arquivo de predições por teste. Os
   valores anteriores do baseline foram conferidos e são idênticos.

## Efeito medido (baseline_v1)

| Conjunto | top-1 calibrado | com a regra | Linhas alteradas | ECE antes → depois |
|---|---|---|---|---|
| Treino, fora da dobra | 0,8778 | 0,8844 | 6 | — |
| test_v1 | 0,9315 | 0,9452 | t008, t009 | 0,0635 → 0,0753 |
| test_v2 | 0,9324 | 0,9459 | v045 | 0,0504 → 0,0624 |

Todas as linhas alteradas pela regra nos testes foram corrigidas.

Revisão manual (limiar 0,6525):

| Conjunto | Enviado para revisão | top-1 dos aceitos |
|---|---|---|
| Treino, fora da dobra | 14,9% [12,7–17,2] | 95,0% [93,5–96,5] |
| test_v1 | 11,0% [6,2–16,4] | 98,5% [96,2–100] |
| test_v2 | 13,5% [6,8–21,6] | 100% [100–100] |

## Consequências e limitações

- **A regra nasceu de um erro do test_v2.** O ganho no test_v2 não é evidência independente.
  As evidências justas são o test_v1 (t008 e t009, que não motivaram a regra) e as 6 linhas do
  treino.
- **O ganho é pequeno** (2 de 146 e 1 de 74 linhas) e os intervalos se sobrepõem.
- **A calibração piora um pouco**, porque a regra concentra a confiança na 31.05.
- **A regra só vê pesos escritos no texto.** Grafias que `normalize_text` não reconhece, como
  "5k", não acionam a regra; isso é conservador.
- **A meta de 95% é medida no treino, fora da dobra.** Nos testes ela é só observada; com
  poucas linhas aceitas, o intervalo do acerto dos aceitos é largo.
