# CHECKLIST — XadTitans

Passo a passo do início ao fim. Marque `- [x]` ao concluir cada item. Só avance de fase quando o bloco **Pronto quando** estiver cumprido. Detalhes técnicos estão no [`README.md`](README.md).

## Painel de progresso

| Fase | Assunto | Status |
|---|---|---|
| 0 | Preparação | ✅ |
| 1 | Tabuleiro na tela | ✅ |
| 2 | Regras e jogabilidade | ✅ |
| 3 | Visual estilo Chess Titans | ⬜ |
| 4 | Inteligência artificial | ⬜ |
| 5 | Recursos do jogo | ⬜ |
| 6 | Qualidade e desempenho | ⬜ |
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

- [ ] Definir o conjunto de peças final (próprio ou de licença aberta) e registrar no `CREDITS.md`
- [ ] Criar `tools/gen_board.py` (Pillow) que gera `board_perspective.png` e `squares.json` (centro e escala de cada casa)
- [ ] `BoardView` usando `squares.json` para posicionar as peças
- [ ] Escala das peças por fileira (mais longe = menor)
- [ ] Ordem de desenho de trás para frente
- [ ] Sombras sob as peças
- [ ] Destaque da casa selecionada (brilho)
- [ ] Destaque dos movimentos legais (ponto para casa vazia, anel para captura)
- [ ] Destaque do último lance
- [ ] Brilho vermelho no rei em xeque
- [ ] Hover (casa sob o mouse)
- [ ] Módulo `animations.py` (tween e easing)
- [ ] Animação de deslize das peças e esmaecer na captura
- [ ] Bloquear entrada do jogador durante a animação
- [ ] `audio.py` e sons: mover, capturar, xeque, fim de jogo, clique
- [ ] Fundo e moldura do tabuleiro (mármore ou madeira)
- [ ] Painel lateral: lista de jogadas com rolagem, peças capturadas
- [ ] Cache de todos os sprites escalados na inicialização
- [ ] Medir o FPS no PC alvo (meta: 30 ou mais) e otimizar se preciso
- [ ] Commit da fase

**Pronto quando:** o jogo tem a aparência final, com animações e sons, e mantém 30 FPS no PC alvo.

---

## FASE 4 — Inteligência artificial

**Base**
- [ ] `ai/evaluation.py`: material e tabelas de posição (piece-square tables)
- [ ] `ai/search.py`: negamax com poda alfa-beta em profundidade fixa
- [ ] Testes: acha mate em 1; acha mate em 2; não entrega a dama de graça
- [ ] Nunca devolver lance ilegal (teste com várias posições)

**Melhorias de busca**
- [ ] Ordenação de lances (capturas por MVV-LVA, lance da tabela, killers)
- [ ] Busca de quiescência com profundidade limitada
- [ ] Aprofundamento iterativo com limite de tempo
- [ ] Respeitar o `stop_event` (cancelamento)
- [ ] Tabela de transposição
- [ ] Empates dentro da busca (repetição, 50 lances, material insuficiente)
- [ ] Valores de mate que preferem mates mais rápidos

**Avaliação refinada**
- [ ] Par de bispos
- [ ] Estrutura de peões (dobrados, isolados, passados)
- [ ] Segurança do rei
- [ ] Interpolação meio-jogo / final
- [ ] Mobilidade (só manter se o custo compensar)

**Integração**
- [ ] `ai/levels.py` com os 4 níveis (Iniciante, Fácil, Médio, Difícil)
- [ ] Aleatoriedade controlada nos níveis baixos e desempate aleatório (com semente nos testes)
- [ ] `ai/worker.py`: `AIWorker` em thread, com `request`, `poll` e `cancel`
- [ ] Ligar a IA ao `GameScene` (jogador vs IA, escolha de cor)
- [ ] Indicador "pensando..." sem travar a interface
- [ ] `tools/bench_ai.py`: nós por segundo e tempo por nível
- [ ] Ajustar profundidade e tempo de cada nível ao PC alvo e registrar no README
- [ ] Teste headless: 10 partidas IA contra IA sem exceção e sem lance ilegal
- [ ] (Opcional) Livro de aberturas simples
- [ ] Commit da fase

**Pronto quando:** dá para jogar contra a IA nos 4 níveis, a interface nunca congela e não há lance ilegal.

---

## FASE 5 — Recursos do jogo

**Menus e fluxo**
- [ ] Menu principal: Novo jogo, Continuar, Carregar, Configurações, Sair
- [ ] Tela Nova partida: modo (vs IA / 2 jogadores), cor, nível, relógio
- [ ] Gerenciador de cenas completo (voltar, trocar, empilhar)
- [ ] `i18n.py` com todos os textos em pt-BR

**Partida**
- [ ] Relógio de xadrez (sem relógio, 3, 5, 10, 15 min, incremento opcional)
- [ ] Fim de partida por tempo esgotado
- [ ] Dica de jogada (usa a IA)
- [ ] Virar o tabuleiro (e virar automático no modo 2 jogadores)
- [ ] Empate por acordo (modo 2 jogadores)
- [ ] Desfazer contra a IA (desfaz o par de lances)
- [ ] Atalhos de teclado (`Esc`, `U`, `F`, `H`, `N`)

**Persistência**
- [ ] `storage/paths.py` (pasta `%APPDATA%\XadTitans` com plano B)
- [ ] Salvar partida em PGN (com cabeçalhos padrão)
- [ ] Carregar partida de um PGN
- [ ] Autosave ao fechar e botão Continuar
- [ ] `settings.json` (som, volume, velocidade das animações, FPS, resolução, ajudas visuais)
- [ ] Tela de Configurações ligada ao `settings.json`
- [ ] `stats.json` e tela de estatísticas
- [ ] Arquivos ausentes ou corrompidos voltam ao padrão sem travar
- [ ] Testes de storage (salvar/carregar, autosave, arquivo corrompido)

**Robustez**
- [ ] Tratamento global de exceções: grava no log e mostra mensagem simples
- [ ] Log com rotação e tamanho limitado
- [ ] Commit da fase

**Pronto quando:** um usuário novo consegue instalar, jogar, salvar, fechar, voltar e continuar sem precisar do desenvolvedor.

---

## FASE 6 — Qualidade e desempenho

- [ ] Cobertura de testes de 80% ou mais em `core/` e `ai/`
- [ ] Smoke test headless da interface (`SDL_VIDEODRIVER=dummy`)
- [ ] `ruff` sem erros; docstrings nos módulos públicos
- [ ] Perfil com `cProfile` da busca da IA e otimizar os gargalos
- [ ] Perfil do desenho (quadros lentos) e otimizar
- [ ] Verificar uso de memória e ajustar se passar da meta
- [ ] Verificar que não há nenhuma chamada de rede no código
- [ ] Rodar a lista de **testes manuais** (final deste arquivo)
- [ ] Testar no PC alvo, com o PC fraco em uso normal
- [ ] Corrigir todos os bugs encontrados
- [ ] Commit da fase

**Pronto quando:** testes automáticos e manuais passam, e o jogo é fluido no PC alvo.

---

## FASE 7 — Empacotamento (.exe)

- [ ] Criar o ícone `assets/icons/xadtitans.ico`
- [ ] Guardar a versão em `xadtitans/__init__.py` e mostrá-la no menu
- [ ] Criar `tools/build_exe.py` (ou script `.bat`) com o comando do PyInstaller
- [ ] Gerar o build em modo `onedir`
- [ ] Conferir que sons, imagens e fontes são encontrados dentro do executável
- [ ] Testar o `.exe` em máquina **sem Python instalado**
- [ ] Testar autosave, salvamento e log dentro do executável
- [ ] Verificar comportamento com o antivírus (falsos positivos)
- [ ] Incluir `LICENSE`, `CREDITS.md` e `README.md` na pasta final
- [ ] Gerar o `.zip` de release e o hash SHA-256
- [ ] (Opcional) Criar instalador com Inno Setup
- [ ] Commit da fase

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

**Regras**
- [ ] Mate do louco termina em xeque-mate
- [ ] Posição de afogamento termina em empate
- [ ] Rei contra rei termina em empate por material insuficiente
- [ ] Roque curto e longo funcionam; roque passando por casa atacada é impedido
- [ ] En passant é oferecido só no lance seguinte
- [ ] Promoção mostra o diálogo e coloca a peça escolhida
- [ ] Tripla repetição e 50 lances encerram a partida
- [ ] Peça cravada não pode se mover de forma que exponha o rei

**Interface**
- [ ] Destaques corretos (seleção, lances legais, último lance, xeque)
- [ ] Animações não travam o clique seguinte
- [ ] Virar o tabuleiro mantém tudo alinhado
- [ ] Redimensionar/tela cheia mantém a proporção
- [ ] Sons tocam e o volume 0 silencia tudo

**IA**
- [ ] Nos quatro níveis, a IA responde sem congelar a janela
- [ ] Iniciante comete erros; Difícil não entrega peças de graça
- [ ] Fechar o jogo durante o pensamento da IA encerra sem erro
- [ ] Desfazer durante o turno da IA cancela o cálculo com segurança

**Persistência**
- [ ] Fechar no meio de uma partida e voltar em Continuar restaura tudo
- [ ] PGN salvo abre em outro programa de xadrez
- [ ] Apagar `settings.json` faz o jogo voltar aos padrões
- [ ] Apagar a pasta de dados não impede o jogo de abrir

**Instalação**
- [ ] O `.exe` abre em PC sem Python
- [ ] Ícone e título aparecem corretamente
- [ ] Nenhuma janela de terminal aparece
