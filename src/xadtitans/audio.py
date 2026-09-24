"""Sons do jogo (pygame.mixer) com degradação graciosa.

Carrega os WAVs sintetizados em ``assets/sounds/`` (ver
``tools/gen_sounds.py``).  Se o mixer não estiver disponível
(por exemplo em teste headless sem áudio), ``play()`` vira
no-op — o jogo nunca quebra por causa de som.
"""

from __future__ import annotations

import pygame

from xadtitans.utils.resources import resource_path

# Nome do som → (arquivo, volume relativo)
_SOUNDS: dict[str, tuple[str, float]] = {
    "click": ("click.wav", 0.50),
    "move": ("move.wav", 0.85),
    "capture": ("capture.wav", 0.95),
    "check": ("check.wav", 0.70),
    "game_over": ("game_over.wav", 0.80),
}


class AudioManager:
    """Toca os efeitos sonoros do jogo."""

    def __init__(self) -> None:
        self.enabled = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._master = 1.0
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            return  # sem áudio disponível: fica desativado

        for name, (filename, _vol) in _SOUNDS.items():
            path = resource_path("assets/sounds") / filename
            if not path.is_file():
                continue  # asset ausente: som individual desativado
            try:
                self._sounds[name] = pygame.mixer.Sound(str(path))
            except pygame.error:
                continue
        self.enabled = bool(self._sounds)

    def play(self, name: str) -> None:
        """Toca um som (se disponível). Nunca lança exceção."""
        if not self.enabled:
            return
        sound = self._sounds.get(name)
        if sound is None:
            return
        _, rel = _SOUNDS[name]
        sound.set_volume(rel * self._master)
        sound.play()

    def set_master_volume(self, value: float) -> None:
        """Volume geral 0.0–1.0 (0 silencia tudo)."""
        self._master = max(0.0, min(1.0, value))
