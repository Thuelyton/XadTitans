"""Loop principal e gerenciador de cenas do XadTitans."""

from __future__ import annotations

import pygame

from xadtitans.config import (
    FPS_DEFAULT,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from xadtitans.ui.scenes.endgame_scene import EndgameScene
from xadtitans.ui.scenes.game_scene import GameScene


class App:
    """Janela principal — roda o loop de eventos e renderização."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Cena atual (GameScene ou FimDePartida)
        self.scene: GameScene | EndgameScene = GameScene()

    def run(self) -> int:
        """Executa o loop até o usuário fechar. Retorna 0."""
        while self.running:
            dt = self.clock.tick(FPS_DEFAULT) / 1000.0

            for event in pygame.event.get():
                if (
                    event.type == pygame.QUIT
                    or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)
                ):
                    self.running = False
                else:
                    self.scene.handle_event(event)

            self._switch_scenes_if_needed()
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
        return 0

    def _switch_scenes_if_needed(self) -> None:
        """Troca de cena: fim de partida ↔ nova partida."""
        if isinstance(self.scene, GameScene):
            if self.scene.game_over:
                self.scene = EndgameScene(self.scene)
        elif isinstance(self.scene, EndgameScene) and (
            self.scene.new_game_requested
        ):
            self.scene.game_scene.new_game()
            self.scene = self.scene.game_scene
