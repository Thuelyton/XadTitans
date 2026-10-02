"""Widget de seletor de opções para o XadTitans.

Permite alternar entre opções pré-definidas usando botões laterais ou clique direto.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pygame


class Selector:
    """Seletor de opções com botões de navegação esquerda/direita."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        options: list[tuple[Any, str]],
        current_index: int = 0,
        on_change: Callable[[Any], None] | None = None,
        *,
        enabled: bool = True,
        font: pygame.font.Font | None = None,
    ) -> None:
        """Cria o seletor; ``options`` são pares (valor, rótulo) exibidos."""
        self.rect = pygame.Rect(rect)
        self.options = options
        self._index = min(max(0, current_index), max(0, len(options) - 1))
        self.on_change = on_change
        self.enabled = enabled
        self.font = font or pygame.font.SysFont("arial", 18, bold=True)

        btn_w = 36
        self.left_btn_rect = pygame.Rect(self.rect.x, self.rect.y, btn_w, self.rect.height)
        self.right_btn_rect = pygame.Rect(
            self.rect.right - btn_w, self.rect.y, btn_w, self.rect.height
        )
        self.val_rect = pygame.Rect(
            self.rect.x + btn_w + 4,
            self.rect.y,
            self.rect.width - (btn_w * 2 + 8),
            self.rect.height,
        )

        self.hover_left = False
        self.hover_right = False
        self.hover_val = False

    @property
    def value(self) -> Any:
        """Valor da opção selecionada."""
        if 0 <= self._index < len(self.options):
            return self.options[self._index][0]
        return None

    @value.setter
    def value(self, val: Any) -> None:
        """Define a opção selecionada pelo valor."""
        for idx, (v, _) in enumerate(self.options):
            if v == val:
                self._index = idx
                break

    @property
    def current_label(self) -> str:
        """Texto legível da opção selecionada."""
        if 0 <= self._index < len(self.options):
            return self.options[self._index][1]
        return ""

    def select_next(self) -> None:
        """Avança para a próxima opção."""
        if not self.enabled or not self.options:
            return
        self._index = (self._index + 1) % len(self.options)
        if self.on_change is not None:
            self.on_change(self.value)

    def select_prev(self) -> None:
        """Volta para a opção anterior."""
        if not self.enabled or not self.options:
            return
        self._index = (self._index - 1) % len(self.options)
        if self.on_change is not None:
            self.on_change(self.value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Processa eventos do seletor."""
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hover_left = self.left_btn_rect.collidepoint(event.pos)
            self.hover_right = self.right_btn_rect.collidepoint(event.pos)
            self.hover_val = self.val_rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_btn_rect.collidepoint(event.pos):
                self.select_prev()
                return True
            if self.right_btn_rect.collidepoint(event.pos):
                self.select_next()
                return True
            if self.val_rect.collidepoint(event.pos):
                self.select_next()
                return True
        return False

    def update_hover(self, pos: tuple[int, int]) -> None:
        """Atualiza o estado de hover dos botões."""
        if self.enabled:
            self.hover_left = self.left_btn_rect.collidepoint(pos)
            self.hover_right = self.right_btn_rect.collidepoint(pos)
            self.hover_val = self.val_rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface) -> None:
        """Renderiza o seletor."""
        bg_col = (45, 45, 45) if self.enabled else (30, 30, 30)
        border_col = (80, 80, 80) if self.enabled else (50, 50, 50)
        txt_col = (240, 240, 240) if self.enabled else (100, 100, 100)

        # Caixa de valor central
        val_bg = (60, 60, 60) if (self.hover_val and self.enabled) else bg_col
        val_border = (255, 215, 0) if (self.hover_val and self.enabled) else border_col
        pygame.draw.rect(surface, val_bg, self.val_rect, border_radius=4)
        pygame.draw.rect(surface, val_border, self.val_rect, 1, border_radius=4)

        v_text = self.font.render(self.current_label, True, txt_col)
        surface.blit(v_text, v_text.get_rect(center=self.val_rect.center))

        # Botão esquerdo (<)
        l_bg = (70, 70, 70) if (self.hover_left and self.enabled) else bg_col
        l_txt = (255, 215, 0) if (self.hover_left and self.enabled) else txt_col
        l_border = (255, 215, 0) if (self.hover_left and self.enabled) else border_col
        pygame.draw.rect(surface, l_bg, self.left_btn_rect, border_radius=4)
        pygame.draw.rect(surface, l_border, self.left_btn_rect, 1, border_radius=4)
        l_arrow = self.font.render("<", True, l_txt)
        surface.blit(l_arrow, l_arrow.get_rect(center=self.left_btn_rect.center))

        # Botão direito (>)
        r_bg = (70, 70, 70) if (self.hover_right and self.enabled) else bg_col
        r_txt = (255, 215, 0) if (self.hover_right and self.enabled) else txt_col
        r_border = (255, 215, 0) if (self.hover_right and self.enabled) else border_col
        pygame.draw.rect(surface, r_bg, self.right_btn_rect, border_radius=4)
        pygame.draw.rect(surface, r_border, self.right_btn_rect, 1, border_radius=4)
        r_arrow = self.font.render(">", True, r_txt)
        surface.blit(r_arrow, r_arrow.get_rect(center=self.right_btn_rect.center))
