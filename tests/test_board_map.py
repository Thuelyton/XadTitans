"""Testes do mapa do tabuleiro em perspectiva (ui/board_map.py).

Usa o asset real gerado por tools/gen_board.py (committed).
"""

from __future__ import annotations

import json
from pathlib import Path

import chess
import pytest

from xadtitans.ui.board_map import BoardMap, _point_in_polygon

ASSET = Path(__file__).resolve().parent.parent / "assets" / "board"


@pytest.fixture(scope="module")
def board_map() -> BoardMap:
    return BoardMap.load(ASSET / "squares.json")


@pytest.fixture(scope="module")
def flipped(board_map: BoardMap) -> BoardMap:
    return board_map.flipped()


class TestCarregamento:
    def test_64_casas(self, board_map: BoardMap) -> None:
        for sq in range(64):
            assert board_map.center(sq) is not None

    def test_dimensoes_conferem_com_json(self) -> None:
        data = json.loads((ASSET / "squares.json").read_text(encoding="utf-8"))
        mapa = BoardMap.load(ASSET / "squares.json")
        assert mapa.width == data["width"] == 720
        assert mapa.height == data["height"] == 696

    def test_poligonos_dentro_da_imagem(self, board_map: BoardMap) -> None:
        for sq in range(64):
            for x, y in board_map.polygon(sq):
                assert 0 <= x < board_map.width
                assert 0 <= y < board_map.height


class TestGeometria:
    def test_a1_perto_h8_longe(self, board_map: BoardMap) -> None:
        """a1 (brancas) em baixo-esquerda; h8 em cima-direita."""
        ax, ay = board_map.center(chess.A1)
        hx, hy = board_map.center(chess.H8)
        assert ax < hx
        assert ay > hy

    def test_escala_decrescente_por_fileira(self, board_map: BoardMap) -> None:
        """Fileiras mais distantes têm peças menores."""
        scales = [board_map.scale(r * 8) for r in range(8)]
        assert scales[0] == pytest.approx(1.0)
        assert scales == sorted(scales, reverse=True)
        assert scales[-1] < 0.8

    def test_ordem_de_desenho_tras_para_frente(
        self, board_map: BoardMap
    ) -> None:
        order = board_map.draw_order()
        ys = [board_map.center(sq)[1] for sq in order]
        assert ys == sorted(ys)
        # a última casa desenhada é a mais próxima (rank 1)
        assert chess.square_rank(order[-1]) == 0


class TestConversao:
    @pytest.mark.parametrize("sq", range(64))
    def test_centro_retorna_a_propria_casa(
        self, board_map: BoardMap, sq: int
    ) -> None:
        cx, cy = board_map.center(sq)
        assert board_map.square_at(cx, cy) == sq

    @pytest.mark.parametrize("sq", range(64))
    def test_centro_retorna_a_propria_casa_virado(
        self, flipped: BoardMap, sq: int
    ) -> None:
        cx, cy = flipped.center(sq)
        assert flipped.square_at(cx, cy) == sq

    def test_fora_do_tabuleiro(self, board_map: BoardMap) -> None:
        assert board_map.square_at(-5, -5) is None
        assert board_map.square_at(2000, 2000) is None
        # canto superior esquerdo da imagem (moldura, fora do campo)
        assert board_map.square_at(30, 60) is None

    def test_flip_e_rotacao_180(self, board_map: BoardMap) -> None:
        """Virado, cada casa ocupa a própria posição rotacionada
        (a1, canto de baixo-esquerda, vai ao topo-direita)."""
        flipped = board_map.flipped()
        w, h = board_map.width, board_map.height
        ax, ay = board_map.center(chess.A1)
        fx, fy = flipped.center(chess.A1)
        assert fx == pytest.approx(w - ax)
        assert fy == pytest.approx(h - ay)

    def test_flip_preserva_escala(self, board_map: BoardMap) -> None:
        flipped = board_map.flipped()
        for sq in range(64):
            assert flipped.scale(sq) == board_map.scale(sq)


class TestPontoEmPoligono:
    def test_quadrado_unitario(self) -> None:
        poly = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
        assert _point_in_polygon(0.5, 0.5, poly)
        assert not _point_in_polygon(1.5, 0.5, poly)
        assert not _point_in_polygon(-0.5, 0.5, poly)

    def test_trapezio(self) -> None:
        """Trapezoide (perspectiva): pontos dentro/fora."""
        poly = ((0.0, 0.0), (10.0, 0.0), (7.0, 4.0), (3.0, 4.0))
        assert _point_in_polygon(5.0, 1.0, poly)
        assert not _point_in_polygon(9.0, 3.5, poly)  # fora (estreita)
        assert _point_in_polygon(5.0, 3.5, poly)
