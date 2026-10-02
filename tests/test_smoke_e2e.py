"""Smoke test E2E headless + regressão do atalho N — Etapa 6.3.

Simula, sem janela gráfica real (SDL dummy), a experiência principal
do usuário:

  App → Menu → Nova Partida → lances válidos → atalho N →
  nova partida → finalização → fechamento → reabertura →
  Continue → restauração → desistência/finalização.

Contratos validados do atalho N:

  - N substitui a GameScene (nunca acumula GameScenes na pilha);
  - a partida abandonada tem IA/dicas canceladas e autosave gravado;
  - o autosave da nova partida não herda estado da antiga;
  - ESC após N volta ao menu (não a uma partida antiga);
  - Continue restaura somente o autosave válido da partida atual.

Determinístico: sem sleeps — eventos pygame sintéticos e os caminhos
reais de código (botões, teclas, ciclo de vida de cenas via
SceneManager). O conftest.py isola o diretório de dados por teste.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import chess
import pygame

from xadtitans.app import App
from xadtitans.core.types import GameMode, Level
from xadtitans.storage.autosave import autosave_exists, load_state
from xadtitans.ui.scene_manager import SceneManager
from xadtitans.ui.scenes.endgame_scene import EndgameScene
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.scenes.menu_scene import MenuScene
from xadtitans.ui.scenes.new_game_scene import NewGameScene

_surf: pygame.Surface | None = None


def _screen() -> pygame.Surface:
    """Garante vídeo dummy ativo (recria o display se o pygame reiniciar)."""
    global _surf
    if _surf is None or not pygame.display.get_init():
        pygame.init()
        _surf = pygame.display.set_mode((1024, 768))
    return _surf


def _key(key: int) -> pygame.event.Event:
    """Evento KEYDOWN sintético (padrão da suíte)."""
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def _click(button) -> None:
    """Clique real de mouse no retângulo central do botão."""
    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center
    )
    button.handle_event(event)


def _game_scenes(sm: SceneManager) -> list[GameScene]:
    """GameScenes presentes na pilha (na ordem da pilha)."""
    return [s for s in sm.scenes if isinstance(s, GameScene)]


def _moves(scene: GameScene) -> list[str]:
    """Lances UCI já aplicados na partida da cena."""
    return [m.uci() for m in scene.game.board.move_stack]


def _play(scene: GameScene, *ucis: str) -> None:
    """Aplica lances pelo caminho real da cena (``_apply_move``)."""
    for uci in ucis:
        scene._apply_move(chess.Move.from_uci(uci))


def _open_new_game_screen(app: App) -> NewGameScene:
    """Abre Nova Partida pelo botão real do menu."""
    menu = app.scene_manager.current
    assert isinstance(menu, MenuScene)
    _click(menu.buttons[0])  # "Novo Jogo"
    ng = app.scene_manager.current
    assert isinstance(ng, NewGameScene)
    return ng


def _start_from_screen(
    ng: NewGameScene,
    mode: GameMode,
    *,
    side: str = "white",
    level: Level = Level.INICIANTE,
) -> GameScene:
    """Configura os seletores e inicia com Enter (caminho do usuário)."""
    ng.sel_mode.value = mode
    if mode == GameMode.HUMAN_VS_AI:
        ng.sel_side.value = side
    ng.sel_level.value = level
    ng._update_visibility()
    ng.handle_event(_key(pygame.K_RETURN))
    gs = ng.scene_manager.current
    assert isinstance(gs, GameScene)
    return gs


def _start_new_game(
    app: App,
    mode: GameMode = GameMode.HUMAN_VS_HUMAN,
    *,
    side: str = "white",
    level: Level = Level.INICIANTE,
) -> GameScene:
    """Fluxo completo menu → Nova Partida → GameScene."""
    return _start_from_screen(_open_new_game_screen(app), mode, side=side, level=level)


# ════════════════════════════════════════════════════════════
# Smoke ponta a ponta
# ════════════════════════════════════════════════════════════


class TestSmokeFluxoPrincipal:
    """Experiência real do usuário, do App aberto ao fechamento."""

    def test_smoke_ponta_a_ponta(self) -> None:
        _screen()

        # 1-2. Inicialização do App e entrada no Menu.
        app = App()
        assert isinstance(app.scene_manager.current, MenuScene)
        assert app.scene_manager.count == 1

        # 3-5. Nova Partida, lances válidos e GameScene correta na pilha.
        g1 = _start_new_game(app)
        assert app.scene_manager.count == 2
        assert app.scene_manager.current is g1
        assert _game_scenes(app.scene_manager) == [g1]

        _play(g1, "e2e4", "e7e5")
        assert _moves(g1) == ["e2e4", "e7e5"]
        assert g1.game.san_history == ["e4", "e5"]

        # 6-7. Atalho N: NewGameScene no topo, GameScene antiga fora.
        g1.handle_event(_key(pygame.K_n))
        assert isinstance(app.scene_manager.current, NewGameScene)
        assert app.scene_manager.count == 2  # [Menu, NewGame] — não acumula
        assert _game_scenes(app.scene_manager) == []

        # 8-9. Partida anterior abandonada: sem IA/dicas órfãs.
        assert g1._ai_worker is None
        assert g1._hint_worker is None

        # 10-11. Nova partida: autosave sem resíduos e progride normalmente.
        g2 = _start_from_screen(app.scene_manager.current, GameMode.HUMAN_VS_HUMAN)
        assert g2 is not g1
        assert app.scene_manager.count == 2
        assert _game_scenes(app.scene_manager) == [g2]
        state = load_state()
        assert state is not None
        assert state["moves"] == []  # nada da partida abandonada persistiu

        _play(g2, "f2f3")
        assert load_state()["moves"] == ["f2f3"]

        # 12-13. Finalizar partida (Fool's Mate: 1.f3 e5 2.g4 Qh4#).
        _play(g2, "e7e5", "g2g4", "d8h4")
        assert g2.game_over is True
        assert not autosave_exists()  # fim de partida remove o autosave

        # Mecanismo real do App para empilhar o fim de partida.
        app._switch_scenes_if_needed()
        assert isinstance(app.scene_manager.current, EndgameScene)

        # 14. Fechar o aplicativo (caminho real de encerramento).
        app.running = False
        assert app.run() == 0

        # 15. Reabrir: sem autosave válido → Continue desabilitado.
        _screen()
        app2 = App()
        assert isinstance(app2.scene_manager.current, MenuScene)
        assert app2.menu_scene.buttons[1].enabled is False

        # Criar partida em andamento e fechar → autosave válido gerado.
        g3 = _start_new_game(app2)
        _play(g3, "e2e4", "e7e5")
        app2.running = False
        assert app2.run() == 0
        assert autosave_exists()
        assert load_state()["moves"] == ["e2e4", "e7e5"]

        # 16-17. Reabrir e usar Continue → restauração do estado.
        _screen()
        app3 = App()
        assert app3.menu_scene.buttons[1].enabled is True
        _click(app3.menu_scene.buttons[1])  # "Continuar"
        g4 = app3.scene_manager.current
        assert isinstance(g4, GameScene)
        assert _moves(g4) == ["e2e4", "e7e5"]
        assert g4.game_mode == GameMode.HUMAN_VS_HUMAN
        assert g4._autosave_enabled is True

        # Jogar sobre a posição restaurada: autosave acompanha a nova
        # progressão (a partida restaurada é a partida atual).
        _play(g4, "d2d4")
        assert load_state()["moves"] == ["e2e4", "e7e5", "d2d4"]

        # 18. Finalizar/abandonar: desistência encerra e remove autosave.
        g4.handle_event(_key(pygame.K_r))
        assert g4.game_over is True
        assert not autosave_exists()
        app3._switch_scenes_if_needed()
        assert isinstance(app3.scene_manager.current, EndgameScene)

        # 19. Encerramento sem exceções não tratadas (exit code 0).
        app3.running = False
        assert app3.run() == 0


# ════════════════════════════════════════════════════════════
# Regressão do atalho N
# ════════════════════════════════════════════════════════════


class TestAtalhoN:
    """O atalho N substitui a partida; nunca acumula GameScenes."""

    def test_n_uma_vez_substitui_gamescene(self) -> None:
        _screen()
        app = App()
        g1 = _start_new_game(app)

        g1.handle_event(_key(pygame.K_n))

        sm = app.scene_manager
        assert isinstance(sm.current, NewGameScene)
        assert sm.count == 2  # [Menu, NewGame] — sem a GameScene antiga
        assert _game_scenes(sm) == []
        assert all(s is not g1 for s in sm.scenes)

    def test_n_repetido_pilha_estavel(self) -> None:
        _screen()
        app = App()
        _start_new_game(app)
        sm = app.scene_manager

        for _ in range(5):
            gs = sm.current
            assert isinstance(gs, GameScene)
            gs.handle_event(_key(pygame.K_n))
            assert isinstance(sm.current, NewGameScene)
            assert sm.count == 2
            sm.current.handle_event(_key(pygame.K_RETURN))
            assert isinstance(sm.current, GameScene)
            assert sm.count == 2
            assert len(_game_scenes(sm)) == 1

        # Pilha final estável: [Menu, Game] — nada acumulou indefinidamente.
        assert sm.count == 2
        assert isinstance(sm.scenes[0], MenuScene)

    def test_n_durante_ia_cancela_worker_e_stale_ignorado(self) -> None:
        _screen()
        app = App()
        # Humano de Pretas → IA (Brancas) começa a pensar (DIFICIL = lenta).
        g1 = _start_new_game(
            app, GameMode.HUMAN_VS_AI, side="black", level=Level.DIFICIL
        )
        worker = g1._ai_worker
        assert worker is not None  # busca em andamento no momento do N

        g1.handle_event(_key(pygame.K_n))

        # IA/dicas da partida abandonada foram canceladas.
        assert g1._ai_worker is None
        assert g1._hint_worker is None
        assert not worker.busy

        # Resultado stale do worker antigo não altera a partida antiga...
        worker._result_queue.put(chess.Move.from_uci("e2e4"))
        g1.update(0.1)
        assert _moves(g1) == []  # cena antiga é inerte

        # ...nem a nova partida (worker próprio, objeto diferente).
        g2 = _start_from_screen(
            app.scene_manager.current,
            GameMode.HUMAN_VS_AI,
            side="black",
            level=Level.INICIANTE,
        )
        assert g2 is not g1
        assert g2._ai_worker is not None
        assert g2._ai_worker is not worker
        assert _moves(g2) == []

    def test_n_esc_retorna_ao_menu_e_nao_partida_antiga(self) -> None:
        _screen()
        app = App()
        g1 = _start_new_game(app)
        _play(g1, "e2e4")

        g1.handle_event(_key(pygame.K_n))
        assert isinstance(app.scene_manager.current, NewGameScene)

        # ESC global (caminho real do App): destino correto = menu.
        app._handle_global_escape()
        sm = app.scene_manager
        assert sm.count == 1
        assert isinstance(sm.current, MenuScene)
        assert not any(isinstance(s, GameScene) for s in sm.scenes)

    def test_autosave_partida_abandonada_nao_sobrescreve_nova(self) -> None:
        _screen()
        app = App()
        g1 = _start_new_game(app)
        _play(g1, "e2e4")
        assert load_state()["moves"] == ["e2e4"]

        g1.handle_event(_key(pygame.K_n))

        # on_exit da partida abandonada gravou o estado dela...
        state = load_state()
        assert state is not None
        assert state["moves"] == ["e2e4"]

        # ...mas a nova partida sobrescreve imediatamente ao começar.
        g2 = _start_from_screen(app.scene_manager.current, GameMode.HUMAN_VS_HUMAN)
        assert load_state()["moves"] == []

        # A progressão persistida é só da nova partida.
        _play(g2, "d2d4")
        state = load_state()
        assert state is not None
        assert state["moves"] == ["d2d4"]


# ════════════════════════════════════════════════════════════
# Continue / autosave
# ════════════════════════════════════════════════════════════


class TestContinueAutosave:
    """Continue restaura somente o autosave válido da partida atual."""

    def test_continue_restaura_estado_apos_reabertura(self) -> None:
        _screen()
        app = App()
        g1 = _start_new_game(app)
        _play(g1, "e2e4", "e7e5")

        # Fechamento preserva a partida em andamento (via on_exit).
        app.running = False
        assert app.run() == 0
        assert autosave_exists()

        _screen()
        app2 = App()
        assert app2.menu_scene.buttons[1].enabled is True
        _click(app2.menu_scene.buttons[1])  # "Continuar"

        gs = app2.scene_manager.current
        assert isinstance(gs, GameScene)
        assert _moves(gs) == ["e2e4", "e7e5"]
        assert gs.game_mode == GameMode.HUMAN_VS_HUMAN
        assert gs._autosave_enabled is True

        # Jogar sobre a restaurada: autosave acompanha a nova progressão.
        _play(gs, "d2d4")
        assert load_state()["moves"] == ["e2e4", "e7e5", "d2d4"]

        app2.running = False
        assert app2.run() == 0
