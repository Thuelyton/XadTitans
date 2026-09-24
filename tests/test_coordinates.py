"""Testes de conversão pixel ↔ casa (64 casas, normal e virado).

As funções de conversão são puras — não precisam de janela pygame.
"""

import chess
import pytest

from xadtitans.config import BOARD_X, BOARD_Y, SQUARE_SIZE
from xadtitans.ui.board_view import pixel_to_square, square_to_pixel

# ════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════

def _center(sq: int, flipped: bool = False) -> tuple[int, int]:
    """Centro em pixels de um square (usando config global)."""
    return square_to_pixel(sq, BOARD_X, BOARD_Y, SQUARE_SIZE, flipped)


def _bottom_left(sq: int, flipped: bool = False) -> tuple[int, int]:
    """Canto inferior-esquerdo do square."""
    cx, cy = _center(sq, flipped)
    return cx - SQUARE_SIZE // 2 + 1, cy - SQUARE_SIZE // 2 + 1


def _top_right(sq: int, flipped: bool = False) -> tuple[int, int]:
    """Canto superior-direito do square."""
    cx, cy = _center(sq, flipped)
    return cx + SQUARE_SIZE // 2 - 1, cy + SQUARE_SIZE // 2 - 1


# ════════════════════════════════════════════════════════════
# square_to_pixel → pixel_to_square (ida e volta)
# ════════════════════════════════════════════════════════════

class TestRoundtripNormal:
    """Centro e cantos de cada square → pixel → square, orientação normal."""

    @pytest.mark.parametrize("sq", range(64))
    def test_center_roundtrips(self, sq: int) -> None:
        cx, cy = _center(sq, flipped=False)
        result = pixel_to_square(cx, cy, flipped=False)
        assert result == sq, f"sq={sq} cx={cx} cy={cy} → {result}"

    @pytest.mark.parametrize("sq", range(64))
    def test_bottom_left_roundtrips(self, sq: int) -> None:
        bx, by = _bottom_left(sq, flipped=False)
        result = pixel_to_square(bx, by, flipped=False)
        assert result == sq, f"sq={sq} bx={bx} by={by} → {result}"

    @pytest.mark.parametrize("sq", range(64))
    def test_top_right_roundtrips(self, sq: int) -> None:
        tx, ty = _top_right(sq, flipped=False)
        result = pixel_to_square(tx, ty, flipped=False)
        assert result == sq, f"sq={sq} tx={tx} ty={ty} → {result}"


class TestRoundtripFlipped:
    """Centro e cantos de cada square → pixel → square, orientação virada."""

    @pytest.mark.parametrize("sq", range(64))
    def test_center_roundtrips(self, sq: int) -> None:
        cx, cy = _center(sq, flipped=True)
        result = pixel_to_square(cx, cy, flipped=True)
        assert result == sq, f"sq={sq} cx={cx} cy={cy} → {result}"

    @pytest.mark.parametrize("sq", range(64))
    def test_bottom_left_roundtrips(self, sq: int) -> None:
        bx, by = _bottom_left(sq, flipped=True)
        result = pixel_to_square(bx, by, flipped=True)
        assert result == sq, f"sq={sq} bx={bx} by={by} → {result}"

    @pytest.mark.parametrize("sq", range(64))
    def test_top_right_roundtrips(self, sq: int) -> None:
        tx, ty = _top_right(sq, flipped=True)
        result = pixel_to_square(tx, ty, flipped=True)
        assert result == sq, f"sq={sq} tx={tx} ty={ty} → {result}"


# ════════════════════════════════════════════════════════════
# Posições conhecidas (orientação normal)
# ════════════════════════════════════════════════════════════

class TestKnownPositionsNormal:
    """Verifica a identidade de casas importantes no modo normal."""

    def test_a1_is_bottom_left(self) -> None:
        cx, cy = _center(chess.A1, flipped=False)
        result = pixel_to_square(cx, cy, flipped=False)
        assert result == chess.A1

    def test_h8_is_top_right(self) -> None:
        cx, cy = _center(chess.H8, flipped=False)
        result = pixel_to_square(cx, cy, flipped=False)
        assert result == chess.H8

    def test_a8_is_top_left(self) -> None:
        cx, cy = _center(chess.A8, flipped=False)
        result = pixel_to_square(cx, cy, flipped=False)
        assert result == chess.A8

    def test_h1_is_bottom_right(self) -> None:
        cx, cy = _center(chess.H1, flipped=False)
        result = pixel_to_square(cx, cy, flipped=False)
        assert result == chess.H1

    def test_e1_is_white_king_home(self) -> None:
        cx, cy = _center(chess.E1, flipped=False)
        result = pixel_to_square(cx, cy, flipped=False)
        assert result == chess.E1

    def test_d8_is_black_king_home(self) -> None:
        cx, cy = _center(chess.D8, flipped=False)
        result = pixel_to_square(cx, cy, flipped=False)
        assert result == chess.D8


class TestKnownPositionsFlipped:
    """Verifica a identidade de casas importantes no modo virado."""

    def test_a1_moves_to_bottom_right(self) -> None:
        cx, cy = _center(chess.A1, flipped=True)
        result = pixel_to_square(cx, cy, flipped=True)
        assert result == chess.A1

    def test_h8_moves_to_bottom_left(self) -> None:
        cx, cy = _center(chess.H8, flipped=True)
        result = pixel_to_square(cx, cy, flipped=True)
        assert result == chess.H8

    def test_a8_moves_to_bottom_right(self) -> None:
        cx, cy = _center(chess.A8, flipped=True)
        result = pixel_to_square(cx, cy, flipped=True)
        assert result == chess.A8


# ════════════════════════════════════════════════════════════
# Fora do tabuleiro
# ════════════════════════════════════════════════════════════

class TestOutOfBounds:
    """Pixels fora do tabuleiro devem retornar None."""

    @pytest.mark.parametrize(
        "px, py",
        [
            (0, 0),                          # canto superior-esquerdo da janela
            (BOARD_X - 1, BOARD_Y),          # à esquerda do tabuleiro
            (BOARD_X, BOARD_Y - 1),          # acima do tabuleiro
            (BOARD_X + SQUARE_SIZE * 8, BOARD_Y),  # à direita
            (BOARD_X, BOARD_Y + SQUARE_SIZE * 8),  # abaixo
        ],
    )
    def test_outside_returns_none(self, px: int, py: int) -> None:
        assert pixel_to_square(px, py) is None


# ════════════════════════════════════════════════════════════
# Consistência entre orientações
# ════════════════════════════════════════════════════════════

class TestFlipConsistency:
    """Verifica que flip inverte corretamente a posição visual."""

    def test_a1_position_differs(self) -> None:
        """A1 deve ter pixel diferente quando flipped vs normal."""
        normal = _center(chess.A1, flipped=False)
        flipped = _center(chess.A1, flipped=True)
        assert normal != flipped

    def test_a1_flipped_equals_h8_normal(self) -> None:
        """A1 virado (top-right) deve ter a mesma posição de H8 normal (top-right)."""
        a1_flipped = _center(chess.A1, flipped=True)
        h8_normal = _center(chess.H8, flipped=False)
        assert a1_flipped == h8_normal

    def test_a8_flipped_equals_h1_normal(self) -> None:
        """A8 virado (bottom-right) deve ter a mesma posição de H1 normal (bottom-right)."""
        a8_flipped = _center(chess.A8, flipped=True)
        h1_normal = _center(chess.H1, flipped=False)
        assert a8_flipped == h1_normal
