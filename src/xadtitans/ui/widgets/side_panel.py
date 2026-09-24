"""Painel lateral: jogadas em SAN (com rolagem) e peças capturadas.

Widget da Fase 3.  A formatação das jogadas (``format_move_pairs``)
é uma função pura, testada em ``tests/test_side_panel.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from xadtitans.core.game import Game
    from xadtitans.ui.board_view import BoardView

_BG = (38, 36, 34)
_BORDER = (70, 66, 62)
_TEXT = (188, 184, 178)
_TITLE = (255, 215, 0)
_LINE_H = 22
_MINI_PIECE = 26


def format_move_pairs(san_history: Sequence[str]) -> list[str]:
    """Histórico SAN → linhas ``"1. e4 e5"``, ``"2. Nf3 Nc6"``..."""
    lines: list[str] = []
    for i in range(0, len(san_history), 2):
        num = i // 2 + 1
        if i + 1 < len(san_history):
            lines.append(f"{num}. {san_history[i]} {san_history[i + 1]}")
        else:
            lines.append(f"{num}. {san_history[i]}")
    return lines


class SidePanel:
    """Painel à direita do tabuleiro (jogadas + capturadas)."""

    def __init__(self, board_view: BoardView, rect: pygame.Rect) -> None:
        self._bv = board_view
        self.rect = rect
        self._scroll = 0
        self._last_count = -1
        self._font = pygame.font.SysFont("arial", 17)
        self._title_font = pygame.font.SysFont("arial", 20, bold=True)

    # ── eventos ──────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Roda a lista com a rodinha; retorna True se consumiu."""
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(
            *pygame.mouse.get_pos()
        ):
            self._scroll = max(0, self._scroll - event.y)
            return True
        return False

    # ── desenho ──────────────────────────────────────────

    def draw(self, surface: pygame.Surface, game: Game) -> None:
        pygame.draw.rect(surface, _BG, self.rect)
        pygame.draw.rect(surface, _BORDER, self.rect, 1)

        x = self.rect.x + 12
        y = self.rect.y + 12
        w = self.rect.width - 24

        # Título
        title = self._title_font.render("XadTitans", True, _TITLE)
        surface.blit(title, (x, y))
        y += 34

        # Turno / status
        y = self._draw_status(surface, game, x, y, w)
        y += 10

        # Peças capturadas
        y = self._draw_captures(
            surface, game, True, x, y
        )
        y = self._draw_captures(surface, game, False, x, y)
        y += 10

        # Jogadas
        label = self._title_font.render("Jogadas", True, _TEXT)
        surface.blit(label, (x, y))
        y += 30

        lines = format_move_pairs(game.san_history)
        if len(lines) != self._last_count:  # nova jogada → p/ o fim
            self._last_count = len(lines)
            self._scroll = max(0, len(lines))
        visible = max(1, (self.rect.bottom - 20 - y) // _LINE_H)
        self._scroll = min(self._scroll, max(0, len(lines) - visible))
        start = max(0, min(self._scroll, len(lines) - visible))
        for line in lines[start : start + visible]:
            text = self._font.render(line, True, _TEXT)
            surface.blit(text, (x, y))
            y += _LINE_H

    def _draw_status(
        self,
        surface: pygame.Surface,
        game: Game,
        x: int,
        y: int,
        w: int,
    ) -> int:
        if game.is_game_over():
            result = game.result()
            text = "Fim de partida" if result else "—"
        elif game.in_check():
            quem = "Brancas" if game.turn else "Pretas"
            text = f"Xeque nas {quem.lower()}!"
        else:
            text = "Vez das brancas" if game.turn else "Vez das pretas"
        rendered = self._font.render(text, True, _TEXT)
        surface.blit(rendered, (x, y))
        return y + _LINE_H + 4

    def _draw_captures(
        self,
        surface: pygame.Surface,
        game: Game,
        color: bool,
        x: int,
        y: int,
    ) -> int:
        name = "Brancas" if color else "Pretas"
        label = self._font.render(f"{name} capturaram", True, _TEXT)
        surface.blit(label, (x, y))
        y += _LINE_H + 2
        captured = game.captured_by(color)
        if not captured:
            dash = self._font.render("—", True, _TEXT)
            surface.blit(dash, (x, y))
            return y + _LINE_H
        px = x
        for piece_type in captured:
            sprite = self._bv.get_sprite(piece_type, not color, _MINI_PIECE)
            surface.blit(sprite, (px, y - 3))
            px += _MINI_PIECE + 2
            if px > self.rect.right - _MINI_PIECE - 8:
                px = x
                y += _LINE_H
        return y + _LINE_H
