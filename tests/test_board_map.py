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
def black_map() -> BoardMap:
    """Mapa da visão das pretas (asset gerado para a própria câmera)."""
    return BoardMap.load(ASSET / "squares_black.json")


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
        self, black_map: BoardMap, sq: int
    ) -> None:
        cx, cy = black_map.center(sq)
        assert black_map.square_at(cx, cy) == sq

    def test_fora_do_tabuleiro(self, board_map: BoardMap) -> None:
        assert board_map.square_at(-5, -5) is None
        assert board_map.square_at(2000, 2000) is None
        # canto superior esquerdo da imagem (moldura, fora do campo)
        assert board_map.square_at(30, 60) is None


class TestCantosPorPerspectiva:
    """Critérios de aceitação da orientação (Fase 6.7/bug de flip).

    BRANCAS: a1 inferior-esquerda, h1 inferior-direita,
             a8 superior-esquerda, h8 superior-direita.
    PRETAS:  h8 inferior-esquerda, a8 inferior-direita,
             h1 superior-esquerda, a1 superior-direita.

    Cada visão usa o mapa gerado para a própria câmera.
    """

    @staticmethod
    def _quadrantes(m: BoardMap) -> dict[int, str]:
        """House → quadrante ("ES|EI|DS|DI") relativo ao centro do campo."""
        xs = [m.center(sq)[0] for sq in range(64)]
        ys = [m.center(sq)[1] for sq in range(64)]
        xmid = (min(xs) + max(xs)) / 2
        ymid = (min(ys) + max(ys)) / 2
        out = {}
        for sq in range(64):
            cx, cy = m.center(sq)
            out[sq] = ("E" if cx < xmid else "D") + (
                "S" if cy < ymid else "I"
            )
        return out

    def test_brancas_cantos(self, board_map: BoardMap) -> None:
        q = self._quadrantes(board_map)
        assert q[chess.A1] == "EI", "brancas: a1 deve ficar em baixo-esquerda"
        assert q[chess.H1] == "DI", "brancas: h1 deve ficar em baixo-direita"
        assert q[chess.A8] == "ES", "brancas: a8 deve ficar em cima-esquerda"
        assert q[chess.H8] == "DS", "brancas: h8 deve ficar em cima-direita"

    def test_pretas_cantos(self, black_map: BoardMap) -> None:
        q = self._quadrantes(black_map)
        assert q[chess.H8] == "EI", "pretas: h8 deve ficar em baixo-esquerda"
        assert q[chess.A8] == "DI", "pretas: a8 deve ficar em baixo-direita"
        assert q[chess.H1] == "ES", "pretas: h1 deve ficar em cima-esquerda"
        assert q[chess.A1] == "DS", "pretas: a1 deve ficar em cima-direita"

    def test_pretas_perspectiva_legitima(
        self, board_map: BoardMap, black_map: BoardMap
    ) -> None:
        """Visão preta é re-projeção (rank 8 perto), não rotação da imagem.

        Rank 8 deve ter a maior escala (casa larga, perto da câmera) e
        rank 1 a menor — o inverso exato das brancas. Uma simples
        rotação 180° dos polígonos manteria as escalas trocadas (bug
        de escala invertida corrigido nesta fase).
        """
        white_scales = [board_map.scale(r * 8) for r in range(8)]
        black_scales = [black_map.scale(r * 8) for r in range(8)]
        assert black_scales == list(reversed(white_scales))
        assert black_scales[7] == pytest.approx(1.0)  # rank 8 = perto
        assert black_scales[0] < 0.8                   # rank 1 = longe
        # E a imagem preta difere da branca (re-projeção própria):
        assert board_map.polygon(chess.A1) != black_map.polygon(chess.A1)


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
