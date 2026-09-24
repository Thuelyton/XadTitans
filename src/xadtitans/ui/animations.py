"""Animações: interpolação (tween) e funções de easing.

Módulo **puro** (sem pygame): calcula posição/escala/alfa ao longo do
tempo.  A cena aplica o resultado no desenho; o ``Animator`` também
serve de "trava": enquanto houver animação de deslize ativa, a entrada
do jogador é bloqueada.

Dois tipos de animação:
  - ``slide``: peça desliza de uma casa até outra (com escala
    interpolada — fileiras distantes são menores);
  - ``fade``: peça capturada esmaece e some no lugar.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

Point = tuple[float, float]
SpriteKey = tuple[int, bool]  # (piece_type, is_white)


# ── easing ─────────────────────────────────────────────

def clamp01(t: float) -> float:
    """Limita t ao intervalo [0, 1]."""
    return 0.0 if t < 0.0 else (min(t, 1.0))


def linear(t: float) -> float:
    """Velocidade constante."""
    return clamp01(t)


def ease_out_cubic(t: float) -> float:
    """Sai rápido, desacelera no fim (padrão para deslizes)."""
    t = clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_sine(t: float) -> float:
    """Entra e sai suavemente (padrão para fades)."""
    t = clamp01(t)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def ease_out_back(t: float) -> float:
    """Pequeno overshoot no fim (encaixe da peça)."""
    t = clamp01(t)
    c1, c3 = 1.70158, 2.70158
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


# ── animação individual ────────────────────────────────

SLIDE = "slide"
FADE = "fade"


@dataclass
class Anim:
    """Uma animação de peça.

    ``square`` é a casa associada: destino do deslize (a peça ainda
    não pousou lá) ou casa da peça que esmaece.
    """

    kind: str                     # SLIDE ou FADE
    sprite: SpriteKey
    square: int
    start: Point
    end: Point
    scale_start: float = 1.0
    scale_end: float = 1.0
    duration: float = 0.18
    easing: Callable[[float], float] = ease_out_cubic
    elapsed: float = field(default=0.0)

    @property
    def progress(self) -> float:
        """Progresso bruto 0..1 (pelo tempo)."""
        if self.duration <= 0.0:
            return 1.0
        return clamp01(self.elapsed / self.duration)

    @property
    def done(self) -> bool:
        return self.progress >= 1.0

    @property
    def pos(self) -> Point:
        """Posição interpolada (com easing)."""
        k = self.easing(self.progress)
        return (
            self.start[0] + (self.end[0] - self.start[0]) * k,
            self.start[1] + (self.end[1] - self.start[1]) * k,
        )

    @property
    def scale(self) -> float:
        """Escala interpolada (fileiras distantes = menores)."""
        k = self.easing(self.progress)
        return self.scale_start + (self.scale_end - self.scale_start) * k

    @property
    def alpha(self) -> float:
        """Alfa: 1.0 no deslize; esmaece no fade."""
        if self.kind == FADE:
            return 1.0 - ease_in_out_sine(self.progress)
        return 1.0


# ── gerenciador ────────────────────────────────────────

class Animator:
    """Conjunto de animações ativas + trava de entrada."""

    def __init__(self) -> None:
        self._anims: list[Anim] = []

    def add(self, anim: Anim) -> None:
        self._anims.append(anim)

    def update(self, dt: float) -> None:
        """Avança o tempo; remove animações concluídas."""
        for a in self._anims:
            a.elapsed += dt
        self._anims = [a for a in self._anims if not a.done]

    @property
    def active(self) -> bool:
        """True se há qualquer animação em curso."""
        return bool(self._anims)

    @property
    def blocking(self) -> bool:
        """True se há deslize em curso (bloqueia entrada do jogador)."""
        return any(a.kind == SLIDE for a in self._anims)

    def clear(self) -> None:
        self._anims.clear()

    def by_square(self) -> dict[int, list[Anim]]:
        """Animações ativas agrupadas pela casa associada."""
        out: dict[int, list[Anim]] = {}
        for a in self._anims:
            out.setdefault(a.square, []).append(a)
        return out
