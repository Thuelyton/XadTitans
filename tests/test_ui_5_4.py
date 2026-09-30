"""Testes para Menus, Telas e Integração da UI (Etapa 5.4).

Cobre:
  - Integração do SceneManager ao App;
  - MenuScene (opções, desabilitação, navegação);
  - NewGameScene (3 modos, escolha de lados, dificuldade, validação);
  - SettingsScene (leitura, edição, salvamento e reset de configurações via UI);
  - StatsScene (leitura e exibição de estatísticas via UI);
  - LoadScene e comportamento de Continuar/Carregar (sem autosave / sem PGNs / com PGNs);
  - Navegação e comportamento do ESC em todas as telas;
  - Transições GameScene ↔ EndgameScene ↔ MenuScene.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import chess
import pygame
import pytest

from xadtitans.app import App
from xadtitans.core.types import GameMode, Level
from xadtitans.storage.settings import Settings
from xadtitans.storage.stats import Stats
from xadtitans.ui.scene_manager import SceneManager
from xadtitans.ui.scenes.endgame_scene import EndgameScene
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.scenes.load_scene import LoadScene
from xadtitans.ui.scenes.menu_scene import MenuScene
from xadtitans.ui.scenes.new_game_scene import NewGameScene
from xadtitans.ui.scenes.settings_scene import SettingsScene
from xadtitans.ui.scenes.stats_scene import StatsScene

_surf: pygame.Surface | None = None


def _get_surface() -> pygame.Surface:
    global _surf
    if _surf is None:
        pygame.init()
        _surf = pygame.display.set_mode((1024, 768))
    return _surf


class TestAppSceneManagerIntegration:
    """Testes de integração do SceneManager com o App."""

    def test_app_initialization_with_scene_manager(self) -> None:
        _get_surface()
        app = App()
        assert app.scene_manager is not None
        assert app.scene_manager.count == 1
        assert isinstance(app.scene_manager.current, MenuScene)
        assert isinstance(app.scene, MenuScene)

    def test_app_scene_setter_retrocompatibility(self) -> None:
        _get_surface()
        app = App()
        mock_scene = MagicMock()
        app.scene = mock_scene
        assert app.scene is mock_scene
        assert app.scene_manager.count == 1

    def test_app_esc_on_menu_requests_quit(self) -> None:
        _get_surface()
        app = App()
        assert app.running is True
        app._handle_global_escape()
        assert app.running is False

    def test_app_esc_on_game_scene_pops_to_menu(self) -> None:
        _get_surface()
        app = App()
        game_scene = GameScene()
        app.scene_manager.push(game_scene)
        assert app.scene_manager.count == 2
        assert isinstance(app.scene_manager.current, GameScene)

        app._handle_global_escape()
        assert app.scene_manager.count == 1
        assert isinstance(app.scene_manager.current, MenuScene)

    def test_app_game_over_pushes_endgame_scene(self) -> None:
        _get_surface()
        app = App()
        game_scene = GameScene()
        app.scene_manager.push(game_scene)

        # Xeque-mate rápido (Fools Mate: 1. f3 e5 2. g4 Qh4#)
        game_scene.game.push(chess.Move.from_uci("f2f3"))
        game_scene.game.push(chess.Move.from_uci("e7e5"))
        game_scene.game.push(chess.Move.from_uci("g2g4"))
        game_scene.game.push(chess.Move.from_uci("d8h4"))
        assert game_scene.game_over is True

        app._switch_scenes_if_needed()
        assert app.scene_manager.count == 3
        assert isinstance(app.scene_manager.current, EndgameScene)


class TestMenuScene:
    """Testes do Menu Principal."""

    def test_menu_buttons_initialization(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)

        assert len(menu.buttons) == 6
        labels = [b.text for b in menu.buttons]
        assert "Novo Jogo" in labels
        assert "Configurações" in labels
        assert "Estatísticas" in labels
        assert "Sair" in labels

    def test_menu_navigate_to_new_game(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)

        menu._on_new_game()
        assert sm.count == 2
        assert isinstance(sm.current, NewGameScene)

    def test_menu_navigate_to_settings(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)

        menu._on_settings()
        assert sm.count == 2
        assert isinstance(sm.current, SettingsScene)

    def test_menu_navigate_to_stats(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)

        menu._on_stats()
        assert sm.count == 2
        assert isinstance(sm.current, StatsScene)

    def test_menu_navigate_to_load(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)

        menu._on_load()
        assert sm.count == 2
        assert isinstance(sm.current, LoadScene)

    def test_menu_quit_action(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        assert menu.quit_requested is False
        menu._on_quit()
        assert menu.quit_requested is True

    def test_menu_continue_without_autosave_shows_message(self, tmp_path: Path) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        menu._on_continue()
        assert menu.message is not None


class TestNewGameScene:
    """Testes da tela de Nova Partida."""

    def test_new_game_creation_human_vs_human(self) -> None:
        _get_surface()
        sm = SceneManager()
        ng = NewGameScene(sm)
        sm.push(ng)

        ng.sel_mode.value = GameMode.HUMAN_VS_HUMAN
        ng._update_visibility()
        assert ng.sel_side.enabled is False
        assert ng.sel_level.enabled is False

        ng._start_game()
        assert sm.count == 1
        assert isinstance(sm.current, GameScene)
        game_scene: GameScene = sm.current
        assert game_scene.game_mode == GameMode.HUMAN_VS_HUMAN

    def test_new_game_creation_human_vs_ai_white(self) -> None:
        _get_surface()
        sm = SceneManager()
        ng = NewGameScene(sm)
        sm.push(ng)

        ng.sel_mode.value = GameMode.HUMAN_VS_AI
        ng.sel_side.value = "white"
        ng.sel_level.value = Level.FACIL
        ng._update_visibility()

        ng._start_game()
        game_scene: GameScene = sm.current
        assert isinstance(game_scene, GameScene)
        assert game_scene.game_mode == GameMode.HUMAN_VS_AI
        assert game_scene.ai_level == Level.FACIL
        # Humano é Brancas -> IA é Pretas (chess.BLACK)
        assert game_scene._black_is_ai is True
        assert game_scene._white_is_ai is False

    def test_new_game_creation_human_vs_ai_black(self) -> None:
        _get_surface()
        sm = SceneManager()
        ng = NewGameScene(sm)
        sm.push(ng)

        ng.sel_mode.value = GameMode.HUMAN_VS_AI
        ng.sel_side.value = "black"
        ng.sel_level.value = Level.DIFICIL
        ng._update_visibility()

        ng._start_game()
        game_scene: GameScene = sm.current
        assert isinstance(game_scene, GameScene)
        assert game_scene.game_mode == GameMode.HUMAN_VS_AI
        assert game_scene.ai_level == Level.DIFICIL
        # Humano é Pretas -> IA é Brancas (chess.WHITE)
        assert game_scene._white_is_ai is True
        assert game_scene._black_is_ai is False

    def test_new_game_creation_ai_vs_ai(self) -> None:
        _get_surface()
        sm = SceneManager()
        ng = NewGameScene(sm)
        sm.push(ng)

        ng.sel_mode.value = GameMode.AI_VS_AI
        ng.sel_level.value = Level.INICIANTE
        ng._update_visibility()

        ng._start_game()
        game_scene: GameScene = sm.current
        assert isinstance(game_scene, GameScene)
        assert game_scene.game_mode == GameMode.AI_VS_AI
        assert game_scene._white_is_ai is True
        assert game_scene._black_is_ai is True

    def test_new_game_esc_returns_to_menu(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)
        ng = NewGameScene(sm)
        sm.push(ng)

        assert sm.count == 2
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        ng.handle_event(event)

        assert sm.count == 1
        assert sm.current is menu


class TestSettingsScene:
    """Testes da tela de Configurações e integração com storage."""

    def test_settings_load_and_save_via_ui(self, tmp_path: Path) -> None:
        _get_surface()
        file_path = tmp_path / "settings.json"
        st = Settings(file_path)

        sm = SceneManager()
        scene = SettingsScene(sm, settings=st)
        sm.push(scene)

        # Alterar valores na UI
        scene.sel_volume.value = 0.4
        scene.sel_speed.value = 1.5
        scene.sel_fps.value = 60
        scene.sel_hints.value = False

        scene._save_settings()

        # Verificar arquivo gravado no storage
        assert file_path.exists()
        loaded_st = Settings(file_path)
        loaded_st.load()
        assert loaded_st.get("volume") == 0.4
        assert loaded_st.get("animation_speed") == 1.5
        assert loaded_st.get("fps") == 60
        assert loaded_st.get("visual_hints") is False

    def test_settings_reset_defaults_via_ui(self, tmp_path: Path) -> None:
        _get_surface()
        file_path = tmp_path / "settings.json"
        st = Settings(file_path)
        st.set("fps", 120)
        st.save()

        sm = SceneManager()
        scene = SettingsScene(sm, settings=st)
        sm.push(scene)

        assert scene.sel_fps.value == 120
        scene._reset_defaults()

        assert scene.sel_fps.value == 30
        assert st.get("fps") == 30

    def test_settings_esc_returns_to_menu(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)
        scene = SettingsScene(sm)
        sm.push(scene)

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        scene.handle_event(event)
        assert sm.count == 1
        assert sm.current is menu


class TestStatsScene:
    """Testes da tela de Estatísticas."""

    def test_stats_display_from_storage(self, tmp_path: Path) -> None:
        _get_surface()
        file_path = tmp_path / "stats.json"
        stats_obj = Stats(file_path)
        stats_obj.record_win("human_vs_ai", level="medio")
        stats_obj.record_loss("human_vs_ai", level="medio")
        stats_obj.record_draw("ai_vs_ai", level="facil")
        stats_obj.save()

        sm = SceneManager()
        scene = StatsScene(sm, stats=stats_obj)
        sm.push(scene)

        tot = scene.stats.get_total()
        assert tot["wins"] == 1
        assert tot["losses"] == 1
        assert tot["draws"] == 1

        mode_stats = scene.stats.get_mode("human_vs_ai")
        assert mode_stats["wins"] == 1
        assert mode_stats["losses"] == 1

    def test_stats_esc_returns_to_menu(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)
        scene = StatsScene(sm)
        sm.push(scene)

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        scene.handle_event(event)
        assert sm.count == 1
        assert sm.current is menu


class TestLoadScene:
    """Testes da tela de Carregar PGNs."""

    def test_load_scene_no_pgns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _get_surface()
        monkeypatch.setattr("xadtitans.ui.scenes.load_scene.list_pgn_files", list)

        sm = SceneManager()
        scene = LoadScene(sm)
        sm.push(scene)

        assert len(scene.pgn_files) == 0
        assert len(scene.file_buttons) == 0

    def test_load_scene_with_pgns(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _get_surface()
        dummy_pgn = tmp_path / "partida_test.pgn"
        dummy_pgn.write_text('[Event "Test"]\n\n1. e4 e5 2. Nf3 Nc6\n', encoding="utf-8")
        monkeypatch.setattr("xadtitans.ui.scenes.load_scene.list_pgn_files", lambda: [dummy_pgn])

        sm = SceneManager()
        scene = LoadScene(sm)
        sm.push(scene)

        assert len(scene.file_buttons) == 1
        path, _btn = scene.file_buttons[0]
        assert path == dummy_pgn

        # Simula o clique no botão do PGN
        scene._load_pgn_file(path)
        assert sm.count == 1
        assert isinstance(sm.current, GameScene)


class TestEndgameSceneNavigation:
    """Testes de navegação e atalhos na EndgameScene."""

    def test_endgame_enter_restarts_game(self) -> None:
        _get_surface()
        sm = SceneManager()
        gs = GameScene()
        sm.push(gs)
        es = EndgameScene(gs, sm)
        sm.push(es)

        assert sm.count == 2
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        es.handle_event(event)

        assert sm.count == 1
        assert sm.current is gs

    def test_endgame_esc_returns_to_menu(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)
        gs = GameScene()
        sm.push(gs)
        es = EndgameScene(gs, sm)
        sm.push(es)

        assert sm.count == 3
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        es.handle_event(event)

        assert sm.count == 1
        assert sm.current is menu
