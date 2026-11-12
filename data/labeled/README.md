# Dados rotulados

| Arquivo | O que é | Uso |
|---|---|---|
| `test_v1.csv` | Descrições reais, congeladas com checksum | Só avaliação |
| `test_v2.csv` | Descrições reais de fontes novas, coletadas depois dos sintéticos e congeladas com checksum | Só avaliação |
| `train_real_v1.csv` | Descrições reais de páginas que nunca alimentaram os testes | Treino |
| `train_synthetic_v1.csv` | Descrições escritas por um LLM (Claude Opus 5.5), marcadas como `synthetic` | Treino, decidido por experimento |

As linhas de treino só são usadas depois que uma pessoa marca `reviewed` como `true`. As
descrições oficiais da tabela NCM são uma terceira fonte de treino, montada a partir da tabela por
`scripts/build_train_set.py`, por isso não ficam guardadas aqui.

As linhas sintéticas imitam o jeito como os produtos aparecem em anúncios e licitações (abreviações,
maiúsculas, falta de acentos). Elas incluem de propósito adubos em embalagens pequenas, para ensinar
a regra 31.05. Se elas ajudam é medido, não suposto: o modelo é treinado com e sem elas, e os dois
resultados são publicados.

## Testes congelados (`test_v1.csv` e `test_v2.csv`)

Descrições reais de produtos, copiadas sem alteração de fontes públicas e usadas **só para
avaliação**. O modelo nunca treina com essas linhas, e o SHA-256 de cada arquivo (`.sha256`) é
conferido antes de qualquer leitura. O `test_v1` cobre todas as posições do escopo; o `test_v2` foi
coletado depois, em fontes novas, para medir sem viés o efeito dos sintéticos, que foram escritos
depois de ver o `test_v1`.

| Coluna | Significado |
|---|---|
| `id` | Identificador estável. Um id nunca é reaproveitado nem renumerado. |
| `text` | Descrição exatamente como a fonte publicou. |
| `position` | Classe-alvo: posição NCM/SH (4 dígitos). |
| `source_type` | `public_procurement` (licitação pública) ou `marketplace` (loja ou anúncio). |
| `source_url` | Página onde o texto foi encontrado. |
| `label_rule` | Por que o texto pertence à posição (o texto da posição ou a nota legal aplicada). |
| `reviewed` | `true` depois que uma pessoa conferiu o texto, a fonte e o rótulo. |

Os arquivos de treino têm as mesmas colunas.

### O que a fonte prova, e o que não prova

A fonte prova que a descrição existe no mundo real. Ela **não** prova a classificação fiscal. O
rótulo vem do texto da posição na NCM e das notas legais (Regra Geral 1), está escrito em
`label_rule` e é conferido por uma pessoa.

### Alcance de um rótulo "correto"

Os rótulos são validados só no nível da **posição de 4 dígitos**. Eles não validam o código NCM
completo de 8 dígitos, e este projeto é uma ferramenta de apoio à decisão, não um parecer fiscal.

### Convenções de rotulagem

- **O texto fica como foi publicado**, com erros de digitação (por exemplo, a `t055` diz "barro"
  quando quer dizer "barra"). Descrições reais têm erros, e o modelo precisa lidar com eles.
- **Embalagem de adubo:** quando o texto não informa a embalagem, o produto é tratado como vendido a
  granel ou em embalagens acima de 10 kg, e fica na posição do próprio adubo. Só vão para a 31.05
  os textos que informam peso bruto de até 10 kg.
- **"Sal mineral" e suplementos:** no mercado brasileiro, o termo designa uma mistura de sal e
  minerais preparada para alimentação animal, por isso vai para a 23.09. Sal comum vendido para
  gado, sem minerais acrescentados no texto, vai para a 25.01.

### Fontes

Os textos foram coletados em outubro de 2026. Muitos endereços de marketplace são páginas de
resultados de busca, que mudam com o tempo; o texto do arquivo é a versão que foi revisada. Para
linhas novas, páginas de produto têm preferência.

### Direitos e redistribuição

- Os textos `marketplace` (Mercado Livre, MF Rural, Magazine Luiza e outras lojas) e
  `public_procurement` pertencem aos seus autores ou publicadores. Eles ficam aqui só para que os
  experimentos possam ser reproduzidos e auditados, com o endereço de cada fonte, para estudo e
  pesquisa. Eles não estão cobertos pela licença MIT deste repositório.
- Eles **não** fazem parte do dataset publicado no Hugging Face Hub, que tem só os textos oficiais
  da NCM e as linhas sintéticas (veja `docs/adr/0003-escolha-do-modelo.md` e o cartão do dataset).
- Quem tiver direitos sobre um texto pode pedir a remoção abrindo uma issue; o texto sai dos
  arquivos e os resultados afetados são recalculados.

### Lacunas conhecidas

- A `t039` foi removida: o rótulo dependia de um contexto que não está no texto.
- Descrições cuja posição depende de fatos que o texto não traz, e que nenhuma convenção acima
  resolve, ficam fora do conjunto.
