"""Cena do tabuleiro — partida de 2 jogadores com regras completas.

Responsabilidades (Fase 2):
  - Selecionar peça e mostrar lances legais;
  - Mover por clique (somente lances legais, via ``core.game.Game``);
  - Diálogo de promoção do peão;
  - Destaque de xeque, último lance e seleção;
  - Painel simples com jogadas em SAN e peças capturadas;
  - Desfazer (``U``), desistir (``R``) e virar o tabuleiro (``F``).
"""

from __future__ import annotations

import chess
import pygame

from xadtitans.config import (
    BOARD_SIZE,
    BOARD_X,
    BOARD_Y,
    COLOR_BG,
    COLOR_COORD,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from xadtitans.core.game import Game
from xadtitans.ui.board_view import BoardView, pixel_to_square

# Símbolos das opções de promoção (por cor).
_PROMO_SYMBOLS: dict[bool, list[str]] = {
    chess.WHITE: ["♕", "♖", "♗", "♘"],
    chess.BLACK: ["♛", "♜", "♝", "♞"],
}
_PROMO_PIECES: list[chess.PieceType] = [
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
]

_PANEL_X = BOARD_X + BOARD_SIZE + 12  # painel de texto à direita
_PANEL_W = WINDOW_WIDTH - _PANEL_X - 8


class GameScene:
    """Tela principal da partida."""

    def __init__(self) -> None:
        self.game = Game()
        self.board_view = BoardView()
        self._sync_view()

        # Promoção pendente: (origem, destino) aguardando escolha da peça.
        self.pending_promotion: tuple[int, int] | None = None
        # Retângulos do diálogo de promoção (preenchidos no draw).
        self._promo_rects: list[tuple[pygame.Rect, chess.PieceType]] = []

        self._info_font = pygame.font.SysFont("arial", 16)
        self._info_bold = pygame.font.SysFont("arial", 16, bold=True)

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_left_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                self.board_view.toggle_flip()
            elif event.key == pygame.K_u:
                self.undo()
            elif event.key == pygame.K_r:
                self.resign()

    def update(self, dt: float) -> None:
        pass  # nada animado nesta fase

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)
        self.board_view.draw(surface)
        self._draw_info_panel(surface)
        self._draw_promotion_dialog(surface)

    # ── estado da partida ─────────────────────────────────

    @property
    def game_over(self) -> bool:
        """True quando a partida terminou (App troca para FimDePartida)."""
        return self.game.is_game_over()

    def new_game(self) -> None:
        """Recomeça a partida da posição inicial."""
        self.game.reset()
        self.pending_promotion = None
        self._sync_view()

    def undo(self) -> None:
        """Desfaz o último lance (tecla U)."""
        self.game.undo()
        self.pending_promotion = None
        self._sync_view()

    def resign(self) -> None:
        """O jogador da vez desiste (tecla R)."""
        if not self.game.is_game_over():
            self.game.resign(self.game.turn)

    # ── sincronização com a visão ─────────────────────────

    def _sync_view(self) -> None:
        """Replica o estado do ``Game`` no ``BoardView``."""
        self.board_view.set_board(self.game.board)
        self.board_view.last_move = (
            self.game.board.peek() if self.game.board.move_stack else None
        )
        self.board_view.check_square = self.game.check_square()

    def _apply_move(self, move: chess.Move) -> None:
        """Executa o lance no ``Game`` e atualiza a visão."""
        self.game.push(move)
        self.pending_promotion = None
        self._sync_view()

    # ── interação por clique ──────────────────────────────

    def _on_left_click(self, pos: tuple[int, int]) -> None:
        # Diálogo de promoção aberto → o clique escolhe (ou cancela).
        if self.pending_promotion is not None:
            self._handle_promotion_click(pos)
            return

        if self.game.is_game_over():
            return  # partida encerrada: sem lances

        sq = pixel_to_square(pos[0], pos[1], flipped=self.board_view.flipped)
        if sq is None:
            self.board_view.selected_square = None
            self.board_view.legal_destinations = []
            return

        # Peça selecionada + clique em destino legal → move
        selected = self.board_view.selected_square
        if selected is not None and sq in self.board_view.legal_destinations:
            move = chess.Move(selected, sq)
            if self.game.needs_promotion(selected, sq):
                self.pending_promotion = (selected, sq)
            else:
                self._apply_move(move)
            return

        # Seleciona peça da cor que joga
        piece = self.game.board.piece_at(sq)
        if piece is not None and piece.color == self.game.turn:
            self.board_view.selected_square = sq
            self.board_view.legal_destinations = [
                m.to_square for m in self.game.legal_moves_from(sq)
            ]
        else:
            self.board_view.selected_square = None
            self.board_view.legal_destinations = []

    # ── diálogo de promoção ───────────────────────────────

    def _handle_promotion_click(self, pos: tuple[int, int]) -> None:
        """Clique no diálogo: escolhe a peça ou cancela fora dele."""
        for rect, piece_type in self._promo_rects:
            if rect.collidepoint(pos):
                from_sq, to_sq = self.pending_promotion
                self._apply_move(
                    chess.Move(from_sq, to_sq, promotion=piece_type)
                )
                return
        self.pending_promotion = None  # clique fora cancela

    def _draw_promotion_dialog(self, surface: pygame.Surface) -> None:
        """Barra com as 4 opções de promoção (dama, torre, bispo, cavalo)."""
        if self.pending_promotion is None:
            self._promo_rects = []
            return

        cell = 64
        width = cell * 4 + 16
        height = cell + 16
        x = (WINDOW_WIDTH - width) // 2
        y = 180

        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((30, 30, 30, 230))
        surface.blit(panel, (x, y))
        pygame.draw.rect(
            surface, (200, 200, 200), (x, y, width, height), 2
        )

        font = pygame.font.SysFont("segoeuisymbol", cell - 20)
        symbols = _PROMO_SYMBOLS[self.game.turn]
        self._promo_rects = []
        for i, (symbol, piece_type) in enumerate(
            zip(symbols, _PROMO_PIECES, strict=True)
        ):
            rect = pygame.Rect(x + 8 + i * cell, y + 8, cell, cell)
            pygame.draw.rect(surface, (70, 70, 70), rect, 1)
            glyph = font.render(symbol, True, (240, 240, 240))
            surface.blit(
                glyph,
                (
                    rect.centerx - glyph.get_width() // 2,
                    rect.centery - glyph.get_height() // 2,
                ),
            )
            self._promo_rects.append((rect, piece_type))

    # ── painel de informações (SAN + capturadas) ──────────

    def _draw_info_panel(self, surface: pygame.Surface) -> None:
        """Painel de texto: peças capturadas e lances em SAN."""
        if _PANEL_W < 80:
            return  # sem espaço na janela: não desenha

        x, y = _PANEL_X, BOARD_Y

        title = self._info_bold.render("Partida", True, COLOR_COORD)
        surface.blit(title, (x, y))
        y += 26

        # Peças capturadas por cor
        y = self._draw_captures(surface, chess.WHITE, x, y)
        y = self._draw_captures(surface, chess.BLACK, x, y)
        y += 10

        # Jogadas em SAN (pares numerados, mais recentes por último)
        san = self.game.san_history
        label = self._info_bold.render("Jogadas", True, COLOR_COORD)
        surface.blit(label, (x, y))
        y += 22
        pairs = [
            f"{i}. {san[i - 1]} {san[i]}"
            for i in range(1, len(san), 2)
        ]
        if len(san) % 2 == 1:
            pairs.append(
                f"{(len(san) + 1) // 2}. {san[-1]}"
            )
        # Mostra apenas as últimas que cabem no painel
        max_lines = (WINDOW_HEIGHT - y - 16) // 20
        for line in pairs[-max(0, max_lines):]:
            text = self._info_font.render(line, True, COLOR_COORD)
            surface.blit(text, (x, y))
            y += 20

    def _draw_captures(
        self, surface: pygame.Surface, color: chess.Color, x: int, y: int
    ) -> int:
        """Desenha as peças capturadas por ``color``; retorna o novo y."""
        # Símbolos Unicode das peças capturadas (cor do adversário)
        symbols = {
            (chess.PAWN, True): "♟",
            (chess.KNIGHT, True): "♞",
            (chess.BISHOP, True): "♝",
            (chess.ROOK, True): "♜",
            (chess.QUEEN, True): "♛",
            (chess.KING, True): "♚",
            (chess.PAWN, False): "♙",
            (chess.KNIGHT, False): "♘",
            (chess.BISHOP, False): "♗",
            (chess.ROOK, False): "♖",
            (chess.QUEEN, False): "♕",
            (chess.KING, False): "♔",
        }
        captured = self.game.captured_by(color)
        name = "Brancas" if color else "Pretas"
        label = self._info_bold.render(f"{name} capturaram:", True, COLOR_COORD)
        surface.blit(label, (x, y))
        y += 20
        if captured:
            line = " ".join(
                symbols[(pt, not color)] for pt in captured
            )
            text = self._info_font.render(line, True, COLOR_COORD)
            surface.blit(text, (x, y))
            y += 20
        else:
            text = self._info_font.render("—", True, COLOR_COORD)
            surface.blit(text, (x, y))
            y += 20
        return y + 4
