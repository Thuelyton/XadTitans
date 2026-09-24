"""Cena do tabuleiro — mostra a posição e interage com cliques."""

from __future__ import annotations

import chess
import pygame

from xadtitans.config import COLOR_BG
from xadtitans.ui.board_view import BoardView, pixel_to_square


class GameScene:
    """Tela principal do tabuleiro (Fase 1: apenas visualização + clique)."""

    def __init__(self) -> None:
        self.board_view = BoardView()
        self.board_view.set_board(chess.Board())

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_left_click(event.pos)

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            self.board_view.toggle_flip()

    def update(self, dt: float) -> None:
        pass  # Fase 1: nada animado ainda

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)
        self.board_view.draw(surface)

    # ── lógica interna ───────────────────────────────────

    def _on_left_click(self, pos: tuple[int, int]) -> None:
        """Clique esquerdo: seleciona ou deseleciona uma peça."""
        sq = pixel_to_square(pos[0], pos[1], flipped=self.board_view.flipped)
        if sq is None:
            self.board_view.selected_square = None
            self.board_view.legal_destinations = []
            return

        board = self.board_view.board

        # Se já há uma peça selecionada e o clique é um destino legal → move
        if (
            self.board_view.selected_square is not None
            and sq in self.board_view.legal_destinations
        ):
            move = chess.Move(self.board_view.selected_square, sq)
            # Promoção: assumir dama por agora (diálogo será na Fase 2)
            if board.is_legal(move):
                board.push(move)
                self.board_view.last_move = move
                self.board_view.selected_square = None
                self.board_view.legal_destinations = []
                return

        # Seleciona nova peça
        piece = board.piece_at(sq)
        if piece is not None and piece.color == board.turn:
            self.board_view.selected_square = sq
            self.board_view.legal_destinations = [
                m.to_square for m in board.legal_moves if m.from_square == sq
            ]
        else:
            self.board_view.selected_square = None
            self.board_view.legal_destinations = []
