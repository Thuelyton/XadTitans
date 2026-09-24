"""Busca de IA: negamax com poda alfa-beta.

Componentes:
  - Negamax com poda alfa-beta
  - Quiescence search (capturas apenas)
  - Iterative deepening
  - Tabela de transposição (``_transposition_key`` do python-chess)
  - Move ordering: MVV-LVA, killer moves, history heuristic
  - Extensão de xeque (+1 ply)
  - Mate distance pruning

Unidade de pontuação: centipawns (100 = 1 peão).
MATE_SCORE = 20000.  ``mate_in(n)`` = 20000 - n.
"""

from __future__ import annotations

import threading

import chess

from xadtitans.ai.evaluation import evaluate

MATE_SCORE = 20000


def mate_in(ply: int) -> int:
    return MATE_SCORE - ply


def is_mate(score: int) -> bool:
    return abs(score) >= MATE_SCORE - 1000


# ════════════════════════════════════════════════════════════
# Tabela de transposição
# ════════════════════════════════════════════════════════════

EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2


class TranspositionTable:
    """Tabela de transposição baseada em ``_transposition_key``."""

    def __init__(self, max_size: int = 1 << 20) -> None:
        self._table: dict = {}
        self._max_size = max_size

    def store(
        self,
        board: chess.Board,
        depth: int,
        score: int,
        flag: int,
        best_move: chess.Move | None,
    ) -> None:
        if len(self._table) >= self._max_size:
            self._table.clear()
        self._table[board._transposition_key()] = (
            depth, score, flag, best_move,
        )

    def probe(
        self, board: chess.Board
    ) -> tuple[int, int, int, chess.Move | None] | None:
        return self._table.get(board._transposition_key())

    def clear(self) -> None:
        self._table.clear()

    def __len__(self) -> int:
        return len(self._table)


# ════════════════════════════════════════════════════════════
# Move ordering
# ════════════════════════════════════════════════════════════

MVV_LVA: dict[int, int] = {
    chess.PAWN: 10,
    chess.KNIGHT: 30,
    chess.BISHOP: 31,
    chess.ROOK: 50,
    chess.QUEEN: 90,
    chess.KING: 9000,
}


def _mvv_lva(board: chess.Board, move: chess.Move) -> int:
    victim = board.piece_type_at(move.to_square)
    attacker = board.piece_type_at(move.from_square)
    return MVV_LVA.get(victim, 0) * 100 - MVV_LVA.get(attacker, 0)


class _MoveOrderer:
    """Ordena lances: TT best → MVV-LVA → killer → history."""

    def __init__(
        self,
        board: chess.Board,
        tt_move: chess.Move | None,
        killer1: chess.Move | None,
        killer2: chess.Move | None,
        history: dict[tuple[int, int], int],
    ) -> None:
        self.board = board
        self.tt_move = tt_move
        self.killer1 = killer1
        self.killer2 = killer2
        self.history = history

    def key(self, move: chess.Move) -> int:
        if move == self.tt_move:
            return -1_000_000
        if self.board.is_capture(move):
            return -100_000 + _mvv_lva(self.board, move)
        if move == self.killer1:
            return -50_000
        if move == self.killer2:
            return -40_000
        return -self.history.get((move.from_square, move.to_square), 0)

    def sorted(self) -> list[chess.Move]:
        moves = list(self.board.legal_moves)
        moves.sort(key=self.key)
        return moves


# ════════════════════════════════════════════════════════════
# Quiescence search
# ════════════════════════════════════════════════════════════

def _quiescence(
    board: chess.Board,
    alpha: int,
    beta: int,
    ply: int,
    stop_event: threading.Event | None,
    tt: TranspositionTable,
) -> int:
    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta
    alpha = max(alpha, stand_pat)

    if stop_event is not None and stop_event.is_set():
        return alpha

    tt_entry = tt.probe(board)
    if tt_entry is not None:
        tt_depth, tt_score, tt_flag, _ = tt_entry
        if tt_depth >= 0:
            if tt_flag == EXACT:
                return tt_score
            if tt_flag == LOWERBOUND and tt_score > alpha:
                alpha = tt_score
            if tt_flag == UPPERBOUND and tt_score < beta:
                beta = tt_score
            if alpha >= beta:
                return tt_score

    captures = [
        m for m in board.legal_moves
        if board.is_capture(m) or m.promotion
    ]
    captures.sort(key=lambda m: _mvv_lva(board, m), reverse=True)

    for move in captures:
        if stop_event is not None and stop_event.is_set():
            return alpha
        board.push(move)
        score = -_quiescence(board, -beta, -alpha, ply + 1, stop_event, tt)
        board.pop()
        if score >= beta:
            return beta
        alpha = max(alpha, score)

    return alpha


# ════════════════════════════════════════════════════════════
# Negamax com alfa-beta
# ════════════════════════════════════════════════════════════

def _negamax(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    ply: int,
    killers: list[list[chess.Move | None]],
    history: dict[tuple[int, int], int],
    tt: TranspositionTable,
    nodes: list[int],
    stop_event: threading.Event | None,
) -> int:
    nodes[0] += 1

    if stop_event is not None and stop_event.is_set():
        return 0

    # Mate distance pruning
    alpha = max(alpha, -MATE_SCORE + ply)
    beta = min(beta, MATE_SCORE - ply - 1)
    if alpha >= beta:
        return alpha

    # TT probe
    tt_move = None
    tt_entry = tt.probe(board)
    if tt_entry is not None:
        tt_depth, tt_score, tt_flag, tt_best = tt_entry
        tt_move = tt_best
        if tt_depth >= depth:
            if tt_flag == EXACT:
                return tt_score
            if tt_flag == LOWERBOUND:
                alpha = max(alpha, tt_score)
            if tt_flag == UPPERBOUND:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score

    # Folha
    if depth <= 0:
        return _quiescence(board, alpha, beta, 0, stop_event, tt)

    in_check = board.is_check()
    legal = list(board.legal_moves)
    if not legal:
        return -MATE_SCORE + ply if in_check else 0
    if in_check:
        depth += 1  # extensão de xeque

    # Ensure killers list is large enough
    while len(killers) <= ply:
        killers.append([None, None])

    orderer = _MoveOrderer(board, tt_move, killers[ply][0], killers[ply][1], history)
    moves = orderer.sorted()

    best_score = -MATE_SCORE - 1
    best_move = moves[0]
    flag = UPPERBOUND

    for i, move in enumerate(moves):
        if stop_event is not None and stop_event.is_set():
            return best_score

        board.push(move)
        if i == 0:
            score = -_negamax(
                board, depth - 1, -beta, -alpha, ply + 1,
                killers, history, tt, nodes, stop_event,
            )
        else:
            score = -_negamax(
                board, depth - 1, -alpha - 1, -alpha, ply + 1,
                killers, history, tt, nodes, stop_event,
            )
            if alpha < score < beta:
                score = -_negamax(
                    board, depth - 1, -beta, -score, ply + 1,
                    killers, history, tt, nodes, stop_event,
                )
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        if score > alpha:
            alpha = score
            flag = EXACT

        if alpha >= beta:
            flag = LOWERBOUND
            if not board.is_capture(move):
                key = (move.from_square, move.to_square)
                history[key] = history.get(key, 0) + depth * depth
                if killers[ply][0] != move:
                    killers[ply][1] = killers[ply][0]
                    killers[ply][0] = move
            break

    tt.store(board, depth, best_score, flag, best_move)
    return best_score


# ════════════════════════════════════════════════════════════
# Iterative deepening
# ════════════════════════════════════════════════════════════

def iterative_deepening(
    board: chess.Board,
    max_depth: int,
    tt: TranspositionTable | None = None,
    stop_event: threading.Event | None = None,
) -> tuple[chess.Move | None, int, int, float]:
    """Busca iterativa por profundidade.

    Returns:
        (melhor_lance, pontuação, profundidade_alcançada, nós_por_segundo)
    """
    if tt is None:
        tt = TranspositionTable()
    tt.clear()  # limpa uma vez no início

    best_move: chess.Move | None = None
    best_score = -MATE_SCORE - 1
    nodes = [0]

    import time
    t0 = time.perf_counter()

    killers: list[list[chess.Move | None]] = []
    history: dict[tuple[int, int], int] = {}

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None, 0, 0, 0.0
    if len(legal_moves) == 1:
        elapsed = time.perf_counter() - t0
        nps = nodes[0] / max(elapsed, 1e-9)
        return legal_moves[0], 0, 1, nps

    for depth in range(1, max_depth + 1):
        if stop_event is not None and stop_event.is_set():
            break

        # TT NÃO é limpa entre iterações — reutiliza resultados
        score = _negamax(
            board, depth, -MATE_SCORE - 1, MATE_SCORE + 1, 0,
            killers, history, tt, nodes, stop_event,
        )

        if stop_event is not None and stop_event.is_set():
            break

        # Procurar o melhor lance na TT
        tt_entry = tt.probe(board)
        if tt_entry is not None and tt_entry[3] is not None:
            best_move = tt_entry[3]
            best_score = score

        elapsed = time.perf_counter() - t0
        nps = nodes[0] / max(elapsed, 1e-9)

    elapsed = time.perf_counter() - t0
    nps = nodes[0] / max(elapsed, 1e-9)

    # Se nenhum lance foi encontrado, usar o primeiro legal
    if best_move is None:
        best_move = legal_moves[0]

    return best_move, best_score, max_depth, nps
