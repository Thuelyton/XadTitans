"""Cena de Configuração de Nova Partida do XadTitans.

Permite escolher:
  - Modo de jogo (Humano vs Humano, Humano vs IA, IA vs IA)
  - Cor do jogador humano (Brancas, Pretas, Aleatório) quando aplicável
  - Nível de dificuldade da IA (Iniciante, Fácil, Médio, Difícil)
  - Configuração visual de relógio (preparatório para etapas futuras)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import chess
import pygame

from xadtitans.audio import AudioManager
from xadtitans.config import COLOR_BG, WINDOW_WIDTH
from xadtitans.core.types import GameMode, Level
from xadtitans.i18n import t
from xadtitans.ui.widgets.button import Button
from xadtitans.ui.widgets.selector import Selector

if TYPE_CHECKING:
    from xadtitans.ui.scene_manager import SceneManager


class NewGameScene:
    """Tela para configurar e iniciar uma nova partida."""

    def __init__(
        self,
        scene_manager: SceneManager | None = None,
        audio: AudioManager | None = None,
    ) -> None:
        self.scene_manager = scene_manager
        self.audio = audio or AudioManager()

        self._title_font = pygame.font.SysFont("arial", 38, bold=True)
        self._label_font = pygame.font.SysFont("arial", 20, bold=True)

        # ── Opções dos Seletores ──────────────────────────────
        mode_options = [
            (GameMode.HUMAN_VS_HUMAN, t("mode.human_vs_human")),
            (GameMode.HUMAN_VS_AI, t("mode.human_vs_ai")),
            (GameMode.AI_VS_AI, t("mode.ai_vs_ai")),
        ]

        side_options = [
            ("white", t("color.white")),
            ("black", t("color.black")),
            ("random", t("color.random")),
        ]

        level_options = [
            (Level.INICIANTE, t("level.iniciante")),
            (Level.FACIL, t("level.facil")),
            (Level.MEDIO, t("level.medio")),
            (Level.DIFICIL, t("level.dificil")),
        ]

        clock_options = [
            ("none", t("new_game.clock_none")),
            (3, t("new_game.clock_3")),
            (5, t("new_game.clock_5")),
            (10, t("new_game.clock_10")),
            (15, t("new_game.clock_15")),
        ]

        increment_options = [
            (0, t("new_game.inc_none")),
            (2, t("new_game.inc_2")),
            (3, t("new_game.inc_3")),
            (5, t("new_game.inc_5")),
            (10, t("new_game.inc_10")),
        ]

        # ── Posicionamento dos controles ──────────────────────
        left_x = WINDOW_WIDTH // 2 - 220
        start_y = 150
        row_h = 55
        sel_w, sel_h = 240, 35

        self.sel_mode = Selector(
            rect=(left_x + 200, start_y, sel_w, sel_h),
            options=mode_options,
            current_index=1,  # Padrão: Humano vs IA
            on_change=self._on_mode_change,
        )

        self.sel_side = Selector(
            rect=(left_x + 200, start_y + row_h, sel_w, sel_h),
            options=side_options,
            current_index=0,  # Padrão: Brancas
        )

        self.sel_level = Selector(
            rect=(left_x + 200, start_y + row_h * 2, sel_w, sel_h),
            options=level_options,
            current_index=2,  # Padrão: Médio
        )

        self.sel_clock = Selector(
            rect=(left_x + 200, start_y + row_h * 3, sel_w, sel_h),
            options=clock_options,
            current_index=0,
            on_change=self._on_clock_change,
        )

        self.sel_inc = Selector(
            rect=(left_x + 200, start_y + row_h * 4, sel_w, sel_h),
            options=increment_options,
            current_index=0,
        )

        # Botões Iniciar e Voltar
        btn_w, btn_h = 200, 48
        btn_y = start_y + row_h * 5 + 10
        self.btn_start = Button(
            rect=(WINDOW_WIDTH // 2 - btn_w - 15, btn_y, btn_w, btn_h),
            text=t("new_game.start"),
            callback=self._start_game,
        )
        self.btn_back = Button(
            rect=(WINDOW_WIDTH // 2 + 15, btn_y, btn_w, btn_h),
            text=t("common.back"),
            callback=self._go_back,
        )

        self._update_visibility()

    def _on_mode_change(self, mode: GameMode) -> None:
        self._update_visibility()

    def _on_clock_change(self, clock_val: str | int) -> None:
        self._update_visibility()

    def _update_visibility(self) -> None:
        mode = self.sel_mode.value
        if mode == GameMode.HUMAN_VS_HUMAN:
            self.sel_side.enabled = False
            self.sel_level.enabled = False
        elif mode == GameMode.HUMAN_VS_AI:
            self.sel_side.enabled = True
            self.sel_level.enabled = True
        else:  # AI_VS_AI
            self.sel_side.enabled = False
            self.sel_level.enabled = True

        clock_val = self.sel_clock.value
        if clock_val == "none":
            self.sel_inc.enabled = False
            self.sel_inc.value = 0
        else:
            self.sel_inc.enabled = True

    def _start_game(self) -> None:
        self.audio.play("click")
        mode: GameMode = self.sel_mode.value
        level: Level = self.sel_level.value
        side_choice = self.sel_side.value
        clock_val = self.sel_clock.value
        clock_min = 0 if clock_val == "none" else int(clock_val)
        increment_sec = int(self.sel_inc.value)

        ai_color: chess.Color | None = None
        if mode == GameMode.HUMAN_VS_AI:
            if side_choice == "random":
                human_color = random.choice([chess.WHITE, chess.BLACK])
            elif side_choice == "black":
                human_color = chess.BLACK
            else:
                human_color = chess.WHITE
            ai_color = chess.BLACK if human_color == chess.WHITE else chess.WHITE

        if self.scene_manager is not None:
            from xadtitans.ui.scenes.game_scene import GameScene

            game_scene = GameScene(
                audio=self.audio,
                game_mode=mode,
                ai_color=ai_color,
                ai_level=level,
                clock_minutes=clock_min,
                clock_increment=increment_sec,
            )
            # Nova partida: invalida o autosave anterior logo de início
            # (o Continuar nunca reabre a partida antiga).
            game_scene._autosave()
            # Substitui a tela de Nova Partida pela GameScene
            self.scene_manager.switch(game_scene)

    def _go_back(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            self.scene_manager.pop()

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._start_game()
                return

        if self.sel_mode.handle_event(event):
            return
        if self.sel_side.handle_event(event):
            return
        if self.sel_level.handle_event(event):
            return
        if self.sel_clock.handle_event(event):
            return
        if self.sel_inc.handle_event(event):
            return

        if self.btn_start.handle_event(event):
            return
        if self.btn_back.handle_event(event):
            return

    def update(self, dt: float) -> None:
        pos = pygame.mouse.get_pos()
        self.sel_mode.update_hover(pos)
        self.sel_side.update_hover(pos)
        self.sel_level.update_hover(pos)
        self.sel_clock.update_hover(pos)
        self.sel_inc.update_hover(pos)
        self.btn_start.update_hover(pos)
        self.btn_back.update_hover(pos)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)

        # Título
        title_surf = self._title_font.render(t("new_game.title"), True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 80))
        surface.blit(title_surf, title_rect)

        # Rótulos e Seletores
        left_x = WINDOW_WIDTH // 2 - 220
        start_y = 155
        row_h = 55

        rows = [
            (t("new_game.mode"), self.sel_mode),
            (t("new_game.side"), self.sel_side),
            (t("new_game.level"), self.sel_level),
            (t("new_game.clock"), self.sel_clock),
            (t("new_game.increment"), self.sel_inc),
        ]

        for idx, (label_text, selector) in enumerate(rows):
            y = start_y + idx * row_h
            lbl_col = (240, 240, 240) if selector.enabled else (100, 100, 100)
            lbl_surf = self._label_font.render(label_text, True, lbl_col)
            surface.blit(lbl_surf, (left_x, y + 6))
            selector.draw(surface)

        # Botões
        self.btn_start.draw(surface)
        self.btn_back.draw(surface)
