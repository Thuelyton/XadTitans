"""Núcleo de regras do XadTitans.

``Game`` encapsula um ``chess.Board`` (python-chess) como **fonte única
de verdade das regras**: legalidade, roque, en passant, promoção, xeque,
mate, afogamento, material insuficiente, 50 lances, repetição, desfazer,
histórico em SAN e peças capturadas.

Este módulo **não importa pygame** — pode ser usado em testes e,
futuramente, pela IA.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import chess

from xadtitans.core.types import GameResult, Status

if TYPE_CHECKING:
    from collections.abc import Sequence

# Mapeamento chess.Termination → Status (termina em empate salvo mate).
_TERMINATION_TO_STATUS: dict[chess.Termination, Status] = {
    chess.Termination.CHECKMATE: Status.XEQUE_MATE,
    chess.Termination.STALEMATE: Status.AFOGAMENTO,
    chess.Termination.INSUFFICIENT_MATERIAL: Status.MATERIAL_INSUFICIENTE,
    chess.Termination.FIFTY_MOVES: Status.CINQUENTA_LANCES,
    chess.Termination.SEVENTYFIVE_MOVES: Status.CINQUENTA_LANCES,
    chess.Termination.THREEFOLD_REPETITION: Status.TRIPLA_REPETICAO,
    chess.Termination.FIVEFOLD_REPETITION: Status.TRIPLA_REPETICAO,
    chess.Termination.VARIANT_DRAW: Status.EMPATE_ACORDO,
}


class Game:
    """Partida de xadrez para 2 jogadores, com regras via python-chess."""

    def __init__(self, fen: str | None = None) -> None:
        self.board = chess.Board(fen) if fen is not None else chess.Board()
        self._san_history: list[str] = []
        # Peças capturadas por cada cor (na ordem das capturas).
        self._captured_by_white: list[chess.PieceType] = []
        self._captured_by_black: list[chess.PieceType] = []
        # Cor que desistiu (None = ninguém desistiu).
        self._resigned: chess.Color | None = None

    # ── estado básico ────────────────────────────────────

    def reset(self) -> None:
        """Volta à posição inicial e limpa todo o histórico."""
        self.board = chess.Board()
        self._san_history.clear()
        self._captured_by_white.clear()
        self._captured_by_black.clear()
        self._resigned = None

    @property
    def turn(self) -> chess.Color:
        """Cor que joga agora."""
        return self.board.turn

    # ── legalidade e execução ────────────────────────────

    def legal_moves_from(self, square: int) -> list[chess.Move]:
        """Lances legais cuja casa de origem é ``square``."""
        return [m for m in self.board.legal_moves if m.from_square == square]

    def is_legal(self, move: chess.Move) -> bool:
        """True se ``move`` é um lance legal na posição atual."""
        return move in self.board.legal_moves

    def needs_promotion(self, from_square: int, to_square: int) -> bool:
        """True se o peão em ``from_square`` chegaria à última fileira."""
        piece = self.board.piece_at(from_square)
        if piece is None or piece.piece_type != chess.PAWN:
            return False
        rank = chess.square_rank(to_square)
        return rank in (0, 7)

    def push(self, move: chess.Move) -> str:
        """Executa um lance legal e retorna a notação SAN dele.

        Raises:
            ValueError: se o lance não for legal.
        """
        if not self.is_legal(move):
            raise ValueError(f"Lance ilegal: {move.uci()}")
        san = self.board.san(move)  # SAN inclui '+'/'#' quando aplicável
        if self.board.is_capture(move):
            piece_type = self.board.piece_type_at(move.to_square)
            if piece_type is None and self.board.is_en_passant(move):
                piece_type = chess.PAWN
            if piece_type is not None:
                captures = (
                    self._captured_by_white
                    if self.board.turn  # brancas capturam
                    else self._captured_by_black
                )
                captures.append(piece_type)
        self.board.push(move)
        self._san_history.append(san)
        return san

    def undo(self) -> chess.Move | None:
        """Desfaz o último lance (ou None se não houver histórico).

        Também reverte SAN, peças capturadas e desistência.
        """
        self._resigned = None
        if not self.board.move_stack:
            return None
        move = self.board.peek()
        if self.board.is_capture(move):
            piece_type = self.board.piece_type_at(move.to_square)
            if piece_type is None and self.board.is_en_passant(move):
                piece_type = chess.PAWN
            captures = (
                self._captured_by_white
                if not self.board.turn  # quem moveu foi quem capturou
                else self._captured_by_black
            )
            if captures and captures[-1] == piece_type:
                captures.pop()
        self.board.pop()
        if self._san_history:
            self._san_history.pop()
        return move

    # ── xeque ────────────────────────────────────────────

    def in_check(self) -> bool:
        """True se o lado que joga agora está em xeque."""
        return self.board.is_check()

    def check_square(self) -> int | None:
        """Casa do rei em xeque (lado que joga), ou None."""
        if not self.board.is_check():
            return None
        return self.board.king(self.board.turn)

    # ── fim de partida ───────────────────────────────────

    def is_game_over(self) -> bool:
        """True se a partida terminou (inclui desistência e empates
        reivindicáveis — 50 lances e tripla repetição)."""
        if self._resigned is not None:
            return True
        # claim_draw=True: encerra em 50 lances / tripla repetição
        # reivindicáveis, sem exigir botão de "empate".
        return self.board.is_game_over(claim_draw=True)

    def status(self) -> Status:
        """Status atual da partida."""
        result = self.result()
        return result.status if result is not None else Status.EM_ANDAMENTO

    def result(self) -> GameResult | None:
        """Resultado final, ou None se a partida está em andamento."""
        if self._resigned is not None:
            return GameResult(
                status=Status.DESISTENCIA,
                winner=not self._resigned,  # quem não desistiu vence
            )
        outcome = self.board.outcome(claim_draw=True)
        if outcome is None:
            return None
        status = _TERMINATION_TO_STATUS.get(outcome.termination)
        if status is None:  # terminações de variantes — não ocorrem aqui
            status = Status.EMPATE_ACORDO if outcome.winner is None else (
                Status.XEQUE_MATE
            )
        return GameResult(status=status, winner=outcome.winner)

    def resign(self, color: chess.Color) -> None:
        """A cor ``color`` desiste; a adversária vence."""
        self._resigned = color

    # ── empates reivindicáveis (expostos pelo python-chess) ──

    def can_claim_fifty_moves(self) -> bool:
        """True se é possível reivindicar empate pela regra dos 50 lances."""
        return self.board.can_claim_fifty_moves()

    def can_claim_threefold_repetition(self) -> bool:
        """True se é possível reivindicar empate por tripla repetição."""
        return self.board.can_claim_threefold_repetition()

    # ── histórico ────────────────────────────────────────

    @property
    def san_history(self) -> Sequence[str]:
        """Lances já jogados, em notação algébrica (SAN)."""
        return list(self._san_history)

    def captured_by(self, color: chess.Color) -> list[chess.PieceType]:
        """Peças capturadas por ``color`` (lista de tipos, na ordem)."""
        captures = (
            self._captured_by_white if color else self._captured_by_black
        )
        return list(captures)
