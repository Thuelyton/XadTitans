"""Visão do tabuleiro em perspectiva (estilo Chess Titans).

Este módulo fornece:
  - Funções **puras** (sem pygame) de conversão pixel ↔ casa do
    tabuleiro **plano** — legado da Fase 1, mantidas (com seus
    testes) como utilitário;
  - ``BoardView``: desenha o tabuleiro em perspectiva
    (``assets/board/board_perspective.png`` + ``squares.json``),
    as peças em sprite (``assets/pieces/``) com escala por fileira,
    sombras, destaques (seleção, lances legais, último lance, xeque,
    hover) e animações, de trás para frente.

**Importante:** ``core/`` e ``ai/`` não importam ``pygame``.
Este módulo pertence a ``ui/`` e pode usar pygame livremente.
"""

from __future__ import annotations

import math

import chess
import pygame

from xadtitans.config import (
    BOARD_IMG_H,
    BOARD_IMG_W,
    BOARD_PERSP_X,
    BOARD_PERSP_Y,
    BOARD_X,
    BOARD_Y,
    SQUARE_SIZE,
)
from xadtitans.ui.animations import Anim
from xadtitans.ui.board_map import BoardMap
from xadtitans.utils.resources import resource_path

# ════════════════════════════════════════════════════════════
# Conversões puras do tabuleiro PLANO (legado da Fase 1)
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
# BoardView em perspectiva
# ════════════════════════════════════════════════════════════

# Fração do canvas 256px ocupada pela peça (~121px) → o canvas é
# exibido com ~2.02 × a largura da casa para a peça ocupar ~95%.
_PIECE_FACTOR = 256 / 121 * 0.95

# Âncora do sprite: ponto de apoio da peça no canvas 256×256.
_ANCHOR_X = 128 / 256
_ANCHOR_Y = 244 / 256

# Quantização de tamanho p/ cache de sprites durante animações.
_SIZE_STEP = 4

# Cores dos destaques (RGBA)
_C_SELECTED = (255, 244, 130, 105)
_C_LAST_MOVE = (230, 195, 70, 80)
_C_CHECK = (235, 64, 52, 130)
_C_HOVER = (255, 255, 255, 55)
_C_DOT = (40, 30, 20, 130)
_C_RING = (40, 30, 20, 150)
_C_SHADOW = (0, 0, 0, 80)


def _load_image(path) -> pygame.Surface:
    """Carrega PNG com convert_alpha quando possível."""
    surf = pygame.image.load(str(path))
    try:
        return surf.convert_alpha()
    except pygame.error:
        return surf


class BoardView:
    """Desenha o tabuleiro em perspectiva, peças e destaques."""

    def __init__(self) -> None:
        self.flipped = False

        base_map = BoardMap.load(resource_path("assets/board/squares.json"))
        self._base_map = base_map
        self._map = base_map

        self._board_img = _load_image(
            resource_path("assets/board/board_perspective.png")
        )
        if self._board_img.get_size() != (BOARD_IMG_W, BOARD_IMG_H):
            self._board_img = pygame.transform.smoothscale(
                self._board_img, (BOARD_IMG_W, BOARD_IMG_H)
            )

        # Largura da casa mais próxima (referência de escala das peças)
        a1 = self._base_map.polygon(chess.A1)
        self._base_cell_w = a1[1][0] - a1[0][0]

        # Cache de sprites: (piece_type, is_white, size) → Surface
        self._sprites: dict[tuple[int, bool, int], pygame.Surface] = {}
        self._shadows: dict[int, pygame.Surface] = {}
        self._build_cache()

        # Estado de destaque (preenchido pela cena)
        self.selected_square: int | None = None
        self.legal_destinations: list[int] = []
        self.last_move: chess.Move | None = None
        self.check_square: int | None = None
        self.hover_square: int | None = None

        # Tabuleiro (cópia só para consulta de peças)
        self.board: chess.Board = chess.Board()

    # ── cache de sprites ─────────────────────────────────

    def _sprite_size(self, scale: float) -> int:
        """Largura exibida do canvas 256px para a escala dada."""
        return max(
            _SIZE_STEP,
            int(self._base_cell_w * scale * _PIECE_FACTOR)
            // _SIZE_STEP * _SIZE_STEP,
        )

    def _build_cache(self) -> None:
        """Pré-renderiza todos os sprites nas 8 escalas de fileira."""
        for rank in range(8):
            size = self._sprite_size(self._base_map.scale(rank * 8))
            for piece_type in chess.PIECE_TYPES:
                for color in (True, False):
                    self._sprite(piece_type, color, size)
            self._shadow(size)

    def _sprite_path(self, piece_type: int, color: bool) -> object:
        name = chess.piece_name(piece_type)
        return resource_path("assets/pieces") / (
            f"{'white' if color else 'black'}_{name}.png"
        )

    def _raw_sprites(self) -> dict[tuple[int, bool], pygame.Surface]:
        if not hasattr(self, "_raw"):
            self._raw = {
                (pt, c): _load_image(self._sprite_path(pt, c))
                for pt in chess.PIECE_TYPES
                for c in (True, False)
            }
        return self._raw

    def _sprite(self, piece_type: int, color: bool, size: int) -> pygame.Surface:
        """Sprite em tamanho (com cache; quantizado em _SIZE_STEP)."""
        size = max(_SIZE_STEP, size // _SIZE_STEP * _SIZE_STEP)
        key = (piece_type, color, size)
        cached = self._sprites.get(key)
        if cached is None:
            raw = self._raw_sprites()[(piece_type, color)]
            cached = pygame.transform.smoothscale(
                raw, (size, size * raw.get_height() // raw.get_width())
            )
            self._sprites[key] = cached
        return cached

    def get_sprite(
        self, piece_type: int, color: bool, size: int
    ) -> pygame.Surface:
        """Sprite público (usado pelo painel lateral, diálogo etc.)."""
        return self._sprite(piece_type, color, size)

    def _shadow(self, size: int) -> pygame.Surface:
        size = max(_SIZE_STEP, size // _SIZE_STEP * _SIZE_STEP)
        cached = self._shadows.get(size)
        if cached is None:
            w, h = int(size * 0.52), max(4, int(size * 0.14))
            cached = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(cached, _C_SHADOW, (0, 0, w, h))
            self._shadows[size] = cached
        return cached

    # ── estado ───────────────────────────────────────────

    def set_board(self, board: chess.Board) -> None:
        """Define a posição a ser exibida."""
        self.board = board.copy()
        self.selected_square = None
        self.legal_destinations = []

    def toggle_flip(self) -> None:
        """Inverte a orientação do tabuleiro (rotação de 180°)."""
        self.flipped = not self.flipped
        self._map = self._base_map.flipped() if self.flipped else self._base_map

    def square_at(self, px: float, py: float) -> int | None:
        """Casa sob o pixel da TELA (não da imagem do tabuleiro)."""
        return self._map.square_at(
            px - BOARD_PERSP_X, py - BOARD_PERSP_Y
        )

    # ── desenho ──────────────────────────────────────────

    def draw(
        self,
        surface: pygame.Surface,
        anims: dict[int, list[Anim]] | None = None,
    ) -> None:
        """Desenha tabuleiro, destaques e peças (de trás p/ frente)."""
        surface.blit(self._board_img, (BOARD_PERSP_X, BOARD_PERSP_Y))
        anims = anims or {}

        self._draw_last_move(surface)
        self._draw_selected(surface)
        self._draw_check(surface)
        self._draw_legal(surface)
        self._draw_hover(surface)

        # Peças estáticas: trás → frente, pulando casas animadas
        for sq in self._map.draw_order():
            if sq in anims:
                continue
            piece = self.board.piece_at(sq)
            if piece is not None:
                self._draw_piece(surface, piece, sq)

        # Peças animadas: fades por baixo, deslizes por cima
        anim_list = [a for group in anims.values() for a in group]
        for a in sorted(anim_list, key=lambda a: (a.kind != "fade", a.pos[1])):
            self._draw_anim(surface, a)

    # ── destaques ────────────────────────────────────────

    def _overlay(self, surface: pygame.Surface, sq: int, color) -> None:
        """Preenche o polígono da casa com cor RGBA."""
        poly = [
            (x + BOARD_PERSP_X, y + BOARD_PERSP_Y)
            for x, y in self._map.polygon(sq)
        ]
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        rect = pygame.Rect(
            int(min(xs)), int(min(ys)),
            int(max(xs) - min(xs)) + 2, int(max(ys) - min(ys)) + 2,
        )
        tile = pygame.Surface(rect.size, pygame.SRCALPHA)
        # desloca o polígono para a origem do tile
        local = [(p[0] - rect.x, p[1] - rect.y) for p in poly]
        pygame.draw.polygon(tile, color, local)
        surface.blit(tile, rect.topleft)

    def _center(self, sq: int) -> tuple[float, float]:
        cx, cy = self._map.center(sq)
        return cx + BOARD_PERSP_X, cy + BOARD_PERSP_Y

    def _cell_w(self, sq: int) -> float:
        poly = self._map.polygon(sq)
        return (poly[1][0] - poly[0][0] + poly[2][0] - poly[3][0]) / 2.0

    def _draw_last_move(self, surface: pygame.Surface) -> None:
        if self.last_move is not None:
            for sq in (self.last_move.from_square, self.last_move.to_square):
                self._overlay(surface, sq, _C_LAST_MOVE)

    def _draw_selected(self, surface: pygame.Surface) -> None:
        if self.selected_square is not None:
            self._overlay(surface, self.selected_square, _C_SELECTED)

    def _draw_check(self, surface: pygame.Surface) -> None:
        if self.check_square is not None:
            t = pygame.time.get_ticks() / 1000.0
            pulse = 0.75 + 0.25 * (0.5 + 0.5 * math.sin(t * 5.0))
            color = (
                _C_CHECK[0], _C_CHECK[1], _C_CHECK[2],
                int(_C_CHECK[3] * pulse),
            )
            self._overlay(surface, self.check_square, color)

    def _draw_legal(self, surface: pygame.Surface) -> None:
        for sq in self.legal_destinations:
            cx, cy = self._center(sq)
            w = self._cell_w(sq)
            if self.board.piece_at(sq) is not None:
                # Anel de captura
                radius = int(w * 0.44)
                _ring(surface, (cx, cy), radius, _C_RING, max(3, w * 0.06))
            else:
                # Ponto central
                radius = int(w * 0.11)
                _dot(surface, (cx, cy), radius, _C_DOT)

    def _draw_hover(self, surface: pygame.Surface) -> None:
        if (
            self.hover_square is not None
            and self.hover_square != self.selected_square
        ):
            poly = [
                (x + BOARD_PERSP_X, y + BOARD_PERSP_Y)
                for x, y in self._map.polygon(self.hover_square)
            ]
            pygame.draw.polygon(surface, _C_HOVER, poly, 2)

    # ── peças ────────────────────────────────────────────

    def _foot(self, sq: int) -> tuple[float, float]:
        """Ponto de apoio da peça: centro da casa + leve offset p/ baixo."""
        cx, cy = self._center(sq)
        poly = self._map.polygon(sq)
        near_y = (poly[0][1] + poly[1][1]) / 2.0
        far_y = (poly[2][1] + poly[3][1]) / 2.0
        return cx, cy + (near_y - far_y) * 0.16

    def piece_anchor(self, sq: int) -> tuple[float, float]:
        """Ponto de apoio da peça na casa (coords da TELA; p/ animações)."""
        return self._foot(sq)

    def scale_of(self, sq: int) -> float:
        """Escala da peça na casa (p/ animações entre fileiras)."""
        return self._map.scale(sq)

    def _draw_piece(
        self,
        surface: pygame.Surface,
        piece: chess.Piece,
        sq: int,
        pos: tuple[float, float] | None = None,
        scale: float | None = None,
        alpha: float = 1.0,
    ) -> None:
        if scale is None:
            scale = self._map.scale(sq)
        size = self._sprite_size(scale)
        sprite = self._sprite(piece.piece_type, piece.color, size)
        shadow = self._shadow(size)
        fx, fy = pos if pos is not None else self._foot(sq)
        x = fx - size * _ANCHOR_X
        y = fy - size * _ANCHOR_Y
        surface.blit(
            shadow,
            (x + size * 0.24, fy - shadow.get_height() * 0.55),
        )
        if alpha < 1.0:
            sprite = sprite.copy()
            sprite.set_alpha(int(alpha * 255))
        surface.blit(sprite, (x, y))

    def _draw_anim(self, surface: pygame.Surface, a: Anim) -> None:
        piece = chess.Piece(a.sprite[0], a.sprite[1])
        self._draw_piece(
            surface, piece, a.square, pos=a.pos, scale=a.scale, alpha=a.alpha
        )


# ── primitivas com alfa ─────────────────────────────────

def _dot(
    surface: pygame.Surface, pos: tuple[float, float], radius: int, color
) -> None:
    dot = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(dot, color, (radius + 1, radius + 1), radius)
    surface.blit(dot, (pos[0] - radius - 1, pos[1] - radius - 1))


def _ring(
    surface: pygame.Surface,
    pos: tuple[float, float],
    radius: int,
    color,
    width: float,
) -> None:
    size = radius * 2 + int(width) * 2 + 4
    ring = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(
        ring, color, (size // 2, size // 2), radius, max(2, int(width))
    )
    surface.blit(ring, (pos[0] - size // 2, pos[1] - size // 2))
