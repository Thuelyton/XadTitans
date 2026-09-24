"""Geometria do tabuleiro em perspectiva (sem pygame).

Carrega ``assets/board/squares.json`` (gerado por ``tools/gen_board.py``)
e fornece:
  - centro/escala/polígono de cada casa;
  - conversão pixel → casa (teste de ponto em polígono);
  - o mapa espelhado (tabuleiro virado: rotação de 180°);
  - ordem de desenho de trás para frente (longe → perto).

Módulo **puro** — usado por ``ui/board_view.py`` e pelos testes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

Point = tuple[float, float]


@dataclass(frozen=True)
class SquareGeom:
    """Geometria de uma casa na imagem do tabuleiro."""

    square: int
    polygon: tuple[Point, ...]
    center: Point
    scale: float


class BoardMap:
    """Mapa de casa → geometria na imagem do tabuleiro."""

    def __init__(
        self,
        squares: dict[int, SquareGeom],
        width: int,
        height: int,
    ) -> None:
        self._squares = squares
        self.width = width
        self.height = height

    # ── construção ───────────────────────────────────────

    @classmethod
    def load(cls, path: str | Path) -> BoardMap:
        """Carrega o mapa de um squares.json."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        squares = {
            entry["square"]: SquareGeom(
                square=entry["square"],
                polygon=tuple(
                    (float(x), float(y)) for x, y in entry["polygon"]
                ),
                center=(float(entry["center"][0]), float(entry["center"][1])),
                scale=float(entry["scale"]),
            )
            for entry in data["squares"]
        }
        return cls(squares, int(data["width"]), int(data["height"]))

    def flipped(self) -> BoardMap:
        """Mapa do tabuleiro virado (rotação de 180° da imagem).

        Cada casa mantém sua identidade: a posição exibida é a
        posição física da própria casa rotacionada 180° (a1, que era
        o canto de baixo-esquerda, passa ao topo-direita).
        """

        def rot(p: Point) -> Point:
            return (float(self.width) - p[0], float(self.height) - p[1])

        squares = {
            sq: SquareGeom(
                square=sq,
                polygon=tuple(rot(p) for p in self._squares[sq].polygon),
                center=rot(self._squares[sq].center),
                scale=self._squares[sq].scale,
            )
            for sq in self._squares
        }
        return BoardMap(squares, self.width, self.height)

    # ── consultas ────────────────────────────────────────

    def center(self, square: int) -> Point:
        """Centro (px) da casa na imagem."""
        return self._squares[square].center

    def scale(self, square: int) -> float:
        """Escala relativa da peça na casa (1.0 na fileira mais perto)."""
        return self._squares[square].scale

    def polygon(self, square: int) -> tuple[Point, ...]:
        """Polígono (4 cantos) da casa na imagem."""
        return self._squares[square].polygon

    def square_at(self, x: float, y: float) -> int | None:
        """Casa sob o ponto (px na imagem), ou None fora do campo."""
        for geom in self._squares.values():
            if _point_in_polygon(x, y, geom.polygon):
                return geom.square
        return None

    def draw_order(self) -> list[int]:
        """Casas ordenadas de trás para frente (y do centro crescente)."""
        return sorted(
            self._squares, key=lambda sq: self._squares[sq].center[1]
        )


def _point_in_polygon(x: float, y: float, poly: tuple[Point, ...]) -> bool:
    """Teste par-ímpar (ray casting) para ponto em polígono."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        crosses = (yi > y) != (yj > y)
        if crosses:
            x_int = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_int:
                inside = not inside
        j = i
    return inside
