"""Relógio de xadrez do XadTitans.

Gerencia o tempo restante de cada jogador e o incremento.
"""

from __future__ import annotations

import chess


class ChessClock:
    """Relógio de xadrez com suporte a minutos, incremento e turnos."""

    def __init__(self, minutes: int = 0, increment: int = 0) -> None:
        """Inicializa o relógio.

        Args:
            minutes: Minutos iniciais por jogador. Se 0, relógio inativo.
            increment: Segundos adicionados a cada lance.
        """
        self.initial_seconds = minutes * 60.0
        self.increment = float(increment)

        self.white_time = self.initial_seconds
        self.black_time = self.initial_seconds

        self.is_active = minutes > 0
        self.is_paused = False

    def reset(self) -> None:
        """Restaura o relógio para os valores iniciais."""
        self.white_time = self.initial_seconds
        self.black_time = self.initial_seconds
        self.is_paused = False

    def tick(self, dt: float, turn: chess.Color) -> None:
        """Diminui o tempo do jogador atual (turn)."""
        if not self.is_active or self.is_paused:
            return

        if turn == chess.WHITE:
            self.white_time = max(0.0, self.white_time - dt)
        else:
            self.black_time = max(0.0, self.black_time - dt)

    def apply_increment(self, turn: chess.Color) -> None:
        """Aplica o incremento ao jogador atual, que acabou de fazer um lance."""
        if not self.is_active:
            return

        if turn == chess.WHITE:
            self.white_time += self.increment
        else:
            self.black_time += self.increment

    def get_time(self, color: chess.Color) -> float:
        """Retorna o tempo restante de uma cor."""
        return self.white_time if color == chess.WHITE else self.black_time

    def set_time(self, color: chess.Color, time_left: float) -> None:
        """Define o tempo restante de uma cor. Útil para Undo e persistência."""
        if color == chess.WHITE:
            self.white_time = time_left
        else:
            self.black_time = time_left

    def is_timeout(self, color: chess.Color) -> bool:
        """Verifica se o tempo de uma cor esgotou."""
        if not self.is_active:
            return False
        return self.get_time(color) <= 0.0

    def pause(self) -> None:
        """Pausa o relógio."""
        self.is_paused = True

    def resume(self) -> None:
        """Retoma o relógio."""
        self.is_paused = False
