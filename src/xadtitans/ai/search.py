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
import time

import chess

from xadtitans.ai.evaluation import evaluate

MATE_SCORE = 20000

# Relógio de monotonic usado para os LIMITES DE TEMPO da busca
# (``time.monotonic``, como pedido: adequado para deadlines de
# 0,5–15s; substituível em testes determinísticos via monkeypatch em
# ``xadtitans.ai.search._clock``).  A medição de NPS/tempo usa
# ``time.perf_counter`` (resolução ~1µs; no Windows ``monotonic``
# tem granularidade de ~15ms via GetTickCount64).
_clock = time.monotonic

# A checagem de tempo é feita a cada nó (negamax e quiescence): o
# custo de ``_clock()`` é desprezível frente ao custo de um nó, e
# isso limita o overshoot a aproximadamente o custo de um único nó.


class _TimeLimitReached(Exception):
    """Sinaliza que o limite de tempo da busca foi atingido.

    A exceção desfaz o caminho atual SEM armazenar resultados
    parciais na TT (os ``tt.store`` acontecem após o laço, então o
    unwind por exceção os pula).  Os subárvores que concluíram antes
    do disparo armazenaram resultados válidos.
    """


def mate_in(ply: int) -> int:
    """Pontuação que indica xeque-mate em ``ply`` lances (20000 - ply)."""
    return MATE_SCORE - ply


def is_mate(score: int) -> bool:
    """True se a pontuação indica mate (|score| >= MATE_SCORE - 1000)."""
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
        """Cria a tabela com capacidade máxima de ``max_size`` entradas."""
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
        """Armazena uma entrada para a posição; limpa a tabela se cheia."""
        if len(self._table) >= self._max_size:
            self._table.clear()
        self._table[board._transposition_key()] = (
            depth, score, flag, best_move,
        )

    def probe(
        self, board: chess.Board
    ) -> tuple[int, int, int, chess.Move | None] | None:
        """Retorna (profundidade, pontuação, bandeira, melhor_lance) ou None."""
        return self._table.get(board._transposition_key())

    def clear(self) -> None:
        """Remove todas as entradas da tabela."""
        self._table.clear()

    def __len__(self) -> int:
        """Número de entradas armazenadas."""
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
    deadline: float | None = None,
) -> int:
    if deadline is not None and _clock() >= deadline:
        raise _TimeLimitReached

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
        score = -_quiescence(
            board, -beta, -alpha, ply + 1, stop_event, tt, deadline
        )
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
    deadline: float | None = None,
) -> int:
    nodes[0] += 1

    if stop_event is not None and stop_event.is_set():
        return 0

    if deadline is not None and _clock() >= deadline:
        raise _TimeLimitReached

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
        return _quiescence(board, alpha, beta, 0, stop_event, tt, deadline)

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
                killers, history, tt, nodes, stop_event, deadline,
            )
        else:
            score = -_negamax(
                board, depth - 1, -alpha - 1, -alpha, ply + 1,
                killers, history, tt, nodes, stop_event, deadline,
            )
            if alpha < score < beta:
                score = -_negamax(
                    board, depth - 1, -beta, -score, ply + 1,
                    killers, history, tt, nodes, stop_event, deadline,
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
    time_limit: float | None = None,
) -> tuple[chess.Move | None, int, int, float]:
    """Busca iterativa por profundidade.

    Args:
        board: posição atual a analisar.
        max_depth: profundidade máxima de busca.
        tt: tabela de transposição a reutilizar (criada se None).
        stop_event: sinaliza interrupção prematura da busca.
        time_limit: limite de tempo em segundos (``None`` = sem limite).
            O relógio é checado entre iterações e a cada nó da busca;
            quando o tempo é atingido, a iteração em curso é abortada
            (sem armazenar resultados parciais) e retorna-se o melhor
            resultado COMPLETO da última iteração concluída dentro do
            limite.  Se nenhuma iteração completa couber no limite,
            retorna o primeiro lance legal (fallback documentado) com
            profundidade 0.

    Returns:
        (melhor_lance, pontuação, profundidade_completa, nós_por_segundo)
        — ``profundidade_completa`` é o número de iterações REALMENTE
        concluídas (nunca afirma ``max_depth`` se a busca foi
        interrompida antes).
    """
    if tt is None:
        tt = TranspositionTable()
    tt.clear()  # limpa uma vez no início

    best_move: chess.Move | None = None
    best_score = 0
    reached_depth = 0
    nodes = [0]

    t0 = _clock()  # base do deadline (monotonic)
    deadline = t0 + time_limit if time_limit is not None else None
    t0_measure = time.perf_counter()  # medição de NPS (alta resolução)

    killers: list[list[chess.Move | None]] = []
    history: dict[tuple[int, int], int] = {}

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None, 0, 0, 0.0
    if len(legal_moves) == 1:
        elapsed = time.perf_counter() - t0_measure
        nps = nodes[0] / max(elapsed, 1e-9)
        return legal_moves[0], 0, 1, nps

    # Comprimento da pilha original para restaurar em caso de aborto
    # (a exceção de tempo desfaz o unwind sem ``board.pop()``).
    original_stack_len = len(board.move_stack)

    for depth in range(1, max_depth + 1):
        if stop_event is not None and stop_event.is_set():
            break
        if deadline is not None and _clock() >= deadline:
            break

        try:
            # TT NÃO é limpa entre iterações — reutiliza resultados
            score = _negamax(
                board, depth, -MATE_SCORE - 1, MATE_SCORE + 1, 0,
                killers, history, tt, nodes, stop_event, deadline,
            )
        except _TimeLimitReached:
            # Iteração interrompida no meio: descarta o resultado
            # parcial e mantém o último COMPLETO.  A TT não recebeu
            # entradas do caminho interrompido (store após o laço).
            break

        if stop_event is not None and stop_event.is_set():
            break

        # Iteração COMPLETA: registra o melhor lance e a profundidade
        # realmente alcançada.
        tt_entry = tt.probe(board)
        if tt_entry is not None and tt_entry[3] is not None:
            best_move = tt_entry[3]
            best_score = score
        reached_depth = depth

        if deadline is not None and _clock() >= deadline:
            break

    # Restaura o board caso uma exceção de tempo tenha abortado com
    # pushes pendentes no caminho de unwind.
    while len(board.move_stack) > original_stack_len:
        board.pop()

    elapsed = time.perf_counter() - t0_measure
    nps = nodes[0] / max(elapsed, 1e-9)

    # Nenhuma iteração completa: fallback legal documentado — o
    # primeiro lance legal da posição (sempre um lance legal).
    if best_move is None:
        best_move = legal_moves[0]

    return best_move, best_score, reached_depth, nps
