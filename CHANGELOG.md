# CHANGELOG

## [0.1.0] - 2026-09-24

### Fase 0 - Preparação
- Definida a versão alvo do Python: 3.12.10 (Windows 10 detectado; README pede 3.11+).
- Ambiente virtual `.venv` criado; versões fixadas e testadas no Python 3.12:
  `pygame 2.6.1`, `chess 1.11.2`, `pytest 9.1.1`, `pyinstaller 6.22.3`,
  `Pillow 12.3.0`, `ruff 0.16.8`.
- Estrutura de pastas da seção 7 do README criada (`src/xadtitans`, `assets`, `tests`, `tools`).
- `main.py`: janela 1024x768 "XadTitans", encerra com Esc ou X.
- `pytest.ini` e primeiro teste passando.

## [0.3.0] - 2026-09-24

### Fase 3 - Visual estilo Chess Titans
- Peças finais em sprite (12 PNGs próprios, gerados por `tools/gen_pieces.py`;
  registradas no `CREDITS.md` como CC0).
- Tabuleiro em perspectiva com moldura de madeira: `tools/gen_board.py` gera
  `assets/board/board_perspective.png` + `squares.json` (projeção pinhole real:
  centro, polígono e escala de cada casa).
- `ui/board_map.py`: geometria pura do tabuleiro (pixel→casa por polígono,
  flip por rotação de 180°, ordem de desenho trás→frente).
- `BoardView` em perspectiva: peças com escala por fileira, sombras, desenho
  back-to-front, brilho de seleção, ponto/anel de lances legais, destaque do
  último lance, pulso vermelho no rei em xeque, hover.
- `ui/animations.py`: tween + easing (linear, out-cubic, in-out-sine, out-back);
  deslize da peça (com interpolação de escala), esmaecimento na captura e
  bloqueio de entrada durante a animação. Roque anima rei e torre; en passant
  esmaece o peão capturado.
- `audio.py` + sons sintetizados (`tools/gen_sounds.py`): mover, capturar,
  xeque, fim de jogo, clique. Degradação graciosa sem mixer.
- Painel lateral (`ui/widgets/side_panel.py`): jogadas em SAN com rolagem
  (rodinha), peças capturadas por cor, status da partida.
- Cache completo de sprites escalados na inicialização.
- Contador de FPS (F3) e `tools/bench_fps.py`: ~400 FPS de renderização
  headless (meta: 30).
- Corrigido: `utils/resources.py` resolvia a raiz errada em desenvolvimento.
- 613 testes passando (173 novos da Fase 3); Ruff limpo.
