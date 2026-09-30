"""Loop principal e gerenciador de cenas do XadTitans com SceneManager."""

from __future__ import annotations

from typing import Any

import pygame

from xadtitans.audio import AudioManager
from xadtitans.config import (
    FPS_DEFAULT,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from xadtitans.storage.settings import Settings
from xadtitans.ui.scene_manager import SceneManager
from xadtitans.ui.scenes.endgame_scene import EndgameScene
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.scenes.menu_scene import MenuScene


class App:
    """Janela principal — roda o loop de eventos e renderização."""

    def __init__(self) -> None:
        pygame.init()

        self.settings = Settings()
        self.settings.load()

        fps_val = self.settings.get("fps", FPS_DEFAULT)
        vol_val = self.settings.get("volume", 0.8)
        res_val = self.settings.get("resolution", [WINDOW_WIDTH, WINDOW_HEIGHT])

        self.screen = pygame.display.set_mode((res_val[0], res_val[1]))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.fps_target = int(fps_val)

        self.audio = AudioManager()
        self.audio.volume = float(vol_val)
        self.show_fps = False
        self._fps_font = pygame.font.SysFont("arial", 16, bold=True)

        self.scene_manager = SceneManager()
        self.menu_scene = MenuScene(self.scene_manager, self.audio)
        self.scene_manager.push(self.menu_scene)

    @property
    def scene(self) -> Any:
        """Propriedade para compatibilidade com a cena ativa atual."""
        return self.scene_manager.current

    @scene.setter
    def scene(self, new_scene: Any) -> None:
        """Setter de retrocompatibilidade: substitui a cena topo da pilha."""
        self.scene_manager.switch(new_scene)

    def run(self) -> int:
        """Executa o loop até o usuário fechar. Retorna 0."""
        while self.running:
            dt = self.clock.tick(self.fps_target) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_F3
                ):
                    self.show_fps = not self.show_fps
                elif (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE
                ):
                    self._handle_global_escape()
                else:
                    self.scene_manager.handle_event(event)

            if self.menu_scene.quit_requested or self.scene_manager.current is None:
                self.running = False
                break

            self._switch_scenes_if_needed()
            self.scene_manager.update(dt)
            self.scene_manager.draw(self.screen)
            if self.show_fps:
                self._draw_fps()
            pygame.display.flip()

        self.scene_manager.clear()
        pygame.quit()
        return 0

    def _handle_global_escape(self) -> None:
        """Trata a tecla ESC de forma contextual na pilha de cenas."""
        current = self.scene_manager.current
        if current is None or isinstance(current, MenuScene):
            self.running = False
        elif isinstance(current, GameScene):
            self.scene_manager.pop()
        else:
            self.scene_manager.handle_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
            )

    def _draw_fps(self) -> None:
        fps = self.clock.get_fps()
        color = (80, 220, 80) if fps >= 30 else (240, 90, 60)
        text = self._fps_font.render(f"{fps:5.1f} FPS", True, color)
        self.screen.blit(text, (8, WINDOW_HEIGHT - 24))

    def _switch_scenes_if_needed(self) -> None:
        """Troca/empilhamento de cena: fim de partida ou reinício."""
        current = self.scene_manager.current

        if isinstance(current, GameScene):
            if current.game_over:
                self.scene_manager.push(
                    EndgameScene(current, self.scene_manager)
                )
        elif isinstance(current, EndgameScene):
            if current.new_game_requested:
                current.new_game_requested = False
                current.game_scene.new_game()
                self.scene_manager.pop()
            elif current.back_to_menu_requested:
                current.back_to_menu_requested = False
                self.scene_manager.pop()  # Pop EndgameScene
                if self.scene_manager.current is current.game_scene:
                    self.scene_manager.pop()  # Pop GameScene
