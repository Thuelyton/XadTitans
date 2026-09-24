"""Loop principal e gerenciador de cenas do XadTitans."""

from __future__ import annotations

import pygame

from xadtitans.config import (
    FPS_DEFAULT,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from xadtitans.ui.scenes.game_scene import GameScene


class App:
    """Janela principal — roda o loop de eventos e renderização."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Cena atual (por enquanto, direto na GameScene)
        self.scene: GameScene = GameScene()

    def run(self) -> int:
        """Executa o loop até o usuário fechar. Retorna 0."""
        while self.running:
            dt = self.clock.tick(FPS_DEFAULT) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self.scene.handle_event(event)

            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
        return 0
