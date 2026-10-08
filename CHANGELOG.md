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

## [0.6.5] - 2026-10-04

### Fase 6.5 — Profiling de renderização e memória

- Nova ferramenta `tools/profile_render.py` (headless, sem intervenção
  manual, com diretório de dados isolado): cenários de menu, partida
  estática/seleção/hover+xeque/animação/fim de partida; FPS e frame
  time (média, p50, p95, máximo); atribuição de custo por componente
  do draw; cProfile de uma sessão completa; memória via tracemalloc +
  RSS; e teste de churn de cenas (criar/sair/recriar GameScene).
  Limitação documentada: driver de vídeo dummy (sem GPU/vsync) — os
  custos absolutos de blit diferem de hardware real, mas a atribuição
  relativa entre componentes é representativa.
- Baseline no commit `999f77d` (mesma ferramenta/configuração):
  partida estática 2,91 ms/344 FPS; com seleção 2,88 ms/347 FPS;
  hover+xeque 2,71 ms/368 FPS; animação 2,87 ms/348 FPS (máx 14,3 ms);
  fim de partida 6,03 ms/166 FPS (p95 7,5 ms); menu 0,47 ms. Meta de
  30 FPS (33,3 ms/quadro) atendida em todos os cenários. Sessão
  cProfile: 0,971 s, com `is_game_over()` → `outcome()` →
  `can_claim_threefold_repetition` do python-chess respondendo por
  34% do tempo (0,336 s; ~1,3 ms por chamada; ~1,5 chamadas por
  quadro durante toda a partida). Memória estável: sessão de 720
  frames ~0 MB de crescimento; churn de 30 ciclos de GameScene com
  delta de 0,4 KB/ciclo após o ciclo 5 (sem vazamento).
- Otimização 1 (comprovada pelo cProfile): cache de fim de partida em
  `core/game.py` — `is_game_over()` memoizado e invalidado em toda
  mutação (push/undo/reset/desistência/timeout/empate e substituição
  do tabuleiro via property). Valor retornado idêntico ao cálculo
  direto; API pública preservada.
- Otimização 2 (comprovada por frame time): `EndgameScene` criava o
  véu escurecido fullscreen (≈3 MB) e re-renderizava os 3 textos do
  resultado a cada quadro; agora véu e textos são estáticos por cena
  (véu por tamanho de tela).
- Depois (back-to-back, mesma ferramenta): partida estática
  2,20 ms/454 FPS (−24% de frame, +32% de FPS); com seleção
  2,41 ms/415 FPS (−16%); hover+xeque 2,04 ms/490 FPS (−25%);
  animação 2,27 ms/440 FPS (−21%; máx 14,3 → 7,5 ms); fim de
  partida 4,68 ms/214 FPS (−22%). Painel lateral (custo por
  componente): 1,03 → 0,28 ms por quadro (−74%). Sessão cProfile:
  0,971 → 0,533 s (−45%); chamadas de função 440 mil → 153 mil.
- Gargalos restantes (mantidos por não serem relevantes): blits/fill
  do full-redraw em C (~0,6 ms tabuleiro + ~0,8 ms peças — inerentes
  à arquitetura de redesenho completo) e ~0,2 ms de `font.render`
  (~10% do frame de partida, < 1% do orçamento de 33 ms).
- Memória após as otimizações: inalterada e estável (sessão longa e
  churn de cenas sem crescimento).
- Regressão: 996 testes passando; Ruff limpo; 10 partidas AI vs AI
  sem lances ilegais nem exceções (5–4, 1 empate); `tools/bench_fps.py`
  com 423 FPS (meta ≥ 30).

## [0.6.6] - 2026-10-08

### Fase 6.6 — Rede, testes manuais e correção de bugs

- Auditoria de rede completa: estática (grep de `requests`, `httpx`,
  `urllib`, `socket`, `websocket`, `aiohttp`, `subprocess`, URLs,
  telemetria/analytics/update-check em `src/`, `main.py` e `tools/`),
  de imports/dependências (`requirements.txt`: apenas `pygame` e
  `chess`) e de runtime (guarda de socket ativa durante toda a sessão
  de testes — 0 tentativas de conexão/DNS). O jogo permanece 100%
  offline; nenhuma correção de rede foi necessária.
- Nova ferramenta `tools/manual_checks.py`: harness que executa a
  **aplicação real** (App, cenas, eventos pygame, storage) em modo
  headless (SDL dummy, dados isolados em diretório temporário) e
  registra PASS/FAIL de 49 verificações das listas de testes manuais
  (regras, interface, IA, persistência, robustez + guarda de rede em
  runtime), com console UTF-8 (corrige `UnicodeEncodeError` do
  cp1252 no Windows).
- Nova ferramenta `tools/ai_vs_ai_10.py`: smoke E2E de 10 partidas
  AI vs AI headless com verificação de legalidade de todos os lances,
  exceções e timeouts (deadlock).
- Correções de bugs encontrados nos testes manuais:
  - **Volume órfão** (`audio.py`): `audio.volume = x` (usado por
    `App` e `SettingsScene`) era um atributo sem efeito — a
    configuração de volume não alterava nada e "volume 0" não
    silenciava. Adicionado `property volume` que espelha `_master`
    com clamp 0..1. Testes de regressão: `test_audio.py` (+3).
  - **Tabuleiro virado** (`board_view.py`): com o mapa flipped a
    fórmula de `_cell_w` invertia o sinal e o desenho de lances
    legais tentava criar `Surface` com resolução negativa
    (`pygame.error: Invalid resolution for Surface`), derrubando o
    App ao selecionar peça com o tabuleiro virado; além disso
    `_foot` assumia a ordem dos cantos do polígono e deslocava as
    peças para cima no mapa flipped. Corrigido com `abs()` na
    largura e comparação de y no ponto de apoio. Testes de
    regressão: `test_ui_perspective.py` (+3).
  - **Deadlock AI vs AI com `ai_vs_ai_delay=0.0`**
    (`ui/scenes/game_scene.py`): `_poll_ai` agendava
    `timer = delay`, mas `_update_ai_vs_ai_timer` retornava cedo em
    `timer <= 0.0` — com delay 0 a IA seguinte nunca era iniciada e a
    partida travava após o 1º lance (10/10 timeouts no smoke).
    Corrigido: com `delay <= 0` a próxima busca inicia
    imediatamente. Teste de regressão:
    `test_game_scene_modes.py` `test_aia_delay_zero_inicia_proxima_ia`.
- Testes manuais executados de verdade via harness da aplicação real:
  49/49 PASS (Regras 11/11, Interface 9/9, IA 10/10, Persistência
  7/7, Robustez 10/10, Rede 2/2). Limitações do ambiente registradas
  no CHECKLIST (sem display: destaques/alinamento verificados por
  estado geométrico; sem áudio audível; janela não redimensionável e
  sem fullscreen — recurso não implementado, marcado N/A; PGN
  validado com python-chess, sem programa de xadrez GUI disponível).
- IA: os quatro níveis responderam dentro dos limites nominais
  (INICIANTE ~0 s, FÁCIL 0,67 s, MÉDIO 3,00 s, DIFÍCIL 14,89 s) com
  lances legais e sem congelar a janela; cancelamentos (undo, novo
  jogo, fecho) seguros; Difícil preservou a dama em posição simples.
- 10 partidas AI vs AI (após a correção): 0 lances ilegais, 0
  exceções, 0 deadlocks; resultados plausíveis (xeques-mates e
  triplas repetições).
- Regressão: 1003 testes passando (996 da Fase 6.4/6.5 + 6 de
  regressão dos bugs corrigidos + 1 do deadlock); Ruff limpo.
- Pendente para a Fase 6.7 (não executado aqui): teste no PC alvo,
  com o PC fraco em uso normal; conferência visual/audível real.

## [0.6.7] - 2026-10-08

### Fase 6.7 — Validação no PC alvo e fechamento da Fase 6

- Teste manual no PC real (executado pelo usuário): partida completa
  jogada no XadTitans — abertura, tabuleiro, movimentos e IA
  funcionando; sem travamentos, crashes ou problemas durante a
  partida. Resultado: PASS.
- Regressão final antes do fechamento: suíte completa passando,
  Ruff limpo, `git diff --check` sem erros.
- Fase 6 (Qualidade e desempenho) oficialmente concluída. Itens
  ainda pendentes de validação em ambiente real (áudio audível,
  PGN em programa de xadrez de terceiros) seguem documentados no
  CHECKLIST como limitações do ambiente de CI; o jogo em uso real
  foi validado no PC alvo.

## [1.0.0-dev] - 2026-10-08

### Fase 7.2 — Empacotamento Windows (onedir, windowed)

- Ícone `assets/icons/xadtitans.ico` gerado por `tools/gen_icon.py`
  a partir do sprite próprio CC0 do rei branco (recorte por bounding
  box do alfa + centralização em tela 256×256); 7 resoluções
  (16/24/32/48/64/128/256 px, 32-bit com alfa); sem arte de
  terceiros e sem dependência nova (Pillow já era requisito de dev).
- Versão centralizada: `xadtitans.__version__ = "1.0.0"` é a única
  fonte de verdade — menu (rótulo discreto `v1.0.0` no canto
  inferior esquerdo via `menu_scene.version_label()`), version-file
  e metadados do executável derivam do mesmo valor.
- `tools/build_exe.py`: build reproduzível com o PyInstaller do
  `.venv` (nunca o global do PATH); argumentos fixos documentados —
  onedir, windowed, sem UPX, `--paths src`, `--add-data assets;assets`,
  `--icon`, exclusões de `tests`/`pytest`; version-file gerado de
  `__version__` em `build/` (gitignored) com validação round-trip pelo
  parser real do PyInstaller; pós-validação obrigatória dos assets no
  pacote (inclusive a visão preta `board_perspective_black.png` +
  `squares_black.json`).
- Correção de robustez para `--windowed`: `main.py` ganhou
  `_ensure_streams()` — no modo windowed o PyInstaller define
  `sys.stdout/stderr = None`, o que quebraria `print(file=sys.stderr)`
  no handler de erro fatal e o `StreamHandler` do logger; agora os
  streams ausentes são apontados para `os.devnull` antes de qualquer
  import que possa logar.
- Primeiro pacote gerado e validado nesta máquina: `dist/XadTitans`
  (33.6 MB), recursos RT_ICON/RT_GROUP_ICON/RT_VERSION presentes,
  version resource com `1.0.0.0` e string table correta; exe inicia o
  App completo (Settings → janela → áudio → menu → loop) e roda sem
  erro por 10 s com SDL dummy e diretório de dados isolado. O teste em
  máquina sem Python, autosave/log reais e antivírus ficam para a
  Fase 7.3; zip + hash para a 7.4.
- Testes: +11 (`tests/test_packaging.py` — ícone multiresolução,
  versão 1.0.0/label do menu, argumentos do build, version-file
  determinístico, guarda de streams). 1021 testes passando; Ruff limpo.
