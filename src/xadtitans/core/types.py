"""Tipos centrais do XadTitans.

Define os enums e dataclasses usados por ``core/game.py`` e pelo resto
do projeto.  **Não importa pygame** — é puro Python (``chess`` só
aparece em anotações de tipo).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chess


class Level(Enum):
    """Níveis de dificuldade da IA (usado a partir da Fase 4)."""

    INICIANTE = auto()
    FACIL = auto()
    MEDIO = auto()
    DIFICIL = auto()


class Status(Enum):
    """Possíveis estados de uma partida."""

    EM_ANDAMENTO = "em andamento"
    XEQUE_MATE = "xeque-mate"
    AFOGAMENTO = "afogamento"
    MATERIAL_INSUFICIENTE = "material insuficiente"
    CINQUENTA_LANCES = "regra dos 50 lances"
    TRIPLA_REPETICAO = "tripla repetição"
    EMPATE_ACORDO = "empate por acordo"
    DESISTENCIA = "desistência"
    TEMPO_ESGOTADO = "tempo esgotado"


@dataclass(frozen=True)
class GameResult:
    """Resultado final (ou parcial) de uma partida.

    ``winner`` é ``chess.WHITE``/``chess.BLACK`` ou ``None`` em empates.
    """

    status: Status
    winner: chess.Color | None  # None = empate

    @property
    def is_draw(self) -> bool:
        """True quando a partida terminou empatada."""
        return self.winner is None
