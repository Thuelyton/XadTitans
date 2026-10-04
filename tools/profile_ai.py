"""Profiling da IA do XadTitans com cProfile.

Mede o custo real da busca (iterative_deepening) em posições
representativas e do módulo de avaliação isoladamente.

Uso:
    .venv/Scripts/python.exe tools/profile_ai.py
    .venv/Scripts/python.exe tools/profile_ai.py --save baseline.prof
    .venv/Scripts/python.exe tools/profile_ai.py --compare before.prof after.prof
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import chess

from xadtitans.ai.evaluation import clear_caches, evaluate
from xadtitans.ai.search import TranspositionTable, iterative_deepening

# Posições representativas (mesmas do tools/bench_ai.py + táticas)
POSITIONS: list[tuple[str, str]] = [
    ("Posição inicial", chess.STARTING_FEN),
    ("Siciliana",
     "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2"),
    ("Meio-jogo tático",
     "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"),
    ("Final de torres", "8/5pk1/5p1p/8/8/8/4R1PK/8 w - - 0 1"),
    ("Ataque ao rei",
     "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 7"),
]

# Profundidades padrão do benchmark (mantidas iguais para comparabilidade)
DEFAULT_DEPTHS: list[int] = [3]


def _profile_search(fen: str, depth: int) -> tuple[dict, float, int, int, float]:
    """Executa iterative_deepening sob cProfile.

    Retorna (stats_dict, elapsed, nps, depth_reached, score).
    """
    board = chess.Board(fen)
    tt = TranspositionTable()
    profiler = cProfile.Profile()
    t0 = time.perf_counter()
    profiler.enable()
    _move, score, depth_reached, nps = iterative_deepening(board, depth, tt)
    profiler.disable()
    elapsed = time.perf_counter() - t0
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(15)
    return stats.stats, elapsed, nps, depth_reached, score


def _profile_eval(iterations: int = 2000) -> tuple[dict, float]:
    """Executa evaluate() sob cProfile (custo bruto, sem cache)."""
    boards = [chess.Board(fen) for _, fen in POSITIONS]
    profiler = cProfile.Profile()
    t0 = time.perf_counter()
    profiler.enable()
    for _ in range(iterations):
        for board in boards:
            clear_caches()
            evaluate(board)
    profiler.disable()
    elapsed = time.perf_counter() - t0
    stats = pstats.Stats(profiler)
    return stats.stats, elapsed


def _top_functions(
    stats: dict, n: int = 10
) -> list[tuple[str, int, float, float, float]]:
    """Extrai as n maiores funções por tempo cumulativo.

    Retorna lista de (nome, chamadas, tottime, cumtime, pct_cum).
    """
    total_cum = sum(s[3] for s in stats.values()) or 1.0
    ranked = sorted(stats.items(), key=lambda kv: kv[1][3], reverse=True)[:n]
    out = []
    for (filename, lineno, funcname), (
        _cc, _nc, tottime, cumtime, _callers
    ) in ranked:
        out.append((f"{filename}:{lineno}:{funcname}", _nc, tottime, cumtime, 100.0 * cumtime / total_cum))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Profiling da IA")
    parser.add_argument(
        "--save", help="salva o profiling agregado em arquivo .prof"
    )
    parser.add_argument(
        "--depths", default="3",
        help="profundidades separadas por vírgula (padrão: 3)",
    )
    parser.add_argument(
        "--compare", nargs=2, metavar=("ANTES", "DEPOIS"),
        help="compara dois arquivos .prof salvos",
    )
    args = parser.parse_args()
    depths = [int(d) for d in args.depths.split(",")]

    if args.compare:
        stats_a = pstats.Stats(args.compare[0])
        stats_b = pstats.Stats(args.compare[1])
        print("=== Comparação (cumulative, top 15) ===")
        for label, st in (("ANTES", stats_a), ("DEPOIS", stats_b)):
            print(f"\n--- {label} ---")
            st.sort_stats("cumulative")
            st.print_stats(15)
        return 0

    combined: dict = {}

    # ── Busca por posição/profundidade ──────────────────────
    print(f"{'Posição':<20} {'D':>2} {'Tempo':>8} {'NPS':>8} {'Prof':>4} {'Score':>7}")
    print("-" * 60)
    for name, fen in POSITIONS:
        for depth in depths:
            stats, elapsed, nps, depth_reached, score = _profile_search(fen, depth)
            print(
                f"{name:<20} {depth:>2} {elapsed:>7.2f}s {nps:>8.0f} "
                f"{depth_reached:>4} {score:>7}"
            )
            for key, value in stats.items():
                if key in combined:
                    prev = combined[key]
                    combined[key] = (
                        prev[0] + value[0],
                        prev[1] + value[1],
                        prev[2] + value[2],
                        prev[3] + value[3],
                        value[4],
                    )
                else:
                    combined[key] = value
    print()

    # ── Avaliação isolada ───────────────────────────────────
    eval_stats, eval_elapsed = _profile_eval()
    print(
        f"Avaliação (cProfile, sem cache): {eval_elapsed:.2f}s para "
        f"{len(POSITIONS) * 2000} chamadas "
        f"({eval_elapsed / (len(POSITIONS) * 2000) * 1e6:.1f} us/chamada)"
    )
    for key, value in eval_stats.items():
        if key in combined:
            prev = combined[key]
            combined[key] = (
                prev[0] + value[0],
                prev[1] + value[1],
                prev[2] + value[2],
                prev[3] + value[3],
                value[4],
            )
        else:
            combined[key] = value
    print()

    # ── Tabela de gargalos ──────────────────────────────────
    print("=== Gargalos (busca + avaliação, por tempo cumulativo) ===")
    print(f"{'Função':<55} {'Chamadas':>10} {'TotTime':>9} {'CumTime':>9} {'%Cum':>6}")
    print("-" * 95)
    total_cum = sum(s[3] for s in combined.values()) or 1.0
    for fname, calls, tottime, cumtime, pct in _top_functions(combined, 12):
        print(
            f"{fname[:55]:<55} {calls:>10} {tottime:>9.3f} "
            f"{cumtime:>9.3f} {pct:>5.1f}%"
        )
    print()
    print(f"Tempo cumulativo total combinado: {total_cum:.2f}s")

    if args.save:
        profiler = cProfile.Profile()
        profiler.enable()
        for name, fen in POSITIONS:
            board = chess.Board(fen)
            iterative_deepening(board, depths[0], TranspositionTable())
        profiler.disable()
        profiler.dump_stats(args.save)
        print(f"\nProfiling salvo em {args.save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
