# API do NCM Classifier

API REST (FastAPI) que serve o modelo publicado
[`AmandaGondra/ncm-classifier`](https://huggingface.co/AmandaGondra/ncm-classifier) na versão
fixa `v0.1.0`.

> **Aviso.** As respostas são sugestões, não decisões fiscais. A responsabilidade pela
> classificação fiscal permanece com quem emite a nota.

## Endpoints

| Método e rota | Para quê | Respostas |
|---|---|---|
| `POST /v1/predictions` | até 3 posições NCM por descrição, para uma descrição ou um lote | 200, 400, 413, 422, 429, 500, 503 |
| `GET /health` | estado da API e do modelo | 200 pronto · 503 carregando ou indisponível |
| `GET /v1/model` | versão, escopo, métricas publicadas, calibração, regra 31.05 e aviso fiscal | 200, 503 |
| `GET /docs`, `/redoc`, `/openapi.json` | documentação interativa e o esquema OpenAPI | 200 |

O código classifica a **posição** NCM (4 dígitos, campo `level: "position"`). A API não inventa
os 8 dígitos do subitem.

### Exemplo

```bash
curl -X POST http://localhost:7860/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"description": "Ureia agrícola, pacote 1 kg"}'
```

Cada resultado traz:
- `predictions`: posição, descrição oficial, ordem e confiança calibrada;
- `requires_manual_review`;
- `rule_3105_applied`;
- `applied_rule`.

Toda resposta traz o cabeçalho `X-Request-ID`.

## Como uma requisição é tratada

1. **CORS:** só as origens de `ALLOWED_ORIGINS` recebem cabeçalhos de CORS. Por padrão, nenhuma
   recebe.
2. **Contexto:** a requisição ganha um `request_id`. Uma linha de log registra rota, status e
   tempo.
3. **Limite de pedidos:** acima de `RATE_LIMIT_PER_MINUTE` pedidos por cliente e por minuto
   (padrão 120) às rotas `/v1/`, a resposta é 429 com `Retry-After`. O `/health` e a
   documentação não entram no limite.
   - Os contadores ficam na memória do processo e são limpos a cada minuto.
   - O cliente é identificado pelo endereço da conexão. Atrás de um proxy, como num Space, esse
     endereço é o do proxy, e o limite passa a valer para a API inteira.
   - Cabeçalhos de encaminhamento (`X-Forwarded-For`) não são usados, porque o cliente poderia
     forjá-los para escapar do limite.
4. **Limite de corpo:** acima de `MAX_REQUEST_BODY_BYTES`, a resposta é 413. O limite vale tanto
   para o tamanho declarado quanto para os bytes de fato recebidos.
5. **Validação (Pydantic):** exatamente um entre `description` e `descriptions`; sem texto vazio;
   textos e lote dentro dos limites. Fora disso, a resposta é 422 e o modelo não chega a ser
   chamado.
6. **Serviço:** se o modelo não estiver pronto, a resposta é 503. Se estiver, os textos vão
   intactos para o `NcmPredictor`, que aplica normalização, probabilidades, temperatura, regra
   31.05, top-3 e marca de revisão.
7. **Resposta:** a rota só renomeia os campos e acrescenta a descrição oficial de cada posição
   (`src/ncm_classifier/data/positions.json`, gerado da tabela NCM por
   `scripts/build_positions.py`).

O modelo é carregado **uma vez**, em segundo plano, quando a API sobe (`lifespan.py`). Enquanto
isso, o `/health` responde 503 com `"starting"`. Se a carga falhar, responde 503 com
`"unavailable"`, e o motivo fica só no log do servidor.

## Rodar localmente

```bash
pip install -e ".[api]"     # núcleo de inferência + API (sem pandas nem PyTorch)
uvicorn ncm_classifier.api.main:create_app --factory --port 8000
# http://localhost:8000/docs
```

Com Docker:

```bash
docker build -t ncm-classifier-api .
docker run --rm -p 7860:7860 ncm-classifier-api
# http://localhost:7860/docs
```

As configurações vêm de variáveis de ambiente; veja `.env.example`.

## Testes

```bash
pytest --cov                              # unitários e de integração com mocks, sem rede
NCM_RUN_HUB_TESTS=1 pytest -m hub         # modelo real do Hub, comparado com a avaliação
```

No GitHub Actions:
- **a cada push**, rodam lint, formatação, mypy e os testes com cobertura (mínimo de 90% na API);
- **ao disparar à mão o workflow** (*Run workflow*), rodam também o teste com o Hub e o build e
  teste da imagem Docker.

## Implantação gratuita na Render

**No ar em https://ncm-classifier-api.onrender.com** ([documentação](https://ncm-classifier-api.onrender.com/docs)).
O primeiro deploy, de 2026-11-03, a partir do commit `0370383`, foi verificado com
`verify_deployment.py`: a API publicada reproduziu o top-1 e a regra 31.05 da avaliação nas 146
linhas do test_v1.

Os Spaces Docker e Gradio do Hugging Face passaram a exigir o plano PRO (ADR 0004). A API roda
num serviço web gratuito da Render, construído a partir do mesmo `Dockerfile`, conforme
`render.yaml`.

**Primeira vez (feito pela dona da conta):**
1. Crie a conta em render.com entrando com o GitHub.
2. Clique em **New → Blueprint** e escolha o repositório `amanda-gondra/ncm-classifier`.
3. Clique em **Apply**. A Render constrói a imagem e publica o serviço `ncm-classifier-api`.

**Novos deploys** são sempre manuais: no painel do serviço, **Manual Deploy → Deploy latest
commit**.

**Depois de cada deploy:**

```bash
python scripts/verify_deployment.py --url https://<serviço>.onrender.com
```

**O que esperar do plano gratuito:**
- 512 MB de RAM e CPU compartilhada. A API usa cerca de 100 MB.
- O serviço dorme depois de 15 minutos sem uso. A primeira requisição depois disso leva perto
  de um minuto.
- Nenhum segredo é necessário, porque o modelo é público. A origem da interface da etapa 9 vai
  em `ALLOWED_ORIGINS`, no painel da Render.
- O plano gratuito não garante disponibilidade, e as condições podem mudar.
