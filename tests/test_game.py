"""Testes das regras de xadrez (Fase 2) — core/game.py com python-chess.

Cobre: posição inicial, mate do louco, mate do pastor, afogamento,
material insuficiente, roque ilegal, en passant, promoção, desfazer,
lances ilegais, xeque, xeque-mate, histórico/SAN, peças capturadas,
desistência e empates (50 lances, tripla repetição).

Nenhum teste importa pygame: o core é puro.
"""

import chess
import pytest

from xadtitans.core.game import Game
from xadtitans.core.types import GameResult, Level, Status


def _uci(game: Game, uci: str) -> str:
    """Empurra um lance em UCI e retorna o SAN."""
    return game.push(chess.Move.from_uci(uci))


# ════════════════════════════════════════════════════════════
# Posição inicial
# ════════════════════════════════════════════════════════════

class TestPosicaoInicial:
    def test_fen_inicial(self) -> None:
        game = Game()
        assert game.board.fen() == chess.STARTING_FEN
        assert game.turn is chess.WHITE

    def test_vinte_lances_legais(self) -> None:
        game = Game()
        assert len(list(game.board.legal_moves)) == 20

    def test_status_em_andamento(self) -> None:
        game = Game()
        assert game.status() is Status.EM_ANDAMENTO
        assert game.result() is None
        assert not game.is_game_over()
        assert not game.in_check()
        assert game.check_square() is None

    def test_historicos_vazios(self) -> None:
        game = Game()
        assert list(game.san_history) == []
        assert game.captured_by(chess.WHITE) == []
        assert game.captured_by(chess.BLACK) == []
        assert game.undo() is None  # nada para desfazer

    def test_lances_de_uma_casa(self) -> None:
        game = Game()
        peao_e2 = {m.uci() for m in game.legal_moves_from(chess.E2)}
        assert peao_e2 == {"e2e3", "e2e4"}
        cavalo_g1 = {m.uci() for m in game.legal_moves_from(chess.G1)}
        assert cavalo_g1 == {"g1f3", "g1h3"}


# ════════════════════════════════════════════════════════════
# Fins de partida clássicos
# ════════════════════════════════════════════════════════════

class TestMateDoLouco:
    """1.f3 e5 2.g4 Dh4# — mate mais rápido do xadrez."""

    def test_mate_do_louco(self) -> None:
        game = Game()
        sans = [
            _uci(game, "f2f3"),
            _uci(game, "e7e5"),
            _uci(game, "g2g4"),
            _uci(game, "d8h4"),
        ]
        assert sans == ["f3", "e5", "g4", "Qh4#"]
        assert game.is_game_over()
        result = game.result()
        assert result is not None
        assert result.status is Status.XEQUE_MATE
        assert result.winner is chess.BLACK
        assert game.in_check()
        assert game.check_square() == chess.E1


class TestMateDoPastor:
    """1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6 4.Qxf7# — mate do pastor."""

    def test_mate_do_pastor(self) -> None:
        game = Game()
        for uci in (
            "e2e4", "e7e5",
            "f1c4", "b8c6",
            "d1h5", "g8f6",
            "h5f7",
        ):
            game.push(chess.Move.from_uci(uci))
        assert game.is_game_over()
        result = game.result()
        assert result is not None
        assert result.status is Status.XEQUE_MATE
        assert result.winner is chess.WHITE
        assert list(game.san_history)[-1] == "Qxf7#"


class TestAfogamento:
    def test_stalemate(self) -> None:
        game = Game("k7/8/1Q6/8/8/8/8/K7 b - - 0 1")
        assert game.turn is chess.BLACK
        assert not game.in_check()  # afogado, não em xeque
        assert list(game.board.legal_moves) == []
        assert game.is_game_over()
        result = game.result()
        assert result is not None
        assert result.status is Status.AFOGAMENTO
        assert result.winner is None
        assert result.is_draw


class TestMaterialInsuficiente:
    def test_rei_contra_rei(self) -> None:
        game = Game("8/8/8/8/8/8/8/K6k w - - 0 1")
        assert game.is_game_over()
        result = game.result()
        assert result is not None
        assert result.status is Status.MATERIAL_INSUFICIENTE
        assert result.winner is None

    def test_rei_e_bispo_contra_rei(self) -> None:
        game = Game("8/8/8/8/8/8/4B3/K6k w - - 0 1")
        result = game.result()
        assert result is not None
        assert result.status is Status.MATERIAL_INSUFICIENTE


# ════════════════════════════════════════════════════════════
# Regras especiais
# ════════════════════════════════════════════════════════════

class TestRoque:
    def test_roque_ilegal_por_casa_atacada(self) -> None:
        # Torre preta em f2 ataca f1: O-O é ilegal, O-O-O é legal.
        game = Game("r3k2r/8/8/8/8/8/5r2/R3K2R w KQkq - 0 1")
        curto = chess.Move.from_uci("e1g1")
        longo = chess.Move.from_uci("e1c1")
        assert not game.is_legal(curto)
        assert game.is_legal(longo)

    def test_roques_legais_executam(self) -> None:
        game = Game("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        san = _uci(game, "e1g1")
        assert san == "O-O"
        assert game.board.piece_at(chess.G1) == chess.Piece(
            chess.KING, chess.WHITE
        )
        assert game.board.piece_at(chess.F1) == chess.Piece(
            chess.ROOK, chess.WHITE
        )
        _uci(game, "e8c8")  # pretas: roque grande
        assert game.board.has_queenside_castling_rights(chess.WHITE) is False


class TestEnPassant:
    def test_en_passant_disponivel_e_executa(self) -> None:
        game = Game()
        for uci in ("e2e4", "a7a6", "e4e5", "d7d5"):
            game.push(chess.Move.from_uci(uci))
        ep = chess.Move.from_uci("e5d6")
        assert game.is_legal(ep)
        assert _uci(game, "e5d6") == "exd6"
        # Peão branco em d6; peão preto de d5 foi removido
        assert game.board.piece_at(chess.D6) == chess.Piece(
            chess.PAWN, chess.WHITE
        )
        assert game.board.piece_at(chess.D5) is None
        # O peão preto capturado entra na lista das brancas
        assert game.captured_by(chess.WHITE) == [chess.PAWN]

    def test_en_passant_expira_apos_outro_lance(self) -> None:
        game = Game()
        for uci in ("e2e4", "a7a6", "e4e5", "d7d5", "a2a3", "a6a5"):
            game.push(chess.Move.from_uci(uci))
        assert chess.Move.from_uci("e5d6") not in game.board.legal_moves


class TestPromocao:
    FEN = "8/P6k/8/8/8/8/8/K7 w - - 0 1"

    def test_detecta_necessidade_de_promocao(self) -> None:
        game = Game(self.FEN)
        assert game.needs_promotion(chess.A7, chess.A8)
        assert not game.needs_promotion(chess.A1, chess.A2)  # rei
        game2 = Game()
        assert not game2.needs_promotion(chess.E2, chess.E4)  # peão comum

    def test_promocao_para_dama(self) -> None:
        game = Game(self.FEN)
        san = _uci(game, "a7a8q")
        assert san == "a8=Q"
        assert game.board.piece_at(chess.A8) == chess.Piece(
            chess.QUEEN, chess.WHITE
        )

    def test_promocao_para_cavalo(self) -> None:
        game = Game(self.FEN)
        _uci(game, "a7a8n")
        assert game.board.piece_at(chess.A8) == chess.Piece(
            chess.KNIGHT, chess.WHITE
        )


# ════════════════════════════════════════════════════════════
# Lances ilegais
# ════════════════════════════════════════════════════════════

class TestLancesIlegais:
    def test_lance_impossivel_erro(self) -> None:
        game = Game()
        with pytest.raises(ValueError):
            game.push(chess.Move.from_uci("e2e5"))

    def test_mover_pecas_do_adversario(self) -> None:
        game = Game()
        assert not game.is_legal(chess.Move.from_uci("b8c6"))

    def test_peca_cravada_nao_expoem_o_rei(self) -> None:
        game = Game("4k3/4r3/8/8/8/8/4B3/4K3 w - - 0 1")
        assert not game.is_legal(chess.Move.from_uci("e2d3"))

    def test_xeque_continua_a_partida(self) -> None:
        game = Game("4k3/8/8/8/8/8/4R3/4K3 b - - 0 1")
        assert game.in_check()
        assert game.check_square() == chess.E8
        assert not game.is_game_over()  # dá para sair do xeque


# ════════════════════════════════════════════════════════════
# Desfazer e histórico
# ════════════════════════════════════════════════════════════

class TestUndo:
    def test_undo_restaura_posicao(self) -> None:
        game = Game()
        fen_antes = game.board.fen()
        _uci(game, "e2e4")
        fen_depois = game.board.fen()
        game.undo()
        assert game.board.fen() == fen_antes
        assert game.board.fen() != fen_depois

    def test_undo_restaura_san_e_capturas(self) -> None:
        game = Game()
        for uci in ("e2e4", "d7d5", "e4d5"):
            game.push(chess.Move.from_uci(uci))
        assert game.captured_by(chess.WHITE) == [chess.PAWN]
        assert list(game.san_history) == ["e4", "d5", "exd5"]
        game.undo()
        assert game.captured_by(chess.WHITE) == []
        assert list(game.san_history) == ["e4", "d5"]
        assert game.board.piece_at(chess.D5) == chess.Piece(
            chess.PAWN, chess.BLACK
        )

    def test_undo_multiplos_lances(self) -> None:
        game = Game()
        fen_inicial = game.board.fen()
        for uci in ("e2e4", "e7e5", "g1f3"):
            game.push(chess.Move.from_uci(uci))
        for _ in range(3):
            game.undo()
        assert game.board.fen() == fen_inicial
        assert list(game.san_history) == []


# ════════════════════════════════════════════════════════════
# Histórico em SAN
# ════════════════════════════════════════════════════════════

class TestSan:
    def test_historico_san(self) -> None:
        game = Game()
        for uci in ("e2e4", "e7e5", "g1f3"):
            san = game.push(chess.Move.from_uci(uci))
            assert isinstance(san, str)
        assert list(game.san_history) == ["e4", "e5", "Nf3"]

    def test_san_de_captura_e_mate(self) -> None:
        game = Game()
        for uci in (
            "e2e4", "e7e5",
            "f1c4", "b8c6",
            "d1h5", "g8f6",
            "h5f7",
        ):
            game.push(chess.Move.from_uci(uci))
        assert list(game.san_history)[-1] == "Qxf7#"

    def test_pilha_de_lances_do_python_chess(self) -> None:
        game = Game()
        _uci(game, "e2e4")
        assert game.board.move_stack == [chess.Move.from_uci("e2e4")]


# ════════════════════════════════════════════════════════════
# Peças capturadas
# ════════════════════════════════════════════════════════════

class TestCapturadas:
    def test_capturas_por_cor(self) -> None:
        game = Game()
        for uci in ("e2e4", "d7d5", "e4d5", "d8d5"):
            game.push(chess.Move.from_uci(uci))
        # Brancas capturaram o peão de d5; pretas recapturaram com a dama
        assert game.captured_by(chess.WHITE) == [chess.PAWN]
        assert game.captured_by(chess.BLACK) == [chess.PAWN]

    def test_captura_de_dama(self) -> None:
        # 1.e4 d5 2.exd5 Qxd5 3.Nc3 Qxd2+ 4.Qxd2
        game = Game()
        for uci in ("e2e4", "d7d5", "e4d5", "d8d5", "b1c3", "d5d2", "d1d2"):
            game.push(chess.Move.from_uci(uci))
        assert game.captured_by(chess.WHITE) == [chess.PAWN, chess.QUEEN]
        # Pretas capturaram os peões brancos de d5 e d2
        assert game.captured_by(chess.BLACK) == [chess.PAWN, chess.PAWN]


# ════════════════════════════════════════════════════════════
# Desistência
# ════════════════════════════════════════════════════════════

class TestDesistencia:
    def test_pretas_desistem_brancas_vencem(self) -> None:
        game = Game()
        _uci(game, "e2e4")
        game.resign(chess.BLACK)
        assert game.is_game_over()
        result = game.result()
        assert result is not None
        assert result.status is Status.DESISTENCIA
        assert result.winner is chess.WHITE
        assert not result.is_draw

    def test_undo_reverte_desistencia(self) -> None:
        game = Game()
        game.resign(chess.WHITE)
        assert game.is_game_over()
        game.undo()
        assert not game.is_game_over()
        assert game.result() is None


# ════════════════════════════════════════════════════════════
# Empates (50 lances e repetição)
# ════════════════════════════════════════════════════════════

class TestRegraDosCinquentaLances:
    def test_claim_de_50_lances(self) -> None:
        # 100 meios-lances sem captura nem movimento de peão
        game = Game("4k3/8/8/8/8/8/8/4K2R w - - 100 60")
        assert game.can_claim_fifty_moves()
        assert game.is_game_over()
        result = game.result()
        assert result is not None
        assert result.status is Status.CINQUENTA_LANCES
        assert result.winner is None

    def test_abaixo_do_limite_nao_encerra(self) -> None:
        # 90 meios-lances: longe do limite de 100 (a partir de 99 um
        # lance não-zeroing já permite a reivindicação, por isso 90)
        game = Game("4k3/8/8/8/8/8/8/4K2R w - - 90 60")
        assert not game.can_claim_fifty_moves()
        assert not game.is_game_over()


class TestTriplaRepeticao:
    SEQ = ("g1f3", "g8f6", "f3g1", "f6g8")

    def test_duas_repeticoes_nao_encerram(self) -> None:
        game = Game()
        for uci in self.SEQ:
            game.push(chess.Move.from_uci(uci))
        assert not game.can_claim_threefold_repetition()
        assert not game.is_game_over()

    def test_tripla_repeticao_encerra(self) -> None:
        game = Game()
        for uci in self.SEQ * 2:
            game.push(chess.Move.from_uci(uci))
        assert game.can_claim_threefold_repetition()
        assert game.is_game_over()
        result = game.result()
        assert result is not None
        assert result.status is Status.TRIPLA_REPETICAO
        assert result.winner is None


# ════════════════════════════════════════════════════════════
# Tipos centrais
# ════════════════════════════════════════════════════════════

class TestTipos:
    def test_level_possui_quatro_niveis(self) -> None:
        assert len(Level) == 4

    def test_game_result_dataclass(self) -> None:
        result = GameResult(status=Status.XEQUE_MATE, winner=chess.WHITE)
        assert not result.is_draw
        empate = GameResult(status=Status.AFOGAMENTO, winner=None)
        assert empate.is_draw

    def test_reset(self) -> None:
        game = Game()
        for uci in ("e2e4", "e7e5"):
            game.push(chess.Move.from_uci(uci))
        game.reset()
        assert game.board.fen() == chess.STARTING_FEN
        assert list(game.san_history) == []
        assert game.captured_by(chess.WHITE) == []
        assert game.result() is None
