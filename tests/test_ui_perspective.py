"""Testes de integração da UI em perspectiva (headless, driver dummy).

Requer os assets gerados (assets/board, assets/pieces) — committed.
Usa SDL_VIDEODRIVER=dummy: nenhum monitor é necessário.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import chess
import pygame

from xadtitans.core.game import Game
from xadtitans.ui.board_view import BoardView
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.widgets.side_panel import format_move_pairs

_surf: pygame.Surface | None = None


def _screen() -> pygame.Surface:
    global _surf
    if _surf is None:
        pygame.init()
        _surf = pygame.display.set_mode((1024, 768))
    return _surf


def _click(scene: GameScene, sq: int) -> None:
    fx, fy = scene.board_view.piece_anchor(sq)
    scene._on_left_click((int(fx), int(fy) - 20))


def _finish_animations(scene: GameScene) -> None:
    for _ in range(60):
        scene.update(1 / 30)


class TestBoardViewPerspectiva:
    def test_carrega_assets_e_cache(self) -> None:
        _screen()
        bv = BoardView()
        # cache pré-construído: 12 peças x 8 fileiras (tamanhos por fileira)
        assert len(bv._sprites) >= 12 * 4  # fileiras dão >=4 tamanhos distintos
        assert len(bv._shadows) >= 4

    def test_square_at_no_ponto_de_apoio(self) -> None:
        _screen()
        bv = BoardView()
        for sq in range(0, 64, 5):
            ax, ay = bv.piece_anchor(sq)
            assert bv.square_at(ax, ay) == sq

    def test_flip_mantem_clique_consistente(self) -> None:
        _screen()
        bv = BoardView()
        bv.toggle_flip()
        # no tabuleiro virado, a casa A1 fica onde a8 estava (rotacionado)
        ax, ay = bv.piece_anchor(chess.A1)
        assert bv.square_at(ax, ay - 20) is not None
        bv.toggle_flip()
        assert not bv.flipped

    def test_desenha_sem_erro_com_estado(self) -> None:
        surf = _screen()
        bv = BoardView()
        bv.set_board(chess.Board())
        bv.selected_square = chess.E2
        bv.legal_destinations = [chess.E3, chess.E4]
        bv.last_move = chess.Move.from_uci("e2e4")
        bv.check_square = None
        bv.hover_square = chess.E4
        bv.draw(surf)  # não deve lançar


class TestGameScenePerspectiva:
    def test_clique_move_e_anima(self) -> None:
        _screen()
        scene = GameScene()
        _click(scene, chess.E2)
        assert scene.board_view.selected_square == chess.E2
        assert chess.E4 in scene.board_view.legal_destinations
        _click(scene, chess.E4)
        assert scene.game.san_history[0] == "e4"

    def test_input_bloqueado_durante_animacao(self) -> None:
        _screen()
        scene = GameScene()
        _click(scene, chess.E2)
        _click(scene, chess.E4)
        assert scene.animator.blocking
        # cliques durante a animação são ignorados
        _click(scene, chess.E7)
        assert scene.board_view.selected_square != chess.E7
        _finish_animations(scene)
        assert not scene.animator.blocking
        # agora o clique volta a funcionar
        _click(scene, chess.E7)
        assert scene.board_view.selected_square == chess.E7

    def test_captura_gera_fade(self) -> None:
        _screen()
        scene = GameScene()
        for uci in ("e2e4", "d7d5"):
            scene._apply_move(chess.Move.from_uci(uci))
            _finish_animations(scene)
        scene._apply_move(chess.Move.from_uci("e4d5"))
        kinds = {a.kind for a in scene.animator._anims}
        assert kinds == {"slide", "fade"}
        assert scene.game.captured_by(chess.WHITE) == [chess.PAWN]

    def test_roque_anima_rei_e_torre(self) -> None:
        _screen()
        scene = GameScene()
        scene.game = Game("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        scene._sync_view()
        _click(scene, chess.E1)
        assert chess.G1 in scene.board_view.legal_destinations
        _click(scene, chess.G1)
        assert scene.game.san_history[0] == "O-O"
        slides = [a for a in scene.animator._anims if a.kind == "slide"]
        assert len(slides) == 2  # rei + torre

    def test_hover_define_casa(self) -> None:
        _screen()
        scene = GameScene()
        ax, ay = scene.board_view.piece_anchor(chess.E4)
        scene._on_hover((int(ax), int(ay)))
        assert scene.board_view.hover_square is not None

    def test_promocao_com_dialogo(self) -> None:
        _screen()
        scene = GameScene()
        scene.game = Game("8/P6k/8/8/8/8/8/K7 w - - 0 1")
        scene._sync_view()
        _click(scene, chess.A7)
        _click(scene, chess.A8)
        assert scene.pending_promotion == (chess.A7, chess.A8)
        scene.draw(_screen())  # desenha o diálogo (preenche _promo_rects)
        rect, piece_type = scene._promo_rects[0]
        assert piece_type == chess.QUEEN
        scene._handle_promotion_click(rect.center)
        assert scene.game.board.piece_at(chess.A8).piece_type == chess.QUEEN

    def test_undo_e_flip(self) -> None:
        _screen()
        scene = GameScene()
        scene._apply_move(chess.Move.from_uci("e2e4"))
        _finish_animations(scene)
        scene.undo()
        assert scene.game.board.fen() == chess.STARTING_FEN
        era = scene.board_view.flipped
        scene.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        )
        assert scene.board_view.flipped != era
        scene.draw(_screen())

    def test_desenho_completo_nao_quebra(self) -> None:
        _screen()
        scene = GameScene()
        scene._apply_move(chess.Move.from_uci("e2e4"))
        scene.draw(_screen())  # com animação em curso
        _finish_animations(scene)
        scene.draw(_screen())  # depois da animação

    def test_painel_lateral_formata_jogadas(self) -> None:
        _screen()
        scene = GameScene()
        for uci in ("e2e4", "e7e5", "g1f3"):
            scene._apply_move(chess.Move.from_uci(uci))
            _finish_animations(scene)
        scene.draw(_screen())
        assert format_move_pairs(scene.game.san_history)[0] == "1. e4 e5"
