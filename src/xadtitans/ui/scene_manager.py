"""Gerenciador de cenas do XadTitans.

Gerencia o empilhamento (stack) e a transição entre telas do jogo,
garantindo chamadas seguras ao ciclo de vida das cenas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pygame


class SceneManager:
    """Gerenciador de cenas baseado em pilha (stack)."""

    def __init__(self) -> None:
        self._stack: list[Any] = []

    @property
    def current(self) -> Any | None:
        """Retorna a cena no topo da pilha, ou None se estiver vazia."""
        return self._stack[-1] if self._stack else None

    @property
    def count(self) -> int:
        """Quantidade de cenas na pilha."""
        return len(self._stack)

    def push(self, scene: Any) -> None:
        """Empilha uma nova cena e aciona hooks de ciclo de vida."""
        prev = self.current
        if prev is not None:
            self._call_lifecycle(prev, "on_pause")

        self._stack.append(scene)
        self._call_lifecycle(scene, "on_enter")

    def pop(self) -> Any | None:
        """Desempilha a cena do topo e aciona hooks de ciclo de vida."""
        if not self._stack:
            return None

        old_scene = self._stack.pop()
        self._call_lifecycle(old_scene, "on_exit")
        self._call_lifecycle(old_scene, "cleanup")

        new_current = self.current
        if new_current is not None:
            self._call_lifecycle(new_current, "on_resume")

        return old_scene

    def switch(self, scene: Any) -> None:
        """Substitui a cena atual no topo da pilha por uma nova cena."""
        if self._stack:
            old_scene = self._stack.pop()
            self._call_lifecycle(old_scene, "on_exit")
            self._call_lifecycle(old_scene, "cleanup")

        self._stack.append(scene)
        self._call_lifecycle(scene, "on_enter")

    def clear(self) -> None:
        """Desempilha todas as cenas executando a limpeza de cada uma."""
        while self._stack:
            scene = self._stack.pop()
            self._call_lifecycle(scene, "on_exit")
            self._call_lifecycle(scene, "cleanup")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Encaminha eventos para a cena ativa no topo da pilha."""
        scene = self.current
        if scene is not None and hasattr(scene, "handle_event"):
            scene.handle_event(event)

    def update(self, dt: float) -> None:
        """Atualiza a lógica da cena ativa no topo da pilha."""
        scene = self.current
        if scene is not None and hasattr(scene, "update"):
            scene.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Renderiza a cena ativa no topo da pilha."""
        scene = self.current
        if scene is not None and hasattr(scene, "draw"):
            scene.draw(surface)

    def _call_lifecycle(self, scene: Any, method_name: str) -> None:
        """Chama um método de ciclo de vida de forma segura se ele existir."""
        method = getattr(scene, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:  # noqa: BLE001, S110
                pass
