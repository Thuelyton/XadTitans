"""Cena de Estatísticas do XadTitans.

Exibe estatísticas de vitórias, derrotas e empates:
  - Totais gerais
  - Por modo de jogo (Humano vs Humano, Humano vs IA, IA vs IA)
  - Por nível de dificuldade da IA (Iniciante, Fácil, Médio, Difícil)

Lê os dados utilizando a API de `storage.stats.Stats`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from xadtitans.audio import AudioManager
from xadtitans.config import COLOR_BG, WINDOW_HEIGHT, WINDOW_WIDTH
from xadtitans.i18n import t
from xadtitans.storage.stats import Stats
from xadtitans.ui.widgets.button import Button

if TYPE_CHECKING:
    from xadtitans.ui.scene_manager import SceneManager


class StatsScene:
    """Tela de exibição das estatísticas do jogo."""

    def __init__(
        self,
        scene_manager: SceneManager | None = None,
        audio: AudioManager | None = None,
        stats: Stats | None = None,
    ) -> None:
        """Carrega as estatísticas persistidas e monta o botão Voltar."""
        self.scene_manager = scene_manager
        self.audio = audio or AudioManager()
        self.stats = stats or Stats()
        self.stats.load()

        self._title_font = pygame.font.SysFont("arial", 38, bold=True)
        self._section_font = pygame.font.SysFont("arial", 22, bold=True)
        self._label_font = pygame.font.SysFont("arial", 18)
        self._val_font = pygame.font.SysFont("arial", 18, bold=True)

        btn_w, btn_h = 200, 44
        self.btn_back = Button(
            rect=(WINDOW_WIDTH // 2 - btn_w // 2, WINDOW_HEIGHT - 70, btn_w, btn_h),
            text=t("common.back"),
            callback=self._go_back,
        )

    def _go_back(self) -> None:
        self.audio.play("click")
        if self.scene_manager is not None:
            self.scene_manager.pop()

    # ── interface de cena ─────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        """Esc ou Voltar retornam à tela anterior."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._go_back()
            return

        if self.btn_back.handle_event(event):
            return

    def update(self, dt: float) -> None:
        """Atualiza o hover do botão Voltar (``dt`` é ignorado)."""
        pos = pygame.mouse.get_pos()
        self.btn_back.update_hover(pos)

    def draw(self, surface: pygame.Surface) -> None:
        """Desenha totais, estatísticas por modo/nível e o botão Voltar."""
        surface.fill(COLOR_BG)

        # Título
        title_surf = self._title_font.render(t("stats.title"), True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 60))
        surface.blit(title_surf, title_rect)

        # ── 1. Total Geral ────────────────────────────────────
        y = 120
        self._draw_section_header(surface, t("stats.total"), y)
        y += 35
        tot = self.stats.get_total()
        y = self._draw_bucket_row(surface, "Total", tot, y)

        # ── 2. Por Modo de Jogo ───────────────────────────────
        y += 20
        self._draw_section_header(surface, t("stats.by_mode"), y)
        y += 35

        modes = [
            ("human_vs_human", t("mode.human_vs_human")),
            ("human_vs_ai", t("mode.human_vs_ai")),
            ("ai_vs_ai", t("mode.ai_vs_ai")),
        ]
        for mode_key, mode_label in modes:
            bucket = self.stats.get_mode(mode_key)
            y = self._draw_bucket_row(surface, mode_label, bucket, y)

        # ── 3. Por Nível de Dificuldade ──────────────────────
        y += 20
        self._draw_section_header(surface, t("stats.by_level"), y)
        y += 35

        levels = [
            ("iniciante", t("level.iniciante")),
            ("facil", t("level.facil")),
            ("medio", t("level.medio")),
            ("dificil", t("level.dificil")),
        ]
        for lvl_key, lvl_label in levels:
            bucket = self.stats.get_level(lvl_key)
            y = self._draw_bucket_row(surface, lvl_label, bucket, y)

        # Botão Voltar
        self.btn_back.draw(surface)

    def _draw_section_header(
        self, surface: pygame.Surface, text: str, y: int
    ) -> None:
        header = self._section_font.render(text, True, (255, 215, 0))
        surface.blit(header, (140, y))
        pygame.draw.line(
            surface, (80, 80, 80), (140, y + 28), (WINDOW_WIDTH - 140, y + 28), 1
        )

    def _draw_bucket_row(
        self,
        surface: pygame.Surface,
        label: str,
        bucket: dict[str, int],
        y: int,
    ) -> int:
        lbl_surf = self._label_font.render(label, True, (240, 240, 240))
        surface.blit(lbl_surf, (160, y))

        w = bucket.get("wins", 0)
        l = bucket.get("losses", 0)
        d = bucket.get("draws", 0)

        # Vitórias (verde), Derrotas (vermelho), Empates (cinza)
        txt_w = self._val_font.render(f"V: {w}", True, (80, 220, 80))
        txt_l = self._val_font.render(f"D: {l}", True, (240, 90, 60))
        txt_d = self._val_font.render(f"E: {d}", True, (180, 180, 180))

        surface.blit(txt_w, (520, y))
        surface.blit(txt_l, (620, y))
        surface.blit(txt_d, (720, y))

        return y + 28
