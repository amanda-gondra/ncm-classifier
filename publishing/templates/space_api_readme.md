---
title: NCM Classifier API
emoji: 🌾
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Sugestão de posições NCM para produtos do agro (API REST)
models:
  - $model_repo
---

# NCM Classifier API

API REST que sugere as **três posições NCM mais prováveis** (4 dígitos) para descrições
comerciais de produtos agropecuários. Ela serve o modelo
[`$model_repo`](https://huggingface.co/$model_repo) na versão fixa **$model_revision**.

> **Aviso.** As respostas são sugestões, não decisões fiscais. A responsabilidade pela
> classificação fiscal permanece com quem emite a nota.

- **Documentação interativa:** [`/docs`](./docs) · [`/redoc`](./redoc)
- **Rotas:** `POST /v1/predictions` · `GET /v1/model` · `GET /health`
- **Código:** [$github]($github), commit `$commit`

```bash
curl -X POST https://$host/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"description": "Ureia agrícola, pacote 1 kg"}'
```

**Limites por pedido:**
- até $max_text_length caracteres por descrição;
- até $max_batch_size descrições;
- até $rate_limit pedidos por minuto às rotas `/v1/`.

Este Space roda no plano gratuito de CPU. Ele pode hibernar quando fica sem uso, e a primeira
requisição depois disso demora alguns segundos.
