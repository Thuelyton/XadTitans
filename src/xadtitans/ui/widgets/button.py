"""Widget de botão reutilizável para a interface do XadTitans.

Fornece interação por clique, navegação visual (hover, ativo, desabilitado)
e renderização de texto centralizado com fontes personalizadas.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame


class Button:
    """Botão interativo para menus e telas do XadTitans."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        text: str,
        callback: Callable[[], None] | None = None,
        *,
        enabled: bool = True,
        visible: bool = True,
        font: pygame.font.Font | None = None,
        bg_color: tuple[int, int, int] = (45, 45, 45),
        hover_bg_color: tuple[int, int, int] = (70, 70, 70),
        disabled_bg_color: tuple[int, int, int] = (30, 30, 30),
        text_color: tuple[int, int, int] = (240, 240, 240),
        hover_text_color: tuple[int, int, int] = (255, 215, 0),
        disabled_text_color: tuple[int, int, int] = (100, 100, 100),
        border_color: tuple[int, int, int] = (80, 80, 80),
        hover_border_color: tuple[int, int, int] = (255, 215, 0),
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.enabled = enabled
        self.visible = visible
        self.font = font or pygame.font.SysFont("arial", 20, bold=True)
        self.is_hovered = False

        self.bg_color = bg_color
        self.hover_bg_color = hover_bg_color
        self.disabled_bg_color = disabled_bg_color
        self.text_color = text_color
        self.hover_text_color = hover_text_color
        self.disabled_text_color = disabled_text_color
        self.border_color = border_color
        self.hover_border_color = hover_border_color

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Processa eventos de mouse. Retorna True se o botão foi clicado."""
        if not self.visible or not self.enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos) and self.callback is not None:
            self.callback()
            return True
        return False

    def update_hover(self, pos: tuple[int, int]) -> None:
        """Atualiza estado de hover a partir da posição do mouse."""
        if self.visible and self.enabled:
            self.is_hovered = self.rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface) -> None:
        """Renderiza o botão na superfície informada."""
        if not self.visible:
            return

        if not self.enabled:
            bg = self.disabled_bg_color
            border = self.disabled_bg_color
            txt_col = self.disabled_text_color
        elif self.is_hovered:
            bg = self.hover_bg_color
            border = self.hover_border_color
            txt_col = self.hover_text_color
        else:
            bg = self.bg_color
            border = self.border_color
            txt_col = self.text_color

        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)

        rendered_text = self.font.render(self.text, True, txt_col)
        text_rect = rendered_text.get_rect(center=self.rect.center)
        surface.blit(rendered_text, text_rect)
