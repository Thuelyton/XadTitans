"""Cena de fim de partida — mostra o resultado sobre o tabuleiro.

Enter (ou N) inicia uma nova partida; Esc retorna ao menu principal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from xadtitans.config import COLOR_BG, WINDOW_WIDTH
from xadtitans.core.types import GameResult, Status
from xadtitans.i18n import t

if TYPE_CHECKING:
    from xadtitans.ui.scene_manager import SceneManager
    from xadtitans.ui.scenes.game_scene import GameScene


def result_text(result: GameResult) -> str:
    """Texto legível do resultado, em pt-BR usando i18n."""
    if result.winner is None:
        return f"{t('game.draw')} — {result.status.value}"
    vencedor = "Brancas" if result.winner else "Pretas"
    if result.status is Status.DESISTENCIA:
        verbo = t("game.resigned_wins")
    elif result.status is Status.TEMPO_ESGOTADO:
        verbo = t("game.timeout_wins")
    else:
        verbo = t("game.wins")
    return f"{vencedor} {verbo} — {result.status.value}"


class EndgameScene:
    """Overlay do resultado final (cena FimDePartida)."""

    def __init__(
        self,
        game_scene: GameScene,
        scene_manager: SceneManager | None = None,
    ) -> None:
        self.game_scene = game_scene
        self.scene_manager = scene_manager
        self.new_game_requested = False
        self.back_to_menu_requested = False
        self._result = game_scene.game.result()

        self._font = pygame.font.SysFont("arial", 36, bold=True)
        self._hint_font = pygame.font.SysFont("arial", 18)

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_n):
                self.new_game_requested = True
                if self.scene_manager is not None:
                    self.game_scene.new_game()
                    self.scene_manager.pop()
            elif event.key == pygame.K_ESCAPE:
                self.back_to_menu_requested = True
                if self.scene_manager is not None:
                    # Desempilha EndgameScene e GameScene para voltar ao menu
                    self.scene_manager.pop()
                    if self.scene_manager.current is self.game_scene:
                        self.scene_manager.pop()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        # Tabuleiro congelado ao fundo
        surface.fill(COLOR_BG)
        self.game_scene.board_view.draw(surface)

        # Véu escurecido
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 160))
        surface.blit(veil, (0, 0))

        # Resultado
        assert self._result is not None
        text = result_text(self._result)
        rendered = self._font.render(text, True, (240, 240, 240))
        rect = rendered.get_rect(center=(WINDOW_WIDTH // 2, 300))
        surface.blit(rendered, rect)

        # Título e dica
        title = self._font.render(t("game.game_over"), True, (255, 215, 0))
        surface.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 240)))
        hint = self._hint_font.render(
            t("hint.endgame"), True, (180, 180, 180)
        )
        surface.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, 350)))
