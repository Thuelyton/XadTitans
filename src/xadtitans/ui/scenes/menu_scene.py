"""Cena do Menu Principal do XadTitans.

Exibe as opções principais do jogo:
  - Novo Jogo (transita para NewGameScene)
  - Continuar (desabilitado se não houver autosave)
  - Carregar (abre LoadScene para escolher PGN)
  - Configurações (transita para SettingsScene)
  - Estatísticas (transita para StatsScene)
  - Sair (encerra o aplicativo)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from xadtitans.audio import AudioManager
from xadtitans.config import COLOR_BG, WINDOW_HEIGHT, WINDOW_WIDTH
from xadtitans.i18n import t
from xadtitans.storage.paths import autosave_file
from xadtitans.storage.pgn import list_pgn_files
from xadtitans.ui.widgets.button import Button

if TYPE_CHECKING:
    from xadtitans.ui.scene_manager import SceneManager


class MenuScene:
    """Tela de Menu Principal."""

    def __init__(
        self,
        scene_manager: SceneManager | None = None,
        audio: AudioManager | None = None,
    ) -> None:
        self.scene_manager = scene_manager
        self.audio = audio or AudioManager()
        self.quit_requested = False
        self.message: str | None = None
        self.message_timer: float = 0.0

        self._title_font = pygame.font.SysFont("arial", 48, bold=True)
        self._subtitle_font = pygame.font.SysFont("arial", 20)
        self._msg_font = pygame.font.SysFont("arial", 18)

        self.buttons: list[Button] = []
        self._build_buttons()

    def _build_buttons(self) -> None:
        has_autosave = autosave_file().exists()

        btn_w, btn_h = 280, 48
        start_y = 260
        spacing = 60
        center_x = WINDOW_WIDTH // 2 - btn_w // 2

        options = [
            ("menu.new_game", self._on_new_game, True),
            ("menu.continue", self._on_continue, has_autosave),
            ("menu.load", self._on_load, True),  # Abre LoadScene (exibe PGNs ou aviso)
            ("menu.settings", self._on_settings, True),
            ("menu.stats", self._on_stats, True),
            ("menu.quit", self._on_quit, True),
        ]

        self.buttons.clear()
        for idx, (key, callback, enabled) in enumerate(options):
            rect = (center_x, start_y + idx * spacing, btn_w, btn_h)
            btn = Button(
                rect=rect,
                text=t(key),
                callback=callback,
                enabled=enabled,
            )
            self.buttons.append(btn)

    def _on_new_game(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            from xadtitans.ui.scenes.new_game_scene import NewGameScene

            self.scene_manager.push(NewGameScene(self.scene_manager, self.audio))

    def _on_continue(self) -> None:
        self.audio.play("click")
        if not autosave_file().exists():
            self._show_message(t("load.no_autosave"))

    def _on_load(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            from xadtitans.ui.scenes.load_scene import LoadScene

            self.scene_manager.push(LoadScene(self.scene_manager, self.audio))
        elif not list_pgn_files():
            self._show_message(t("load.no_pgns"))

    def _on_settings(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            from xadtitans.ui.scenes.settings_scene import SettingsScene

            self.scene_manager.push(SettingsScene(self.scene_manager, self.audio))

    def _on_stats(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            from xadtitans.ui.scenes.stats_scene import StatsScene

            self.scene_manager.push(StatsScene(self.scene_manager, self.audio))

    def _on_quit(self) -> None:
        self.audio.play("click")
        self.quit_requested = True

    def _show_message(self, msg: str, duration: float = 3.0) -> None:
        self.message = msg
        self.message_timer = duration

    # ── ciclo de vida ─────────────────────────────────────

    def on_enter(self) -> None:
        """Atualiza estado dos botões ao retornar ao menu."""
        self._build_buttons()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.quit_requested = True
            return

        for btn in self.buttons:
            if btn.handle_event(event):
                break

    def update(self, dt: float) -> None:
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.update_hover(mouse_pos)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)

        # Título principal
        title_surf = self._title_font.render(t("menu.title"), True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 120))
        surface.blit(title_surf, title_rect)

        # Subtítulo
        sub_surf = self._subtitle_font.render(t("menu.subtitle"), True, (180, 180, 180))
        sub_rect = sub_surf.get_rect(center=(WINDOW_WIDTH // 2, 175))
        surface.blit(sub_surf, sub_rect)

        # Botões
        for btn in self.buttons:
            btn.draw(surface)

        # Mensagem temporária
        if self.message:
            msg_surf = self._msg_font.render(self.message, True, (240, 100, 100))
            msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40))
            surface.blit(msg_surf, msg_rect)
