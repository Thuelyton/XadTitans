"""Testes de áudio (audio.py) — degradação graciosa headless.

Sem mixer disponível, ``AudioManager`` fica desativado e ``play()``
nunca lança exceção.  Com driver dummy o mixer pode até iniciar:
os dois caminhos são válidos, o teste só garante robustez.
"""

from __future__ import annotations

import pygame

from xadtitans.audio import AudioManager


def test_audio_manager_nunca_quebra() -> None:
    """Constrói e toca todos os sons sem exceção (com ou sem mixer)."""
    manager = AudioManager()
    for name in ("click", "move", "capture", "check", "game_over"):
        manager.play(name)  # não deve lançar
    manager.play("som-inexistente")  # também não deve lançar
    assert isinstance(manager.enabled, bool)


def test_volume_mestre_limitado() -> None:
    manager = AudioManager()
    manager.set_master_volume(2.0)
    assert manager._master == 1.0
    manager.set_master_volume(-1.0)
    assert manager._master == 0.0
    manager.set_master_volume(0.5)
    assert manager._master == 0.5


def test_pygame_quit_nao_era_necessario() -> None:
    """Smoke: pygame importável no processo de teste."""
    assert pygame.version.vernum >= (2, 6)
