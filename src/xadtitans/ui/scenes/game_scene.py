"""Cena do tabuleiro — partida com IA ou 2 jogadores.

Responsabilidades:
  - Seleção e movimentação por clique (regras via ``core.game.Game``);
  - Animações de deslize/esmaecimento (``ui.animations``) com
    **bloqueio de entrada** enquanto duram;
  - Hover, destaques e diálogo de promoção com sprites;
  - Sons (``audio.AudioManager``);
  - Painel lateral (jogadas em SAN + peças capturadas);
  - IA local em thread separada (``ai.worker.AIWorker``).

Teclas: ``F`` vira o tabuleiro, ``U`` desfaz, ``R`` desiste.
"""

from __future__ import annotations

import chess
import pygame

from xadtitans.ai.worker import AIWorker
from xadtitans.audio import AudioManager
from xadtitans.config import (
    BOARD_PERSP_X,
    COLOR_BG,
    PANEL_W,
    PANEL_X,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from xadtitans.core.game import Game
from xadtitans.core.types import Level
from xadtitans.ui.animations import FADE, SLIDE, Anim, Animator, ease_out_cubic
from xadtitans.ui.board_view import BoardView
from xadtitans.ui.widgets.side_panel import SidePanel

_PROMO_PIECES: list[chess.PieceType] = [
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
]

_MOVE_DUR = 0.16
_FADE_DUR = 0.22


class GameScene:
    """Tela principal da partida (humano vs humano ou humano vs IA)."""

    def __init__(
        self,
        audio: AudioManager | None = None,
        ai_color: chess.Color | None = None,
        ai_level: Level = Level.MEDIO,
    ) -> None:
        self.game = Game()
        self.board_view = BoardView()
        self.audio = audio or AudioManager()
        self.animator = Animator()
        self._sync_view()

        self.side_panel = SidePanel(
            self.board_view,
            pygame.Rect(PANEL_X, 12, PANEL_W, WINDOW_HEIGHT - 24),
        )

        # IA
        self.ai_color = ai_color  # None = 2 jogadores
        self.ai_level = ai_level
        self._ai_worker: AIWorker | None = None

        # Promoção pendente
        self.pending_promotion: tuple[int, int] | None = None
        self._promo_rects: list[tuple[pygame.Rect, chess.PieceType]] = []

        # Fonte para "Pensando..."
        self._thinking_font = pygame.font.SysFont("arial", 20, bold=True)

        # Se a IA joga primeiro, iniciar busca imediatamente
        if self.ai_color is not None and self.game.board.turn == self.ai_color:
            self._start_ai()

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.side_panel.handle_event(event):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_left_click(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            self._on_hover(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                self.board_view.toggle_flip()
                self.animator.clear()
            elif event.key == pygame.K_u:
                self.undo()
            elif event.key == pygame.K_r:
                self.resign()

    def update(self, dt: float) -> None:
        self.animator.update(dt)
        self._poll_ai()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)
        self.board_view.draw(surface, anims=self.animator.by_square())
        self.side_panel.draw(surface, self.game)
        self._draw_promotion_dialog(surface)
        self._draw_thinking(surface)

    # ── estado da partida ─────────────────────────────────

    @property
    def game_over(self) -> bool:
        return self.game.is_game_over()

    def new_game(self) -> None:
        self.game.reset()
        self.animator.clear()
        self.pending_promotion = None
        self._cancel_ai()
        self._sync_view()

    def undo(self) -> None:
        # Se a IA está pensando, cancelar
        if self._ai_worker is not None and self._ai_worker.busy:
            self._cancel_ai()
        # Se a IA jogou o último lance, desfazer 2 lances (IA + humano)
        if (
            self.ai_color is not None
            and self.game.board.move_stack
            and len(self.game.board.move_stack) >= 2
        ):
            self.game.undo()  # desfaz lance da IA
            self.game.undo()  # desfaz lance do humano
        else:
            self.game.undo()
        self.animator.clear()
        self.pending_promotion = None
        self._sync_view()

    def resign(self) -> None:
        if not self.game.is_game_over():
            self._cancel_ai()
            self.game.resign(self.game.turn)
            self.audio.play("game_over")

    # ── IA ────────────────────────────────────────────────

    def _cancel_ai(self) -> None:
        if self._ai_worker is not None:
            self._ai_worker.cancel()
            self._ai_worker = None

    def _start_ai(self) -> None:
        """Inicia a busca da IA no turno atual."""
        if self.ai_color is None:
            return
        if self.game.board.turn != self.ai_color:
            return
        if self.game.is_game_over():
            return
        snapshot = self.game.board.copy()
        self._ai_worker = AIWorker(snapshot, level=self.ai_level)
        self._ai_worker.request()

    def _poll_ai(self) -> None:
        """Verifica se a IA terminou de pensar."""
        if self._ai_worker is None:
            return
        if self._ai_worker.busy:
            return
        move = self._ai_worker.poll()
        self._ai_worker = None
        if move is not None and move in self.game.board.legal_moves:
            self._apply_move(move)

    def _draw_thinking(self, surface: pygame.Surface) -> None:
        """Indicador 'Pensando...' quando a IA está ativa."""
        if (
            self._ai_worker is not None
            and self._ai_worker.busy
            and not self.game.is_game_over()
        ):
            text = self._thinking_font.render("Pensando...", True, (255, 215, 0))
            surface.blit(
                text,
                (
                    BOARD_PERSP_X + 10,
                    WINDOW_HEIGHT - 30,
                ),
            )

    # ── sincronização com a visão ─────────────────────────

    def _sync_view(self) -> None:
        self.board_view.set_board(self.game.board)
        self.board_view.last_move = (
            self.game.board.peek() if self.game.board.move_stack else None
        )
        self.board_view.check_square = self.game.check_square()

    def _apply_move(self, move: chess.Move) -> None:
        """Executa o lance: anima, toca som e atualiza a visão."""
        board = self.game.board
        piece = board.piece_at(move.from_square)
        was_capture = board.is_capture(move)
        was_castling = board.is_castling(move)

        # Animações
        if piece is not None:
            self.animator.add(
                Anim(
                    kind=SLIDE,
                    sprite=(piece.piece_type, piece.color),
                    square=move.to_square,
                    start=self.board_view.piece_anchor(move.from_square),
                    end=self.board_view.piece_anchor(move.to_square),
                    scale_start=self.board_view.scale_of(move.from_square),
                    scale_end=self.board_view.scale_of(move.to_square),
                    duration=_MOVE_DUR,
                    easing=ease_out_cubic,
                )
            )
        if was_capture:
            cap_sq = move.to_square
            if board.is_en_passant(move):
                cap_sq = chess.square(
                    chess.square_file(move.to_square),
                    chess.square_rank(move.from_square),
                )
            captured = board.piece_at(cap_sq)
            if captured is not None:
                self.animator.add(
                    Anim(
                        kind=FADE,
                        sprite=(captured.piece_type, captured.color),
                        square=cap_sq,
                        start=self.board_view.piece_anchor(cap_sq),
                        end=self.board_view.piece_anchor(cap_sq),
                        scale_start=self.board_view.scale_of(cap_sq),
                        duration=_FADE_DUR,
                        easing=ease_out_cubic,
                    )
                )
        if was_castling and piece is not None:
            rook_from, rook_to = _castling_rook_squares(move)
            rook = board.piece_at(rook_from)
            if rook is not None:
                self.animator.add(
                    Anim(
                        kind=SLIDE,
                        sprite=(rook.piece_type, rook.color),
                        square=rook_to,
                        start=self.board_view.piece_anchor(rook_from),
                        end=self.board_view.piece_anchor(rook_to),
                        scale_start=self.board_view.scale_of(rook_from),
                        scale_end=self.board_view.scale_of(rook_to),
                        duration=_MOVE_DUR,
                        easing=ease_out_cubic,
                    )
                )

        # Regras + som
        self.game.push(move)
        self.pending_promotion = None
        self._sync_view()

        if was_capture:
            self.audio.play("capture")
        else:
            self.audio.play("move")
        if self.game.in_check():
            self.audio.play("check")
        if self.game.is_game_over():
            self.audio.play("game_over")
        elif self.ai_color is not None and self.game.board.turn == self.ai_color:
            self._start_ai()

    # ── interação ─────────────────────────────────────────

    def _is_ai_thinking(self) -> bool:
        return self._ai_worker is not None and self._ai_worker.busy

    def _on_hover(self, pos: tuple[int, int]) -> None:
        if self._is_ai_thinking() or self.game.is_game_over():
            self.board_view.hover_square = None
            return
        self.board_view.hover_square = self.board_view.square_at(*pos)

    def _on_left_click(self, pos: tuple[int, int]) -> None:
        if self.pending_promotion is not None:
            self._handle_promotion_click(pos)
            return
        if self.animator.blocking or self._is_ai_thinking():
            return
        if self.game.is_game_over():
            return
        # Se é turno da IA, não permitir clique do humano
        if self.ai_color is not None and self.game.board.turn == self.ai_color:
            return

        sq = self.board_view.square_at(pos[0], pos[1])
        if sq is None:
            self.board_view.selected_square = None
            self.board_view.legal_destinations = []
            return

        selected = self.board_view.selected_square
        if selected is not None and sq in self.board_view.legal_destinations:
            move = chess.Move(selected, sq)
            if self.game.needs_promotion(selected, sq):
                self.pending_promotion = (selected, sq)
            else:
                self._apply_move(move)
            return

        piece = self.game.board.piece_at(sq)
        if piece is not None and piece.color == self.game.turn:
            self.board_view.selected_square = sq
            self.board_view.legal_destinations = [
                m.to_square for m in self.game.legal_moves_from(sq)
            ]
            self.audio.play("click")
        else:
            self.board_view.selected_square = None
            self.board_view.legal_destinations = []

    # ── promoção ──────────────────────────────────────────

    def _handle_promotion_click(self, pos: tuple[int, int]) -> None:
        for rect, piece_type in self._promo_rects:
            if rect.collidepoint(pos):
                from_sq, to_sq = self.pending_promotion
                self._apply_move(
                    chess.Move(from_sq, to_sq, promotion=piece_type)
                )
                return
        self.pending_promotion = None

    def _draw_promotion_dialog(self, surface: pygame.Surface) -> None:
        if self.pending_promotion is None:
            self._promo_rects = []
            return
        cell = 72
        width = cell * 4 + 16
        height = cell + 16
        x = (BOARD_PERSP_X + (WINDOW_WIDTH - PANEL_W) - width) // 2
        y = 180
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((30, 30, 30, 235))
        surface.blit(panel, (x, y))
        pygame.draw.rect(surface, (200, 200, 200), (x, y, width, height), 2)
        self._promo_rects = []
        for i, piece_type in enumerate(_PROMO_PIECES):
            rect = pygame.Rect(x + 8 + i * cell, y + 8, cell, cell)
            pygame.draw.rect(surface, (70, 70, 70), rect, 1)
            sprite = self.board_view.get_sprite(
                piece_type, self.game.turn, cell - 8
            )
            surface.blit(
                sprite,
                (
                    rect.centerx - sprite.get_width() // 2,
                    rect.centery - sprite.get_height() // 2,
                ),
            )
            self._promo_rects.append((rect, piece_type))


def _castling_rook_squares(move: chess.Move) -> tuple[int, int]:
    rook_moves = {
        chess.G1: (chess.H1, chess.F1),
        chess.C1: (chess.A1, chess.D1),
        chess.G8: (chess.H8, chess.F8),
        chess.C8: (chess.A8, chess.D8),
    }
    return rook_moves[move.to_square]
