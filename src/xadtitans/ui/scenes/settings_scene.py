"""Cena de Configurações do XadTitans.

Permite visualizar e alterar as configurações do jogo:
  - Volume do áudio (0% a 100%)
  - Velocidade das animações (0.5x a 2.0x)
  - Taxa de quadros FPS (15, 30, 60, 120)
  - Resolução (1024x768)
  - Ajudas visuais (Ativado/Desativado)

Utiliza a API de `storage.settings.Settings` para carregar e salvar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from xadtitans.audio import AudioManager
from xadtitans.config import COLOR_BG, WINDOW_HEIGHT, WINDOW_WIDTH
from xadtitans.i18n import t
from xadtitans.storage.settings import Settings
from xadtitans.ui.widgets.button import Button
from xadtitans.ui.widgets.selector import Selector

if TYPE_CHECKING:
    from xadtitans.ui.scene_manager import SceneManager


class SettingsScene:
    """Tela de edição das configurações do jogo."""

    def __init__(
        self,
        scene_manager: SceneManager | None = None,
        audio: AudioManager | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Carrega as configurações e monta seletores e botões de ação."""
        self.scene_manager = scene_manager
        self.audio = audio or AudioManager()
        self.settings = settings or Settings()
        self.settings.load()

        self._title_font = pygame.font.SysFont("arial", 38, bold=True)
        self._label_font = pygame.font.SysFont("arial", 20, bold=True)
        self._msg_font = pygame.font.SysFont("arial", 18)

        self.message: str | None = None
        self.message_timer: float = 0.0

        # Opções de seletores
        vol_options = [
            (0.0, "0%"),
            (0.2, "20%"),
            (0.4, "40%"),
            (0.6, "60%"),
            (0.8, "80%"),
            (1.0, "100%"),
        ]

        speed_options = [
            (0.5, "0.5x"),
            (1.0, "1.0x (Padrão)"),
            (1.5, "1.5x"),
            (2.0, "2.0x"),
        ]

        fps_options = [
            (15, "15 FPS"),
            (30, "30 FPS (Padrão)"),
            (60, "60 FPS"),
            (120, "120 FPS"),
        ]

        res_options = [
            ([1024, 768], "1024 x 768"),
        ]

        hints_options = [
            (True, t("settings.enabled")),
            (False, t("settings.disabled")),
        ]

        # Posicionamento
        left_x = WINDOW_WIDTH // 2 - 250
        start_y = 150
        row_h = 60
        sel_w, sel_h = 240, 40

        self.sel_volume = Selector(
            rect=(left_x + 240, start_y, sel_w, sel_h),
            options=vol_options,
        )
        self.sel_speed = Selector(
            rect=(left_x + 240, start_y + row_h, sel_w, sel_h),
            options=speed_options,
        )
        self.sel_fps = Selector(
            rect=(left_x + 240, start_y + row_h * 2, sel_w, sel_h),
            options=fps_options,
        )
        self.sel_res = Selector(
            rect=(left_x + 240, start_y + row_h * 3, sel_w, sel_h),
            options=res_options,
        )
        self.sel_hints = Selector(
            rect=(left_x + 240, start_y + row_h * 4, sel_w, sel_h),
            options=hints_options,
        )

        self._load_values_into_ui()

        # Botões
        btn_w, btn_h = 180, 44
        btn_y = start_y + row_h * 5 + 20

        self.btn_save = Button(
            rect=(WINDOW_WIDTH // 2 - btn_w * 1.5 - 15, btn_y, btn_w, btn_h),
            text=t("common.save"),
            callback=self._save_settings,
        )
        self.btn_reset = Button(
            rect=(WINDOW_WIDTH // 2 - btn_w // 2, btn_y, btn_w, btn_h),
            text=t("common.reset"),
            callback=self._reset_defaults,
        )
        self.btn_back = Button(
            rect=(WINDOW_WIDTH // 2 + btn_w * 0.5 + 15, btn_y, btn_w, btn_h),
            text=t("common.back"),
            callback=self._go_back,
        )

    def _load_values_into_ui(self) -> None:
        """Carrega os valores do objeto `Settings` para a UI."""
        self.sel_volume.value = self.settings.get("volume", 0.8)
        self.sel_speed.value = self.settings.get("animation_speed", 1.0)
        self.sel_fps.value = self.settings.get("fps", 30)
        self.sel_res.value = self.settings.get("resolution", [1024, 768])
        self.sel_hints.value = self.settings.get("visual_hints", True)

    def _save_settings(self) -> None:
        self.audio.play("click")
        self.settings.set("volume", self.sel_volume.value)
        self.settings.set("animation_speed", self.sel_speed.value)
        self.settings.set("fps", self.sel_fps.value)
        self.settings.set("resolution", self.sel_res.value)
        self.settings.set("visual_hints", self.sel_hints.value)
        self.settings.save()

        # Atualizar volume no AudioManager
        self.audio.volume = float(self.sel_volume.value)

        self._show_message(t("settings.saved"))

    def _reset_defaults(self) -> None:
        self.audio.play("click")
        self.settings.reset()
        self._load_values_into_ui()
        self.settings.save()
        self.audio.volume = float(self.sel_volume.value)
        self._show_message("Configurações restauradas para o padrão.")

    def _go_back(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            self.scene_manager.pop()

    def _show_message(self, msg: str, duration: float = 2.5) -> None:
        self.message = msg
        self.message_timer = duration

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Esc volta; demais eventos vão aos seletores e botões."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._go_back()
            return

        if self.sel_volume.handle_event(event):
            return
        if self.sel_speed.handle_event(event):
            return
        if self.sel_fps.handle_event(event):
            return
        if self.sel_res.handle_event(event):
            return
        if self.sel_hints.handle_event(event):
            return

        if self.btn_save.handle_event(event):
            return
        if self.btn_reset.handle_event(event):
            return
        if self.btn_back.handle_event(event):
            return

    def update(self, dt: float) -> None:
        """Decrementa o temporizador da mensagem e atualiza os hovers."""
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None

        pos = pygame.mouse.get_pos()
        self.sel_volume.update_hover(pos)
        self.sel_speed.update_hover(pos)
        self.sel_fps.update_hover(pos)
        self.sel_res.update_hover(pos)
        self.sel_hints.update_hover(pos)
        self.btn_save.update_hover(pos)
        self.btn_reset.update_hover(pos)
        self.btn_back.update_hover(pos)

    def draw(self, surface: pygame.Surface) -> None:
        """Desenha título, linhas de configuração, botões e mensagem (se houver)."""
        surface.fill(COLOR_BG)

        # Título
        title_surf = self._title_font.render(t("settings.title"), True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 70))
        surface.blit(title_surf, title_rect)

        # Rótulos e Seletores
        left_x = WINDOW_WIDTH // 2 - 250

        rows = [
            (t("settings.volume"), self.sel_volume),
            (t("settings.anim_speed"), self.sel_speed),
            (t("settings.fps"), self.sel_fps),
            (t("settings.resolution"), self.sel_res),
            (t("settings.visual_hints"), self.sel_hints),
        ]

        for label_text, selector in rows:
            lbl_surf = self._label_font.render(label_text, True, (240, 240, 240))
            surface.blit(lbl_surf, (left_x, selector.rect.y + 6))
            selector.draw(surface)

        # Botões
        self.btn_save.draw(surface)
        self.btn_reset.draw(surface)
        self.btn_back.draw(surface)

        # Mensagem temporária
        if self.message:
            msg_surf = self._msg_font.render(self.message, True, (80, 220, 80))
            msg_rect = msg_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 35))
            surface.blit(msg_surf, msg_rect)
