"""Testes de robustez e persistência (Etapa 5.6).

Cobre:
  - Autosave: criação, atualização, atomicidade, conteúdo,
    versionamento, remoção após partida finalizada;
  - Continue: autosave válido, sem autosave, corrompido,
    incompatível, restauração do estado;
  - HvAI/HvH/AIvAI: restauração (posição, turno, relógio, undo,
    perspectiva, retomada da IA sem geração antiga);
  - Corrupção: JSON inválido, vazio, tipos errados, campos
    ausentes, valores inválidos, versão desconhecida;
  - Logging: criação, mensagens, traceback, rotação, limite;
  - Exceção global: registro, encerramento controlado,
    autosave de preservação, mensagem amigável;
  - Fechamento: partida em andamento, finalizada, falha de autosave;
  - Menus: Continuar, Nova Partida (invalida autosave), retorno ao menu.

Isolamento: ``tests/conftest.py`` aponta ``XADTITANS_DATA`` para um
diretório temporário — nada toca o ``%APPDATA%`` real.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import chess
import pygame
import pytest

import xadtitans.utils.logger as logger_mod
from xadtitans.core.types import GameMode, Level
from xadtitans.storage import autosave as asv
from xadtitans.storage.autosave import (
    SAVE_VERSION,
    autosave_exists,
    delete_autosave,
    load_state,
    save_state,
)
from xadtitans.storage.paths import DATA_DIR, autosave_file, autosave_path
from xadtitans.ui.scene_manager import SceneManager
from xadtitans.ui.scenes import game_scene as gs_mod
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.scenes.menu_scene import MenuScene
from xadtitans.ui.scenes.new_game_scene import NewGameScene

_surf: pygame.Surface | None = None


def _get_surface() -> pygame.Surface:
    global _surf
    if _surf is None:
        pygame.init()
        _surf = pygame.display.set_mode((1024, 768))
    return _surf


def _clear_autosave() -> None:
    """Remove autosave (e quarentena) entre os testes."""
    if autosave_path().exists():
        for f in autosave_path().iterdir():
            f.unlink(missing_ok=True)


def _valid_state(**overrides: object) -> dict:
    """Estado válido padrão (HvH, 5 min, um lance e2e4)."""
    state = {
        "mode": "human_vs_human",
        "ai_color": None,
        "ai_level": "medio",
        "clock_minutes": 5,
        "clock_increment": 3,
        "white_time": 297.0,
        "black_time": 300.0,
        "flipped": True,
        "moves": ["e2e4"],
        "clock_history": [[300.0, 300.0]],
    }
    state.update(overrides)
    return state


def _make_scene(
    mode: GameMode = GameMode.HUMAN_VS_HUMAN,
    ai_color: chess.Color | None = None,
    clock_minutes: int = 5,
    clock_increment: int = 3,
    ai_level: Level = Level.MEDIO,
) -> GameScene:
    _get_surface()
    return GameScene(
        game_mode=mode,
        ai_color=ai_color,
        clock_minutes=clock_minutes,
        clock_increment=clock_increment,
        ai_level=ai_level,
    )


@pytest.fixture(autouse=True)
def _isolated_autosave():
    """Cada teste começa sem autosave e termina limpando o diretório."""
    _clear_autosave()
    yield
    _clear_autosave()


# ════════════════════════════════════════════════════════
# Autosave — gravação, conteúdo, atomicidade
# ════════════════════════════════════════════════════════


class TestAutosaveWrite:
    def test_save_creates_versioned_file(self) -> None:
        save_state(_valid_state())
        assert autosave_exists()
        raw = json.loads(autosave_file().read_text(encoding="utf-8"))
        assert raw["version"] == SAVE_VERSION
        assert raw["mode"] == "human_vs_human"
        assert raw["moves"] == ["e2e4"]

    def test_save_is_atomic_no_tmp_leftover(self) -> None:
        save_state(_valid_state())
        save_state(_valid_state(moves=[]))
        # Nenhum temporário deve sobrar no diretório de autosave.
        files = {f.name for f in autosave_path().iterdir()}
        assert files == {"game.json"}

    def test_save_overwrites_previous(self) -> None:
        save_state(_valid_state(moves=["e2e4"]))
        save_state(_valid_state(moves=["e2e4", "e7e5"]))
        raw = json.loads(autosave_file().read_text(encoding="utf-8"))
        assert raw["moves"] == ["e2e4", "e7e5"]

    def test_roundtrip_content(self) -> None:
        state = _valid_state()
        save_state(state)
        loaded = load_state()
        assert loaded is not None
        assert loaded["mode"] == state["mode"]
        assert loaded["ai_color"] is None
        assert loaded["ai_level"] == "medio"
        assert loaded["clock_minutes"] == 5
        assert loaded["clock_increment"] == 3
        assert loaded["white_time"] == 297.0
        assert loaded["black_time"] == 300.0
        assert loaded["flipped"] is True
        assert loaded["moves"] == ["e2e4"]
        assert loaded["clock_history"] == [(300.0, 300.0)]

    def test_delete_removes_autosave(self) -> None:
        save_state(_valid_state())
        delete_autosave()
        assert not autosave_exists()

    def test_delete_without_file_is_noop(self) -> None:
        delete_autosave()  # não deve lançar
        assert not autosave_exists()

    def test_save_failure_raises_for_caller(self) -> None:
        # Falha de gravação: a exceção propaga para quem chamou decidir
        # (o GameScene._autosave registra no log e segue o jogo).
        original = asv.autosave_file
        asv.autosave_file = lambda: Path("Z:/inexistente/x/y/game.json")  # type: ignore[assignment]
        try:
            with pytest.raises(OSError):
                save_state(_valid_state())
        finally:
            asv.autosave_file = original  # type: ignore[assignment]


# ════════════════════════════════════════════════════════
# Autosave — corrupção e recuperação
# ════════════════════════════════════════════════════════


class TestAutosaveCorruption:
    def _write_raw(self, content: str) -> None:
        autosave_path().mkdir(parents=True, exist_ok=True)
        autosave_file().write_text(content, encoding="utf-8")

    def _assert_quarantined(self) -> None:
        assert not autosave_exists()
        quarantined = list(autosave_path().glob("corrupt_*.json"))
        assert len(quarantined) == 1

    def test_missing_file_returns_none(self) -> None:
        assert load_state() is None

    def test_invalid_json_quarantined(self) -> None:
        self._write_raw("{isto não é json")
        assert load_state() is None
        self._assert_quarantined()

    def test_empty_file_quarantined(self) -> None:
        self._write_raw("")
        assert load_state() is None
        self._assert_quarantined()

    def test_empty_json_object_quarantined(self) -> None:
        self._write_raw("{}")
        assert load_state() is None
        self._assert_quarantined()

    def test_json_array_instead_of_object(self) -> None:
        self._write_raw(json.dumps([_valid_state()]))
        assert load_state() is None
        self._assert_quarantined()

    def test_unknown_version_rejected(self) -> None:
        save_state(_valid_state())
        raw = json.loads(autosave_file().read_text(encoding="utf-8"))
        raw["version"] = 999
        autosave_file().write_text(json.dumps(raw), encoding="utf-8")
        assert load_state() is None
        self._assert_quarantined()

    @pytest.mark.parametrize(
        "key",
        [
            "mode",
            "ai_color",
            "ai_level",
            "clock_minutes",
            "clock_increment",
            "white_time",
            "black_time",
            "flipped",
        ],
    )
    def test_missing_required_field(self, key: str) -> None:
        state = _valid_state()
        state.pop(key)
        save_state(state)
        assert load_state() is None
        self._assert_quarantined()

    @pytest.mark.parametrize(
        ("key", "bad"),
        [
            ("mode", "pvp"),
            ("mode", 1),
            ("ai_color", "green"),
            ("ai_level", "mestre"),
            ("ai_level", 3),
            ("clock_minutes", "5"),
            ("clock_minutes", True),
            ("clock_minutes", -1),
            ("clock_increment", -2),
            ("white_time", "300"),
            ("white_time", -1),
            ("black_time", -0.5),
            ("flipped", "sim"),
            ("flipped", 1),
        ],
    )
    def test_wrong_types_and_values(self, key: str, bad: object) -> None:
        save_state(_valid_state(**{key: bad}))
        assert load_state() is None
        self._assert_quarantined()

    def test_illegal_move_sequence_rejected(self) -> None:
        save_state(_valid_state(moves=["e2e5"]))  # e2→e5 é ilegal
        assert load_state() is None
        self._assert_quarantined()

    def test_non_string_moves_rejected(self) -> None:
        save_state(_valid_state(moves=[42]))
        assert load_state() is None
        self._assert_quarantined()

    def test_finished_game_rejected(self) -> None:
        # Mate do pastor: posição final não pode ser continuada.
        save_state(_valid_state(moves=["f2f3", "e7e5", "g2g4", "d8h4"]))
        assert load_state() is None
        self._assert_quarantined()

    def test_bad_clock_history_degrades_gracefully(self) -> None:
        # Histórico do relógio é auxiliar: malformado → None, partida OK.
        save_state(_valid_state(clock_history=[[1.0]]))  # tamanho errado
        loaded = load_state()
        assert loaded is not None
        assert loaded["clock_history"] is None

    def test_ai_color_ignored_outside_hvai(self) -> None:
        # ai_color só faz sentido no modo vs IA — nos outros é ignorado.
        save_state(_valid_state(mode="ai_vs_ai", ai_color="white"))
        loaded = load_state()
        assert loaded is not None
        assert loaded["ai_color"] is None

    def test_zero_clock_normalizes_times(self) -> None:
        save_state(
            _valid_state(
                mode="human_vs_ai",
                ai_color="black",
                clock_minutes=0,
                clock_increment=0,
                white_time=123.0,
                black_time=456.0,
            )
        )
        loaded = load_state()
        assert loaded is not None
        assert loaded["white_time"] == 0.0
        assert loaded["black_time"] == 0.0


# ════════════════════════════════════════════════════════
# GameScene — gravação do autosave nos momentos corretos
# ════════════════════════════════════════════════════════


class TestGameSceneAutosaveTriggers:
    def test_autosave_after_move(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        state = load_state()
        assert state is not None
        assert state["moves"] == ["e2e4"]
        assert state["mode"] == "human_vs_human"
        assert state["clock_minutes"] == 5
        assert state["clock_increment"] == 3
        assert state["white_time"] == 303.0  # incremento aplicado

    def test_autosave_updated_after_undo(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs.undo()
        state = load_state()
        assert state is not None
        assert state["moves"] == []

    def test_autosave_removed_after_checkmate(self) -> None:
        gs = _make_scene(clock_minutes=0, clock_increment=0)
        for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):  # mate do pastor
            gs._apply_move(chess.Move.from_uci(uci))
        assert gs.game.is_game_over()
        assert not autosave_exists()

    def test_autosave_removed_after_resign(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert autosave_exists()
        gs.resign()
        assert not autosave_exists()

    def test_autosave_removed_after_timeout(self) -> None:
        gs = _make_scene(clock_minutes=1)
        gs.clock.set_time(chess.WHITE, 0.0)
        gs.update(0.01)
        assert gs.game.is_game_over()
        assert not autosave_exists()

    def test_autosave_removed_after_draw_agreement(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs._request_draw()
        gs._accept_draw()
        assert gs.game.is_game_over()
        assert not autosave_exists()

    def test_new_game_invalidates_previous_autosave(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert autosave_exists()
        gs.new_game()
        state = load_state()
        assert state is not None
        assert state["moves"] == []

    def test_on_exit_saves_in_progress_game(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs.on_exit()
        state = load_state()
        assert state is not None
        assert state["moves"] == ["e2e4"]

    def test_on_exit_removes_finished_game(self) -> None:
        gs = _make_scene(clock_minutes=0, clock_increment=0)
        for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
            gs._apply_move(chess.Move.from_uci(uci))
        gs.on_exit()
        assert not autosave_exists()

    def test_pgn_loaded_scene_does_not_autosave(self) -> None:
        # Cenas vindas do Carregar (PGN) não podem sobrescrever o autosave.
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert autosave_exists()
        gs._autosave_enabled = False  # como a LoadScene faz
        gs._apply_move(chess.Move.from_uci("e7e5"))
        # Autosave continua com o estado anterior (do jogo real).
        state = load_state()
        assert state is not None
        assert state["moves"] == ["e2e4"]

    def test_autosave_failure_does_not_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        gs = _make_scene()
        # Patchar a referência importada pelo game_scene (não o módulo).
        monkeypatch.setattr(
            gs_mod, "save_state", MagicMock(side_effect=OSError("disco cheio"))
        )
        gs._apply_move(chess.Move.from_uci("e2e4"))  # não deve lançar
        assert len(gs.game.board.move_stack) == 1
        # Falha registrada no log
        for h in logger_mod.get_logger().handlers:
            h.flush()
        content = logger_mod.log_path().read_text(encoding="utf-8")
        assert "Falha ao gravar autosave" in content


# ════════════════════════════════════════════════════════
# GameScene.from_saved_state — restauração
# ════════════════════════════════════════════════════════


class TestRestore:
    def test_restore_hvh_full_state(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs._apply_move(chess.Move.from_uci("e7e5"))
        state = load_state()
        assert state is not None

        rs = GameScene.from_saved_state(state)
        # Posição e turno
        assert len(rs.game.board.move_stack) == 2
        assert rs.game.turn == chess.WHITE
        # Relógio
        assert rs.clock.get_time(chess.WHITE) == pytest.approx(303.0)
        assert rs.clock.get_time(chess.BLACK) == pytest.approx(303.0)
        assert rs.clock.initial_seconds == pytest.approx(300.0)
        assert rs.clock.increment == pytest.approx(3.0)
        # Modo
        assert rs.game_mode == GameMode.HUMAN_VS_HUMAN
        # Perspectiva: turno das brancas → não virado
        assert not rs.board_view.flipped
        # Sem IA
        assert rs._ai_worker is None

    def test_restore_hvh_perspective(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))  # turno das pretas
        state = load_state()
        assert state is not None
        rs = GameScene.from_saved_state(state)
        assert rs.game.turn == chess.BLACK
        assert rs.board_view.flipped  # perspectiva das pretas

    def test_restore_undo_history_and_clock(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs._apply_move(chess.Move.from_uci("e7e5"))
        state = load_state()
        assert state is not None
        rs = GameScene.from_saved_state(state)
        # Undo restaura relógio salvo do histórico
        rs.undo()
        assert len(rs.game.board.move_stack) == 1
        assert rs.clock.get_time(chess.BLACK) == pytest.approx(300.0)
        rs.undo()
        assert rs.clock.get_time(chess.WHITE) == pytest.approx(300.0)

    def test_restore_hvai_human_turn(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs._apply_move(chess.Move.from_uci("e7e5"))  # resposta da IA
        state = load_state()
        assert state is not None
        assert state["ai_color"] == "black"
        rs = GameScene.from_saved_state(state)
        assert rs.game.turn == chess.WHITE  # humano
        assert rs._ai_worker is None  # não é turno da IA
        assert rs.ai_level == Level.MEDIO
        assert rs._black_is_ai and not rs._white_is_ai

    def test_restore_hvai_ai_turn_resumes_search(self) -> None:
        # Salvo no turno da IA (IA ainda não respondeu).
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        state = load_state()
        assert state is not None
        assert state["moves"] == ["e2e4"]

        rs = GameScene.from_saved_state(state)
        assert rs.game.turn == chess.BLACK
        # IA retomou a busca na posição restaurada
        assert rs._ai_worker is not None
        rs._ai_worker.cancel()
        # Posição não avançou sozinha
        assert len(rs.game.board.move_stack) == 1
    def test_restore_hvai_old_generation_never_reapplies(self) -> None:
        # Cena antiga com worker em andamento; ao restaurar, nenhuma
        # resposta da sessão antiga pode alterar a cena nova.
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        old_worker = gs._ai_worker
        assert old_worker is not None

        state = load_state()
        assert state is not None
        rs = GameScene.from_saved_state(state)
        assert rs._ai_worker is not None
        assert rs._ai_worker is not old_worker
        rs._ai_worker.cancel()
        # O worker antigo pertence à cena descartada: ninguém mais faz
        # poll dele — resposta antiga não pode reaparecer na cena nova.

    def test_restore_hvai_ai_reply_applies_to_restored_scene(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        state = load_state()
        assert state is not None
        rs = GameScene.from_saved_state(state)
        rs._ai_worker.cancel()
        # Simular resposta pronta na cena restaurada
        worker = MagicMock()
        worker.busy = False
        worker.poll.return_value = chess.Move.from_uci("e7e5")
        rs._ai_worker = worker
        rs._poll_ai()
        assert len(rs.game.board.move_stack) == 2

    def test_restore_aivai_resumes(self) -> None:
        gs = _make_scene(mode=GameMode.AI_VS_AI, clock_minutes=0, clock_increment=0)
        gs._cancel_ai()  # controlar o fluxo no teste
        gs._apply_move(chess.Move.from_uci("e2e4"))
        state = load_state()
        assert state is not None
        assert state["mode"] == "ai_vs_ai"
        rs = GameScene.from_saved_state(state)
        assert rs._white_is_ai and rs._black_is_ai
        assert rs.game.turn == chess.BLACK
        # IA retoma imediatamente na posição restaurada
        assert rs._ai_worker is not None
        rs._ai_worker.cancel()

    def test_restore_human_as_black_perspective(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        gs._cancel_ai()  # controlar o fluxo no teste
        # Humano de pretas: tabuleiro começa virado.
        gs._apply_move(chess.Move.from_uci("e2e4"))  # IA (brancas)
        state = load_state()
        assert state is not None
        rs = GameScene.from_saved_state(state)
        assert rs.board_view.flipped  # perspectiva do humano (pretas)
        assert rs.game.turn == chess.BLACK  # humano


# ════════════════════════════════════════════════════════
# Menu — Continuar / Nova Partida
# ════════════════════════════════════════════════════════


class TestMenuContinue:
    def _menu(self, sm: SceneManager) -> MenuScene:
        menu = MenuScene(sm)
        sm.push(menu)
        return menu

    def test_continue_with_valid_autosave(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = self._menu(sm)
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs._apply_move(chess.Move.from_uci("e7e5"))
        gs.on_exit()
        assert autosave_exists()

        menu._on_continue()
        current = sm.current
        assert isinstance(current, GameScene)
        assert current is not gs
        assert len(current.game.board.move_stack) == 2
        assert current.game.turn == chess.WHITE
        assert current.clock.get_time(chess.WHITE) == pytest.approx(303.0)
        sm.clear()

    def test_continue_without_autosave_shows_message(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = self._menu(sm)
        menu._on_continue()
        assert menu.message is not None
        assert sm.current is menu
        sm.clear()

    def test_continue_with_corrupt_autosave_shows_message(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = self._menu(sm)
        autosave_path().mkdir(parents=True, exist_ok=True)
        autosave_file().write_text("}{ json quebrado", encoding="utf-8")

        menu._on_continue()
        assert menu.message is not None  # aviso ao usuário
        assert sm.current is menu  # permanece no menu
        assert not autosave_exists()  # corrompido foi para quarentena
        assert list(autosave_path().glob("corrupt_*.json"))
        # Aplicativo segue utilizável: continuar de novo informa ausência
        menu._on_continue()
        sm.clear()

    def test_continue_with_incompatible_version_shows_message(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = self._menu(sm)
        save_state(_valid_state())
        raw = json.loads(autosave_file().read_text(encoding="utf-8"))
        raw["version"] = SAVE_VERSION + 1
        autosave_file().write_text(json.dumps(raw), encoding="utf-8")

        menu._on_continue()
        assert menu.message is not None
        assert sm.current is menu
        sm.clear()

    def test_new_game_from_menu_invalidates_autosave(self) -> None:
        _get_surface()
        sm = SceneManager()
        self._menu(sm)
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs.on_exit()
        assert autosave_exists()

        ng = NewGameScene(sm)
        sm.push(ng)
        ng._start_game()
        state = load_state()
        assert state is not None
        assert state["moves"] == []  # partida antiga invalidada
        sm.clear()

    def test_continue_button_disabled_without_autosave(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = self._menu(sm)
        continue_btn = next(
            b for b in menu.buttons if b.text == "Continuar"
        )
        assert continue_btn.enabled is False
        sm.clear()

    def test_continue_button_enabled_with_autosave(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = self._menu(sm)
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        menu._build_buttons()  # refletir o autosave recém-criado
        continue_btn = next(
            b for b in menu.buttons if b.text == "Continuar"
        )
        assert continue_btn.enabled is True
        sm.clear()


# ════════════════════════════════════════════════════════
# Logging
# ════════════════════════════════════════════════════════


class TestLogging:
    def _reset(self) -> None:
        logger_mod.reset_logger()

    def teardown_method(self) -> None:
        self._reset()

    def test_log_file_created_in_data_dir(self) -> None:
        self._reset()
        logger_mod.get_logger()
        assert logger_mod.log_path().exists()
        assert logger_mod.log_path().parent.parent == DATA_DIR

    def test_log_records_messages_with_timestamp_and_level(self) -> None:
        self._reset()
        log = logger_mod.get_logger()
        log.info("mensagem de teste 5.6")
        for h in log.handlers:
            h.flush()
        content = logger_mod.log_path().read_text(encoding="utf-8")
        assert "mensagem de teste 5.6" in content
        assert "INFO" in content

    def test_log_records_traceback(self) -> None:
        self._reset()
        log = logger_mod.get_logger()
        try:
            raise ValueError("erro simulado para o log")
        except ValueError:
            log.exception("capturado")
        for h in log.handlers:
            h.flush()
        content = logger_mod.log_path().read_text(encoding="utf-8")
        assert "Traceback" in content
        assert "ValueError" in content

    def test_log_rotation_and_backup_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset()
        # Rotação com tamanho pequeno para o teste ser rápido.
        monkeypatch.setattr(logger_mod, "_MAX_BYTES", 512)
        monkeypatch.setattr(logger_mod, "_BACKUP_COUNT", 1)
        log = logger_mod.get_logger()

        payload = "x" * 128
        for _ in range(40):  # bem mais que 2 × 512 bytes
            log.info(payload)
        for h in log.handlers:
            h.flush()

        files = sorted(f.name for f in logger_mod.log_dir().iterdir())
        # xadtitans.log + no máximo backup_count arquivos antigos
        assert "xadtitans.log" in files
        assert len([f for f in files if f.startswith("xadtitans.log.")]) <= 1
        # O arquivo ativo não cresce sem limite
        assert logger_mod.log_path().stat().st_size <= 512 + 4096

    def test_invalid_log_level_falls_back_to_info(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XADTITANS_LOG_LEVEL", "NIVEL_QUE_NAO_EXISTE")
        self._reset()
        log = logger_mod.get_logger()
        assert log.level == logging.INFO

    def test_level_configurable_via_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XADTITANS_LOG_LEVEL", "DEBUG")
        self._reset()
        log = logger_mod.get_logger()
        assert log.level == logging.DEBUG


# ════════════════════════════════════════════════════════
# Tratamento global de exceções / fechamento
# ════════════════════════════════════════════════════════


class _PoisonScene:
    """Cena que lança exceção no update (erro fatal simulado)."""

    def __init__(self) -> None:
        self.calls = 0

    def handle_event(self, event: object) -> None:
        self.calls += 1

    def update(self, dt: float) -> None:
        raise RuntimeError("erro fatal simulado no update")

    def draw(self, surface: object) -> None:
        self.calls += 1


class TestGlobalExceptionHandling:
    def _app(self, monkeypatch: pytest.MonkeyPatch):
        _get_surface()
        monkeypatch.setattr("xadtitans.app.App._show_error_screen", lambda self, msg: None)
        from xadtitans.app import App

        app = App()
        return app

    def test_fatal_error_logged_and_controlled_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = self._app(monkeypatch)
        app.scene_manager.push(_PoisonScene())
        code = app.run()
        assert code == 1  # encerramento controlado com código de erro
        assert app.running is False
        # Traceback registrado no log
        content = logger_mod.log_path().read_text(encoding="utf-8")
        assert "erro fatal simulado no update" in content
        assert "Traceback" in content

    def test_fatal_error_preserves_game_via_autosave(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = self._app(monkeypatch)
        gs = _make_scene()
        app.scene_manager.push(gs)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        # Simular que o lance ainda não foi gravado quando o erro ocorreu.
        delete_autosave()
        assert not autosave_exists()

        app.scene_manager.push(_PoisonScene())
        app.run()
        state = load_state()
        assert state is not None
        assert state["moves"] == ["e2e4"]

    def test_close_window_saves_in_progress_game(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = self._app(monkeypatch)
        gs = _make_scene()
        app.scene_manager.push(gs)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        delete_autosave()  # provar que o fechamento grava

        pygame.event.post(pygame.event.Event(pygame.QUIT))
        code = app.run()
        assert code == 0
        state = load_state()
        assert state is not None
        assert state["moves"] == ["e2e4"]

    def test_close_window_removes_finished_game(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = self._app(monkeypatch)
        gs = _make_scene(clock_minutes=0, clock_increment=0)
        app.scene_manager.push(gs)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs.resign()
        assert gs.game.is_game_over()

        pygame.event.post(pygame.event.Event(pygame.QUIT))
        app.run()
        assert not autosave_exists()

    def test_autosave_failure_does_not_block_closing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = self._app(monkeypatch)
        gs = _make_scene()
        app.scene_manager.push(gs)
        gs._apply_move(chess.Move.from_uci("e2e4"))

        monkeypatch.setattr(
            gs_mod, "save_state", MagicMock(side_effect=OSError("disco cheio"))
        )
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        code = app.run()  # não deve lançar; fecha normalmente
        assert code == 0
        # Falha registrada no log
        for h in logger_mod.get_logger().handlers:
            h.flush()
        content = logger_mod.log_path().read_text(encoding="utf-8")
        assert "Falha ao gravar autosave" in content

    def test_main_wraps_startup_errors(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        import logging.handlers

        import main as main_mod

        # O handler de stderr do logger é só para desenvolvimento:
        # removê-lo para checar que o usuário final não vê traceback.
        log = logger_mod.get_logger()
        for h in list(log.handlers):
            if not isinstance(h, logging.handlers.RotatingFileHandler):
                log.removeHandler(h)

        monkeypatch.setattr(
            main_mod, "App", MagicMock(side_effect=RuntimeError("sem display"))
        )
        code = main_mod.main()
        assert code == 1
        out = capsys.readouterr().err
        assert "Erro" in out  # mensagem amigável, não traceback
        assert "Traceback" not in out
        # Traceback completo no log
        content = logger_mod.log_path().read_text(encoding="utf-8")
        assert "sem display" in content
        assert "Traceback" in content
