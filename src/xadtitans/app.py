"""Loop principal e gerenciador de cenas do XadTitans."""

from __future__ import annotations

import pygame

from xadtitans.audio import AudioManager
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

        self.audio = AudioManager()
        self.show_fps = False
        self._fps_font = pygame.font.SysFont("arial", 16, bold=True)

        # Cena atual (GameScene ou FimDePartida)
        self.scene: GameScene | EndgameScene = GameScene(self.audio)

    def run(self) -> int:
        """Executa o loop até o usuário fechar. Retorna 0."""
        while self.running:
            dt = self.clock.tick(FPS_DEFAULT) / 1000.0

            for event in pygame.event.get():
                if (
                    event.type == pygame.QUIT
                    or (
                        event.type == pygame.KEYDOWN
                        and event.key == pygame.K_ESCAPE
                    )
                ):
                    self.running = False
                elif (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_F3
                ):
                    self.show_fps = not self.show_fps
                else:
                    self.scene.handle_event(event)

            self._switch_scenes_if_needed()
            self.scene.update(dt)
            self.scene.draw(self.screen)
            if self.show_fps:
                self._draw_fps()
            pygame.display.flip()

        pygame.quit()
        return 0

    def _draw_fps(self) -> None:
        fps = self.clock.get_fps()
        color = (80, 220, 80) if fps >= 30 else (240, 90, 60)
        text = self._fps_font.render(f"{fps:5.1f} FPS", True, color)
        self.screen.blit(text, (8, WINDOW_HEIGHT - 24))

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
