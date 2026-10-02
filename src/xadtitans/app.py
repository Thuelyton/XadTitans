"""Loop principal e gerenciador de cenas do XadTitans com SceneManager."""

from __future__ import annotations

import sys
import time
from typing import Any

import pygame

from xadtitans.audio import AudioManager
from xadtitans.config import (
    FPS_DEFAULT,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from xadtitans.i18n import t
from xadtitans.storage.settings import Settings
from xadtitans.ui.scene_manager import SceneManager
from xadtitans.ui.scenes.endgame_scene import EndgameScene
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.scenes.menu_scene import MenuScene
from xadtitans.utils.logger import get_logger


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

        # Código de saída (não-zero se encerrado por erro fatal).
        self._exit_code = 0

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
            try:
                self._frame()
            except Exception:  # noqa: BLE001 — handler global de erros fatais
                # Erro fatal não tratado: registra, tenta preservar a
                # partida e encerra de forma controlada (nunca silenciosa).
                self._handle_fatal_error()
                break

        # Encerramento: autosave de partida em andamento (via on_exit de
        # cada cena) e limpeza — uma falha aqui não pode impedir o fechamento.
        try:
            self.scene_manager.clear()
            pygame.quit()
        except Exception:  # noqa: BLE001 — encerramento deve prosseguir
            get_logger().exception("Erro durante o encerramento")
        return self._exit_code

    def _frame(self) -> None:
        """Um quadro do loop principal (eventos → atualização → desenho)."""
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
            return

        self._switch_scenes_if_needed()
        self.scene_manager.update(dt)
        self.scene_manager.draw(self.screen)
        if self.show_fps:
            self._draw_fps()
        pygame.display.flip()

    def _handle_fatal_error(self) -> None:
        """Erro fatal: loga, preserva a partida se seguro e encerra."""
        get_logger().exception("Erro fatal não tratado — encerrando")
        self._exit_code = 1
        self.running = False
        # Preservar partida em andamento quando for seguro.
        for scene in self.scene_manager.scenes:
            if isinstance(scene, GameScene):
                try:
                    scene._autosave()
                except Exception:  # noqa: BLE001 — não impedir o encerramento
                    get_logger().exception(
                        "Falha ao preservar autosave no encerramento"
                    )
        # Mensagem amigável (nunca um traceback cru para o usuário).
        self._show_error_screen(t("error.fatal"))

    def _show_error_screen(self, message: str) -> None:
        """Mostra uma tela de erro amigável até o usuário pressionar uma tecla.

        Se a janela não estiver utilizável, imprime no stderr como plano B.
        """
        try:
            big_font = pygame.font.SysFont("arial", 26, bold=True)
            self.screen.fill((18, 18, 22))
            lines = [t("error.title"), "", message, "", t("error.press_key")]
            y = self.screen.get_height() // 2 - 60
            for i, line in enumerate(lines):
                color = (240, 90, 60) if i == 0 else (220, 220, 220)
                if line:
                    rendered = big_font.render(line, True, color)
                    self.screen.blit(
                        rendered,
                        rendered.get_rect(
                            center=(self.screen.get_width() // 2, y)
                        ),
                    )
                y += 34
            pygame.display.flip()

            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                for event in pygame.event.get():
                    if event.type in (
                        pygame.KEYDOWN,
                        pygame.MOUSEBUTTONDOWN,
                        pygame.QUIT,
                    ):
                        return
                self.clock.tick(30)
        except Exception:  # noqa: BLE001 — plano B: stderr
            print(f"{t('error.title')}: {message}", file=sys.stderr)

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
