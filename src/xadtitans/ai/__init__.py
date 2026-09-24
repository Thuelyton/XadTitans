"""IA do XadTitans — módulo puramente algorítmico (sem pygame)."""

from xadtitans.ai.evaluation import evaluate
from xadtitans.ai.search import (
    MATE_SCORE,
    TranspositionTable,
    iterative_deepening,
    mate_in,
)
from xadtitans.ai.worker import AIWorker

__all__ = [
    "MATE_SCORE",
    "AIWorker",
    "TranspositionTable",
    "evaluate",
    "iterative_deepening",
    "mate_in",
]
