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

## [0.4.0] - 2026-09-24

### Fase 4 - Inteligência artificial
- `ai/evaluation.py`: avaliação posicional com tabelas piece-square
  (meio-jogo + final), tapered eval, mobilidade, par de bispos,
  estrutura de peões (dobrados, isolados, passados), segurança do rei.
- `ai/search.py`: negamax com poda alfa-beta, quiescence search,
  iterative deepening, tabela de transposição (python-chess
  `_transposition_key`), ordenação MVV-LVA + killers + history,
  mate distance pruning, extensão de xeque.
- `ai/worker.py`: `AIWorker` em thread daemon com `request()`,
  `poll()`, `cancel()`, `wait()`, `busy`. 4 níveis de dificuldade
  (Inicinante d2/0.5s, Fácil d3/2s, Médio d4/5s, Difícil d6/15s).
  Aleatoriedade controlada com seed para níveis baixos.
- Integração com `GameScene`: IA joga automaticamente no turno
  designado, indicador "Pensando...", undo desfaz par de lances
  (humano+IA), flip e resign funcionam com IA ativa.
- `tools/bench_ai.py`: benchmark headless (~1000-3000 NPS, eval 670μs).
- 17 categorias de testes da IA (avaliação, TT, mate, legalidade,
  promoção, roque, en passant, empate, cancelamento, determinismo,
  10 partidas AI vs AI headless).
- 643 testes passando (402 originais + 173 novos das Fases 2-4);
  Ruff limpo.
