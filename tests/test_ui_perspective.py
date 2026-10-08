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
import pytest

from xadtitans.core.game import Game
from xadtitans.core.types import GameMode, Level
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
    # Clica exatamente no ponto de apoio da casa: funciona em ambas as
    # orientações (com o virar automático do HvH, as casas distantes ficam
    # pequenas e um deslocamento fixo sairia da casa).
    fx, fy = scene.board_view.piece_anchor(sq)
    scene._on_left_click((int(fx), int(fy)))


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

    def test_flip_troca_mapa_e_imagem_juntos(self) -> None:
        """Regressão do bug de orientação (Fase 6.7/empacotamento):

        ``toggle_flip`` deve trocar o par (mapa de casas, imagem com
        coordenadas gravadas) num único ponto — ``casa → tela``,
        ``tela → casa`` e as coordenadas visuais derivam sempre da
        mesma transformação. Antes, a imagem (com as coordenadas
        gravadas) nunca era trocada: a visão preta mostrava peças
        invertidas com coordenadas ``a..h``/``1..8`` das brancas.
        """
        _screen()
        bv = BoardView()
        img_brancas = bv._board_img
        mapa_brancas = bv._map
        bv.toggle_flip()
        assert bv._board_img is not img_brancas, \
            "flip não trocou a imagem (coordenadas ficariam erradas)"
        assert bv._map is not mapa_brancas
        bv.toggle_flip()
        assert bv._board_img is img_brancas
        assert bv._map is mapa_brancas

    def test_cell_w_positivo_nas_duas_orientacoes(self) -> None:
        """Regressão Fase 6.6: com o mapa flipped a fórmula de arestas
        invertia o sinal e ``_draw_legal`` tentava criar ``Surface``
        com resolução negativa (pygame.error: Invalid resolution),
        derrubando o App ao selecionar peça com o tabuleiro virado."""
        _screen()
        bv = BoardView()
        for sq in chess.SQUARES:
            assert bv._cell_w(sq) > 0, f"base: largura <= 0 em {sq}"
        bv.toggle_flip()
        for sq in chess.SQUARES:
            assert bv._cell_w(sq) > 0, f"flipped: largura <= 0 em {sq}"

    def test_foot_offset_sempre_para_baixo(self) -> None:
        """O ponto de apoio da peça fica abaixo do centro nas duas
        orientações (com o mapa flipped, poly[0,1] deixa de ser o lado
        perto; sem a correção as peças eram deslocadas para cima)."""
        _screen()
        bv = BoardView()
        for _ in range(2):
            for sq in chess.SQUARES:
                _cx, cy = bv._center(sq)
                _fx, fy = bv._foot(sq)
                assert fy >= cy, (
                    f"offset para cima em {sq} (flipped={bv.flipped})"
                )
            bv.toggle_flip()

    def test_desenho_de_lances_legais_com_tabuleiro_virado(self) -> None:
        """Regressão do crash: selecionar peça com o tabuleiro virado
        desenha pontos/aneis de lances legais sem lançar pygame.error."""
        surf = _screen()
        scene = GameScene()
        scene._apply_move(chess.Move.from_uci("e2e4"))
        _finish_animations(scene)
        assert scene.board_view.flipped, "HvH deveria virar após e4"
        # Seleciona o peão preto e7 pelos cliques reais
        _click(scene, chess.E7)
        assert scene.board_view.selected_square == chess.E7
        assert chess.E5 in scene.board_view.legal_destinations
        scene.draw(surf)  # desenha os pontos/aneis — não pode lançar
        scene.draw(surf)
        # Liga também o anel de captura (seleciona casa com peça inimiga)
        scene.board_view.legal_destinations = [chess.D5]
        scene.draw(surf)


class TestOrientacaoPorPerspectiva:
    """Critérios de aceitação da orientação nas DUAS visões.

    BRANCAS: a1 EI, h1 DI, a8 ES, h8 DS.
    PRETAS:  h8 EI, a8 DI, h1 ES, a1 DS.
    Round-trip casa↔tela e clique→seleção nas duas orientações.
    """

    @staticmethod
    def _quadrante(bv: BoardView, sq: int) -> str:
        xs = [bv._center(s)[0] for s in chess.SQUARES]
        ys = [bv._center(s)[1] for s in chess.SQUARES]
        xmid = (min(xs) + max(xs)) / 2
        ymid = (min(ys) + max(ys)) / 2
        cx, cy = bv._center(sq)
        return ("E" if cx < xmid else "D") + ("S" if cy < ymid else "I")

    def test_visao_brancas_cantos(self) -> None:
        _screen()
        bv = BoardView()
        assert self._quadrante(bv, chess.A1) == "EI"
        assert self._quadrante(bv, chess.H1) == "DI"
        assert self._quadrante(bv, chess.A8) == "ES"
        assert self._quadrante(bv, chess.H8) == "DS"

    def test_visao_pretas_cantos(self) -> None:
        _screen()
        bv = BoardView()
        bv.toggle_flip()
        assert self._quadrante(bv, chess.H8) == "EI"
        assert self._quadrante(bv, chess.A8) == "DI"
        assert self._quadrante(bv, chess.H1) == "ES"
        assert self._quadrante(bv, chess.A1) == "DS"

    @pytest.mark.parametrize("flipped", [False, True])
    def test_round_trip_casa_tela_casa(self, flipped: bool) -> None:
        """casa → tela → casa retorna a própria casa nas duas visões."""
        _screen()
        bv = BoardView()
        if flipped:
            bv.toggle_flip()
        for sq in chess.SQUARES:
            cx, cy = bv._center(sq)
            assert bv.square_at(cx, cy) == sq, (
                f"round-trip falhou em {chess.square_name(sq)} "
                f"(flipped={flipped})"
            )

    def test_clique_seleciona_peca_na_visao_pretas(self) -> None:
        """Humano de pretas: clicar na peça visualmente embaixo (fileira
        do jogador) seleciona a casa correta do python-chess."""
        _screen()
        scene = GameScene(
            game_mode=GameMode.HUMAN_VS_AI,
            ai_color=chess.WHITE,
            ai_level=Level.INICIANTE,
        )
        scene._cancel_ai()  # teste determinístico sem busca ativa
        assert scene.board_view.flipped, \
            "humano de pretas deve virar o tabuleiro"
        # Brancas (IA) jogam primeiro: aplicamos o lance delas manualmente
        # para a vez ficar com as pretas (humano).
        scene._apply_move(chess.Move.from_uci("e2e4"))
        _finish_animations(scene)
        # Peões pretos (rank 7) ficam na fileira inferior da visão preta.
        _click(scene, chess.E7)
        assert scene.board_view.selected_square == chess.E7
        assert {chess.E6, chess.E5} <= set(scene.board_view.legal_destinations)
        _click(scene, chess.E5)
        scene._cancel_ai()  # impede a IA branca de mover durante os frames
        _finish_animations(scene)
        assert scene.game.board.move_stack[-1] == chess.Move.from_uci("e7e5")
        # E a casa visualmente no topo (peão branco avançado em e4)
        # também corresponde — clique no topo da visão preta = casas
        # das brancas. (Após o lance preto é turno da IA e o handler
        # ignora cliques humanos por design; verificamos a geometria.)
        ex, ey = scene.board_view.piece_anchor(chess.E4)
        assert scene.board_view.square_at(int(ex), int(ey)) == chess.E4, \
            "topo da visão preta deve corresponder às casas das brancas"

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
