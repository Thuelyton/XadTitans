# XadTitans ♟

Jogo de xadrez para **desktop (Windows)**, **100% offline**, inspirado no visual e na jogabilidade do Chess Titans. Você joga contra o computador (em vários níveis de dificuldade) ou contra outra pessoa no mesmo PC. Feito em **Python**, pensado para rodar bem em **computadores modestos**.

> Este documento é a especificação do projeto. O passo a passo de execução está em [`CHECKLIST.md`](CHECKLIST.md). Se você é um agente de código: leia a seção 15 antes de começar.

---

## 1. Visão geral

| Item | Definição |
|---|---|
| Nome | XadTitans |
| Tipo | Aplicativo desktop, sem internet, sem servidor, sem conta |
| Plataforma alvo | Windows (verificar a versão do PC do desenvolvedor, ver seção 5) |
| Linguagem | Python |
| Interface | pygame, visual pseudo-3D (tabuleiro em perspectiva com peças inclinadas) |
| Regras do xadrez | Biblioteca `python-chess` |
| IA | Própria (negamax + poda alfa-beta), com 4 níveis |
| Entrega | Executável `.exe` (PyInstaller), opcionalmente com instalador |

## 2. Objetivos e não objetivos

**Objetivos**
- Jogar uma partida completa e correta de xadrez, com todas as regras oficiais.
- Ter aparência agradável, próxima da do Chess Titans, sem exigir placa de vídeo.
- Rodar fluido (meta: 30 FPS) em PC fraco, sem travar enquanto a IA pensa.
- Ser um projeto de portfólio bem organizado: código limpo, testes, documentação, release.

**Não objetivos (por decisão do projeto)**
- Nada de multiplayer online, contas, ranking online ou qualquer chamada de rede.
- Nada de 3D em tempo real na primeira versão (o efeito 3D é simulado com imagens).
- Nenhum recurso visual ou sonoro copiado do Chess Titans ou da Microsoft (ver seção 16).

## 3. Requisitos funcionais

**Núcleo do jogo**
- RF01. Todas as regras: movimentos legais, xeque, xeque-mate, roque, en passant, promoção.
- RF02. Empates: afogamento, material insuficiente, regra dos 50 lances, tripla repetição, acordo (2 jogadores).
- RF03. Desistência.
- RF04. Desfazer jogada (contra a IA, desfaz o par: lance da IA + lance do jogador).

**Modos**
- RF05. Jogador vs IA (escolher cor: brancas, pretas ou sorteio).
- RF06. Jogador vs Jogador no mesmo PC (com opção de virar o tabuleiro automaticamente).
- RF07. Níveis: Iniciante, Fácil, Médio, Difícil.
- RF08. Relógio opcional: sem relógio, 3, 5, 10 ou 15 minutos, com incremento opcional.

**Interface**
- RF09. Selecionar peça por clique, mostrar movimentos legais, mover por clique (arrastar é opcional).
- RF10. Destaques: casa selecionada, movimentos possíveis, último lance, rei em xeque.
- RF11. Animação dos lances, sons de movimento, captura, xeque e fim de jogo.
- RF12. Painel lateral: lista de jogadas (notação algébrica), peças capturadas, relógios, botões de ação.
- RF13. Diálogo de promoção do peão.
- RF14. Dica de jogada (usa a própria IA).
- RF15. Virar o tabuleiro.
- RF16. Tela de fim de partida com resultado e opção de nova partida.

**Persistência**
- RF17. Salvar e carregar partidas em PGN.
- RF18. Continuar a última partida automaticamente (autosave ao fechar).
- RF19. Configurações persistentes (som, volume, animações, FPS, resolução, ajudas visuais).
- RF20. Estatísticas simples (vitórias, derrotas e empates por nível).

## 4. Requisitos não funcionais

- **RNF01. Desempenho:** 30 FPS estáveis no PC alvo; a interface nunca congela durante o cálculo da IA.
- **RNF02. Memória:** manter o consumo baixo (meta inicial: abaixo de ~300 MB de RAM; ajustar depois de medir no PC real).
- **RNF03. Offline:** zero acesso à rede em qualquer parte do código.
- **RNF04. Robustez:** nenhuma exceção não tratada chega ao usuário; erros vão para um arquivo de log e a tela mostra uma mensagem simples.
- **RNF05. Manutenção:** separação em camadas, `core` e `ai` nunca importam `pygame`.
- **RNF06. Portabilidade dos dados:** salvamentos em PGN padrão, abrem em qualquer programa de xadrez.
- **RNF07. Idioma:** interface em português (pt-BR), com textos centralizados em um único módulo para facilitar tradução futura.

## 5. Stack e dependências

| Pacote | Uso | Observação |
|---|---|---|
| `pygame` | Janela, desenho, áudio, entrada | Licença LGPL |
| `chess` (python-chess) | Regras, geração de lances, FEN, PGN | Licença GPL-3.0 ou superior (ver seção 16) |
| `pytest` | Testes | Somente desenvolvimento |
| `pyinstaller` | Gerar o `.exe` | Somente desenvolvimento |
| `Pillow` | Ferramenta que gera o tabuleiro em perspectiva | Somente desenvolvimento, não vai no jogo |
| `ruff` | Análise estática de código | Opcional |

> No `pip`, a biblioteca python-chess se instala com **`pip install chess`**.

**Escolha da versão do Python (importante para PC antigo)**
- Se o Windows for o **7**, o último Python com suporte é o **3.8**. Nesse caso, fixe as versões das bibliotecas em versões compatíveis com o 3.8 e teste a instalação **antes** de escrever código.
- Se o Windows for 10 ou mais novo, use uma versão atual do Python (3.11 ou superior).
- Registre a versão escolhida e as versões fixadas em `requirements.txt`.

## 6. Arquitetura

### 6.1 Camadas

```
┌──────────────────────────────────────────────────────┐
│ UI  (pygame)   scenes · board_view · widgets · audio │
└───────────────┬──────────────────────────────────────┘
                │ eventos e comandos
┌───────────────▼──────────────┐      ┌────────────────┐
│ Aplicação (app.py)           │─────▶│ Storage        │
│ gerenciador de cenas         │      │ PGN · JSON     │
└───────┬───────────────┬──────┘      └────────────────┘
        │               │
┌───────▼───────┐ ┌─────▼──────────────┐
│ Core          │ │ AI                 │
│ Game, Clock   │ │ AIWorker (thread)  │
│ python-chess  │ │ search · evaluation│
└───────────────┘ └────────────────────┘
```

**Regras de dependência**
- `core` e `ai` **não** importam `pygame` (podem ser testados sem janela).
- `ai` depende só de `python-chess` e de tipos do `core`.
- `ui` pode importar `core`, `ai`, `storage`, mas não contém regra de xadrez nem lógica de busca.
- `storage` não conhece `ui`.

### 6.2 Fluxo de um lance (jogador vs IA)

1. O clique chega em `BoardView`, que converte pixel em casa (`square`).
2. `GameScene` pede `Game.legal_moves_from(square)` e desenha os destaques.
3. No segundo clique, `GameScene` chama `Game.push(move)` (abrindo o diálogo de promoção se necessário) e inicia a animação.
4. Se a partida continua e é a vez da IA, `GameScene` envia `AIWorker.request(board.copy(), level)`.
5. A cada quadro, `GameScene` consulta `AIWorker.poll()`. Enquanto a IA pensa, a interface continua responsiva e mostra "pensando...".
6. Quando a IA responde, o lance é aplicado com animação.
7. Depois de cada lance, `Game.result()` é verificado; se a partida acabou, abre a cena `GameOver`.

### 6.3 Concorrência

- A IA roda em **uma thread separada** (`AIWorker`), comunicando-se por fila e por um `threading.Event` de cancelamento (`stop_event`).
- A busca tem **limite de tempo** por nível (aprofundamento iterativo): quando o tempo acaba, devolve o melhor lance da última profundidade concluída.
- Se a thread competir demais com a interface por causa do GIL do Python, avaliar `multiprocessing` como alternativa, lembrando de chamar `multiprocessing.freeze_support()` no `main.py` por causa do PyInstaller.

### 6.4 Gerenciador de cenas

Máquina de estados simples, cada cena com `handle_event`, `update(dt)` e `draw(surface)`:

```
Menu ──▶ NovaPartida ──▶ Jogo ──▶ FimDePartida ──▶ Menu
  │                        ▲
  ├──▶ Carregar ───────────┘
  └──▶ Configurações
```

## 7. Estrutura de pastas

```
xadtitans/
├── main.py                     # ponto de entrada
├── README.md
├── CHECKLIST.md
├── CREDITS.md                  # créditos e licenças de assets
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── assets/
│   ├── images/                 # peças, tabuleiro, moldura, ícones de UI
│   ├── sounds/                 # move, capture, check, gameover, click
│   ├── fonts/
│   └── icons/                  # xadtitans.ico
├── src/
│   └── xadtitans/
│       ├── __init__.py         # versão
│       ├── app.py              # loop principal e gerenciador de cenas
│       ├── config.py           # constantes (resolução, FPS, cores)
│       ├── i18n.py             # textos em pt-BR
│       ├── core/
│       │   ├── game.py         # Game: estado, lances, resultado, desfazer
│       │   ├── clock.py        # relógio de xadrez
│       │   ├── types.py        # GameResult, Level, MoveResult...
│       │   └── pgn.py          # conversão de/para PGN
│       ├── ai/
│       │   ├── evaluation.py   # função de avaliação
│       │   ├── search.py       # negamax, alfa-beta, quiescência, TT
│       │   ├── levels.py       # parâmetros de cada nível
│       │   ├── book.py         # livro de aberturas (opcional)
│       │   └── worker.py       # AIWorker (thread)
│       ├── ui/
│       │   ├── scenes/         # menu, new_game, game, game_over, load, settings
│       │   ├── widgets/        # button, panel, dialog_promotion, move_list
│       │   ├── board_view.py   # projeção, peças, destaques
│       │   ├── animations.py   # tweens e easing
│       │   ├── audio.py        # carrega e toca sons
│       │   └── theme.py        # cores, fontes, estilos
│       ├── storage/
│       │   ├── paths.py        # pasta de dados do usuário
│       │   ├── settings.py     # settings.json
│       │   ├── saves.py        # partidas salvas e autosave
│       │   └── stats.py        # stats.json
│       └── utils/
│           ├── resources.py    # resource_path (dev e PyInstaller)
│           └── logger.py       # log em arquivo
├── tests/
│   ├── test_game_rules.py
│   ├── test_game_results.py
│   ├── test_ai_tactics.py
│   ├── test_ai_limits.py
│   ├── test_storage.py
│   ├── test_coordinates.py
│   └── test_ui_smoke.py        # headless (SDL_VIDEODRIVER=dummy)
└── tools/
    ├── gen_board.py            # gera tabuleiro em perspectiva + squares.json
    ├── bench_ai.py             # nós por segundo e tempo por nível
    └── build_exe.py            # empacotamento
```

## 8. Contratos entre módulos

Assinaturas de referência (podem ser refinadas, mas a separação de responsabilidades deve ser mantida).

```python
# core/types.py
class Level(Enum): INICIANTE, FACIL, MEDIO, DIFICIL

class Status(Enum):
    EM_ANDAMENTO, XEQUE_MATE, AFOGAMENTO, MATERIAL_INSUFICIENTE,
    CINQUENTA_LANCES, TRIPLA_REPETICAO, EMPATE_ACORDO, DESISTENCIA, TEMPO_ESGOTADO

@dataclass
class GameResult:
    status: Status
    winner: Optional[chess.Color]   # None em empate ou em andamento

# core/game.py
class Game:
    board: chess.Board
    def __init__(self, fen: str | None = None) -> None: ...
    def legal_moves_from(self, square: int) -> list[chess.Move]: ...
    def needs_promotion(self, from_sq: int, to_sq: int) -> bool: ...
    def push(self, move: chess.Move) -> None: ...
    def undo(self, plies: int = 1) -> None: ...
    def result(self) -> GameResult: ...
    def resign(self, color: chess.Color) -> None: ...
    def san_history(self) -> list[str]: ...
    def captured(self) -> dict[chess.Color, list[chess.PieceType]]: ...
    def to_pgn(self, headers: dict) -> str: ...
    @classmethod
    def from_pgn(cls, text: str) -> "Game": ...

# ai/search.py
def find_best_move(board: chess.Board, level: Level,
                   stop_event: threading.Event) -> chess.Move: ...

# ai/worker.py
class AIWorker:
    def request(self, board: chess.Board, level: Level) -> None: ...
    def poll(self) -> chess.Move | None: ...     # não bloqueia
    def cancel(self) -> None: ...

# storage/saves.py
def save_game(game: Game, name: str) -> Path: ...
def load_game(path: Path) -> Game: ...
def autosave(game: Game, meta: dict) -> None: ...
def load_autosave() -> tuple[Game, dict] | None: ...
```

## 9. Inteligência artificial

### 9.1 Algoritmo

- **Negamax com poda alfa-beta.**
- **Aprofundamento iterativo** com limite de tempo e `stop_event`.
- **Ordenação de lances:** lance da tabela de transposição primeiro, capturas por MVV-LVA (vítima mais valiosa, atacante menos valioso), lances "killer" e heurística de histórico.
- **Busca de quiescência:** só capturas (e xeques opcionalmente), com profundidade máxima limitada, para evitar o "efeito horizonte".
- **Tabela de transposição:** dicionário com chave de posição (por exemplo `chess.polyglot.zobrist_hash`; medir o custo por nó e comparar com alternativas), guardando profundidade, valor e tipo do limite.
- **Detecção de empate na busca:** repetição, 50 lances e material insuficiente valem 0.
- **Valores de mate:** usar um valor grande menos a distância (preferir mates mais rápidos).

### 9.2 Avaliação

Ponto de partida: a "Simplified Evaluation Function" (documentada na wiki Chess Programming), refinada aos poucos.

- Material (peão 100, cavalo 320, bispo 330, torre 500, dama 900).
- Tabelas de posição por peça (piece-square tables), com versão de meio-jogo e de final.
- Par de bispos.
- Estrutura de peões: dobrados, isolados, passados.
- Segurança do rei (escudo de peões, casas próximas atacadas), mais peso no meio-jogo.
- Mobilidade leve (custo alto no Python, medir antes de manter).
- Interpolação por fase do jogo (meio-jogo para final).

### 9.3 Níveis (metas iniciais, ajustar após o benchmark)

| Nível | Profundidade | Tempo máx. | Comportamento |
|---|---|---|---|
| Iniciante | 1 | ~0,3 s | Escolhe entre os melhores lances com bastante aleatoriedade; comete erros táticos |
| Fácil | 2 | ~0,8 s | Alguma aleatoriedade; sem quiescência |
| Médio | 3 | ~2 s | Com quiescência limitada e ordenação de lances |
| Difícil | 4 ou mais (iterativo) | ~5 s | Tabela de transposição, quiescência e avaliação completa |

Os números reais dependem do PC. Rode `tools/bench_ai.py` no computador alvo e ajuste profundidade e tempo para que o nível Difícil responda em tempo razoável sem sobrecarregar a máquina. Registre os resultados neste README.

### 9.4 Detalhes de qualidade

- Pequena aleatoriedade entre lances de avaliação igual, para as partidas não serem sempre idênticas (com semente fixável nos testes).
- Livro de aberturas simples (opcional): um dicionário próprio de primeiras jogadas comuns. Se usar um livro Polyglot de terceiros, conferir a licença.
- O nível **Mestre** (Stockfish via UCI) é uma extensão opcional futura (ver seção 17).

## 10. Interface e visual (efeito pseudo-3D)

**Ideia central:** simular o 3D com imagens, sem renderização 3D em tempo real.

1. **Tabuleiro em perspectiva pré-renderizado.** A ferramenta `tools/gen_board.py` (usa Pillow, `Image.transform` com `PERSPECTIVE`) gera `board_perspective.png` a partir de um tabuleiro plano, e um `squares.json` com o **centro** e o **fator de escala** de cada uma das 64 casas. Essa geração roda uma vez, no desenvolvimento.
2. **Peças como sprites** desenhados de um ângulo levemente inclinado. Em tempo de execução, a peça de cada casa é desenhada no centro registrado, com escala menor nas fileiras mais distantes.
3. **Ordem de desenho de trás para frente** (fileira mais distante primeiro), para as peças da frente cobrirem as de trás.
4. **Sombras** suaves sob as peças e **brilho** nas casas destacadas.
5. **Cache de sprites:** gerar as versões escaladas na inicialização e nunca escalar imagens a cada quadro.

**Boas práticas de desempenho no pygame**
- Usar `convert()` e `convert_alpha()` em todas as imagens carregadas.
- Resolução lógica 1024×768, com opção de 800×600 e tela cheia (avaliar a flag `pygame.SCALED`).
- 30 FPS por padrão (60 opcional nas configurações).
- Pré-criar as superfícies de destaque (não criar a cada quadro).
- Só recalcular o que mudou (por exemplo, a lista de jogadas).

**Animações:** módulo simples de *tween* com *easing* (deslize de 180 a 250 ms, configurável), esmaecer na captura, pulso vermelho no rei em xeque. A entrada do jogador fica bloqueada durante a animação do lance.

**Painel lateral:** lista de jogadas em duas colunas com rolagem, peças capturadas, relógios, botões (Desfazer, Dica, Virar, Desistir, Menu).

**Atalhos:** `Esc` menu, `U` desfazer, `F` virar, `H` dica, `N` nova partida.

## 11. Persistência

Pasta de dados do usuário: `%APPDATA%\XadTitans\` no Windows (com plano B para a pasta do usuário se a variável não existir).

| Arquivo | Conteúdo |
|---|---|
| `settings.json` | Preferências (som, volume, animações, FPS, resolução, ajudas visuais) |
| `stats.json` | Vitórias, derrotas e empates por nível |
| `autosave.pgn` + `autosave.json` | Última partida e metadados (modo, cor do jogador, nível, relógio) |
| `saves/*.pgn` | Partidas salvas pelo usuário |
| `logs/xadtitans.log` | Log de erros (rotacionado, tamanho limitado) |

PGN com cabeçalhos padrão: `Event "XadTitans"`, `White`, `Black` (por exemplo `XadTitans (Médio)`), `Date`, `Result`. Todos os arquivos JSON têm campo `version` para migrações futuras. Leitura sempre tolerante a arquivo ausente ou corrompido (voltar aos valores padrão, sem travar).

## 12. Testes e qualidade

- **Framework:** `pytest`.
- **Core:** mate do pastor e mate do louco (mate rápido), afogamento (FEN conhecido), material insuficiente, 50 lances, tripla repetição, roque (inclusive roque ilegal passando por casa atacada), en passant, promoção, desfazer.
- **IA:** acha mate em 1 e mate em 2; não entrega a dama de graça; respeita o limite de tempo e o `stop_event`; nunca devolve lance ilegal; partidas IA contra IA sem exceções.
- **Storage:** salvar e carregar PGN (ida e volta), autosave, arquivo corrompido não derruba o jogo.
- **Coordenadas:** conversão pixel↔casa para as 64 casas, tabuleiro normal e virado.
- **Interface (smoke test headless):** com `SDL_VIDEODRIVER=dummy`, abre a janela, percorre as cenas e fecha sem erro.
- **Meta de cobertura:** 80% ou mais em `core/` e `ai/`.
- **Desempenho:** `tools/bench_ai.py` mede nós por segundo e tempo por nível; `cProfile` para achar gargalos.
- **Teste manual:** lista no final do `CHECKLIST.md`.

## 13. Build e distribuição

```bat
pip install -r requirements-dev.txt
pyinstaller --noconfirm --windowed --name XadTitans ^
  --icon assets\icons\xadtitans.ico ^
  --add-data "assets;assets" main.py
```

- Preferir o modo **onedir** (pasta), que abre mais rápido em PC fraco. O modo `--onefile` extrai para uma pasta temporária a cada execução e costuma acionar mais falsos positivos de antivírus.
- Todo acesso a arquivos do jogo deve passar por `utils/resources.py` (`resource_path`), que funciona tanto no desenvolvimento quanto dentro do executável (`sys._MEIPASS`).
- Testar o `.exe` em uma máquina **sem Python instalado**.
- Distribuir como `.zip` (e, opcionalmente, com instalador feito no Inno Setup). Publicar o hash SHA-256 no release.
- Versionamento semântico (`v1.0.0`) com `CHANGELOG.md`.

## 14. Roadmap

Detalhes e caixas de marcação no [`CHECKLIST.md`](CHECKLIST.md). Os prazos dependem do seu ritmo; use a ordem, não as datas.

| Fase | Entrega | Pronto quando |
|---|---|---|
| 0. Preparação | Ambiente, repositório, estrutura de pastas | Janela vazia abre e fecha; `pytest` roda |
| 1. Tabuleiro | Tabuleiro 2D e peças na tela | Posição inicial correta; clique vira casa |
| 2. Regras | Partida completa para 2 jogadores | Todos os testes de regras passam |
| 3. Visual | Pseudo-3D, animações, sons | 30 FPS no PC alvo com a estética final |
| 4. IA | 4 níveis, thread, benchmark | IA joga sem travar a interface e sem lance ilegal |
| 5. Recursos | Menu, relógio, dica, salvar/carregar, config | Fluxo completo de uso, sem o teclado do desenvolvedor |
| 6. Qualidade | Testes, perfil, correções | Cobertura e teste manual concluídos |
| 7. Empacotamento | `.exe` funcionando em máquina limpa | Zip de release testado |
| 8. Divulgação | README final, GIF, release, post | Repositório apresentável |
| 9. Futuro | Extras opcionais | (opcional) |

## 15. Instruções para o agente de código

1. Leia este README inteiro e o `CHECKLIST.md`. Trabalhe **uma fase por vez**, na ordem.
2. Ao terminar cada item, marque a caixa no `CHECKLIST.md` (`- [x]`). Só avance de fase quando o critério "Pronto quando" estiver cumprido e os testes passarem.
3. Respeite as regras de dependência da seção 6.1. Nunca importe `pygame` em `core/` ou `ai/`.
4. Toda regra de xadrez vem do `python-chess`. Não reimplementar regras.
5. Nada de acesso à rede, em nenhuma parte.
6. Antes de adicionar uma dependência nova, justifique no `CHANGELOG.md`. Prefira a biblioteca padrão.
7. Escreva testes junto com o código (não deixe para o fim). Rode `pytest` a cada mudança relevante.
8. A interface não pode travar: trabalho pesado só na thread da IA.
9. Não usar imagens, sons ou nomes de arquivo do Chess Titans ou da Microsoft. Todo asset novo entra no `CREDITS.md` com fonte e licença.
10. Commits pequenos e descritivos, um assunto por commit.
11. Em caso de dúvida sobre requisito, escolha a opção mais simples que respeite os RF/RNF e registre a decisão em um comentário curto ou no `CHANGELOG.md`.
12. Ao final de cada fase, resuma em poucas linhas o que foi feito, o que foi testado e o que ficou pendente.

## 16. Licenças e créditos

- **python-chess** é distribuído sob **GPL-3.0 ou superior**. Se o XadTitans for distribuído com ele embutido (o `.exe`), o projeto deve ser compatível com essa licença. Recomendação: licenciar o XadTitans como **GPL-3.0-or-later** e incluir o arquivo `LICENSE`. Confirme as licenças vigentes antes de publicar.
- **pygame** usa LGPL.
- **Stockfish** (se for usado no futuro) é GPL-3.0; incluir o binário implica cumprir a GPL.
- **Assets:** usar apenas material próprio ou com licença aberta (por exemplo CC0, como os pacotes do Kenney para sons e interface) e conferir a licença de cada conjunto de peças. Registrar tudo no `CREDITS.md`.
- **Chess Titans** é da Microsoft. O XadTitans é um projeto independente, apenas *inspirado* no estilo; nenhum código, imagem ou som do original é usado.

## 17. Ideias futuras (opcional)

- Nível **Mestre** com Stockfish via protocolo UCI (binário local, funciona offline), respeitando a GPL.
- Barra de avaliação e análise pós-jogo (mostrar lances bons e erros).
- Importar PGN e rever partidas lance a lance.
- Puzzles táticos (mate em 1, 2 e 3) a partir de posições próprias.
- Temas de tabuleiro (mármore, madeira, vidro) e conjuntos de peças alternativos.
- Tradução (inglês e espanhol) usando o módulo `i18n`.
- Nome das aberturas durante a partida.
- Motor próprio mais rápido (bitboards) ou versão 3D real com Godot.
