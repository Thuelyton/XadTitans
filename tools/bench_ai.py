"""Benchmark headless da IA do XadTitans.

Mede: nós/segundo, tempo por busca, profundidade alcançada e
tamanho da TT em posições representativas.

Uso:
    .venv/Scripts/python.exe tools/bench_ai.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import chess

from xadtitans.ai.evaluation import evaluate
from xadtitans.ai.search import TranspositionTable, iterative_deepening

POSITIONS: list[tuple[str, str]] = [
    ("Posição inicial", chess.STARTING_FEN),
    ("Siciliana", "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2"),
    ("Meio-jogo tático", "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"),
    ("Final de torres", "8/5pk1/5p1p/8/8/8/4R1PK/8 w - - 0 1"),
    ("Ataque ao rei", "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 7"),
]


def main() -> int:
    depths = [3, 4, 5]
    print(f"{'Posição':<30} {'Depth':>5} {'Tempo':>7} {'Nós':>10} {'NPS':>8} {'Score':>7} {'TT':>6}")
    print("-" * 80)

    for name, fen in POSITIONS:
        board = chess.Board(fen)
        for depth in depths:
            tt = TranspositionTable()
            t0 = time.perf_counter()
            _move, score, _, nps = iterative_deepening(board, depth, tt)
            elapsed = time.perf_counter() - t0
            print(
                f"{name:<30} {depth:>5} {elapsed:>6.2f}s {int(nps*elapsed):>10} "
                f"{nps:>8.0f} {score:>7} {len(tt):>6}"
            )
        print()

    # Avaliação
    board = chess.Board()
    t0 = time.perf_counter()
    for _ in range(10000):
        evaluate(board)
    eval_time = (time.perf_counter() - t0) / 10000 * 1e6
    print(f"Avaliação: {eval_time:.1f} us/chamada ({1e6/eval_time:.0f} evals/s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
