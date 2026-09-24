# CREDITS

Créditos e licenças dos assets (imagens, sons, fontes, ícones) usados no XadTitans.

| Asset | Fonte | Licença |
|---|---|---|
| Peças (12 sprites PNG, 256px) | Próprias — geradas proceduralmente por `tools/gen_pieces.py` (Pillow) | CC0 / domínio do projeto |
| Tabuleiro em perspectiva (`board_perspective.png`, `squares.json`) | Próprio — gerado por `tools/gen_board.py` (Pillow, projeção pinhole) | CC0 / domínio do projeto |
| Sons (`assets/sounds/*.wav`) | Próprios — sintetizados por `tools/gen_sounds.py` (osciladores + ruído) | CC0 / domínio do projeto |
| Fontes do sistema (Arial, Segoe UI) | Microsoft Windows | Incluídas no sistema operacional |

> **Nota:** todos os assets visuais e sonoros são gerados por código no
> repositório (`tools/`), sem depender de arquivos de terceiros — a
> regeneração é determinística e a licença é irrestrita. As peças
> Unicode da Fase 1/2 foram substituídas por sprites próprios na
> Fase 3.

Bibliotecas:

| Biblioteca | Licença |
|---|---|
| pygame | LGPL-2.1 (pygame-ce) / LGPL |
| python-chess (chess) | GPL-3.0-or-later |
| Pillow (só ferramentas de build) | HPND / MIT-CMU |
