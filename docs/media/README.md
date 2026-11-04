# Material de divulgação

Capturas do site publicado (https://amanda-gondra.github.io/ncm-classifier/) chamando a API real
na Render, tiradas em 2026-11-04 com o modelo `v0.1.0`. Nenhum resultado foi editado ou simulado.

| Arquivo | O que mostra | Tamanho |
|---|---|---|
| `home-desktop.png` | primeira tela no computador (1280×800, escala 2×) | 2560×1600 |
| `home-result-desktop.png` | a mesma tela depois de classificar "Adubo NPK 20-05-20 saco 50kg" em "Experimente agora" | 2560×1600 |
| `home-mobile.png` | primeira tela no celular (390×844, escala 3×) | 1170×2532 |
| `result-mobile.png` | resultado da mesma classificação no celular | 1170×2532 |
| `demo-desktop.png` | seção de demonstração completa, com o resultado | seção inteira, 2× |
| `demo.gif` | fluxo: primeira tela, digitação em "Experimente agora" e resultado | 960 px de largura |

A imagem que aparece quando o link é compartilhado não está aqui: ela é gerada no build do site
e servida em https://amanda-gondra.github.io/ncm-classifier/og-image.png.

## Como gerar de novo

```bash
cd web
node scripts/capture-media.mjs          # capturas e quadros do GIF, a partir do site publicado
node scripts/check-layout.mjs           # confere rolagem horizontal, seções e imagens de compartilhamento
cd ..
python scripts/build_demo_gif.py        # monta demo.gif e apaga os quadros
```

Antes de capturar, rode o workflow **API health** à mão, para a API já estar acordada.
