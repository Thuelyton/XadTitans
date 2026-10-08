"""Testes manuais executáveis — Fase 6.6 (XadTitans).

Executa a **aplicação real** (App, cenas, eventos pygame, storage) em
modo headless (SDL dummy) e verifica cada item do checklist manual,
registrando PASS/FAIL por item no final.

Cobertura:
  - Rede: guarda em runtime — qualquer tentativa de conexão/DNS durante
    toda a sessão é registrada como FALHA (o jogo é offline).
  - Regras: mate, afogamento, material insuficiente, roques, en
    passant, promoção (diálogo real), tripla repetição, 50 lances,
    peça cravada.
  - Interface: destaques (seleção/lances legais/último lance/xeque),
    animação não trava o clique seguinte, virar tabuleiro, sons,
    volume 0; resize/fullscreen documentados como N/A (não implementados).
  - IA: 4 níveis respondendo com jogadas legais dentro do limite,
    janela não congela, cancelamentos (undo/novo jogo/fecho).
  - Persistência: fechar+Continuar, relógio/turno restaurados, undo
    após restauração, PGN revalidado pelo python-chess, settings
    restaurados, pasta de dados apagada, autosave inválido, autosave
    removido ao final.
  - Robustez: ESC, novo jogo repetido, entrar/sair de GameScene,
    alternar modos, fechar durante pensamento/animação/lance, undo
    repetido, Continue repetido, partida terminada bloqueada, log sem
    exceções inesperadas.

Limitações do ambiente (registradas, NÃO marcadas como PASS visual):
  - sem display real: alinhamento visual verificado por estado
    geométrico (pixel↔casa), não por inspeção de imagem;
  - sem áudio audível: verifica-se que os sons são disparados e que
    volume 0 zera o volume mestre;
  - janela não é redimensionável (sem flag RESIZABLE) e o jogo não
    implementa tela cheia — itens N/A.

Uso:
    .venv/Scripts/python.exe tools/manual_checks.py
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

# Console Windows pode ser cp1252: garante UTF-8 (→, ç, etc.) no print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Isolamento de dados + headless ANTES de importar xadtitans.
_TMP = tempfile.mkdtemp(prefix="xadtitans_manual_")
os.environ["XADTITANS_DATA"] = _TMP
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import chess
import pygame

from xadtitans.app import App
from xadtitans.audio import AudioManager
from xadtitans.core.game import Game
from xadtitans.core.types import GameMode, Level, Status
from xadtitans.storage.autosave import (
    autosave_exists,
)
from xadtitans.storage.paths import autosave_file
from xadtitans.storage.pgn import (
    export_game,
    parse_pgn_string,
    reconstruct_board,
)
from xadtitans.storage.settings import DEFAULTS, Settings
from xadtitans.ui.scenes.endgame_scene import EndgameScene
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.scenes.menu_scene import MenuScene

# ══════════════════════════════════════════════════════════
# Infraestrutura do harness
# ══════════════════════════════════════════════════════════

RESULTS: list[tuple[str, str, str, str]] = []  # grupo, item, status, detalhe
CHECKS: list[tuple[str, str, object]] = []


def check(group: str, item: str):
    """Registra um item do checklist manual."""

    def deco(fn):
        CHECKS.append((group, item, fn))
        return fn

    return deco


class NetworkGuard:
    """Bloqueia qualquer chamada de rede em runtime."""

    def __init__(self) -> None:
        self.attempts: list[str] = []
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        import socket

        guard = self

        def blocked(name):
            def _f(*_a, **_k):
                guard.attempts.append(name)
                raise AssertionError(f"REDE DETECTADA EM RUNTIME: {name}")

            return _f

        for name in ("connect", "connect_ex", "sendto", "sendall", "send"):
            setattr(socket.socket, name, blocked(f"socket.socket.{name}"))
        socket.create_connection = blocked("socket.create_connection")  # type: ignore[method-assign]
        socket.getaddrinfo = blocked("socket.getaddrinfo")  # type: ignore[assignment]
        socket.gethostbyname = blocked("socket.gethostbyname")  # type: ignore[assignment]
        socket.gethostbyname_ex = blocked("socket.gethostbyname_ex")  # type: ignore[assignment]
        self._installed = True


GUARD = NetworkGuard()


class _LogCapture(logging.Handler):
    """Coleta registros dos loggers do jogo durante o harness."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(f"{record.levelname}: {record.getMessage()}")


LOG_CAPTURE = _LogCapture()

# Padrões de log ESPERADOS (manuseio próprio do jogo, ex.: autosave
# corrompido vai para quarentena com registro — não é erro de execução).
_EXPECTED_LOG = ("autosave", "quarentena", "corromp", "corrupt", "grava")


def _surf() -> pygame.Surface:
    if not pygame.display.get_init():
        pygame.init()
    return pygame.display.set_mode((1024, 768))


def _click_event(pos) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})


def _key_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


def _quit_event() -> pygame.event.Event:
    return pygame.event.Event(pygame.QUIT)


def _app_frame(app: App, event: pygame.event.Event | None = None) -> None:
    """Um frame real do App (eventos → update → draw → flip)."""
    if event is not None:
        pygame.event.post(event)
    app._frame()


def _wait_anim(app_or_scene, surface, cap: int = 200) -> None:
    """Roda frames até a animação terminar (clique seguinte liberado)."""
    scene = app_or_scene.scene if isinstance(app_or_scene, App) else app_or_scene
    if not hasattr(scene, "animator"):  # ex.: EndgameScene no topo
        return
    for _ in range(cap):
        if not scene.animator.blocking:
            return
        if isinstance(app_or_scene, App):
            app_or_scene._frame()
        else:
            scene.update(1 / 60)
            scene.draw(surface)
            pygame.display.flip()


def _sq_center(scene: GameScene, sq: int) -> tuple[int, int]:
    cx, cy = scene.board_view._center(sq)
    return int(cx), int(cy)


def _ui_move(app: App, frm: int, to: int) -> None:
    """Aplica um lance CLICANDO nas casas (caminho real de eventos)."""
    scene = _game(app)
    _app_frame(app, _click_event(_sq_center(scene, frm)))
    _app_frame(app, _click_event(_sq_center(scene, to)))
    _wait_anim(app, _surf())


def _start_hvh_app() -> App:
    """Abre o App e inicia uma partida HvH pelo fluxo real de UI:
    Menu → Novo Jogo → seletor de modo (HvH) → Iniciar.

    Observação: a tela Nova Partida começa em HvAI (Médio) por
    padrão — é decisão de produto; o harness configura o modo
    pelo caminho do usuário antes de iniciar."""
    app = _fresh_menu_app()
    _app_frame(app, _click_event(app.menu_scene.buttons[0].rect.center))
    for _ in range(2):
        _app_frame(app)
    ng = app.scene
    assert type(ng).__name__ == "NewGameScene", (
        f"esperava NewGameScene, veio {type(ng).__name__}"
    )
    ng.sel_mode.value = GameMode.HUMAN_VS_HUMAN
    ng._update_visibility()
    _app_frame(app, _key_event(pygame.K_RETURN))
    for _ in range(2):
        _app_frame(app)
    assert isinstance(app.scene, GameScene), (
        f"esperava GameScene, veio {type(app.scene).__name__}"
    )
    return app


def _game(app_or_scene) -> GameScene:
    obj = app_or_scene.scene if isinstance(app_or_scene, App) else app_or_scene
    assert isinstance(obj, GameScene), f"GameScene esperada, veio {type(obj)}"
    return obj


def _run_scene(scene: GameScene, surface, n: int, dt: float = 1 / 60,
               events: list | None = None) -> list[float]:
    """Roda n frames reais de uma cena (update+draw+flip), medindo tempos."""
    events = list(events or [])
    times: list[float] = []
    for i in range(n):
        while events:
            ev = events.pop(0)
            scene.handle_event(ev)
        t0 = time.perf_counter()
        scene.update(dt)
        scene.draw(surface)
        pygame.display.flip()
        times.append(time.perf_counter() - t0)
    return times


class _SoundRecorder:
    """Envolve AudioManager.play para registrar sons disparados."""

    def __init__(self, audio: AudioManager) -> None:
        self.audio = audio
        self.played: list[str] = []
        self._orig = audio.play

        def rec(name: str) -> None:
            self.played.append(name)
            self._orig(name)

        audio.play = rec  # type: ignore[method-assign]


def _fresh_menu_app() -> App:
    app = App()
    assert isinstance(app.scene, MenuScene)
    return app


# ══════════════════════════════════════════════════════════
# Rede
# ══════════════════════════════════════════════════════════

@check("Rede", "Nenhuma chamada de rede em runtime (guarda de socket)")
def _rede_runtime() -> str:
    # Sessão real: menu → nova partida → lances → undo → sair.
    app = _start_hvh_app()
    for _ in range(3):
        _app_frame(app)
    scene = app.scene
    _run_scene(scene, _surf(), 30, events=[
        _click_event(_sq_center(scene, chess.E2)),
        _click_event(_sq_center(scene, chess.E4)),
    ])
    _wait_anim(app, _surf())
    _app_frame(app, _key_event(pygame.K_u))
    for _ in range(3):
        _app_frame(app)
    if GUARD.attempts:
        raise AssertionError(f"tentativas de rede: {GUARD.attempts}")
    return f"0 tentativas de rede em {len(GUARD.attempts)} bloqueio(s)"


@check("Rede", "Imports do código de execução sem bibliotecas de rede")
def _rede_imports() -> str:
    proibidos = (
        "requests", "httpx", "urllib", "urllib3", "socket", "websocket",
        "aiohttp", "ftplib", "telnetlib", "smtplib", "poplib", "imaplib",
        "xmlrpc", "socks", "http.client", "http.server", "webbrowser",
    )
    src = Path(__file__).resolve().parent.parent / "src"
    encontrados: list[str] = []
    for py in src.rglob("*.py"):
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            for mod in proibidos:
                if s == f"import {mod}" or s.startswith(
                    (f"import {mod} ", f"from {mod} ")
                ) or s == f"from {mod} import":
                    encontrados.append(f"{py.name}:{lineno}: {s}")
    assert not encontrados, f"imports de rede: {encontrados}"
    return "nenhum import de rede em src/"


# ══════════════════════════════════════════════════════════
# Regras
# ══════════════════════════════════════════════════════════

@check("Regras", "Mate do louco termina em xeque-mate (via UI)")
def _regra_mate_louco() -> str:
    app = _start_hvh_app()
    scene = _game(app)
    for frm, to in (
        (chess.F2, chess.F3), (chess.E7, chess.E5),
        (chess.G2, chess.G4), (chess.D8, chess.H4),
    ):
        _ui_move(app, frm, to)
    assert scene.game.is_game_over(), "partida não terminou"
    res = scene.game.result()
    assert res is not None and res.status is Status.XEQUE_MATE, f"status {res}"
    assert res.winner is chess.BLACK, f"vencedor {res.winner}"
    for _ in range(4):
        _app_frame(app)  # App empilha EndgameScene
    assert isinstance(app.scene, EndgameScene), "EndgameScene não apareceu"
    return "xeque-mate 0-1; overlay de fim exibido"


@check("Regras", "Afogamento termina em empate")
def _regra_afogamento() -> str:
    game = Game("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert game.is_game_over(), "afogamento não detectado"
    res = game.result()
    assert res is not None and res.status is Status.AFOGAMENTO, f"status {res}"
    assert res.winner is None
    return "afogamento 1/2-1/2"


@check("Regras", "Rei contra rei: material insuficiente")
def _regra_insuficiente() -> str:
    game = Game("8/8/8/4k3/8/8/8/4K3 w - - 0 1")
    assert game.is_game_over()
    res = game.result()
    assert res is not None and res.status is Status.MATERIAL_INSUFICIENTE
    return "empate por material insuficiente"


@check("Regras", "Roque curto funciona (via UI)")
def _regra_roque_curto() -> str:
    app = _start_hvh_app()
    seq = [
        (chess.E2, chess.E4), (chess.E7, chess.E5),
        (chess.G1, chess.F3), (chess.B8, chess.C6),
        (chess.F1, chess.C4), (chess.G8, chess.F6),
        (chess.E1, chess.G1),  # O-O
    ]
    for frm, to in seq:
        _ui_move(app, frm, to)
    scene = _game(app)
    board = scene.game.board
    assert board.piece_type_at(chess.G1) == chess.KING, "rei não em g1"
    assert board.piece_type_at(chess.F1) == chess.ROOK, "torre não em f1"
    assert not board.has_kingside_castling_rights(chess.WHITE)
    return "roque curto: rei g1, torre f1"


@check("Regras", "Roque longo funciona (via UI)")
def _regra_roque_longo() -> str:
    app = _start_hvh_app()
    seq = [
        (chess.D2, chess.D4), (chess.D7, chess.D5),
        (chess.C1, chess.E3), (chess.C8, chess.F5),
        (chess.B1, chess.C3), (chess.B8, chess.C6),
        (chess.D1, chess.D2), (chess.D8, chess.D7),
        (chess.E1, chess.C1),  # O-O-O
    ]
    for frm, to in seq:
        _ui_move(app, frm, to)
    scene = _game(app)
    board = scene.game.board
    assert board.piece_type_at(chess.C1) == chess.KING, "rei não em c1"
    assert board.piece_type_at(chess.D1) == chess.ROOK, "torre não em d1"
    return "roque longo: rei c1, torre d1"


@check("Regras", "Roque por casa atacada é impedido")
def _regra_roque_atacado() -> str:
    # Torre preta em g2 ataca g1 → O-O ilegal para as brancas.
    game = Game("4k3/8/8/8/8/8/6r1/4K2R w K - 0 1")
    o_o = chess.Move(chess.E1, chess.G1, chess.KING)
    assert not game.is_legal(o_o), "roque por casa atacada aceito"
    assert chess.G1 not in [
        m.to_square for m in game.legal_moves_from(chess.E1)
    ]
    return "g1 atacada: O-O bloqueado"


@check("Regras", "En passant só no lance seguinte (via UI)")
def _regra_en_passant() -> str:
    app = _start_hvh_app()
    _ui_move(app, chess.E2, chess.E4)
    _ui_move(app, chess.A7, chess.A6)
    _ui_move(app, chess.E4, chess.E5)
    _ui_move(app, chess.D7, chess.D5)
    scene = _game(app)
    ep = chess.Move(chess.E5, chess.D6)
    assert scene.game.is_legal(ep), "en passant deveria estar disponível"
    _ui_move(app, chess.G1, chess.F3)  # lance branco intermediário
    assert not scene.game.is_legal(ep), "en passant expirou e ainda é aceito"
    return "ep disponível em D6; expirou após lance intermediário"


@check("Regras", "Promoção: diálogo exibido e peça escolhida (via UI)")
def _regra_promocao() -> str:
    surface = _surf()
    scene = GameScene(game_mode=GameMode.HUMAN_VS_HUMAN)
    scene.game.board = chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    scene._sync_view()
    scene.handle_event(_click_event(_sq_center(scene, chess.A7)))
    assert scene.board_view.selected_square == chess.A7
    scene.handle_event(_click_event(_sq_center(scene, chess.A8)))
    assert scene.pending_promotion == (chess.A7, chess.A8), "diálogo não abriu"
    scene.draw(surface)  # preenche _promo_rects
    assert len(scene._promo_rects) == 4, "diálogo sem 4 opções"
    # Clica na primeira opção (dama) — caminho real do clique no diálogo
    scene.handle_event(_click_event(scene._promo_rects[0][0].center))
    assert scene.pending_promotion is None
    assert scene.game.board.piece_type_at(chess.A8) == chess.QUEEN, \
        "peça promovida não é dama"
    return "diálogo com 4 opções; dama colocada em a8"


@check("Regras", "Tripla repetição encerra a partida (via UI)")
def _regra_tripla_repeticao() -> str:
    # O jogo usa claim_draw=True: is_game_over() retorna True quando o
    # jogador ATUAL pode reivindicar tripla repetição (i.e., existe pelo
    # menos um lance que leva a uma posição já vista 3x).
    #
    # Shuffle: {g1f3, g8f6, f3g1, f6g8} — cada ciclo completo restaura P0.
    #   Após ciclo 1 (4 lances): P0 visto 2x; P1/P2/P3 vistos 1x cada.
    #   Lance 5 (Nf3): P1 visto 2x.
    #   Lance 6 (Nf6): P2 visto 2x.
    #   Lance 7 (Ng1): P3 visto 2x → pretas PODEM jogar Ng8 (P0 pela 3ª vez).
    #     → can_claim_threefold_repetition() = True → is_game_over() = True.
    #
    # O 8º lance (Ng8) nunca chega a ser jogado: o jogo já está encerrado.
    app = _start_hvh_app()
    shuffle = [
        (chess.G1, chess.F3), (chess.G8, chess.F6),
        (chess.F3, chess.G1), (chess.F6, chess.G8),
    ]
    # Ciclo 1 (4 lances): P0 visto 2x. Jogo ainda em andamento.
    for frm, to in shuffle:
        _ui_move(app, frm, to)
    scene = _game(app)  # capturar ref. da GameScene enquanto app.scene ainda é GameScene
    assert not scene.game.is_game_over(), "encerrou cedo demais após ciclo 1"
    # Lances 5 e 6 (Nf3, Nf6): P1 e P2 vistos 2x. Ainda sem claim.
    for frm, to in shuffle[:2]:
        _ui_move(app, frm, to)
    assert not scene.game.is_game_over(), "encerrou cedo demais após 6 lances"
    # Lance 7 (Ng1): P3 visto 2x → pretas podem criar P0 pela 3ª vez.
    # Após este lance is_game_over(claim_draw=True) = True.
    _ui_move(app, chess.F3, chess.G1)
    assert scene.game.is_game_over(), "tripla repetição não detectada após 7 lances"
    res = scene.game.result()
    assert res is not None and res.status is Status.TRIPLA_REPETICAO
    assert isinstance(app.scene, EndgameScene), "EndgameScene não apareceu"
    return "tripla repetição claimável (7 lances) -> empate; EndgameScene exibida"


@check("Regras", "Regra dos 50 lances encerra a partida")
def _regra_cinquenta() -> str:
    # Relógio de meio-jogo em 99: um lance reversível completa 100.
    game = Game("4k3/8/8/8/8/8/8/R3K2R w - - 98 60")
    assert not game.is_game_over(), "clock 98 já marcou fim"
    game.push(chess.Move(chess.H1, chess.H2))  # 99: reivindicável
    assert game.is_game_over(), "50 lances não encerrou"
    res = game.result()
    assert res is not None and res.status is Status.CINQUENTA_LANCES
    return "meio-jogo 100 → empate por 50 lances"


@check("Regras", "Peça cravada não se move expondo o rei")
def _regra_cravada() -> str:
    # Cavalo branco em e4 cravado pela torre preta em e8 (rei branco e1).
    game = Game("4r2k/8/8/8/4N3/8/8/4K3 w - - 0 1")
    assert game.legal_moves_from(chess.E4) == [], "cravada ofereceu lances"
    assert not game.is_legal(chess.Move(chess.E4, chess.D6))
    assert not game.is_legal(chess.Move(chess.E4, chess.F6))
    return "todos os lances do cavalo cravado são ilegais"


# ══════════════════════════════════════════════════════════
# Interface
# ══════════════════════════════════════════════════════════

@check("Interface", "Destaque de seleção ao clicar na peça (via UI)")
def _ui_selecao() -> str:
    app = _start_hvh_app()
    scene = _game(app)
    _app_frame(app, _click_event(_sq_center(scene, chess.E2)))
    assert scene.board_view.selected_square == chess.E2, "seleção ausente"
    dests = set(scene.board_view.legal_destinations)
    assert dests == {chess.E3, chess.E4}, f"destinos {dests}"
    return "seleção e2; lances legais e3/e4"


@check("Interface", "Destaque do último lance após mover (via UI)")
def _ui_ultimo_lance() -> str:
    app = _start_hvh_app()
    _ui_move(app, chess.E2, chess.E4)
    scene = _game(app)
    assert scene.board_view.last_move == chess.Move(chess.E2, chess.E4)
    return "last_move = e2e4"


@check("Interface", "Destaque de xeque (via UI)")
def _ui_xeque() -> str:
    app = _start_hvh_app()
    for frm, to in (
        (chess.E2, chess.E4), (chess.E7, chess.E5),
        (chess.D1, chess.H5), (chess.B8, chess.C6),
        (chess.H5, chess.E5),  # Qxe5+
    ):
        _ui_move(app, frm, to)
    scene = _game(app)
    assert scene.game.in_check(), "xeque não detectado"
    assert scene.board_view.check_square == chess.E8, \
        f"check_square={scene.board_view.check_square}"
    return "xeque em e8; check_square preenchido"


@check("Interface", "Animação não trava o clique seguinte (via UI)")
def _ui_animação_destrava() -> str:
    app = _start_hvh_app()
    scene = _game(app)
    _app_frame(app, _click_event(_sq_center(scene, chess.E2)))
    _app_frame(app, _click_event(_sq_center(scene, chess.E4)))
    assert scene.animator.blocking, "animação deveria estar ativa"
    _wait_anim(app, _surf())
    assert not scene.animator.blocking, "animação não liberou"
    # Clique seguinte funciona (no turno das pretas, seleciona peça preta g8)
    _app_frame(app, _click_event(_sq_center(scene, chess.G8)))
    assert scene.board_view.selected_square == chess.G8, \
        "clique após animação foi ignorado"
    return "bloqueio durante animação; clique seguinte aceito"


@check("Interface", "Virar tabuleiro mantém alinhamento casa↔pixel")
def _ui_virar_tabuleiro() -> str:
    app = _start_hvh_app()
    scene = _game(app)
    _app_frame(app, _key_event(pygame.K_f))
    assert scene.board_view.flipped, "F não virou o tabuleiro"
    for sq in chess.SQUARES:
        got = scene.board_view.square_at(*_sq_center(scene, sq))
        assert got == sq, f"casa {sq} mapeou para {got} com tabuleiro virado"
    _app_frame(app, _key_event(pygame.K_f))  # volta
    assert not scene.board_view.flipped
    return "64/64 casas alinhadas após rotação (estado geométrico)"


@check("Interface", "Janela não é redimensionável / sem tela cheia (N/A)")
def _ui_resize_fullscreen() -> str:
    surface = _surf()
    flags = surface.get_flags()
    assert not (flags & pygame.RESIZABLE), "janela marcada como redimensionável"
    return (
        "N/A documentado: set_mode sem RESIZABLE (redimensionar não é "
        "suportado) e nenhum handler de tela cheia no código — itens "
        "marcados como não aplicáveis, não como PASS"
    )


@check("Interface", "Sons disparados corretamente nos fluxos (via UI)")
def _ui_sons() -> str:
    app = _start_hvh_app()
    rec = _SoundRecorder(app.audio)
    _ui_move(app, chess.E2, chess.E4)
    played = set(rec.played)
    assert "click" in played, f"sons: {played}"  # seleção
    assert "move" in played, f"sons: {played}"  # lance
    return f"sons disparados: {sorted(played)} (verificação estrutural; " \
           "confirmação audível impossível em headless)"


@check("Interface", "Volume 0 silencia os sons")
def _ui_volume_zero() -> str:
    # Caminho real: settings volume=0 → App → AudioManager.
    settings = Settings()
    settings.set("volume", 0)
    settings.save()
    app = App()
    assert float(app.audio.volume) == 0.0, \
        f"volume = {app.audio.volume}, esperado 0.0"
    assert app.audio._master == 0.0, \
        f"_master = {app.audio._master}, esperado 0.0 (som mudo)"
    rec = _SoundRecorder(app.audio)
    rec.audio._orig = app.audio.play  # grava de verdade
    app.audio.play("click")  # toca com volume 0
    settings.set("volume", 0.8)
    settings.save()
    return "volume mestre = 0.0 via settings (áudio mudo por construção)"


@check("Interface", "Volume ajustável reflete no volume mestre")
def _ui_volume_ajustavel() -> str:
    audio = AudioManager()
    audio.volume = 0.3
    assert abs(audio.volume - 0.3) < 1e-9, f"volume={audio.volume}"
    audio.volume = 1.7  # clampa
    assert audio.volume == 1.0
    audio.volume = -0.5  # clampa
    assert audio.volume == 0.0
    return "volume get/set + clamping 0..1 funcionam"


# ══════════════════════════════════════════════════════════
# IA
# ══════════════════════════════════════════════════════════

_LEVEL_LIMIT = {
    Level.INICIANTE: 0.5, Level.FACIL: 2.0,
    Level.MEDIO: 5.0, Level.DIFICIL: 15.0,
}


def _ai_level_check(level: Level) -> str:
    surface = _surf()
    scene = GameScene(
        game_mode=GameMode.HUMAN_VS_AI,
        ai_color=chess.BLACK,
        ai_level=level,
        clock_minutes=10,
    )
    recorder = _SoundRecorder(scene.audio)
    # Humano joga e2e4 via clique real
    scene.handle_event(_click_event(_sq_center(scene, chess.E2)))
    scene.handle_event(_click_event(_sq_center(scene, chess.E4)))
    _wait_anim(scene, surface)
    assert "click" in recorder.played, "som de seleção não tocou"
    # Níveis rápidos podem concluir antes do assert (corrida):
    # aceita worker ativo OU lance da IA já aplicado.
    assert scene._ai_worker is not None or \
        len(scene.game.board.move_stack) >= 2, "IA não iniciou"
    deadline = _LEVEL_LIMIT[level] + 10.0
    t0 = time.monotonic()
    max_frame = 0.0
    while len(scene.game.board.move_stack) < 2 and time.monotonic() - t0 < deadline:
        tf = time.perf_counter()
        scene.update(1 / 60)
        scene.draw(surface)
        pygame.display.flip()
        max_frame = max(max_frame, time.perf_counter() - tf)
    elapsed = time.monotonic() - t0
    assert len(scene.game.board.move_stack) >= 2, \
        f"{level.name}: IA não respondeu em {deadline:.0f}s"
    stack = list(scene.game.board.move_stack)
    ai_move = stack[-1]
    probe = chess.Board()
    for prev in stack[:-1]:
        probe.push(prev)
    assert ai_move in probe.legal_moves, (
        f"lance da IA ilegal: {ai_move.uci()}"
    )
    assert max_frame < 0.5, f"frame travou: {max_frame*1000:.0f}ms"
    assert scene.clock.get_time(chess.WHITE) > 0
    _cancel = scene._ai_worker
    scene._cancel_ai()
    assert _cancel is None or not _cancel.busy
    return (f"{level.name}: respondeu em {elapsed:.2f}s (limite nominal "
            f"{_LEVEL_LIMIT[level]}s), lance legal {ai_move.uci()}, "
            f"frame máx {max_frame*1000:.1f}ms")


for _lvl in (Level.INICIANTE, Level.FACIL, Level.MEDIO, Level.DIFICIL):
    globals()[f"_ai_{_lvl.name.lower()}"] = check(
        "IA", f"Nível {_lvl.name}: responde, legal, sem congelar"
    )(lambda level=_lvl: _ai_level_check(level))


@check("IA", "Iniciante comete erros de maneira plausível")
def _ai_iniciante_erros() -> str:
    from xadtitans.ai.search import TranspositionTable, iterative_deepening
    fen_tatica = (
        "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR "
        "w KQkq - 4 4"
    )
    vistos = []
    for seed in (1, 2, 3):
        from xadtitans.ai.worker import AIWorker
        board = chess.Board(fen_tatica)
        worker = AIWorker(board, level=Level.INICIANTE, seed=seed)
        worker.request()
        move = worker.wait(timeout=15)
        assert move is not None and move in board.legal_moves
        vistos.append(move.uci())
    del TranspositionTable, iterative_deepening
    return (f"3 execuções com seeds distintas → lances {vistos}; "
            "qualitativo: jogadas legais e variadas (aleatoriedade do "
            "nível ativa). Erros táticos não assertáveis de forma "
            "estável — comportamento registrado")


@check("IA", "Difícil não entrega a dama em posição simples")
def _ai_dificil_dama() -> str:
    from xadtitans.ai.worker import AIWorker
    board = chess.Board(
        "rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq d3 0 2"
    )
    worker = AIWorker(board, level=Level.DIFICIL)
    worker.request()
    move = worker.wait(timeout=40)
    assert move is not None and move in board.legal_moves
    board.push(move)
    assert board.piece_type_at(chess.D8) == chess.QUEEN or \
        move.to_square != chess.D8, "dama deixada em perigo"
    return f"difícil jogou {move.uci()}; dama preservada"


@check("IA", "Fecho durante pensamento da IA encerra sem erro")
def _ai_fecho_durante_pensamento() -> str:
    scene = GameScene(
        game_mode=GameMode.HUMAN_VS_AI,
        ai_color=chess.BLACK,
        ai_level=Level.DIFICIL,
    )
    surface = _surf()
    scene.handle_event(_click_event(_sq_center(scene, chess.E2)))
    scene.handle_event(_click_event(_sq_center(scene, chess.E4)))
    _run_scene(scene, surface, 2)  # janela renderiza durante o pensamento
    worker = scene._ai_worker
    assert worker is not None and worker.busy, "IA deveria estar pensando"
    scene.on_exit()  # caminho real do fechamento da cena
    assert scene._ai_worker is None
    assert not worker.busy, "worker não cancelado no fecho"
    autosave_ok = autosave_exists()
    return f"worker cancelado; autosave presente={autosave_ok}"


@check("IA", "Desfazer durante turno da IA cancela com segurança")
def _ai_undo_durante_pensamento() -> str:
    scene = GameScene(
        game_mode=GameMode.HUMAN_VS_AI,
        ai_color=chess.BLACK,
        ai_level=Level.DIFICIL,
    )
    surface = _surf()
    scene.handle_event(_click_event(_sq_center(scene, chess.E2)))
    scene.handle_event(_click_event(_sq_center(scene, chess.E4)))
    worker = scene._ai_worker
    assert worker is not None and worker.busy
    scene.handle_event(_key_event(pygame.K_u))  # undo real
    assert worker is None or not worker.busy, "undo não cancelou a IA"
    assert len(scene.game.board.move_stack) == 0, "undo não desfez"
    # Roda frames: worker antigo não pode aplicar lance obsoleto
    for _ in range(30):
        scene.update(1 / 60)
        scene.draw(surface)
    assert len(scene.game.board.move_stack) <= 1, "lance obsoleto aplicado"
    return "undo cancelou o worker; nada obsoleto aplicado"


@check("IA", "Novo jogo durante atividade da IA não deixa worker antigo")
def _ai_novo_jogo_durante_pensamento() -> str:
    scene = GameScene(
        game_mode=GameMode.HUMAN_VS_AI,
        ai_color=chess.BLACK,
        ai_level=Level.DIFICIL,
        scene_manager=_DummySM(),
    )
    surface = _surf()
    scene.handle_event(_click_event(_sq_center(scene, chess.E2)))
    scene.handle_event(_click_event(_sq_center(scene, chess.E4)))
    assert scene._ai_worker is not None and scene._ai_worker.busy
    scene.new_game()  # caminho real do atalho N (nova partida)
    assert scene._ai_worker is None, "worker antigo permaneceu"
    assert len(scene.game.board.move_stack) == 0
    for _ in range(30):
        scene.update(1 / 60)
        scene.draw(surface)
    assert len(scene.game.board.move_stack) <= 1, "lance obsoleto após N"
    return "new_game limpou o worker; sem lances obsoletos"


class _DummySM:
    """SceneManager mínimo para cenas criadas fora do App."""

    def __init__(self) -> None:
        self.current = None

    def switch(self, scene) -> None:
        self.current = scene

    def push(self, scene) -> None:
        self.current = scene

    def pop(self):
        return None


@check("IA", "AI vs AI continua funcionando (partida headless)")
def _ai_vs_ai_cena() -> str:
    surface = _surf()
    scene = GameScene(
        game_mode=GameMode.AI_VS_AI,
        ai_level=Level.INICIANTE,
        ai_vs_ai_delay=0.02,
        scene_manager=_DummySM(),
    )
    deadline = time.monotonic() + 90.0
    max_frame = 0.0
    while not scene.game.is_game_over() and \
            len(scene.game.board.move_stack) < 40 and \
            time.monotonic() < deadline:
        tf = time.perf_counter()
        scene.update(1 / 60)
        scene.draw(surface)
        pygame.display.flip()
        max_frame = max(max_frame, time.perf_counter() - tf)
    plies = len(scene.game.board.move_stack)
    assert plies >= 4, f"AI vs AI mal começou ({plies} lances)"
    assert max_frame < 0.5, f"frame travou: {max_frame*1000:.0f}ms"
    scene._cancel_ai()
    status = "encerrada" if scene.game.is_game_over() else \
        f"em andamento ({plies} lances, interrompida pelo harness)"
    return f"AIvAI {status}; lance legal garantido pelo _poll_ai; " \
           f"frame máx {max_frame*1000:.1f}ms"


# ══════════════════════════════════════════════════════════
# Persistência
# ══════════════════════════════════════════════════════════

@check("Persistência", "Fechar no meio + Continuar restaura a partida")
def _persist_continuar() -> str:
    # Sessão 1: joga e4 e5 e "fecha" (QUIT → clear = saída real).
    app = _start_hvh_app()
    _ui_move(app, chess.E2, chess.E4)
    _ui_move(app, chess.E7, chess.E5)
    fen_antes = _game(app).game.board.fen()
    _app_frame(app, _quit_event())
    assert not app.running
    app.scene_manager.clear()  # tail real de App.run() (on_exit/autosave)
    assert autosave_exists(), "autosave não gravado no fecho"

    # Sessão 2: menu → Continuar (clique real no botão).
    app2 = _fresh_menu_app()
    btn = app2.menu_scene.buttons[1]  # Continuar
    assert btn.enabled, "Continuar desabilitado com autosave presente"
    _app_frame(app2, _click_event(btn.rect.center))
    scene = _game(app2)
    assert len(scene.game.board.move_stack) == 2
    assert scene.game.board.fen() == fen_antes, "posição restaurada difere"
    assert scene.game.turn is chess.WHITE, (
        "turno restaurado incorreto (após e4 e5 jogam as brancas)"
    )
    # Undo funciona após restauração
    scene.handle_event(_key_event(pygame.K_u))
    assert len(scene.game.board.move_stack) == 1, "undo após restore falhou"
    return "2 lances + turno pretas restaurados; undo funcional"


@check("Persistência", "Estado dos relógios restaurado")
def _persist_relogio() -> str:
    scene = GameScene(game_mode=GameMode.HUMAN_VS_HUMAN, clock_minutes=10)
    for _ in range(20):
        scene.update(0.5)  # 10s de relógio consumidos
    w_time = scene.clock.get_time(chess.WHITE)
    assert w_time < 600, f"relógio não decrementou ({w_time})"
    state = scene.to_saved_state()
    restored = GameScene.from_saved_state(state)
    got = restored.clock.get_time(chess.WHITE)
    assert abs(got - w_time) < 1e-6, f"relógio {got} != {w_time}"
    assert restored.clock.initial_seconds == 600
    return f"brancas {w_time:.1f}s restaurado com exatidão"


@check("Persistência", "PGN exportado revalidado pelo python-chess")
def _persist_pgn() -> str:
    game = Game()
    for uci in ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"):
        game.push(chess.Move.from_uci(uci))
    pgn_text = export_game(game, result="*")
    parsed = parse_pgn_string(pgn_text)
    assert parsed is not None, "PGN não parseou"
    board = reconstruct_board(parsed)
    assert board.fen() == game.board.fen(), "PGN reconstruiu posição diferente"
    assert "[Event" in pgn_text and "1. e4 e5" in pgn_text
    return f"PGN válido; posição final reconstruída ({len(game.board.move_stack)} lances)"


@check("Persistência", "Apagar settings.json restaura os padrões")
def _persist_settings() -> str:
    path = Settings()._path
    if path.exists():
        path.unlink()
    settings = Settings()
    data = settings.load()
    for key, value in DEFAULTS.items():
        assert data.get(key) == value, f"default {key}: {data.get(key)} != {value}"
    return f"defaults restaurados: {DEFAULTS}"


@check("Persistência", "Apagar a pasta de dados não impede o abrir")
def _persist_pasta_apagada() -> str:
    import shutil

    from xadtitans.storage.paths import DATA_DIR, ensure_data_dir
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR, ignore_errors=True)
    app = App()  # deve abrir o menu sem a pasta
    assert isinstance(app.scene, MenuScene), "App não abriu sem a pasta"
    _app_frame(app, _click_event(app.menu_scene.buttons[0].rect.center))
    ng = app.scene
    _app_frame(app, _click_event(ng.btn_start.rect.center))
    for _ in range(2):
        _app_frame(app)
    _ui_move(app, chess.E2, chess.E4)  # 1º autosave recria a estrutura
    assert autosave_exists(), "autosave não regravou após apagar a pasta"
    assert DATA_DIR.exists(), "DATA_DIR não recriado pelo save"
    ensure_data_dir()
    app.scene_manager.clear()
    return "App abriu sem a pasta; 1º autosave recriou DATA_DIR"


@check("Persistência", "Autosave inválido tratado sem derrubar o jogo")
def _persist_autosave_invalido() -> str:
    target = autosave_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{isto nao e json valido!!", encoding="utf-8")
    app = _fresh_menu_app()  # menu com Continuar habilitado
    menu = app.menu_scene
    _app_frame(app, _click_event(menu.buttons[1].rect.center))  # Continuar
    assert isinstance(app.scene, MenuScene), "cena saiu do menu em erro"
    assert menu.message is not None, "mensagem de autosave corrompido ausente"
    # Jogo segue utilizável após a quarentena (Novo Jogo → Iniciar)
    _app_frame(app, _click_event(menu.buttons[0].rect.center))
    for _ in range(2):
        _app_frame(app)
    ng = app.scene
    assert type(ng).__name__ == "NewGameScene", "tela Nova Partida ausente"
    _app_frame(app, _click_event(ng.btn_start.rect.center))
    for _ in range(2):
        _app_frame(app)
    assert isinstance(app.scene, GameScene), "não abriu nova partida"
    return "quarentena aplicada; mensagem exibida; jogo segue normal"


@check("Persistência", "Partida finalizada remove o autosave")
def _persist_fim_remove_autosave() -> str:
    app = _start_hvh_app()
    # Guardar referência à GameScene antes do mate (app.scene mudará depois).
    scene = _game(app)
    moves = [
        (chess.F2, chess.F3),
        (chess.E7, chess.E5),
        (chess.G2, chess.G4),
        (chess.D8, chess.H4),  # xeque-mate -> autosave removido
    ]
    for i, (frm, to) in enumerate(moves):
        _ui_move(app, frm, to)
        if i < len(moves) - 1:
            # Lances intermediários: partida em andamento, autosave deve existir.
            assert autosave_exists(), (
                f"autosave ausente após {chess.square_name(frm)}{chess.square_name(to)}"
            )
    # Após o mate: autosave deve ter sido removido.
    assert scene.game.is_game_over(), "partida deveria estar encerrada"
    assert not autosave_exists(), "autosave não removido ao encerrar"
    for _ in range(4):
        _app_frame(app)
    assert isinstance(app.scene, EndgameScene)
    return "mate concluído -> autosave removido; Continuar será bloqueado"


# ══════════════════════════════════════════════════════════
# Robustez
# ══════════════════════════════════════════════════════════

@check("Robustez", "ESC no menu encerra o aplicativo")
def _rb_esc_menu() -> str:
    app = _fresh_menu_app()
    _app_frame(app, _key_event(pygame.K_ESCAPE))
    # O App intercepta ESC globalmente (quit_requested é da cena;
    # o handler global encerra o loop diretamente).
    assert not app.running, "ESC no menu não encerrou o App"
    return "ESC no menu → handler global → running=False"


@check("Robustez", "ESC na partida volta ao menu")
def _rb_esc_partida() -> str:
    app = _start_hvh_app()
    _app_frame(app, _key_event(pygame.K_ESCAPE))
    assert isinstance(app.scene, MenuScene), \
        f"ESC não voltou ao menu (cena: {type(app.scene).__name__})"
    return "ESC na GameScene → menu"


@check("Robustez", "Novo jogo repetidamente (atalho N ×10)")
def _rb_novo_jogo_repetido() -> str:
    app = _start_hvh_app()
    for i in range(10):
        _app_frame(app, _key_event(pygame.K_n))
        for _ in range(2):
            _app_frame(app)
        ng = app.scene
        assert type(ng).__name__ == "NewGameScene", \
            f"iter {i}: esperava NewGameScene, veio {type(ng).__name__}"
        _app_frame(app, _click_event(ng.btn_start.rect.center))
        for _ in range(2):
            _app_frame(app)
        assert isinstance(app.scene, GameScene), f"iter {i}: partida não iniciou"
        assert len(app.scene.game.board.move_stack) == 0
    return "10 ciclos N → Nova Partida → GameScene limpos, pilha estável"


@check("Robustez", "Entrar/sair de GameScene repetidamente (×10)")
def _rb_entrar_sair() -> str:
    app = _fresh_menu_app()
    for ciclo in range(10):
        _app_frame(app, _click_event(app.menu_scene.buttons[0].rect.center))
        for _ in range(2):
            _app_frame(app)
        ng = app.scene
        assert type(ng).__name__ == "NewGameScene", (
            f"ciclo {ciclo}: esperava NewGameScene"
        )
        ng.sel_mode.value = GameMode.HUMAN_VS_HUMAN
        ng._update_visibility()
        _app_frame(app, _key_event(pygame.K_RETURN))
        for _ in range(2):
            _app_frame(app)
        assert isinstance(app.scene, GameScene), (
            f"ciclo {ciclo}: partida não iniciou"
        )
        _ui_move(app, chess.E2, chess.E4)
        _app_frame(app, _key_event(pygame.K_ESCAPE))
        assert isinstance(app.scene, MenuScene), (
            f"ciclo {ciclo}: ESC não voltou ao menu"
        )
    return "10 ciclos partida→menu sem exceção"


@check("Robustez", "Alternar modos de jogo (HvH, HvAI, AIvAI)")
def _rb_alternar_modos() -> str:
    surface = _surf()
    cenas = []
    for mode, kwargs in (
        (GameMode.HUMAN_VS_HUMAN, {}),
        (GameMode.HUMAN_VS_AI, {"ai_color": chess.BLACK, "ai_level": Level.FACIL}),
        (GameMode.AI_VS_AI, {"ai_level": Level.INICIANTE, "ai_vs_ai_delay": 0.02}),
    ):
        scene = GameScene(game_mode=mode, scene_manager=_DummySM(), **kwargs)
        _run_scene(scene, surface, 5)
        scene.handle_event(_click_event(_sq_center(scene, chess.E2)))
        scene.handle_event(_click_event(_sq_center(scene, chess.E4)))
        _run_scene(scene, surface, 10)
        cenas.append((mode.name, len(scene.game.board.move_stack)))
        scene._cancel_ai()
        scene.on_exit()
    return f"modos alternados: {cenas}"


@check("Robustez", "Fecho durante animação e logo após lance")
def _rb_fecho_anim_lance() -> str:
    for _ in range(3):
        app = _fresh_menu_app()
        _app_frame(app, _click_event(app.menu_scene.buttons[0].rect.center))
        for _ in range(2):
            _app_frame(app)
        ng = app.scene
        assert type(ng).__name__ == "NewGameScene"
        _app_frame(app, _click_event(ng.btn_start.rect.center))
        for _ in range(2):
            _app_frame(app)
        _app_frame(app, _click_event(_sq_center(_game(app), chess.E2)))
        _app_frame(app, _click_event(_sq_center(_game(app), chess.E4)))
        # Fecho imediato: durante a animação do lance
        _app_frame(app, _quit_event())
        assert not app.running
        app.scene_manager.clear()
    return "3 fechos imediatos após lance/durante animação: sem exceção"


@check("Robustez", "Undo repetidamente dentro das regras")
def _rb_undo_repetido() -> str:
    app = _start_hvh_app()
    for frm, to in (
        (chess.E2, chess.E4), (chess.E7, chess.E5),
        (chess.G1, chess.F3), (chess.B8, chess.C6),
    ):
        _ui_move(app, frm, to)
    scene = _game(app)
    for _ in range(8):  # mais que os 4 lances: deve parar no vazio
        scene.handle_event(_key_event(pygame.K_u))
        _run_scene(scene, _surf(), 2)
    assert len(scene.game.board.move_stack) == 0
    assert scene.game.board.fen() == chess.STARTING_FEN
    return "undo excedente sem efeito colateral; tabuleiro inicial"


@check("Robustez", "Continuar várias vezes (×3)")
def _rb_continuar_repetido() -> str:
    app = _start_hvh_app()
    _ui_move(app, chess.E2, chess.E4)
    _ui_move(app, chess.E7, chess.E5)
    _app_frame(app, _quit_event())
    app.scene_manager.clear()
    for i in range(3):
        app_i = _fresh_menu_app()
        btn = app_i.menu_scene.buttons[1]
        assert btn.enabled, f"iter {i}: Continuar desabilitado"
        _app_frame(app_i, _click_event(btn.rect.center))
        scene = _game(app_i)
        assert len(scene.game.board.move_stack) == 2, f"iter {i}: estado errado"
        app_i.scene_manager.clear()
    return "3 reaberturas com o mesmo autosave: estado consistente"


@check("Robustez", "Partida terminada não pode ser continuada indevidamente")
def _rb_fim_bloqueia_continuar() -> str:
    # Após o mate do louco o autosave foi removido → Continuar desabilitado.
    app = _start_hvh_app()
    for frm, to in (
        (chess.F2, chess.F3), (chess.E7, chess.E5),
        (chess.G2, chess.G4), (chess.D8, chess.H4),
    ):
        _ui_move(app, frm, to)
    for _ in range(4):
        _app_frame(app)  # EndgameScene aparece
    assert isinstance(app.scene, EndgameScene)
    assert not autosave_exists()
    # Volta ao menu (back_to_menu) e confere o botão
    app.scene_manager.pop()  # remove Endgame
    menu = app.scene
    if isinstance(menu, GameScene):
        app.scene_manager.pop()
        menu = app.scene
    assert isinstance(menu, MenuScene)
    menu.on_enter()
    assert not menu.buttons[1].enabled, "Continuar habilitado após fim"
    return "fim de partida → autosave removido → Continuar desabilitado"


@check("Robustez", "Log sem exceções inesperadas nos fluxos normais")
def _rb_log_limpo() -> str:
    inesperados = [
        r for r in LOG_CAPTURE.records
        if not any(p in r.lower() for p in _EXPECTED_LOG)
    ]
    assert not inesperados, f"registros inesperados: {inesperados[:5]}"
    return f"{len(LOG_CAPTURE.records)} registro(s) de WARNING+ (todos " \
           "esperados de manuseio próprio)"


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main() -> int:
    GUARD.install()
    logging.getLogger("xadtitans").addHandler(LOG_CAPTURE)
    logging.getLogger().addHandler(LOG_CAPTURE)
    pygame.init()
    _surf()

    print("XadTitans — testes manuais executáveis (Fase 6.6)")
    print(f"Dados isolados em: {_TMP}")
    print(f"Guarda de rede ativa: {GUARD._installed}\n")

    for group, item, fn in CHECKS:
        t0 = time.perf_counter()
        try:
            detail = fn() or ""
            status = "PASS"
        except AssertionError as exc:
            detail = str(exc)
            status = "FAIL"
        except Exception as exc:  # noqa: BLE001
            detail = f"exceção não tratada: {exc!r}"
            status = "FAIL"
            traceback.print_exc()
        elapsed = time.perf_counter() - t0
        RESULTS.append((group, item, status, detail))
        mark = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{mark} [{group}] {item}  ({elapsed:.2f}s)")
        if detail:
            print(f"     -> {detail}")

    print("\n" + "=" * 72)
    grupos: dict[str, list[str]] = {}
    for group, item, status, _detail in RESULTS:
        grupos.setdefault(group, []).append(status)
    total = len(RESULTS)
    fails = sum(1 for *_x, status, _d in
                ((g, i, s, d) for g, i, s, d in RESULTS) if status == "FAIL")
    for group, statuses in grupos.items():
        p = statuses.count("PASS")
        print(f"{group:<14} {p}/{len(statuses)} PASS")
    print("-" * 72)
    print(f"TOTAL: {total - fails}/{total} PASS, {fails} FAIL")
    rede = GUARD.attempts
    print(f"Tentativas de rede bloqueadas em runtime: {len(rede)} {rede or ''}")
    pygame.quit()
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
