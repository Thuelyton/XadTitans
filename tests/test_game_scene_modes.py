"""Testes para suporte a modos de jogo — Etapa 5.2.

Cobre: GameMode integrado ao GameScene, AI_VS_AI com timer,
generation token para invalidação, undo por modo, orientação
do tabuleiro e compatibilidade com a Fase 4.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock, patch

import chess
import pygame

from xadtitans.core.types import GameMode, Level
from xadtitans.ui.scenes.game_scene import AI_VS_AI_DELAY, GameScene

_surf: pygame.Surface | None = None


def _screen() -> pygame.Surface:
    global _surf
    if _surf is None:
        import pygame
        pygame.init()
        _surf = pygame.display.set_mode((1024, 768))
    return _surf


def _make_scene(
    mode: GameMode = GameMode.HUMAN_VS_HUMAN,
    ai_color: chess.Color | None = None,
    ai_level: Level = Level.INICIANTE,
) -> GameScene:
    """Cria uma GameScene com modo especificado."""
    _screen()
    return GameScene(
        game_mode=mode,
        ai_color=ai_color,
        ai_level=ai_level,
        ai_vs_ai_delay=0.05,  # intervalo curto para testes
    )


# ════════════════════════════════════════════════════════════
# GameMode e flags de IA
# ════════════════════════════════════════════════════════════


class TestGameModeFlags:
    """Verifica que as flags de IA são derivadas corretamente do GameMode."""

    def test_human_vs_human_nenhum_ia(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        assert scene._white_is_ai is False
        assert scene._black_is_ai is False
        assert scene.game_mode == GameMode.HUMAN_VS_HUMAN

    def test_human_vs_ai_ia_pretas_padrao(self) -> None:
        # Padrão: ai_color=None → IA controla pretas.
        scene = _make_scene(GameMode.HUMAN_VS_AI)
        assert scene._white_is_ai is False
        assert scene._black_is_ai is True

    def test_human_vs_ai_ia_brancas(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        assert scene._white_is_ai is True
        assert scene._black_is_ai is False

    def test_ai_vs_ai_ambos_ia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        assert scene._white_is_ai is True
        assert scene._black_is_ai is True


class TestIsAiTurn:
    """Verifica a propriedade _is_ai_turn."""

    def test_hvh_nunca_e_turno_ia(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        assert scene._is_ai_turn is False

    def test_hva_ia_pretas_turno_brancas_false(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI)
        # Turno inicial: brancas
        assert scene.game.board.turn is chess.WHITE
        assert scene._is_ai_turn is False

    def test_hva_ia_brancas_turno_brancas_true(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        assert scene.game.board.turn is chess.WHITE
        assert scene._is_ai_turn is True

    def test_aia_sempre_e_turno_ia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        assert scene._is_ai_turn is True


# ════════════════════════════════════════════════════════════
# Inicialização e IA automática
# ════════════════════════════════════════════════════════════


class TestAutoStartAI:
    """Verifica se a IA inicia automaticamente quando necessário."""

    def test_hvh_nao_inicia_ia(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        assert scene._ai_worker is None

    def test_hva_ia_pretas_nao_inicia_imediatamente(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI)
        # Brancas jogam primeiro → humano joga → IA não inicia.
        assert scene._ai_worker is None

    def test_hva_ia_brancas_inicia_imediatamente(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        # Brancas jogam primeiro → IA joga → deve iniciar.
        assert scene._ai_worker is not None

    def test_aia_inicia_imediatamente(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        assert scene._ai_worker is not None


# ════════════════════════════════════════════════════════════
# Generation token
# ════════════════════════════════════════════════════════════


class TestGenerationToken:
    """Verifica que a geração invalida resultados obsoletos."""

    def test_generation_incrementa_no_cancel(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        gen_before = scene._generation
        scene._cancel_ai()
        assert scene._generation == gen_before + 1

    def test_generation_incrementa_no_new_game(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        gen_before = scene._generation
        scene.new_game()
        # new_game chama _cancel_ai (+1) e incrementa mais 1 = +2 total.
        assert scene._generation == gen_before + 2

    def test_poll_ignora_resultado_obsoleto(self) -> None:
        """Se a geração mudou entre request e poll, o resultado é descartado."""
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        # IA branca inicia; simular lance pronto.
        assert scene._ai_worker is not None
        scene._ai_worker._result_queue.put(chess.Move(chess.E2, chess.E4))

        # Incrementar geração para invalidar.
        scene._generation += 1

        # Poll deve ignorar o resultado.
        scene._poll_ai()
        # Jogo não deve ter avançado (nenhum lance aplicado).
        assert len(scene.game.board.move_stack) == 0


# ════════════════════════════════════════════════════════════
# AI_VS_AI: timer e fluxo
# ════════════════════════════════════════════════════════════


class TestAIAiTimer:
    """Verifica o timer de intervalo visual no modo AI_VS_AI."""

    def test_timer_nao_ativo_no_hvh(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        scene._ai_vs_ai_timer = 1.0
        scene.update(0.1)
        # Timer não deve ser decrementado (não é AI_VS_AI).
        assert scene._ai_vs_ai_timer == 1.0

    def test_timer_decrementa_no_aia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        scene._ai_vs_ai_timer = 0.5
        scene.update(0.3)
        assert abs(scene._ai_vs_ai_timer - 0.2) < 0.01

    def test_timer_inicia_ia_quando_expira(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        # Parar IA existente e simular timer ativo.
        scene._cancel_ai()
        scene._ai_worker = None
        scene._ai_vs_ai_timer = 0.01

        # Mockar _start_ai para verificar chamada.
        with patch.object(scene, "_start_ai") as mock_start:
            scene.update(0.1)  # dt > timer
            mock_start.assert_called_once()

    def test_aia_delay_configuravel(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        assert scene.ai_vs_ai_delay == 0.05  # valor do fixture


# ════════════════════════════════════════════════════════════
# Undo por modo
# ════════════════════════════════════════════════════════════


class TestUndoByMode:
    """Verifica o comportamento de undo conforme o modo de jogo."""

    def test_hvh_undo_um_lance(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        scene.game.push(chess.Move(chess.E2, chess.E4))
        scene._sync_view()
        assert len(scene.game.board.move_stack) == 1

        scene.undo()
        assert len(scene.game.board.move_stack) == 0

    def test_hva_undo_apos_humano(self) -> None:
        """HUMAN_VS_AI: humano joga, desfaz 1 lance."""
        # ai_color=BLACK: humano controla brancas.
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        # Humano (brancas) joga e4.
        scene.game.push(chess.Move(chess.E2, chess.E4))
        scene._sync_view()
        assert scene.game.board.turn is chess.BLACK

        scene.undo()
        assert len(scene.game.board.move_stack) == 0
        assert scene.game.board.turn is chess.WHITE

    def test_hva_undo_apos_ia(self) -> None:
        """HUMAN_VS_AI: após IA jogar, desfaz 2 lances (IA + humano)."""
        # ai_color=BLACK: humano brancas, IA pretas.
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.BLACK)
        # Humano joga e4.
        scene.game.push(chess.Move(chess.E2, chess.E4))
        # IA joga e5.
        scene.game.push(chess.Move(chess.E7, chess.E5))
        scene._sync_view()
        assert len(scene.game.board.move_stack) == 2

        scene.undo()
        # Deve desfazer 2 lances (IA + humano).
        assert len(scene.game.board.move_stack) == 0
        assert scene.game.board.turn is chess.WHITE

    def test_aia_undo_dois_lances(self) -> None:
        """AI_VS_AI: desfaz sempre 2 lances (par IA+IA)."""
        scene = _make_scene(GameMode.AI_VS_AI)
        scene.game.push(chess.Move(chess.E2, chess.E4))
        scene.game.push(chess.Move(chess.E7, chess.E5))
        scene._sync_view()

        scene.undo()
        assert len(scene.game.board.move_stack) == 0

    def test_undo_pilha_vazia(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        # Não deve estourar erro.
        scene.undo()
        assert len(scene.game.board.move_stack) == 0

    def test_undo_cancela_ia_ativa(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        assert scene._ai_worker is not None
        scene.undo()
        assert scene._ai_worker is None

    def test_undo_limpa_timer_aia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        scene._ai_vs_ai_timer = 1.0
        scene.undo()
        assert scene._ai_vs_ai_timer == 0.0


# ════════════════════════════════════════════════════════════
# Orientação do tabuleiro
# ════════════════════════════════════════════════════════════


class TestBoardOrientation:
    """Verifica a orientação inicial do tabuleiro."""

    def test_hvh_tabuleiro_normal(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        assert scene.board_view.flipped is False

    def test_hva_humano_brancas_normal(self) -> None:
        # Padrão: ai_color=None → humano Brancas, IA Pretas → normal.
        scene = _make_scene(GameMode.HUMAN_VS_AI)
        assert scene.board_view.flipped is False

    def test_hva_humano_pretas_invertido(self) -> None:
        # ai_color=WHITE: humano controla pretas → tabuleiro invertido.
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        assert scene.board_view.flipped is True

    def test_aia_tabuleiro_normal(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        assert scene.board_view.flipped is False


# ════════════════════════════════════════════════════════════
# New game preserva modo
# ════════════════════════════════════════════════════════════


class TestNewGamePreservesMode:
    """Verifica que new_game preserva o modo de jogo."""

    def test_new_game_hva_reinicia_ia(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        scene.game.push(chess.Move(chess.E2, chess.E4))
        scene.game.push(chess.Move(chess.E7, chess.E5))

        scene.new_game()
        assert len(scene.game.board.move_stack) == 0
        # IA branca deve iniciar automaticamente.
        assert scene._ai_worker is not None

    def test_new_game_aia_reinicia_ia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        scene.game.push(chess.Move(chess.E2, chess.E4))

        scene.new_game()
        assert len(scene.game.board.move_stack) == 0
        assert scene._ai_worker is not None

    def test_new_game_hvh_nao_inicia_ia(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        scene.game.push(chess.Move(chess.E2, chess.E4))

        scene.new_game()
        assert scene._ai_worker is None


# ════════════════════════════════════════════════════════════
# Cancelamento e thread safety
# ════════════════════════════════════════════════════════════


class TestCancellation:
    """Verifica cancelamento seguro de IA."""

    def test_cancel_ai_limpa_worker(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        assert scene._ai_worker is not None
        scene._cancel_ai()
        assert scene._ai_worker is None

    def test_cancel_ai_limpa_timer(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        scene._ai_vs_ai_timer = 1.0
        scene._cancel_ai()
        assert scene._ai_vs_ai_timer == 0.0

    def test_cancel_ai_incrementa_geracao(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        gen = scene._generation
        scene._cancel_ai()
        assert scene._generation == gen + 1

    def test_on_exit_cancela_ia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        scene.on_exit()
        assert scene._ai_worker is None


# ════════════════════════════════════════════════════════════
# Integração com App (compatibilidade)
# ════════════════════════════════════════════════════════════


class TestCompatibility:
    """Verifica compatibilidade com o código existente (App, EndgameScene)."""

    def test_construtor_padrao_hvh(self) -> None:
        """GameScene() sem argumentos = HUMAN_VS_HUMAN (compatível com App)."""
        scene = GameScene()
        assert scene.game_mode == GameMode.HUMAN_VS_HUMAN
        assert scene._white_is_ai is False
        assert scene._black_is_ai is False

    def test_endgame_scene_funciona(self) -> None:
        """EndgameScene continua recebendo GameScene corretamente."""
        from xadtitans.ui.scenes.endgame_scene import EndgameScene

        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        # Simular fim de partida.
        scene.game.resign(chess.WHITE)
        endgame = EndgameScene(scene)
        assert endgame.game_scene is scene
        assert endgame._result is not None

    def test_any_ai_property(self) -> None:
        assert _make_scene(GameMode.HUMAN_VS_HUMAN)._any_ai is False
        assert _make_scene(GameMode.HUMAN_VS_AI)._any_ai is True
        assert _make_scene(GameMode.AI_VS_AI)._any_ai is True

    def test_thinking_font_existe(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        assert scene._thinking_font is not None

    def test_animator_existe(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        assert scene.animator is not None
        assert scene.animator.blocking is False

    def test_side_panel_existe(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        assert scene.side_panel is not None


# ════════════════════════════════════════════════════════════
# Resign por modo
# ════════════════════════════════════════════════════════════


class TestResignByMode:
    """Verifica desistência em diferentes modos."""

    def test_resign_hvh(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        scene.resign()
        assert scene.game.is_game_over()

    def test_resign_hva_cancela_ia(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        scene.resign()
        assert scene.game.is_game_over()
        assert scene._ai_worker is None

    def test_resign_aia_cancela_ia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        scene.resign()
        assert scene.game.is_game_over()
        assert scene._ai_worker is None


# ════════════════════════════════════════════════════════════
# Constantes e valores
# ════════════════════════════════════════════════════════════


class TestConstants:
    """Verifica constantes do módulo."""

    def test_ai_vs_ai_delay_positivo(self) -> None:
        assert AI_VS_AI_DELAY > 0

    def test_ai_vs_ai_delay_razoavel(self) -> None:
        # Deve ser entre 0.1 e 5.0 segundos.
        assert 0.1 <= AI_VS_AI_DELAY <= 5.0


# ════════════════════════════════════════════════════════════
# Poll com resultado legal
# ════════════════════════════════════════════════════════════


class TestPollApplyMove:
    """Verifica que poll aplica lance legal e avança o jogo."""

    @staticmethod
    def _make_ready_worker(move: chess.Move | None) -> MagicMock:
        """Cria um mock de AIWorker que não está busy e tem resultado."""
        worker = MagicMock()
        worker.busy = False
        worker.poll.return_value = move
        return worker

    def test_poll_aplica_lance(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        scene._cancel_ai()  # Parar IA real.
        scene._ai_worker = self._make_ready_worker(chess.Move(chess.E2, chess.E4))

        scene._poll_ai()
        assert len(scene.game.board.move_stack) == 1
        assert scene.game.board.peek() == chess.Move(chess.E2, chess.E4)

    def test_poll_ignora_lance_ilegal(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        scene._cancel_ai()
        # Lance impossível.
        scene._ai_worker = self._make_ready_worker(chess.Move(chess.E2, chess.E6))

        scene._poll_ai()
        assert len(scene.game.board.move_stack) == 0

    def test_poll_ignora_none(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_AI, ai_color=chess.WHITE)
        scene._cancel_ai()
        scene._ai_worker = self._make_ready_worker(None)

        scene._poll_ai()
        assert len(scene.game.board.move_stack) == 0
        # Worker foi limpo (poll processou o resultado).
        assert scene._ai_worker is None


# ════════════════════════════════════════════════════════════
# draw e handle_event não crasham
# ════════════════════════════════════════════════════════════


class TestDrawAndEvents:
    """Verifica que draw/handle_event não crasham em nenhum modo."""

    def test_draw_hvh(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        surf = _screen()
        scene.draw(surf)  # não deve estourar

    def test_draw_aia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        surf = _screen()
        scene.draw(surf)

    def test_handle_event_hvh(self) -> None:
        scene = _make_scene(GameMode.HUMAN_VS_HUMAN)
        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        event.pos = (500, 400)
        scene.handle_event(event)

    def test_update_aia(self) -> None:
        scene = _make_scene(GameMode.AI_VS_AI)
        scene.update(0.016)
        # Não deve crashar.
