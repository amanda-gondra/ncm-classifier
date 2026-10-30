# Labeled data

## `test_v1.csv` — frozen test set

Real product descriptions copied verbatim from public sources, used **only for evaluation**.
The model never trains on these rows.

| Column | Meaning |
|---|---|
| `id` | Stable identifier. Ids are never reused or renumbered. |
| `text` | Description exactly as published by the source. |
| `position` | Target class: NCM/HS position (4 digits). |
| `source_type` | `public_procurement` or `marketplace`. |
| `source_url` | Page where the text was found. |
| `label_rule` | Why the text belongs to the position (the heading text or legal note applied). |
| `reviewed` | `true` once a human has checked the text, the source and the label. |

### What the source proves, and what it does not

The source proves that the description exists in the real world. It does **not** prove the
fiscal classification. The label comes from the heading text of the NCM and its legal notes
(General Rule 1), written in `label_rule`, and is checked by a human reviewer.

### Scope of a "correct" label

Labels are validated at the **4-digit position** level only. They are not a validation of the
full 8-digit NCM code, and this project is a decision-support tool, not a fiscal opinion.

### Labeling conventions

- **Text is kept verbatim**, typos included (for example, `t055` says "barro" where it means
  "barra"). Real descriptions contain errors, and the model must handle them.
- **Fertilizer package size:** when the text does not state the package, the product is read as
  sold in bulk or in packages above 10 kg, and keeps the position of the fertilizer itself.
  Only texts that state a gross weight of 10 kg or less go to 31.05.
- **"Sal mineral" and supplements:** in the Brazilian market the term names a mixture of salt
  and minerals prepared for animal feed, so it goes to 23.09. Plain salt sold for cattle, with
  no added minerals in the text, goes to 25.01.

### Sources

Texts were collected in October 2026. Many marketplace URLs are search-result pages, which change
over time; the text in the file is the snapshot that was reviewed. Product pages are preferred
for new rows.

### Known gaps

- `t039` was removed: its label depended on context that is not in the text.
- Descriptions whose position depends on facts the text does not give, and that no convention
  above settles, are kept out of the set.
