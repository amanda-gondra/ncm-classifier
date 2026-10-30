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

### Known gaps

- `t039` was removed: its label depended on context that is not in the text.
- Descriptions that are ambiguous on purpose are kept out of the set. Examples: products whose
  position depends on composition the text does not state, or on the size of the package when
  the text omits it.
