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
        """Cria o overlay com o resultado da ``game_scene`` no momento atual."""
        self.game_scene = game_scene
        self.scene_manager = scene_manager
        self.new_game_requested = False
        self.back_to_menu_requested = False
        self._result = game_scene.game.result()

        self._font = pygame.font.SysFont("arial", 36, bold=True)
        self._hint_font = pygame.font.SysFont("arial", 18)
        # Elementos estáticos por cena: véu escurecido (superfície
        # fullscreen — alocar ~3 MB por frame era o maior custo do
        # overlay, medido na Fase 6.5) e textos pré-renderizados.
        self._veil: pygame.Surface | None = None
        self._texts: tuple[pygame.Surface, ...] | None = None

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Enter/N inicia nova partida; Esc volta ao menu principal."""
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
        """Overlay estática; não há lógica a atualizar (``dt`` é ignorado)."""

    def draw(self, surface: pygame.Surface) -> None:
        """Desenha tabuleiro congelado, véu escurecido e o texto do resultado."""
        # Tabuleiro congelado ao fundo
        surface.fill(COLOR_BG)
        self.game_scene.board_view.draw(surface)

        # Véu escurecido (estático: criado uma única vez por tamanho
        # de tela; uma vez por sessão em resolução fixa)
        size = surface.get_size()
        if self._veil is None or self._veil.get_size() != size:
            self._veil = pygame.Surface(size, pygame.SRCALPHA)
            self._veil.fill((0, 0, 0, 160))
        surface.blit(self._veil, (0, 0))

        # Resultado
        assert self._result is not None
        # Textos estáticos: pré-renderizados uma única vez por cena
        if self._texts is None:
            self._texts = (
                self._font.render(
                    result_text(self._result), True, (240, 240, 240)
                ),
                self._font.render(t("game.game_over"), True, (255, 215, 0)),
                self._hint_font.render(
                    t("hint.endgame"), True, (180, 180, 180)
                ),
            )
        rendered, title, hint = self._texts
        rect = rendered.get_rect(center=(WINDOW_WIDTH // 2, 300))
        surface.blit(rendered, rect)

        # Título e dica
        surface.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, 240)))
        surface.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, 350)))
