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

## [0.6.4] - 2026-10-04

### Fase 6.4 — Profiling da IA, otimização incremental e `_TIME_LIMIT` real

- Nova ferramenta `tools/profile_ai.py` (cProfile): posições
  representativas, gargalos por tempo cumulativo, NPS, profundidade e
  avaliação isolada; modos `--depths`, `--save` e `--compare`.
- Baseline medida no commit `4154e98`: NPS 240–3000 conforme a posição;
  avaliação 725,4 μs/chamada; no cProfile combinado (5 posições, d3)
  `evaluate()` respondia por ~93% do tempo de busca, e
  `can_claim_threefold_repetition` sozinho custava ~35% (laço de
  "trêsfold jogável no próximo lance" com push + zobrist por lance
  legal, executado em CADA avaliação com pilha de lances não vazia).
- Otimizações incrementais — TODAS com avaliação bit a bit idêntica
  (guarda em `tests/eval_equivalence.json` + teste de equivalência):
  - terminal (mate/afogado) detectado pela própria mobilidade:
    2 gerações de lances legais por avaliação em vez de 4;
  - `_pawn_structure` calculada uma vez (era chamada 2×);
  - janelas de peão passado e escudo do rei em máscaras
    pré-calculadas (substituem laços `piece_at` + `chess.Piece`);
  - laço de material/PST via `piece_map()` com contagem de bispos na
    mesma passada;
  - `_king_safety` reutiliza a fase já calculada;
  - cache de mobilidade por chave de transposição (~20–33% de posições
    repetidas na árvore; valores determinísticos; `clear_caches()`
    para benchmarks);
  - repetição: `is_repetition(3)` no lugar de
    `can_claim_threefold_repetition` — mantém "posição já repetida
    3× → 0"; descarta apenas a extensão "trêsfold alcançável jogando
    um lance" (cara e rara). Nuance documentada; testes de empate
    preservados.
- Busca: `iterative_deepening(..., time_limit=)` implementado de fato —
  deadline com `time.monotonic`, checagem a cada nó (negamax +
  quiescence) via exceção `_TimeLimitReached` que aborta a iteração
  parcial SEM poluir a TT; retorna o melhor resultado COMPLETO da
  última iteração concluída dentro do limite; fallback legal
  documentado (primeiro lance legal, profundidade 0) se nenhuma
  iteração couber no tempo; profundidade retornada = iterações
  realmente concluídas (corrige a imprecisão de sempre devolver
  `max_depth`); tabuleiro restaurado após aborto.
- `AIWorker` agora passa `self._time_limit` para a busca
  (0,5 s / 2 s / 5 s / 15 s por nível). `stop_event`, geração,
  request/poll/wait, cancelamento e fallback de exceção preservados.
- Benchmark antes → depois (mesmas posições e profundidades,
  `tools/bench_ai.py`): NPS inicial d3 1186 → 3893; Siciliana d3
  1110 → 3375; final de torres d3 2761 → 8547; ataque ao rei d3
  266 → 894 (≈ 3,1–3,8× em todas as posições); ataque ao rei d5
  157,9 s → 48,6 s; Siciliana d5 36,0 s → 9,8 s; avaliação bruta
  725,4 → 200,8 μs/chamada; cProfile combinado 358,2 s → 103,8 s
  (3,45×). A contagem de nós é idêntica à baseline em todas as
  posições: a árvore de busca foi preservada.
- Comportamento com limite real por nível (teste de duração com folga
  generosa): INICIANTE ~0,5 s, FÁCIL ~2 s, MÉDIO ~5 s, DIFÍCIL ~15 s.
  Overshoot medido ≈ 0 para um limite de 0,5 s (teto teórico: ~15 ms
  de granularidade do `monotonic` no Windows + custo de um nó).
- Testes: +15 (time_limit por nível, mecanismo com relógio controlado
  determinístico, fallback, profundidade reportada, stop_event, mate
  com tempo suficiente, determinismo com seed, equivalência da
  avaliação à baseline). 996 testes passando; Ruff limpo; 10 partidas
  AI vs AI sem lances ilegais nem exceções (4–4, 2 empates).
