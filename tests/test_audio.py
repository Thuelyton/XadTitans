"""Testes de áudio (audio.py) — degradação graciosa headless.

Sem mixer disponível, ``AudioManager`` fica desativado e ``play()``
nunca lança exceção.  Com driver dummy o mixer pode até iniciar:
os dois caminhos são válidos, o teste só garante robustez.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

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


def test_volume_propriedade_espelha_mestre() -> None:
    """Regressão Fase 6.6: ``audio.volume = x`` (usado por App e
    SettingsScene) deve ajustar o volume mestre de verdade.

    Antes da correção era um atributo órfão: a configuração de volume
    não tinha efeito e o "volume 0" não silenciava nada.
    """
    manager = AudioManager()
    manager.volume = 0.0
    assert manager.volume == 0.0
    assert manager._master == 0.0
    manager.volume = 0.3
    assert manager.volume == 0.3
    assert manager._master == 0.3
    # Clamp pelo property também
    manager.volume = 1.7
    assert manager._master == 1.0
    manager.volume = -0.5
    assert manager._master == 0.0


def test_volume_zero_zera_play() -> None:
    """Com volume 0, ``play()`` define volume 0.0 no som (mudo real)."""
    manager = AudioManager()

    class _FakeSound:
        def __init__(self) -> None:
            self.volumes: list[float] = []

        def set_volume(self, value: float) -> None:
            self.volumes.append(value)

        def play(self) -> None:
            pass

    fake = _FakeSound()
    manager._sounds = {"click": fake}
    manager.enabled = True
    manager.volume = 0.0
    manager.play("click")
    assert fake.volumes == [0.0], "volume 0 não silenciou o som"
    manager.volume = 1.0
    manager.play("click")
    assert fake.volumes[-1] > 0, "volume 1.0 não tocou o som"


def test_settings_volume_atinge_master_via_app() -> None:
    """App lê ``volume`` das settings e aplica no AudioManager."""
    from xadtitans.storage.settings import Settings

    settings = Settings()
    settings.set("volume", 0)
    settings.save()

    from xadtitans.app import App

    app = App()
    try:
        assert float(app.audio.volume) == 0.0
        assert app.audio._master == 0.0, \
            "volume 0 das settings não silenciou o mestre"
    finally:
        app.scene_manager.clear()
        settings.set("volume", 0.8)
        settings.save()


def test_pygame_quit_nao_era_necessario() -> None:
    """Smoke: pygame importável no processo de teste."""
    assert pygame.version.vernum >= (2, 6)
