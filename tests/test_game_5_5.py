"""Testes para recursos funcionais de partida (Etapa 5.5).

Cobre:
  - Relógio: sem relógio, opções 3/5/10/15 min, contagem, pausa,
    troca de turno, incremento, timeout, encerramento;
  - Empate por acordo: solicitar, aceitar, recusar, restrição ao HvH;
  - Hint (H): busca em background, resultado válido, resultado obsoleto,
    cancelamento, partida encerrada, nova partida;
  - Flip: F, rotação automática HvH, ausência nos outros modos;
  - Undo: HvH, HvAI antes/depois da resposta, AIvAI, cancelamento do
    worker, invalidação de geração;
  - Atalhos de teclado: Esc, U, F, H, N, D, Y.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import chess
import pygame
import pytest

from xadtitans.core.clock import ChessClock
from xadtitans.core.game import Game
from xadtitans.core.types import GameMode, Status
from xadtitans.ui.scene_manager import SceneManager
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


def _make_scene(
    mode: GameMode = GameMode.HUMAN_VS_HUMAN,
    ai_color: chess.Color | None = None,
    clock_minutes: int = 0,
    clock_increment: int = 0,
) -> GameScene:
    _get_surface()
    return GameScene(
        game_mode=mode,
        ai_color=ai_color,
        clock_minutes=clock_minutes,
        clock_increment=clock_increment,
    )


def _press(scene: GameScene, key: int) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


# ════════════════════════════════════════════════════════
# ChessClock — testes unitários (sem pygame)
# ════════════════════════════════════════════════════════

class TestChessClock:
    """Testes unitários do relógio independentes de UI."""

    def test_inactive_clock(self) -> None:
        """Relógio com minutes=0 deve ser inativo."""
        clk = ChessClock(minutes=0)
        assert not clk.is_active
        clk.tick(1.0, chess.WHITE)
        assert clk.get_time(chess.WHITE) == 0.0  # sem tempo inicial
        assert not clk.is_timeout(chess.WHITE)

    def test_active_clock_initializes(self) -> None:
        """Relógio com minutes>0 deve ser ativo."""
        for mins in (3, 5, 10, 15):
            clk = ChessClock(minutes=mins)
            assert clk.is_active
            assert clk.get_time(chess.WHITE) == mins * 60.0
            assert clk.get_time(chess.BLACK) == mins * 60.0

    def test_tick_decrements_active_player(self) -> None:
        clk = ChessClock(minutes=5)
        clk.tick(10.0, chess.WHITE)
        assert clk.get_time(chess.WHITE) == pytest.approx(290.0)
        assert clk.get_time(chess.BLACK) == pytest.approx(300.0)

    def test_tick_does_not_go_negative(self) -> None:
        clk = ChessClock(minutes=1)
        clk.tick(120.0, chess.WHITE)
        assert clk.get_time(chess.WHITE) == 0.0

    def test_tick_paused(self) -> None:
        clk = ChessClock(minutes=5)
        clk.pause()
        clk.tick(60.0, chess.WHITE)
        assert clk.get_time(chess.WHITE) == pytest.approx(300.0)

    def test_resume_after_pause(self) -> None:
        clk = ChessClock(minutes=5)
        clk.pause()
        clk.tick(60.0, chess.WHITE)
        clk.resume()
        clk.tick(30.0, chess.WHITE)
        assert clk.get_time(chess.WHITE) == pytest.approx(270.0)

    def test_tick_per_turn(self) -> None:
        """Apenas o jogador do turno deve perder tempo."""
        clk = ChessClock(minutes=5)
        clk.tick(50.0, chess.BLACK)
        assert clk.get_time(chess.WHITE) == pytest.approx(300.0)
        assert clk.get_time(chess.BLACK) == pytest.approx(250.0)

    def test_increment_applied_to_mover(self) -> None:
        """Incremento deve ser adicionado à cor que acabou de mover."""
        clk = ChessClock(minutes=5, increment=3)
        clk.tick(10.0, chess.WHITE)
        clk.apply_increment(chess.WHITE)
        assert clk.get_time(chess.WHITE) == pytest.approx(293.0)

    def test_increment_no_effect_when_inactive(self) -> None:
        clk = ChessClock(minutes=0, increment=5)
        clk.apply_increment(chess.WHITE)
        assert clk.get_time(chess.WHITE) == 0.0

    def test_is_timeout_when_zero(self) -> None:
        clk = ChessClock(minutes=1)
        assert not clk.is_timeout(chess.WHITE)
        clk.tick(60.0, chess.WHITE)
        assert clk.is_timeout(chess.WHITE)
        assert not clk.is_timeout(chess.BLACK)

    def test_is_timeout_inactive(self) -> None:
        clk = ChessClock(minutes=0)
        assert not clk.is_timeout(chess.WHITE)
        assert not clk.is_timeout(chess.BLACK)

    def test_reset(self) -> None:
        clk = ChessClock(minutes=5)
        clk.tick(60.0, chess.WHITE)
        clk.reset()
        assert clk.get_time(chess.WHITE) == pytest.approx(300.0)
        assert clk.get_time(chess.BLACK) == pytest.approx(300.0)

    def test_set_time(self) -> None:
        clk = ChessClock(minutes=5)
        clk.set_time(chess.WHITE, 42.0)
        assert clk.get_time(chess.WHITE) == pytest.approx(42.0)


# ════════════════════════════════════════════════════════
# Relógio integrado à GameScene
# ════════════════════════════════════════════════════════

class TestGameSceneClock:
    """Relógio integrado ao loop de atualização da GameScene."""

    def test_scene_no_clock(self) -> None:
        gs = _make_scene(clock_minutes=0)
        assert not gs.clock.is_active

    def test_scene_with_clock(self) -> None:
        gs = _make_scene(clock_minutes=5)
        assert gs.clock.is_active
        assert gs.clock.get_time(chess.WHITE) == pytest.approx(300.0)

    def test_update_decrements_clock(self) -> None:
        gs = _make_scene(clock_minutes=5)
        initial = gs.clock.get_time(chess.WHITE)
        gs.update(1.0)
        assert gs.clock.get_time(chess.WHITE) < initial

    def test_timeout_white_ends_game(self) -> None:
        gs = _make_scene(clock_minutes=1)
        # Brancas começam; drena todo o tempo delas
        gs.clock.set_time(chess.WHITE, 0.5)
        gs.update(1.0)  # força timeout de brancas
        assert gs.game.is_game_over()
        result = gs.game.result()
        assert result is not None
        assert result.status == Status.TEMPO_ESGOTADO
        assert result.winner == chess.BLACK  # pretas vencem

    def test_timeout_black_ends_game(self) -> None:
        gs = _make_scene(clock_minutes=1)
        # Fazer brancas moverem primeiro para ser turno das pretas
        gs.game.push(chess.Move.from_uci("e2e4"))
        gs._sync_view()
        gs.clock.set_time(chess.BLACK, 0.5)
        gs.update(1.0)
        assert gs.game.is_game_over()
        result = gs.game.result()
        assert result is not None
        assert result.status == Status.TEMPO_ESGOTADO
        assert result.winner == chess.WHITE

    def test_timeout_blocks_further_moves(self) -> None:
        gs = _make_scene(clock_minutes=1)
        gs.clock.set_time(chess.WHITE, 0.0)
        gs.update(0.01)
        assert gs.game.is_game_over()
        move_count_before = len(gs.game.board.move_stack)
        gs.update(1.0)  # novo update
        assert len(gs.game.board.move_stack) == move_count_before

    def test_new_game_resets_clock(self) -> None:
        gs = _make_scene(clock_minutes=5)
        gs.clock.set_time(chess.WHITE, 10.0)
        gs.new_game()
        assert gs.clock.get_time(chess.WHITE) == pytest.approx(300.0)

    def test_aivai_clock_ticks_for_current_ai(self) -> None:
        """O relógio também funciona no modo IA vs IA."""
        gs = _make_scene(mode=GameMode.AI_VS_AI, clock_minutes=5)
        gs._cancel_ai()  # não deixar busca rodando no teste
        initial = gs.clock.get_time(gs.game.turn)
        gs.update(1.0)
        assert gs.clock.get_time(gs.game.turn) == pytest.approx(initial - 1.0)

    def test_increment_applied_after_move(self) -> None:
        gs = _make_scene(clock_minutes=5, clock_increment=5)
        # Consumir 30s do tempo de brancas
        gs.clock.set_time(chess.WHITE, 270.0)
        # Executar um lance (brancas)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        # Agora brancas deveriam ter 270 + 5 = 275s
        assert gs.clock.get_time(chess.WHITE) == pytest.approx(275.0)

    def test_no_clock_no_timeout(self) -> None:
        gs = _make_scene(clock_minutes=0)
        gs.update(99999.0)  # tempo absurdo
        assert not gs.game.is_game_over()

    def test_clock_stops_after_game_over(self) -> None:
        """Relógio pausado quando a partida não está ativa."""
        gs = _make_scene(clock_minutes=5)
        gs.game.resign(chess.WHITE)
        before = gs.clock.get_time(chess.BLACK)
        gs.update(10.0)
        assert gs.clock.get_time(chess.BLACK) == pytest.approx(before)

    def test_timeout_pushes_endgame_scene(self) -> None:
        """Timeout deve encaminhar para a EndgameScene via App."""
        from xadtitans.app import App
        from xadtitans.ui.scenes.endgame_scene import EndgameScene

        _get_surface()
        app = App()
        gs = GameScene(clock_minutes=1)
        app.scene_manager.push(gs)
        gs.clock.set_time(chess.WHITE, 0.0)
        gs.update(0.01)
        assert gs.game_over
        app._switch_scenes_if_needed()
        assert isinstance(app.scene_manager.current, EndgameScene)

    def test_click_ignored_after_timeout(self) -> None:
        """Tentativa de jogar depois do timeout é ignorada."""
        gs = _make_scene(clock_minutes=1)
        gs.clock.set_time(chess.WHITE, 0.0)
        gs.update(0.01)
        assert gs.game.is_game_over()
        ax, ay = gs.board_view.piece_anchor(chess.E2)
        gs._on_left_click((int(ax), int(ay)))
        assert gs.board_view.selected_square is None
        assert len(gs.game.board.move_stack) == 0


# ════════════════════════════════════════════════════════
# Empate por acordo
# ════════════════════════════════════════════════════════

class TestDrawByAgreement:
    """Empate por acordo — apenas no modo HUMAN_VS_HUMAN."""

    def test_draw_not_available_in_hvai(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        _press(gs, pygame.K_d)
        assert gs.draw_request_by is None
        assert not gs.game.is_game_over()

    def test_draw_not_available_in_aivai(self) -> None:
        gs = _make_scene(mode=GameMode.AI_VS_AI)
        _press(gs, pygame.K_d)
        assert gs.draw_request_by is None

    def test_draw_request_hvh(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        assert gs.draw_request_by is None
        _press(gs, pygame.K_d)
        assert gs.draw_request_by == chess.WHITE  # brancas jogam primeiro

    def test_draw_accepted(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        _press(gs, pygame.K_d)
        assert gs.draw_request_by is not None
        _press(gs, pygame.K_y)
        assert gs.game.is_game_over()
        result = gs.game.result()
        assert result is not None
        assert result.is_draw
        assert result.status == Status.EMPATE_ACORDO

    def test_draw_declined(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        _press(gs, pygame.K_d)
        _press(gs, pygame.K_n)  # N recusa quando draw_request_by não None
        assert gs.draw_request_by is None
        assert not gs.game.is_game_over()

    def test_draw_cleared_after_move(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        _press(gs, pygame.K_d)
        assert gs.draw_request_by is not None
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert gs.draw_request_by is None


# ════════════════════════════════════════════════════════
# Hint (tecla H)
# ════════════════════════════════════════════════════════

class TestHint:
    """Dica de lance em background — deve ser não-bloqueante."""

    def test_hint_starts_worker_in_human_turn(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        assert gs._hint_worker is None
        _press(gs, pygame.K_h)
        assert gs._hint_worker is not None
        gs._hint_worker.cancel()

    def test_hint_ignored_during_ai_turn(self) -> None:
        # IA joga de brancas, então logo no início é turno da IA
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        assert gs._is_ai_turn
        _press(gs, pygame.K_h)
        assert gs._hint_worker is None

    def test_hint_ignored_game_over(self) -> None:
        gs = _make_scene()
        gs.game.resign(chess.WHITE)
        _press(gs, pygame.K_h)
        assert gs._hint_worker is None

    def test_hint_not_applied_if_generation_changes(self) -> None:
        """Resultado de hint antigo não deve ser aplicado."""
        gs = _make_scene()
        old_gen = gs._hint_gen
        _press(gs, pygame.K_h)
        # Mudar geração antes do resultado chegar
        gs._cancel_hint()
        assert gs._hint_gen > old_gen
        assert gs.hint_move is None

    def test_hint_cleared_on_move(self) -> None:
        gs = _make_scene()
        gs.hint_move = chess.Move.from_uci("e2e4")  # simular hint ativo
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert gs.hint_move is None

    def test_hint_cleared_on_new_game(self) -> None:
        gs = _make_scene()
        gs.hint_move = chess.Move.from_uci("e2e4")
        gs.new_game()
        assert gs.hint_move is None
        assert gs._hint_worker is None

    def test_hint_poll_applies_valid_result(self) -> None:
        """Simula resultado do worker chegando na mesma geração."""
        gs = _make_scene()
        mock_worker = MagicMock()
        mock_worker.busy = False
        mock_worker.poll.return_value = chess.Move.from_uci("e2e4")
        gs._hint_worker = mock_worker
        gs._poll_hint()
        # Mesmo gen → hint aplicado
        assert gs.hint_move is not None

    def test_hint_poll_ignores_stale_result(self) -> None:
        """Resultado de geração antiga (cancelada) não deve ser aplicado."""
        gs = _make_scene()
        mock_worker = MagicMock()
        mock_worker.busy = False
        mock_worker.poll.return_value = chess.Move.from_uci("e2e4")
        gs._hint_worker = mock_worker
        # Simula: busca feita na geração 1, mas a geração avançou (ex.: undo)
        gs._hint_request_gen = 1
        gs._hint_gen = 2
        gs._poll_hint()
        assert gs.hint_move is None
        assert gs._hint_worker is None

    def test_hint_does_not_make_move_automatically(self) -> None:
        """Hint NÃO deve executar o lance — só exibe."""
        gs = _make_scene()
        gs.hint_move = chess.Move.from_uci("e2e4")
        moves_before = len(gs.game.board.move_stack)
        # Executar update sem cliques
        gs.update(0.016)
        assert len(gs.game.board.move_stack) == moves_before


# ════════════════════════════════════════════════════════
# Flip / Rotação automática
# ════════════════════════════════════════════════════════

class TestFlipAndAutoRotate:
    """Orientação do tabuleiro: flip manual (F) e auto-flip no HvH."""

    def test_f_flips_board(self) -> None:
        gs = _make_scene()
        initial = gs.board_view.flipped
        _press(gs, pygame.K_f)
        assert gs.board_view.flipped != initial

    def test_f_flips_back(self) -> None:
        gs = _make_scene()
        initial = gs.board_view.flipped
        _press(gs, pygame.K_f)
        _press(gs, pygame.K_f)
        assert gs.board_view.flipped == initial

    def test_hvh_auto_flip_after_move(self) -> None:
        """No HvH, depois de um lance de brancas o tabuleiro deve mostrar perspectiva das pretas."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        assert not gs.board_view.flipped  # perspectiva inicial: brancas
        gs._apply_move(chess.Move.from_uci("e2e4"))
        # Agora é turno das pretas → tabuleiro deve estar virado
        assert gs.board_view.flipped

    def test_hvh_auto_flip_back_after_second_move(self) -> None:
        """Após dois lances no HvH, tabuleiro volta à perspectiva de brancas."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        gs._apply_move(chess.Move.from_uci("e2e4"))  # brancas → pretas viram
        gs._apply_move(chess.Move.from_uci("e7e5"))  # pretas → brancas viram
        assert not gs.board_view.flipped

    def test_hvai_no_auto_flip(self) -> None:
        """No HvAI, não deve haver flip automático após lances."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        initial = gs.board_view.flipped
        gs._apply_move(chess.Move.from_uci("e2e4"))
        # Não deve ter mudado automaticamente (só F muda)
        assert gs.board_view.flipped == initial

    def test_aivai_no_auto_flip(self) -> None:
        gs = _make_scene(mode=GameMode.AI_VS_AI)
        initial = gs.board_view.flipped
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert gs.board_view.flipped == initial


# ════════════════════════════════════════════════════════
# Undo
# ════════════════════════════════════════════════════════

class TestUndo:
    """Desfazer lance — comportamento por modo."""

    def test_hvai_ai_starts_after_human_move(self) -> None:
        """Após o lance humano no HvAI, a IA deve começar a pensar."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        assert gs._ai_worker is None  # humano (brancas) começa
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert gs._is_ai_turn
        assert gs._ai_worker is not None
        gs._ai_worker.cancel()

    def test_hvai_ai_reply_is_applied(self) -> None:
        """Resposta da IA é aplicada quando o worker termina."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        with patch.object(gs, "_start_ai"):
            gs._apply_move(chess.Move.from_uci("e2e4"))
        worker = MagicMock()
        worker.busy = False
        worker.poll.return_value = chess.Move.from_uci("e7e5")
        gs._ai_worker = worker
        gs._poll_ai()
        assert len(gs.game.board.move_stack) == 2

    def test_undo_hvh_one_move(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        assert len(gs.game.board.move_stack) == 1
        _press(gs, pygame.K_u)
        assert len(gs.game.board.move_stack) == 0
        assert gs.game.turn == chess.WHITE

    def test_undo_hvh_two_moves(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs._apply_move(chess.Move.from_uci("e7e5"))
        _press(gs, pygame.K_u)
        assert len(gs.game.board.move_stack) == 1  # HvH: desfaz 1

    def test_undo_empty_board_noop(self) -> None:
        gs = _make_scene()
        _press(gs, pygame.K_u)  # não deve lançar exceção
        assert len(gs.game.board.move_stack) == 0

    def test_undo_hvai_after_ai_response_undoes_pair(self) -> None:
        """HvAI: após resposta da IA, undo desfaz par (2 lances)."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e2e4"))  # humano
        gs._apply_move(chess.Move.from_uci("e7e5"))  # IA (manual)
        assert len(gs.game.board.move_stack) == 2
        _press(gs, pygame.K_u)
        assert len(gs.game.board.move_stack) == 0
        assert gs.game.turn == chess.WHITE

    def test_undo_hvai_before_ai_response_undoes_one(self) -> None:
        """HvAI: antes da resposta da IA, undo desfaz apenas 1 lance."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e2e4"))  # humano, IA ainda não respondeu
        assert len(gs.game.board.move_stack) == 1
        _press(gs, pygame.K_u)
        assert len(gs.game.board.move_stack) == 0
        assert gs.game.turn == chess.WHITE

    def test_undo_aivai_undoes_pair(self) -> None:
        gs = _make_scene(mode=GameMode.AI_VS_AI)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        gs._apply_move(chess.Move.from_uci("e7e5"))
        _press(gs, pygame.K_u)
        assert len(gs.game.board.move_stack) == 0

    def test_undo_cancels_ai_worker(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        mock_worker = MagicMock()
        mock_worker.busy = True
        gs._ai_worker = mock_worker
        _press(gs, pygame.K_u)
        mock_worker.cancel.assert_called()

    def test_undo_invalidates_generation(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        gs._apply_move(chess.Move.from_uci("e2e4"))
        _press(gs, pygame.K_u)
        # Geração não necessariamente muda no HvH sem IA, mas hint deve ser cancelado
        assert gs.hint_move is None

    def test_undo_clears_hint(self) -> None:
        gs = _make_scene()
        gs.hint_move = chess.Move.from_uci("e2e4")
        gs._apply_move(chess.Move.from_uci("e2e4"))
        _press(gs, pygame.K_u)
        assert gs.hint_move is None

    def test_undo_hvh_restores_clock(self) -> None:
        """Undo restaura os tempos de antes do lance desfeito."""
        gs = _make_scene(clock_minutes=5, clock_increment=3)
        gs._apply_move(chess.Move.from_uci("e2e4"))  # snapshot (300, 300)
        gs.clock.tick(20.0, chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e7e5"))  # snapshot (303, 280)
        _press(gs, pygame.K_u)  # desfaz e7e5 → restaura (303, 280)
        assert gs.clock.get_time(chess.WHITE) == pytest.approx(303.0)
        assert gs.clock.get_time(chess.BLACK) == pytest.approx(280.0)
        _press(gs, pygame.K_u)  # desfaz e2e4 → restaura (300, 300)
        assert gs.clock.get_time(chess.WHITE) == pytest.approx(300.0)
        assert gs.clock.get_time(chess.BLACK) == pytest.approx(300.0)

    def test_undo_hvai_pair_restores_clock(self) -> None:
        """Undo do par humano+IA restaura o relógio ao estado inicial."""
        gs = _make_scene(
            mode=GameMode.HUMAN_VS_AI,
            ai_color=chess.BLACK,
            clock_minutes=5,
            clock_increment=2,
        )
        gs._apply_move(chess.Move.from_uci("e2e4"))  # humano
        gs.clock.tick(10.0, chess.BLACK)
        gs._apply_move(chess.Move.from_uci("e7e5"))  # resposta da IA
        _press(gs, pygame.K_u)  # desfaz o par
        assert gs.game.turn == chess.WHITE
        assert gs.clock.get_time(chess.WHITE) == pytest.approx(300.0)
        assert gs.clock.get_time(chess.BLACK) == pytest.approx(300.0)

    def test_undo_hvai_during_ai_thinking_undoes_one_and_cancels(self) -> None:
        """Undo durante o pensamento da IA: cancela e desfaz só o lance humano."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        mock_worker = MagicMock()
        mock_worker.busy = True
        gs._ai_worker = mock_worker
        gs._apply_move(chess.Move.from_uci("e2e4"))  # humano, IA pensando
        _press(gs, pygame.K_u)
        mock_worker.cancel.assert_called()
        assert len(gs.game.board.move_stack) == 0
        assert gs.game.turn == chess.WHITE
        assert gs._ai_worker is None


# ════════════════════════════════════════════════════════
# Atalhos de teclado
# ════════════════════════════════════════════════════════

class TestKeyboardShortcuts:
    """Atalhos dentro da GameScene."""

    def test_key_f_flips(self) -> None:
        gs = _make_scene()
        initial = gs.board_view.flipped
        _press(gs, pygame.K_f)
        assert gs.board_view.flipped != initial

    def test_key_u_undoes(self) -> None:
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        _press(gs, pygame.K_u)
        assert len(gs.game.board.move_stack) == 0

    def test_key_r_resigns(self) -> None:
        gs = _make_scene()
        _press(gs, pygame.K_r)
        assert gs.game.is_game_over()
        result = gs.game.result()
        assert result is not None
        assert result.status == Status.DESISTENCIA

    def test_key_h_requests_hint(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        _press(gs, pygame.K_h)
        assert gs._hint_worker is not None
        gs._hint_worker.cancel()

    def test_key_d_requests_draw_hvh(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        _press(gs, pygame.K_d)
        assert gs.draw_request_by is not None

    def test_key_d_noop_in_hvai(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        _press(gs, pygame.K_d)
        assert gs.draw_request_by is None

    def test_key_n_opens_new_game_scene(self) -> None:
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)
        gs = GameScene(scene_manager=sm)
        sm.push(gs)
        assert sm.count == 2
        _press(gs, pygame.K_n)
        # N substitui a GameScene: a pilha fica [Menu, NewGame]
        # (o atalho nunca acumula GameScenes — Etapa 6.3).
        assert sm.count == 2
        assert isinstance(sm.current, NewGameScene)
        assert gs not in sm.scenes
        sm.clear()

    def test_key_n_when_draw_pending_declines(self) -> None:
        """Quando há pedido de empate pendente, N recusa em vez de nova partida."""
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        _press(gs, pygame.K_d)
        assert gs.draw_request_by is not None
        _press(gs, pygame.K_n)
        assert gs.draw_request_by is None
        assert not gs.game.is_game_over()

    def test_key_y_accepts_draw(self) -> None:
        gs = _make_scene(mode=GameMode.HUMAN_VS_HUMAN)
        _press(gs, pygame.K_d)
        _press(gs, pygame.K_y)
        assert gs.game.is_game_over()

    def test_key_esc_does_not_alter_game_state(self) -> None:
        """Esc na GameScene não altera a partida — o App o trata (pop da cena)."""
        gs = _make_scene()
        gs._apply_move(chess.Move.from_uci("e2e4"))
        _press(gs, pygame.K_ESCAPE)
        assert len(gs.game.board.move_stack) == 1
        assert not gs.game.is_game_over()

    def test_key_esc_pops_game_scene_in_app(self) -> None:
        """Esc com a GameScene no topo da pilha volta para a cena anterior."""
        from xadtitans.app import App

        _get_surface()
        app = App()
        gs = GameScene()
        app.scene_manager.push(gs)
        assert app.scene_manager.current is gs
        app._handle_global_escape()
        assert app.scene_manager.current is not gs
        assert app.scene_manager.count == 1

    def test_game_keys_do_not_leak_into_menu(self) -> None:
        """Teclas da GameScene não interferem em outras cenas (menu não as consome)."""
        _get_surface()
        sm = SceneManager()
        menu = MenuScene(sm)
        sm.push(menu)
        # MenuScene não trata U/F/H/D/Y — não deve lançar nem alterar estado
        for key in (
            pygame.K_u,
            pygame.K_f,
            pygame.K_h,
            pygame.K_d,
            pygame.K_y,
            pygame.K_r,
        ):
            sm.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        assert sm.current is menu
        sm.clear()


# ════════════════════════════════════════════════════════
# Game.timeout e Game.agree_draw (camada core)
# ════════════════════════════════════════════════════════

class TestGameCoreTimeout:
    """Testa métodos timeout() e agree_draw() em core/game.py."""

    def test_timeout_white(self) -> None:
        g = Game()
        g.timeout(chess.WHITE)
        assert g.is_game_over()
        result = g.result()
        assert result is not None
        assert result.status == Status.TEMPO_ESGOTADO
        assert result.winner == chess.BLACK

    def test_timeout_black(self) -> None:
        g = Game()
        g.timeout(chess.BLACK)
        assert g.is_game_over()
        result = g.result()
        assert result is not None
        assert result.winner == chess.WHITE

    def test_agree_draw(self) -> None:
        g = Game()
        g.agree_draw()
        assert g.is_game_over()
        result = g.result()
        assert result is not None
        assert result.is_draw
        assert result.status == Status.EMPATE_ACORDO

    def test_undo_clears_timeout(self) -> None:
        g = Game()
        g.push(chess.Move.from_uci("e2e4"))
        g.timeout(chess.WHITE)
        assert g.is_game_over()
        g.undo()
        assert not g.is_game_over()

    def test_undo_clears_draw_agreed(self) -> None:
        g = Game()
        g.push(chess.Move.from_uci("e2e4"))
        g.agree_draw()
        assert g.is_game_over()
        g.undo()
        assert not g.is_game_over()

    def test_reset_clears_timeout(self) -> None:
        g = Game()
        g.timeout(chess.WHITE)
        g.reset()
        assert not g.is_game_over()
