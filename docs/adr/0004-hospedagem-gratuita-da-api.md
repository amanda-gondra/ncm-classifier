# ADR 0004 — Hospedagem gratuita da API e da demonstração

- **Data:** 2026-11-03
- **Status:** aceita
- **Substitui:** o item 5 da ADR 0001 (demo no Hugging Face Spaces com Gradio)

## Contexto

A ADR 0001 previa a demonstração num Space Gradio gratuito. Ao criar um Space Docker para a API,
o Hugging Face recusou o pedido com `402 Payment Required` e esta mensagem:

> Static Spaces are free for everyone, but hosting Gradio and Docker Spaces on free cpu-basic
> requires a PRO subscription.

Nada foi criado nem cobrado. O projeto tem a restrição de custo zero.

## Decisão

1. **API: serviço web gratuito na Render, construído a partir do mesmo `Dockerfile`**
   (`render.yaml` na raiz do repositório).
   - A Render informa que o plano gratuito não exige cartão de crédito.
   - O serviço gratuito tem 512 MB de RAM e CPU compartilhada, e dorme depois de 15 minutos
     sem uso.
   - O deploy é sempre manual (`autoDeployTrigger: off`).
2. **Interface da etapa 9:** página estática, que continua gratuita no Hugging Face (Static
   Space) ou no GitHub Pages, chamando a API da Render. A origem dessa página entra em
   `ALLOWED_ORIGINS`.
3. **O modelo e o dataset continuam no Hugging Face Hub,** porque repositórios de modelo e de
   dataset não são afetados.

## Consequências

- **Primeira requisição lenta:** depois de um período sem uso, a primeira chamada leva perto de
  um minuto para acordar o serviço. A interface precisa mostrar isso ao usuário.
- **Memória:** a API ocupa bem menos que 512 MB (cerca de 100 MB para o modelo e as bibliotecas).
  A imagem tem 673 MB em disco.
- **A conta na Render é da Amanda,** criada por ela, de preferência entrando com o GitHub. Nenhum
  segredo é necessário, porque o modelo é público.
- **Verificação depois de cada deploy:** `scripts/verify_deployment.py --url <endereço>`.
- **Planos gratuitos mudam.** As condições acima foram conferidas em 2026-11-03 e podem mudar
  sem aviso.
