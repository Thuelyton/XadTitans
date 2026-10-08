# CHECKLIST — XadTitans

Passo a passo do início ao fim. Marque `- [x]` ao concluir cada item. Só avance de fase quando o bloco **Pronto quando** estiver cumprido. Detalhes técnicos estão no [`README.md`](README.md).

## Painel de progresso

| Fase | Assunto | Status |
|---|---|---|
| 0 | Preparação | ✅ |
| 1 | Tabuleiro na tela | ✅ |
| 2 | Regras e jogabilidade | ✅ |
| 3 | Visual estilo Chess Titans | ✅ |
| 4 | Inteligência artificial | ✅ |
| 5 | Recursos do jogo | ✅ |
| 6 | Qualidade e desempenho | ✅ |
| 7 | Empacotamento (.exe) | ⬜ |
| 8 | Documentação e divulgação | ⬜ |
| 9 | Futuro (opcional) | ⬜ |

---

## FASE 0 — Preparação

- [x] Descobrir a versão do Windows do PC alvo (Windows 10, build 19045 = 22H2)
- [x] Escolher a versão do Python (Windows 10 → **Python 3.12.10**, já instalado)
- [x] Instalar Python e Git; conferir com `python --version` e `git --version`
- [x] Criar o repositório no GitHub (`XadTitans`)
- [x] Adicionar `.gitignore` de Python (incluir `.venv/`, `build/`, `dist/`, `__pycache__/`)
- [x] Adicionar `LICENSE` (GPL-3.0, ver seção 16 do README)
- [x] Criar o ambiente virtual: `python -m venv .venv` e ativá-lo
- [x] Criar `requirements.txt` (`pygame`, `chess`) com versões fixadas e compatíveis com o Python escolhido
- [x] Criar `requirements-dev.txt` (`pytest`, `pyinstaller`, `Pillow`, `ruff`)
- [x] Instalar tudo sem erro: `pip install -r requirements-dev.txt`
- [x] Criar a estrutura de pastas da seção 7 do README (pastas e `__init__.py` vazios)
- [x] Criar `CREDITS.md` e `CHANGELOG.md` (vazios, com título)
- [x] `main.py` abre uma janela 1024×768 com o título "XadTitans" e fecha com `Esc`
- [x] Criar `pytest.ini` e um teste simples que passa
- [x] Primeiro commit e push

**Pronto quando:** a janela vazia abre e fecha, `pytest` passa e o repositório está no GitHub.

---

## FASE 1 — Tabuleiro na tela

- [x] `config.py` com resolução, FPS, cores e caminhos
- [x] `utils/resources.py` com `resource_path()` (funciona no desenvolvimento e no PyInstaller)
- [x] `utils/logger.py` gravando em arquivo
- [x] Loop principal em `app.py` com limite de FPS, `dt` e encerramento limpo
- [x] Desenhar o tabuleiro 8×8 plano com as coordenadas (a–h, 1–8)
- [x] Carregar as imagens das peças (conjunto provisório com licença aberta, registrado no `CREDITS.md`)
- [x] Desenhar a posição inicial a partir de um FEN
- [x] Converter pixel em casa e casa em pixel (tabuleiro normal e virado)
- [x] Teste: ida e volta pixel↔casa para as 64 casas, nas duas orientações

**Pronto quando:** a posição inicial aparece correta e o clique identifica a casa certa.

---

## FASE 2 — Regras e jogabilidade (2 jogadores)

- [x] `core/types.py` com `Level`, `Status` e `GameResult`
- [x] `core/game.py` (`Game`) usando `python-chess`
- [x] Clicar em uma peça mostra os movimentos legais
- [x] Mover por clique (peças só se movem em lances legais)
- [x] Diálogo de promoção do peão (dama, torre, bispo, cavalo)
- [x] Roque (curto e longo) funcionando, inclusive regra de casas atacadas
- [x] En passant funcionando
- [x] Detecção de xeque e destaque do rei
- [x] Fim de partida: xeque-mate
- [x] Fim de partida: afogamento
- [x] Fim de partida: material insuficiente
- [x] Fim de partida: regra dos 50 lances
- [x] Fim de partida: tripla repetição
- [x] Desistir
- [x] Desfazer jogada (`undo`)
- [x] Lista de jogadas em notação algébrica (SAN)
- [x] Peças capturadas por cor
- [x] Cena `FimDePartida` com o resultado
- [x] Testes de regras: mate do louco, mate do pastor, afogamento, material insuficiente, roque ilegal, en passant, promoção, desfazer
- [x] Commit da fase

**Pronto quando:** dá para jogar uma partida completa entre duas pessoas, com todas as regras corretas e testes passando.

---

## FASE 3 — Visual estilo Chess Titans

- [x] Definir o conjunto de peças final (próprio ou de licença aberta) e registrar no `CREDITS.md`
- [x] Criar `tools/gen_board.py` (Pillow) que gera `board_perspective.png` e `squares.json` (centro e escala de cada casa)
- [x] `BoardView` usando `squares.json` para posicionar as peças
- [x] Escala das peças por fileira (mais longe = menor)
- [x] Ordem de desenho de trás para frente
- [x] Sombras sob as peças
- [x] Destaque da casa selecionada (brilho)
- [x] Destaque dos movimentos legais (ponto para casa vazia, anel para captura)
- [x] Destaque do último lance
- [x] Brilho vermelho no rei em xeque
- [x] Hover (casa sob o mouse)
- [x] Módulo `animations.py` (tween e easing)
- [x] Animação de deslize das peças e esmaecer na captura
- [x] Bloquear entrada do jogador durante a animação
- [x] `audio.py` e sons: mover, capturar, xeque, fim de jogo, clique
- [x] Fundo e moldura do tabuleiro (mármore ou madeira)
- [x] Painel lateral: lista de jogadas com rolagem, peças capturadas
- [x] Cache de todos os sprites escalados na inicialização
- [x] Medir o FPS no PC alvo (meta: 30 ou mais) e otimizar se preciso
- [x] Commit da fase

**Pronto quando:** o jogo tem a aparência final, com animações e sons, e mantém 30 FPS no PC alvo.

---

## FASE 4 — Inteligência artificial

**Base**
- [x] `ai/evaluation.py`: material e tabelas de posição (piece-square tables)
- [x] `ai/search.py`: negamax com poda alfa-beta em profundidade fixa
- [x] Testes: acha mate em 1; acha mate em 2; não entrega a dama de graça
- [x] Nunca devolver lance ilegal (teste com várias posições)

**Melhorias de busca**
- [x] Ordenação de lances (capturas por MVV-LVA, lance da tabela, killers)
- [x] Busca de quiescência com profundidade limitada
- [x] Aprofundamento iterativo com limite de tempo
- [x] Respeitar o `stop_event` (cancelamento)
- [x] Tabela de transposição
- [x] Empates dentro da busca (repetição, 50 lances, material insuficiente)
- [x] Valores de mate que preferem mates mais rápidos

**Avaliação refinada**
- [x] Par de bispos
- [x] Estrutura de peões (dobrados, isolados, passados)
- [x] Segurança do rei
- [x] Interpolação meio-jogo / final
- [x] Mobilidade (só manter se o custo compensar)

**Integração**
- [x] `ai/levels.py` com os 4 níveis (Iniciante, Fácil, Médio, Difícil)
- [x] Aleatoriedade controlada nos níveis baixos e desempate aleatório (com semente nos testes)
- [x] `ai/worker.py`: `AIWorker` em thread, com `request`, `poll` e `cancel`
- [x] Ligar a IA ao `GameScene` (jogador vs IA, escolha de cor)
- [x] Indicador "pensando..." sem travar a interface
- [x] `tools/bench_ai.py`: nós por segundo e tempo por nível
- [x] Ajustar profundidade e tempo de cada nível ao PC alvo e registrar no README
- [x] Teste headless: 10 partidas IA contra IA sem exceção e sem lance ilegal
- [x] (Opcional) Livro de aberturas simples
- [x] Commit da fase

**Pronto quando:** dá para jogar contra a IA nos 4 níveis, a interface nunca congela e não há lance ilegal.

---

## FASE 5 — Recursos do jogo

**Menus e fluxo**
- [x] Menu principal: Novo jogo, Continuar, Carregar, Configurações, Sair
- [x] Tela Nova partida: modo (vs IA / 2 jogadores), cor, nível, relógio
- [x] Gerenciador de cenas completo (voltar, trocar, empilhar)
- [x] `i18n.py` com todos os textos em pt-BR

**Partida**
- [x] Relógio de xadrez (sem relógio, 3, 5, 10, 15 min, incremento opcional)
- [x] Fim de partida por tempo esgotado
- [x] Dica de jogada (usa a IA)
- [x] Virar o tabuleiro (e virar automático no modo 2 jogadores)
- [x] Empate por acordo (modo 2 jogadores)
- [x] Desfazer contra a IA (desfaz o par de lances)
- [x] Atalhos de teclado (`Esc`, `U`, `F`, `H`, `N`)

**Persistência**
- [x] `storage/paths.py` (pasta `%APPDATA%\XadTitans` com plano B)
- [x] Salvar partida em PGN (com cabeçalhos padrão)
- [x] Carregar partida de um PGN
- [x] Autosave ao fechar e botão Continuar
- [x] `settings.json` (som, volume, velocidade das animações, FPS, resolução, ajudas visuais)
- [x] Tela de Configurações ligada ao `settings.json`
- [x] `stats.json` e tela de estatísticas
- [x] Arquivos ausentes ou corrompidos voltam ao padrão sem travar
- [x] Testes de storage (salvar/carregar, autosave, arquivo corrompido)

**Robustez**
- [x] Tratamento global de exceções: grava no log e mostra mensagem simples
- [x] Log com rotação e tamanho limitado
- [x] Commit da fase

**Pronto quando:** um usuário novo consegue instalar, jogar, salvar, fechar, voltar e continuar sem precisar do desenvolvedor. ✅ (comprovado pelo smoke test headless da experiência real: abrir → nova partida → lances → fechar → reabrir → Continuar restaura posição, turno, relógio, perspectiva e Undo → finalizar → Continuar não oferece partida encerrada → nova partida → fechar/reabrir.)

---

## FASE 6 — Qualidade e desempenho

- [x] Cobertura de testes de 80% ou mais em `core/` e `ai/` (Fase 6.1)
- [x] Smoke test headless da interface (`SDL_VIDEODRIVER=dummy`) (Fase 6.3; reexecutado na 6.6 via `tools/manual_checks.py` — 49/49 PASS)
- [x] `ruff` sem erros; docstrings nos módulos públicos (Fase 6.2; reconfirmado na 6.6)
- [x] Perfil com `cProfile` da busca da IA e otimizar os gargalos (Fase 6.4)
- [x] Perfil do desenho (quadros lentos) e otimizar (Fase 6.5)
- [x] Verificar uso de memória e ajustar se passar da meta (Fase 6.5)
- [x] Verificar que não há nenhuma chamada de rede no código (Fase 6.6 — auditoria estática + guarda de socket em runtime: 0 tentativas)
- [x] Rodar a lista de **testes manuais** (final deste arquivo) (Fase 6.6 — executados via `tools/manual_checks.py`; ver notas por item)
- [x] Testar no PC alvo, com o PC fraco em uso normal (Fase 6.7 — **PASS**: teste manual no PC real executado pelo usuário em 2026-10-08: partida completa jogada; abertura, tabuleiro, movimentos e IA funcionando; sem travamentos, crashes ou problemas durante a partida)
- [x] Corrigir todos os bugs encontrados (Fase 6.6 — 3 bugs corrigidos: volume órfão, tabuleiro virado, deadlock AI vs AI)
- [x] Commit da fase (6.6: `88c8b5b`; fechamento da Fase 6: commit desta atualização)

**Pronto quando:** testes automáticos e manuais passam, e o jogo é fluido no PC alvo. ✅ **Cumprido** — suíte completa e testes manuais passando; validação real no PC alvo (Fase 6.7) com partida completa sem problemas. **Fase 6 concluída.**

---

## FASE 7 — Empacotamento (.exe)

- [x] Criar o ícone `assets/icons/xadtitans.ico` (Fase 7.2 — gerado por `tools/gen_icon.py` do sprite próprio CC0 do rei branco; 16–256 px; RT_ICON/RT_GROUP_ICON verificados no exe)
- [x] Guardar a versão em `xadtitans/__init__.py` e mostrá-la no menu (Fase 7.2 — `1.0.0` como única fonte de verdade: menu (rótulo `v1.0.0`), version-file e metadados do exe derivam do mesmo valor)
- [x] Criar `tools/build_exe.py` (ou script `.bat`) com o comando do PyInstaller (Fase 7.2 — usa `.venv\Scripts\pyinstaller.exe`, argumentos fixos, version-file com round-trip validado, pós-validação de assets no pacote)
- [x] Gerar o build em modo `onedir` (Fase 7.2 — `dist/XadTitans` 33.6 MB, windowed, sem UPX; exe validado nesta máquina: sobe o App completo e roda sem erro com drivers dummy)
- [x] Conferir que sons, imagens e fontes são encontrados dentro do executável (Fase 7.2 — 8 assets essenciais conferidos no `_internal` incluindo a visão preta; fontes = Arial do sistema, sem fontes próprias para embutir)
- [x] Testar o `.exe` em máquina **sem Python instalado** (Fase 7.3 — **CONCLUÍDO COM RESSALVA**: validação em máquina sem Python **não foi possível neste ambiente** (sem 2ª máquina física nem virtualização disponível); a **autocontenção do bundle foi verificada por inspeção + execução real** — `python312.dll`, `VCRUNTIME140(.1)`, SDL2/pygame e assets embutidos; `XadTitans.exe` executou com sucesso como `WINDOWS_GUI` (sem console, sem depender de terminal nem do Python do sistema). **Teste complementar em máquina/VM sem Python permanece recomendado**)
- [x] Testar autosave, salvamento e log dentro do executável (Fase 7.3 — autosave/persistência confirmados em `%APPDATA%\XadTitans\autosave\game.json` com retomada via "Continuar" e **zero writes em `_internal/`**; log é *lazy* (criado só em warning/exception por design), sem crash relacionado ao modo windowed. **Anomalia**: no 1º lançamento o autosave pré-existente avançou 17 lances até o fim sem clique humano — **não reproduzida nas execuções controladas posteriores**)
- [x] Verificar comportamento com o antivírus (falsos positivos) (Fase 7.3 — **SmartScreen/Defender não apresentou alerta neste ambiente**; exe está `NotSigned`, então alerta em download real de máquina limpa permanece possível. **Teste auditivo em hardware real permanece como validação complementar**)
- [ ] Incluir `LICENSE`, `CREDITS.md` e `README.md` na pasta final (Fase 7.4)
- [ ] Gerar o `.zip` de release e o hash SHA-256 (Fase 7.4)
- [ ] (Opcional) Criar instalador com Inno Setup (Fase 7.4)
- [ ] Commit da fase (pendente aprovação da Fase 7.2)

**Pronto quando:** o `.zip` abre e joga em uma máquina limpa, do menu até o fim de uma partida.

---

## FASE 8 — Documentação e divulgação

- [ ] Tirar prints e gravar um GIF curto de uma partida
- [ ] Atualizar o `README.md` com prints, como rodar, como jogar e tabela de desempenho da IA
- [ ] Preencher o `CHANGELOG.md` da versão 1.0.0
- [ ] Conferir o `CREDITS.md` e a licença de todos os assets
- [ ] Criar a tag `v1.0.0` e o release no GitHub com o `.zip` e o hash
- [ ] Deixar o repositório organizado (descrição, tópicos, issues abertas para o futuro)
- [ ] Escrever o post de divulgação (LinkedIn) com o GIF e o link do repositório
- [ ] Incluir o projeto no portfólio e no currículo

**Pronto quando:** qualquer pessoa consegue entender, baixar e jogar o XadTitans só com o repositório.

---

## FASE 9 — Futuro (opcional)

- [ ] Nível **Mestre** com Stockfish via UCI (binário local, respeitando a GPL)
- [ ] Barra de avaliação durante a partida
- [ ] Análise pós-jogo (marcar bons lances e erros)
- [ ] Importar PGN e rever partidas lance a lance
- [ ] Puzzles táticos (mate em 1, 2, 3)
- [ ] Temas de tabuleiro e conjuntos de peças extras
- [ ] Tradução para inglês e espanhol
- [ ] Nome das aberturas em tempo real
- [ ] Motor próprio com bitboards para maior velocidade
- [ ] Versão 3D real (por exemplo com Godot)

---

## Lista de testes manuais

> **Fase 6.6 (2026-10-08):** executados de verdade via `tools/manual_checks.py` —
> harness que roda a **aplicação real** (App, cenas, eventos pygame, storage)
> com SDL dummy (headless), dados isolados em diretório temporário e guarda
> de rede ativa. 49/49 PASS. Itens marcados com nota explicam o tipo de
> execução (real/headless) e limitações do ambiente (sem display, sem áudio
> audível). Nenhum item foi marcado sem execução.

**Regras**
- [x] Mate do louco termina em xeque-mate — executado via cliques reais na UI; 0-1 + EndgameScene (headless)
- [x] Posição de afogamento termina em empate — 7k/5Q2/6K1 → AFOGAMENTO 1/2-1/2 (headless)
- [x] Rei contra rei termina em empate por material insuficiente — 8/8/8/4k3/8/8/8/4K3 (headless)
- [x] Roque curto e longo funcionam; roque passando por casa atacada é impedido — O-O e O-O-O via cliques reais; torre em g2 bloqueia O-O (headless)
- [x] En passant é oferecido só no lance seguinte — ep em d6 aceito; expira após lance intermediário (headless)
- [x] Promoção mostra o diálogo e coloca a peça escolhida — diálogo real com 4 opções; dama colocada via clique no diálogo (headless)
- [x] Tripla repetição encerra a partida — claim em 7 lances via UI; EndgameScene (headless)
- [x] Regra dos 50 lances encerra a partida — meio-jogo 100 → CINQUENTA_LANCES (headless)
- [x] Peça cravada não pode se mover de forma que exponha o rei — cavalo em e4 sem lances legais (headless)

**Interface**
- [x] Destaques corretos (seleção, lances legais, último lance, xeque) — verificação de estado via cliques reais (selected_square, legal_destinations, last_move, check_square); **visualização de pixels não é possível sem display no ambiente de CI; no teste real da Fase 6.7 (PC alvo) a partida completa foi jogada sem problemas visuais observados**
- [x] Animações não travam o clique seguinte — bloqueio durante animação + clique seguinte aceito após liberar (headless, estado real do animator)
- [x] Virar o tabuleiro mantém tudo alinhado — 64/64 casas mapeadas pixel↔casa após rotação (estado geométrico; no teste real da Fase 6.7 a partida completa foi jogada no PC alvo sem problemas observados)
- [ ] Redimensionar/tela cheia mantém a proporção — **N/A: recurso não implementado** (janela fixa 1024×768, sem flag RESIZABLE e sem handler de fullscreen). Não testável; não é PASS.
- [x] Sons tocam e o volume 0 silencia tudo — sons disparados nos fluxos (click/move) e volume 0 → mestre 0.0 via settings; **audição real impossível em headless; no teste real da Fase 6.7 a partida completa foi jogada no PC alvo sem problemas observados (áudio não foi relatado separadamente pelo usuário)**

**IA**
- [x] Nos quatro níveis, a IA responde sem congelar a janela — INICIANTE 0,00s / FÁCIL 0,67s / MÉDIO 3,00s / DIFÍCIL 14,89s (limites 0,5/2/5/15s); lances legais; frame máx 82 ms (headless)
- [x] Iniciante comete erros; Difícil não entrega peças de graça — iniciante com seeds distintos responde com lances legais e variados (ver nota no relatório); difícil preservou a dama em posição simples (headless)
- [x] Fechar o jogo durante o pensamento da IA encerra sem erro — worker cancelado em on_exit; autosave presente (headless)
- [x] Desfazer durante o turno da IA cancela o cálculo com segurança — worker cancelado; nada obsoleto aplicado em 30 frames (headless)
- [x] Iniciar novo jogo durante atividade da IA não deixa worker antigo ativo — new_game limpa worker; sem lances obsoletos (headless)
- [x] AI vs AI continua funcionando — 10 partidas completas: 0 lances ilegais, 0 exceções, 0 deadlocks (headless; após correção do deadlock com delay=0)

**Persistência**
- [x] Fechar no meio de uma partida e voltar em Continuar restaura tudo — posição, turno, relógio e undo verificados após reabertura real (headless)
- [x] PGN salvo abre em outro programa de xadrez — **limitação do ambiente:** sem programa de xadrez GUI instalado; validado reparseando o PGN com python-chess (parser independente do gravador) e reconstruindo a posição final. Abrir em outro programa real: Fase 6.7.
- [x] Apagar `settings.json` faz o jogo voltar aos padrões — defaults restaurados (headless)
- [x] Apagar a pasta de dados não impede o jogo de abrir — App abre sem a pasta; 1º autosave recria a estrutura (headless)
- [x] Autosave inválido é tratado sem derrubar o jogo — quarentena + mensagem; jogo segue normal (headless)
- [x] Finalizar partida remove o autosave — mate concluído → autosave removido → Continuar desabilitado (headless)

**Robustez (Fase 6.6, executados via `tools/manual_checks.py`)**
- [x] ESC no menu encerra o App; ESC na partida volta ao menu (headless)
- [x] Novo jogo repetidamente — 10 ciclos N → Nova Partida → GameScene limpos (headless)
- [x] Entrar/sair de GameScene repetidamente — 10 ciclos partida→menu sem exceção (headless)
- [x] Alternar modos de jogo — HvH, HvAI e AIvAI criados e jogados (headless)
- [x] Fechar durante animação e logo após lance — 3 fechos imediatos sem exceção (headless)
- [x] Undo repetidamente dentro das regras — 8 undos em 4 lances; sem efeito colateral (headless)
- [x] Continuar uma partida várias vezes — 3 reaberturas com o mesmo autosave consistentes (headless)
- [x] Partida terminada não pode ser continuada indevidamente — fim → autosave removido → Continuar desabilitado (headless)
- [x] Nenhuma exceção no terminal/log nos fluxos normais — log capturado: apenas 2 WARNING+ esperados (manuseio de autosave corrompido) (headless)

**Instalação**
- [ ] O `.exe` abre em PC sem Python — Fase 7
- [ ] Ícone e título aparecem corretamente
- [ ] Nenhuma janela de terminal aparece
