"""Visão do tabuleiro de xadrez.

Este módulo fornece:
  - Funções **puras** (sem pygame) de conversão pixel ↔ casa,
    usadas em testes e na interface.
  - ``BoardView``, que usa pygame para desenhar o tabuleiro,
    coordenadas e peças (provisoriamente em Unicode).

**Importante:** ``core/`` e ``ai/`` não importam ``pygame``.
Este módulo pertence a ``ui/`` e pode usar pygame livremente.
"""

from __future__ import annotations

import chess
import pygame

from xadtitans.config import (
    BOARD_SIZE,
    BOARD_X,
    BOARD_Y,
    COLOR_COORD,
    COLOR_DARK_SQ,
    COLOR_LAST_MOVE_DARK,
    COLOR_LAST_MOVE_LIGHT,
    COLOR_LIGHT_SQ,
    COLOR_SELECTED_DARK,
    COLOR_SELECTED_LIGHT,
    SQUARE_SIZE,
)

# ════════════════════════════════════════════════════════════
# Conversões puras (sem pygame) — testáveis independentemente
# ════════════════════════════════════════════════════════════

def pixel_to_square(
    px: float,
    py: float,
    board_x: int = BOARD_X,
    board_y: int = BOARD_Y,
    sq_size: int = SQUARE_SIZE,
    flipped: bool = False,
) -> int | None:
    """Retorna o square (0–63, constante ``chess.A1`` … ``chess.H8``)
    correspondente à posição em pixels, ou ``None`` se estiver fora
    do tabuleiro.
    """
    fx = (px - board_x) / sq_size
    fy = (py - board_y) / sq_size

    if fx < 0.0 or fx >= 8.0 or fy < 0.0 or fy >= 8.0:
        return None

    col = int(fx)
    row = int(fy)

    if flipped:
        file_ = 7 - col
        rank = row
    else:
        file_ = col
        rank = 7 - row

    return chess.square(file_, rank)


def square_to_pixel(
    sq: int,
    board_x: int = BOARD_X,
    board_y: int = BOARD_Y,
    sq_size: int = SQUARE_SIZE,
    flipped: bool = False,
) -> tuple[int, int]:
    """Retorna o centro ``(px, py)`` em pixels de um square."""
    file_ = chess.square_file(sq)
    rank = chess.square_rank(sq)

    if flipped:
        col = 7 - file_
        row = rank
    else:
        col = file_
        row = 7 - rank

    cx = board_x + col * sq_size + sq_size // 2
    cy = board_y + row * sq_size + sq_size // 2
    return cx, cy


# ════════════════════════════════════════════════════════════
# Peças Unicode (provisório — preparado para trocar por sprites)
# ════════════════════════════════════════════════════════════

_UNICODE_PIECES: dict[tuple[int, bool], str] = {
    # (piece_type, is_white) → símbolo Unicode
    (chess.PAWN, True): "♙",
    (chess.KNIGHT, True): "♘",
    (chess.BISHOP, True): "♗",
    (chess.ROOK, True): "♖",
    (chess.QUEEN, True): "♕",
    (chess.KING, True): "♔",
    (chess.PAWN, False): "♟",
    (chess.KNIGHT, False): "♞",
    (chess.BISHOP, False): "♝",
    (chess.ROOK, False): "♜",
    (chess.QUEEN, False): "♛",
    (chess.KING, False): "♚",
}

# Fontes do sistema que contêm símbolos de xadrez (ordem de tentativa)
_CHESS_FONTS = ["segoeuisymbol", "arial unicode ms", "arial", None]

# Cores para renderização das peças Unicode
_PIECE_COLOR_WHITE = (255, 255, 255)
_PIECE_COLOR_BLACK = (30, 30, 30)
_PIECE_SHADOW_WHITE = (0, 0, 0)
_PIECE_SHADOW_BLACK = (220, 220, 220)


def _unicode_symbol(piece: chess.Piece) -> str:
    """Retorna o caractere Unicode para uma peça."""
    return _UNICODE_PIECES[(piece.piece_type, piece.color)]


# ════════════════════════════════════════════════════════════
# BoardView — desenha tabuleiro, coordenadas e peças
# ════════════════════════════════════════════════════════════

class BoardView:
    """Responsável por desenhar o tabuleiro e as peças na tela."""

    def __init__(self) -> None:
        self.flipped = False
        self.board: chess.Board = chess.Board()

        # Peça selecionada e lances legais (para futuras fases)
        self.selected_square: int | None = None
        self.legal_destinations: list[int] = []

        # Último lance (para destaque visual)
        self.last_move: chess.Move | None = None

        # Fonte para coordenadas
        self._coord_font = pygame.font.SysFont("arial", 18, bold=True)

        # Fonte para peças Unicode
        self._piece_font = self._load_piece_font()

        # Cache de superfícies de peça (pre-criadas)
        self._piece_cache: dict[tuple[int, bool], pygame.Surface] = {}

    # ── carregamento ─────────────────────────────────────

    @staticmethod
    def _load_piece_font() -> pygame.font.Font:
        """Tenta carregar uma fonte com suporte a Unicode chess."""
        for name in _CHESS_FONTS:
            try:
                font = pygame.font.SysFont(name, SQUARE_SIZE - 16)
                # Testa se renderiza o símbolo do rei branco
                surf = font.render("♔", True, (255, 255, 255))
                if surf.get_width() > 4:
                    return font
            except (TypeError, OSError):
                continue
        # Fallback
        return pygame.font.Font(None, SQUARE_SIZE - 16)

    def _build_piece_cache(self) -> None:
        """Pré-renderiza todas as peças Unicode em tamanho de cache."""
        for piece_type in chess.PIECE_TYPES:
            for color in (True, False):
                key = (piece_type, color)
                if key in self._piece_cache:
                    continue
                symbol = _UNICODE_PIECES[key]
                color_rgb = _PIECE_COLOR_WHITE if color else _PIECE_COLOR_BLACK
                shadow_rgb = _PIECE_SHADOW_WHITE if color else _PIECE_SHADOW_BLACK
                # Sombra
                shadow = self._piece_font.render(symbol, True, shadow_rgb)
                # Peça
                piece_surf = self._piece_font.render(symbol, True, color_rgb)
                # Surface combinada
                w = max(shadow.get_width(), piece_surf.get_width()) + 4
                h = max(shadow.get_height(), piece_surf.get_height()) + 4
                combined = pygame.Surface((w, h), pygame.SRCALPHA)
                combined.blit(shadow, (2, 2))
                combined.blit(piece_surf, (0, 0))
                self._piece_cache[key] = combined

    # ── configuração ─────────────────────────────────────

    def set_board(self, board: chess.Board) -> None:
        """Define a posição a ser exibida."""
        self.board = board.copy()
        self.selected_square = None
        self.legal_destinations = []

    def toggle_flip(self) -> None:
        """Inverte a orientação do tabuleiro."""
        self.flipped = not self.flipped

    # ── desenho ──────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        """Desenha o tabuleiro completo: casas, coordenadas e peças."""
        self._build_piece_cache()
        self._draw_squares(surface)
        self._draw_highlights(surface)
        self._draw_coordinates(surface)
        self._draw_pieces(surface)

    def _draw_squares(self, surface: pygame.Surface) -> None:
        """Desenha as 64 casas do tabuleiro."""
        for sq in range(64):
            file_ = chess.square_file(sq)
            rank = chess.square_rank(sq)
            is_light = (file_ + rank) % 2 == 0
            color = COLOR_LIGHT_SQ if is_light else COLOR_DARK_SQ
            if self.flipped:
                col = 7 - file_
                row = rank
            else:
                col = file_
                row = 7 - rank
            rect = pygame.Rect(
                BOARD_X + col * SQUARE_SIZE,
                BOARD_Y + row * SQUARE_SIZE,
                SQUARE_SIZE,
                SQUARE_SIZE,
            )
            pygame.draw.rect(surface, color, rect)

    def _draw_highlights(self, surface: pygame.Surface) -> None:
        """Destaca o último lance e a casa selecionada."""
        # Destaque do último lance
        if self.last_move is not None:
            for sq in (self.last_move.from_square, self.last_move.to_square):
                file_ = chess.square_file(sq)
                rank = chess.square_rank(sq)
                is_light = (file_ + rank) % 2 == 0
                color = COLOR_LAST_MOVE_LIGHT if is_light else COLOR_LAST_MOVE_DARK
                x, y = square_to_pixel(
                    sq, BOARD_X, BOARD_Y, SQUARE_SIZE, self.flipped
                )
                rect = pygame.Rect(
                    x - SQUARE_SIZE // 2,
                    y - SQUARE_SIZE // 2,
                    SQUARE_SIZE,
                    SQUARE_SIZE,
                )
                pygame.draw.rect(surface, color, rect)

        # Destaque da casa selecionada
        if self.selected_square is not None:
            sq = self.selected_square
            file_ = chess.square_file(sq)
            rank = chess.square_rank(sq)
            is_light = (file_ + rank) % 2 == 0
            color = COLOR_SELECTED_LIGHT if is_light else COLOR_SELECTED_DARK
            x, y = square_to_pixel(
                sq, BOARD_X, BOARD_Y, SQUARE_SIZE, self.flipped
            )
            rect = pygame.Rect(
                x - SQUARE_SIZE // 2,
                y - SQUARE_SIZE // 2,
                SQUARE_SIZE,
                SQUARE_SIZE,
            )
            pygame.draw.rect(surface, color, rect)

        # Pontos nos destinos legais
        for dest in self.legal_destinations:
            piece = self.board.piece_at(dest)
            cx, cy = square_to_pixel(
                dest, BOARD_X, BOARD_Y, SQUARE_SIZE, self.flipped
            )
            if piece is not None:
                # Anel de captura
                pygame.draw.circle(
                    surface,
                    (100, 100, 100),
                    (cx, cy),
                    SQUARE_SIZE // 2,
                    4,
                )
            else:
                # Ponto central
                pygame.draw.circle(
                    surface,
                    (100, 100, 100),
                    (cx, cy),
                    SQUARE_SIZE // 8,
                )

    def _draw_coordinates(self, surface: pygame.Surface) -> None:
        """Desenha as coordenadas (a–h e 1–8) ao redor do tabuleiro."""
        files = "abcdefgh"
        ranks = "87654321"

        if self.flipped:
            files = files[::-1]
            ranks = ranks[::-1]

        # Letras (abaixo do tabuleiro)
        for i, letter in enumerate(files):
            x = BOARD_X + i * SQUARE_SIZE + SQUARE_SIZE // 2
            y = BOARD_Y + BOARD_SIZE + 4
            text = self._coord_font.render(letter, True, COLOR_COORD)
            surface.blit(text, (x - text.get_width() // 2, y))

        # Números (à esquerda do tabuleiro)
        for i, digit in enumerate(ranks):
            x = BOARD_X - 22
            y = BOARD_Y + i * SQUARE_SIZE + SQUARE_SIZE // 2
            text = self._coord_font.render(digit, True, COLOR_COORD)
            surface.blit(text, (x, y - text.get_height() // 2))

    def _draw_pieces(self, surface: pygame.Surface) -> None:
        """Desenha as peças usando Unicode (provisório)."""
        for sq in range(64):
            piece = self.board.piece_at(sq)
            if piece is None:
                continue
            key = (piece.piece_type, piece.color)
            cached = self._piece_cache.get(key)
            if cached is None:
                continue
            cx, cy = square_to_pixel(
                sq, BOARD_X, BOARD_Y, SQUARE_SIZE, self.flipped
            )
            surface.blit(
                cached,
                (cx - cached.get_width() // 2, cy - cached.get_height() // 2),
            )
