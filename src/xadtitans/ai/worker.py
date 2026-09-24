"""AIWorker — busca de IA em thread separada.

A UI usa ``request()`` para iniciar uma busca e ``poll()`` /
``cancel()`` para obter/cancelar o resultado.  A thread de IA
trabalha somente com ``chess.Board`` — nenhum acesso a pygame.
"""

from __future__ import annotations

import threading
from queue import Queue

import chess

from xadtitans.ai.search import TranspositionTable, iterative_deepening
from xadtitans.core.types import Level

# Profundidade máxima por nível
_MAX_DEPTH: dict[Level, int] = {
    Level.INICIANTE: 2,
    Level.FACIL: 3,
    Level.MEDIO: 4,
    Level.DIFICIL: 6,
}

# Limite de tempo por lance (segundos)
_TIME_LIMIT: dict[Level, float] = {
    Level.INICIANTE: 0.5,
    Level.FACIL: 2.0,
    Level.MEDIO: 5.0,
    Level.DIFICIL: 15.0,
}

# Aleatoriedade controlada (0 = sem aleatoriedade)
_RANDOMNESS: dict[Level, float] = {
    Level.INICIANTE: 0.15,
    Level.FACIL: 0.05,
    Level.MEDIO: 0.0,
    Level.DIFICIL: 0.0,
}


class AIWorker:
    """Worker de IA que roda em thread separada."""

    def __init__(
        self,
        board: chess.Board,
        level: Level = Level.MEDIO,
        seed: int | None = None,
    ) -> None:
        self._board = board.copy()
        self._level = level
        self._max_depth = _MAX_DEPTH[level]
        self._time_limit = _TIME_LIMIT[level]
        self._randomness = _RANDOMNESS[level]
        self._stop_event = threading.Event()
        self._result_queue: Queue[chess.Move | None] = Queue()
        self._thread: threading.Thread | None = None
        self._tt = TranspositionTable()
        self._seed = seed
        self._rng = __import__("random").Random(seed) if seed is not None else None

    def request(self) -> None:
        """Inicia a busca em thread separada."""
        if self._thread is not None and self._thread.is_alive():
            return  # já em execução
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def poll(self) -> chess.Move | None:
        """Verifica se há resultado disponível (não-bloqueante)."""
        try:
            return self._result_queue.get_nowait()
        except Exception:  # noqa: BLE001
            return None

    def cancel(self) -> None:
        """Cancela a busca em andamento."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=0.5)

    def wait(self, timeout: float | None = None) -> chess.Move | None:
        """Bloca até obter o resultado (ou timeout)."""
        try:
            return self._result_queue.get(timeout=timeout)
        except Exception:  # noqa: BLE001
            return None

    @property
    def busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        """Executa a busca na thread de IA."""
        try:
            best_move, score, _depth, _nps = iterative_deepening(
                self._board,
                self._max_depth,
                self._tt,
                self._stop_event,
            )

            # Aleatoriedade controlada: pode escolher entre lances
            # de pontuação similar (para níveis baixos)
            if (
                self._randomness > 0
                and self._rng is not None
                and best_move is not None
                and not self._stop_event.is_set()
            ):
                best_move = self._apply_randomness(best_move, score)

            self._result_queue.put(best_move)

        except Exception:  # noqa: BLE001
            # Em caso de erro, retorna lance legal qualquer
            legal = list(self._board.legal_moves)
            self._result_queue.put(legal[0] if legal else None)

    def _apply_randomness(
        self, best_move: chess.Move, best_score: int
    ) -> chess.Move:
        """Para níveis baixos, pode escolher entre top lances.

        Roda uma avaliação rápida (depth 1) de todos os lances
        para encontrar candidatos similares ao melhor.
        """
        from xadtitans.ai.evaluation import evaluate

        candidates = [best_move]
        threshold = 30  # 0.3 peão de tolerância

        for move in self._board.legal_moves:
            if move == best_move:
                continue
            self._board.push(move)
            # evaluate retorna da perspectiva do adversário;
            # negamos para comparar com best_score (minha perspectiva).
            score = -evaluate(self._board)
            self._board.pop()
            if best_score - score <= threshold:
                candidates.append(move)

        if len(candidates) > 1 and self._rng is not None:
            return self._rng.choice(candidates)
        return best_move
