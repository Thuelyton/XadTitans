"""Avaliação de posição de xadrez — puro, sem pygame.

Unidade: centipawns (100 = 1 peão).  Pontuação de WHITE positiva.
Usa ``tapered eval``: interpolação entre tabela de meio-jogo e tabela
de final com base na quantidade de material remanescente.

Tabelas de posição SIMÉTRICAS (rank 1 no topo, index = rank*8+file).
Para peças pretas, o rank é espelhado (7 - rank) para garantir
avaliação justa.

Módulo **determinístico** e **sem efeitos colaterais**.
"""

from __future__ import annotations

import chess

# ════════════════════════════════════════════════════════════
# Valores materiais
# ════════════════════════════════════════════════════════════

PIECE_VALUE_MG: dict[int, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

PIECE_VALUE_EG: dict[int, int] = {
    chess.PAWN: 140,
    chess.KNIGHT: 300,
    chess.BISHOP: 320,
    chess.ROOK: 550,
    chess.QUEEN: 1000,
    chess.KING: 0,
}

PHASE_WEIGHT: dict[int, int] = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
    chess.KING: 0,
}

BISHOP_PAIR_BONUS_MG = 50
BISHOP_PAIR_BONUS_EG = 70
MOBILITY_WEIGHT_MG = 5
MOBILITY_WEIGHT_EG = 3
CONNECTED_ROOKS_BONUS = 25
ROOK_OPEN_FILE_BONUS = 30
ROOK_SEMI_OPEN_FILE_BONUS = 15
DOUBLED_PAWN_PENALTY = -15
ISOLATED_PAWN_PENALTY = -20
PASSED_PAWN_BONUS_MG = [0, 10, 15, 25, 40, 60, 80, 0]
PASSED_PAWN_BONUS_EG = [0, 15, 25, 40, 65, 95, 130, 0]
KING_SAFETY_PENALTY_MG = -50
KING_SAFETY_PENALTY_EG = -10

TOTAL_PHASE = 24


# ════════════════════════════════════════════════════════════
# Tabelas de posição (rank 1 no topo, index = rank*8+file)
# Simétricas: mesma tabela para ambas as cores (espelhamento
# para pretas feito no evaluate()).
# ════════════════════════════════════════════════════════════

# Peão: valoriza centro e avanço; penaliza peão em coluna inicial no fim
_PAWN_MG = (
     0,   0,   0,   0,   0,   0,   0,   0,   # rank 1
   -35,  -1, -20, -23, -15,  24,  38, -22,   # rank 2
   -26,  -4,  -4, -10,   3,   3,  33, -12,   # rank 3
   -27,  -2,  -5,  12,  17,   6,  10, -25,   # rank 4
   -14,  13,   6,  21,  23,  12,  17, -23,   # rank 5
    -6,   7,  26,  31,  65,  56,  25, -20,   # rank 6
    98, 134,  61,  95,  68, 126,  34, -11,   # rank 7
     0,   0,   0,   0,   0,   0,   0,   0,   # rank 8
)

_PAWN_EG = (
     0,   0,   0,   0,   0,   0,   0,   0,
    13,   8,   8,  26,  31,  33,  28,  40,
     4,   7,  -6,   1,   0,  -5,  -1,  -8,
    13,   9,  -3,  -7,  -7,  -8,   3,  -1,
    32,  24,  13,   5,  -2,   4,  17,  17,
    94, 100,  85,  67,  56,  53,  82,  84,
   178, 173, 158, 134, 147, 132, 165, 187,
     0,   0,   0,   0,   0,   0,   0,   0,
)

# Cavalo: valoriza centro; penaliza canto/borda
_KNIGHT_MG = (
  -105, -21, -58, -33, -17, -28, -19, -23,
   -29, -53, -12,  -3,  -1,  18, -14, -19,
   -23,  -9,  12,  10,  19,  17,  25, -16,
   -13,   4,  16,  13,  28,  19,  21,  -8,
    -9,  17,  19,  53,  37,  69,  18,  22,
   -47,  60,  37,  65,  84, 129,  73,  44,
   -73, -41,  72,  36,  23,  62,   7, -17,
  -167, -89, -34, -49,  61, -97, -15,-107,
)

_KNIGHT_EG = (
   -29, -51, -23, -15, -22, -18, -50, -64,
   -42, -20, -10,  -5,  -2, -20, -23, -44,
   -23,  -3,  -1,  15,  10,  -3, -20, -22,
   -18,  -6,  16,  25,  16,  17,   4, -18,
   -17,   3,  22,  22,  22,  11,   8, -18,
   -24, -20,  10,   9,  -1,  -9, -19, -41,
   -25,  -8, -25,  -2,  -9, -25, -24, -52,
   -58, -38, -13, -28, -31, -27, -63, -99,
)

# Bispo: valoriza diagonais longas; penaliza canto
_BISHOP_MG = (
   -33,  -3, -14, -21, -13, -12, -39, -21,
     4,  15,  16,   0,   7,  21,  33,   1,
     0,  15,  15,  15,  14,  27,  18,  10,
    -6,  13,  13,  26,  34,  12,  12,  -4,
    -4,   5,  19,  50,  37,  37,   7,  -2,
   -16,  37,  43,  40,  35,  50,  37,  -2,
   -26,  16, -18, -13,  30,  59,  18, -47,
   -29,   4, -82, -37, -25, -42,   7,  -8,
)

_BISHOP_EG = (
   -14, -18,  -7,  -1,  -4,  -9, -15, -27,
   -12,  -3,  -8,  -3,  -4,  -9,  -5, -11,
    -7,   2,  -1,  -5,  -4,  -1,  -5,  -7,
    -6,  -3,  13,  10,   7,  10,  -6,  -7,
    -3,   9,  12,   9,  14,  10,   3,   2,
     2,  -8,   0,  -1,  -2,   6,   0,   4,
    -8,  -4,   7, -12,  -3, -13,  -4, -14,
   -14, -21, -11,  -8,  -7,  -9, -17, -24,
)

# Torre: valoriza fileiras abertas e 7ª fileira
_ROOK_MG = (
   -19, -13,   1,  17,  16,   7, -37, -26,
   -44, -16, -20,  -9,  -1,  11,  -6, -71,
   -45, -25, -16, -17,   3,   0,  -5, -33,
   -36, -26, -12,  -1,   9,  -7,   6, -23,
   -24, -11,   7,  26,  24,  35,  -8, -20,
    -5,  19,  26,  36,  17,  45,  61,  16,
    27,  32,  58,  62,  80,  67,  26,  44,
    32,  42,  32,  51,  63,   9,  31,  43,
)

_ROOK_EG = (
    -9,   2,   3,  -1,  -5, -13,   4, -20,
    -6,  -6,   0,   2,  -9,  -9, -11,  -3,
    -4,   0,  -5,  -1,  -7, -12,  -8, -16,
     3,   5,   8,   4,  -5,  -6,  -8, -11,
     4,   3,  13,   1,   2,   1,  -1,   2,
     7,   7,   7,   5,   4,  -3,  -5,  -3,
    11,  13,  13,  11,  -3,   3,   8,   3,
    13,  10,  18,  15,  12,  12,   8,   5,
)

# Dama
_QUEEN_MG = (
    -1, -18,  -9,  10, -15, -25, -31, -50,
   -35,  -8,  11,   2,   8,  15,  -3,   1,
   -14,   2, -11,  -2,  -5,   2,  14,   5,
    -9, -26,  -9, -10,  -2,  -4,   3,  -3,
   -27, -27, -16, -16,  -1,  17,  -2,   1,
   -13, -17,   7,   8,  29,  56,  47,  57,
   -24, -39,  -5,   1, -16,  57,  28,  54,
   -28,   0,  29,  12,  59,  44,  43,  45,
)

_QUEEN_EG = (
   -22, -33, -30, -16, -16, -23, -36, -32,
   -25, -16, -17,  -2,  -1, -15, -43, -20,
   -14, -15,  -2,  -5,  -1, -10, -20, -22,
   -30,  -6, -13, -11, -16, -11, -16, -27,
   -18,  28,  19,  25,  26,  33,  26,  37,
    -3,  22,  24,  45,  57,  40,  57,  36,
   -17,  28,  19,  47,  31,  34,  39,  23,
    -9,  22,  22,  27,  27,  19,  10,  20,
)

# Rei: segurança no meio-jogo; centralização no final
_KING_MG = (
   -15,  36,  12, -54,   8, -28,  24,  14,
     1,   7,  -8, -64, -43, -16,   9,   8,
   -14, -14, -22, -46, -44, -30, -15, -27,
   -49,  -1, -27, -39, -46, -44, -33, -51,
   -17, -20, -12, -27, -30, -25, -14, -36,
    -9,  24,   2, -16, -20,   6,  22, -22,
    29,  -1, -20,  -7,  -8,  -4, -38, -29,
   -65,  23,  16, -15, -56, -34,   2,  13,
)

_KING_EG = (
   -53, -34, -21, -11, -28, -14, -24, -43,
   -27, -11,   4,  13,  14,   4,  -5, -17,
   -19,  -3,  11,  21,  23,  16,   7,  -9,
   -18,  -4,  21,  24,  27,  23,   9, -11,
    -8,  22,  24,  27,  26,  33,  26,   3,
    10,  17,  23,  15,  20,  45,  44,  13,
   -12,  17,  14,  17,  17,  38,  23,  11,
   -74, -35, -18, -18, -11,  15,   4, -17,
)

MG_TABLES: dict[int, tuple[int, ...]] = {
    chess.PAWN: _PAWN_MG, chess.KNIGHT: _KNIGHT_MG, chess.BISHOP: _BISHOP_MG,
    chess.ROOK: _ROOK_MG, chess.QUEEN: _QUEEN_MG, chess.KING: _KING_MG,
}

EG_TABLES: dict[int, tuple[int, ...]] = {
    chess.PAWN: _PAWN_EG, chess.KNIGHT: _KNIGHT_EG, chess.BISHOP: _BISHOP_EG,
    chess.ROOK: _ROOK_EG, chess.QUEEN: _QUEEN_EG, chess.KING: _KING_EG,
}

# ════════════════════════════════════════════════════════════
# Avaliação
# ════════════════════════════════════════════════════════════

def _game_phase(board: chess.Board) -> int:
    """Fase da partida: 0 (final) a TOTAL_PHASE (abertura)."""
    phase = 0
    for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        phase += len(board.pieces(pt, chess.WHITE)) * PHASE_WEIGHT[pt]
        phase += len(board.pieces(pt, chess.BLACK)) * PHASE_WEIGHT[pt]
    return min(phase, TOTAL_PHASE)


def _pst_index(square: int, color: bool) -> int:
    """Índice na tabela PST: brancas usam o square direto,
    pretas espelham o rank (7 - rank)."""
    if color:
        return square
    rank = chess.square_rank(square)
    file = chess.square_file(square)
    return (7 - rank) * 8 + file


def evaluate(board: chess.Board) -> int:
    """Avalia a posição em centipawns (brancas positivo).

    ``tapered eval``: interpola meio-jogo e final pela fase.
    Retorna da perspectiva de quem joga (``board.turn``).
    """
    if board.is_checkmate():
        return -20000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    if board.can_claim_fifty_moves() or board.can_claim_threefold_repetition():
        return 0

    mg_score = 0
    eg_score = 0
    phase = _game_phase(board)

    # Material + tabelas de posição
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
        pt = piece.piece_type
        if pt == chess.KING and phase > 8:
            continue
        sign = 1 if piece.color else -1
        idx = _pst_index(square, piece.color)
        mg_score += sign * (PIECE_VALUE_MG[pt] + MG_TABLES[pt][idx])
        eg_score += sign * (PIECE_VALUE_EG[pt] + EG_TABLES[pt][idx])

    # Par de bispos
    wb = len(board.pieces(chess.BISHOP, chess.WHITE))
    bb = len(board.pieces(chess.BISHOP, chess.BLACK))
    if wb >= 2:
        mg_score += BISHOP_PAIR_BONUS_MG
        eg_score += BISHOP_PAIR_BONUS_EG
    if bb >= 2:
        mg_score -= BISHOP_PAIR_BONUS_MG
        eg_score -= BISHOP_PAIR_BONUS_EG

    # Mobilidade
    own = board.turn
    board.turn = chess.WHITE
    mobility_w = board.legal_moves.count()
    board.turn = chess.BLACK
    mobility_b = board.legal_moves.count()
    board.turn = own
    mg_score += (mobility_w - mobility_b) * MOBILITY_WEIGHT_MG
    eg_score += (mobility_w - mobility_b) * MOBILITY_WEIGHT_EG

    # Estrutura de peões
    mg_score += _pawn_structure(board)
    eg_score += _pawn_structure(board)

    # Segurança do rei
    mg_score += _king_safety(board)

    # Torres em fileiras abertas/meiabertas
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color else -1
        rooks = board.pieces(chess.ROOK, color)
        pawns = board.pieces(chess.PAWN, color)
        opp_pawns = board.pieces(chess.PAWN, not color)
        file_mask = chess.BB_FILES
        for sq in rooks:
            f = chess.square_file(sq)
            own_p = bool(int(pawns) & file_mask[f])
            opp_p = bool(int(opp_pawns) & file_mask[f])
            if not own_p and not opp_p:
                mg_score += sign * ROOK_OPEN_FILE_BONUS
                eg_score += sign * ROOK_OPEN_FILE_BONUS
            elif not own_p:
                mg_score += sign * ROOK_SEMI_OPEN_FILE_BONUS
                eg_score += sign * ROOK_SEMI_OPEN_FILE_BONUS

    # Torres conectadas
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color else -1
        rooks = board.pieces(chess.ROOK, color)
        rook_list = list(rooks)
        if len(rook_list) == 2:
            f1 = chess.square_file(rook_list[0])
            f2 = chess.square_file(rook_list[1])
            r1 = chess.square_rank(rook_list[0])
            r2 = chess.square_rank(rook_list[1])
            if r1 == r2 and abs(f1 - f2) <= 2:
                mg_score += sign * CONNECTED_ROOKS_BONUS

    # Interpolação
    mg_weight = phase
    eg_weight = TOTAL_PHASE - phase
    score = (mg_score * mg_weight + eg_score * eg_weight) // TOTAL_PHASE

    # Perspectiva: retorna da cor que joga
    return score if board.turn else -score


def _pawn_structure(board: chess.Board) -> int:
    """Peças dobradas, isoladas e passadas."""
    score = 0
    file_mask = chess.BB_FILES
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color else -1
        pawns = board.pieces(chess.PAWN, color)
        own_files = set()
        for sq in pawns:
            f = chess.square_file(sq)
            rank = chess.square_rank(sq)
            is_own = f in own_files
            own_files.add(f)
            if is_own:
                score += sign * DOUBLED_PAWN_PENALTY
            has_neighbor = bool(
                (file_mask[max(0, f - 1)] | file_mask[min(7, f + 1)])
                & int(pawns)
            )
            if not has_neighbor:
                score += sign * ISOLATED_PAWN_PENALTY
            is_pass = True
            for df in (-1, 0, 1):
                nf = f + df
                if 0 <= nf <= 7:
                    for r in (
                        range(rank + 1, 8) if color else range(rank)
                    ):
                        if board.piece_at(chess.square(nf, r)) == chess.Piece(
                            chess.PAWN, not color
                        ):
                            is_pass = False
                            break
                if not is_pass:
                    break
            if is_pass:
                mg_b = PASSED_PAWN_BONUS_MG[rank]
                eg_b = PASSED_PAWN_BONUS_EG[rank]
                score += sign * ((mg_b + eg_b) // 2)

    return score


def _king_safety(board: chess.Board) -> int:
    """Segurança do rei baseada no escudo de peões."""
    score = 0
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color else -1
        king_sq = board.king(color)
        if king_sq is None:
            continue
        file = chess.square_file(king_sq)
        rank = chess.square_rank(king_sq)
        shelter = 0
        for df in (-1, 0, 1):
            f = file + df
            if 0 <= f <= 7:
                front = range(rank + 1, 8) if color else range(rank)
                found = False
                for r in front:
                    if board.piece_at(chess.square(f, r)) == chess.Piece(
                        chess.PAWN, color
                    ):
                        shelter += 1
                        found = True
                        break
                if not found:
                    shelter -= 1
        phase = _game_phase(board)
        if phase > 12:
            score += sign * (KING_SAFETY_PENALTY_MG if shelter < 2 else 0)
        else:
            score += sign * (KING_SAFETY_PENALTY_EG if shelter < 1 else 0)
    return score
