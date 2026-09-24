"""Testes para SceneManager, GameMode e i18n da Etapa 5.1."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock

import pygame

from xadtitans.core.types import GameMode
from xadtitans.i18n import t
from xadtitans.ui.scene_manager import SceneManager

_surf: pygame.Surface | None = None


def _screen() -> pygame.Surface:
    global _surf
    if _surf is None:
        pygame.init()
        _surf = pygame.display.set_mode((1024, 768))
    return _surf


class MockScene:
    """Cena fictícia para testar ciclo de vida."""

    def __init__(self, name: str = "mock") -> None:
        self.name = name
        self.entered = False
        self.exited = False
        self.cleaned = False
        self.paused = False
        self.resumed = False
        self.updated = False
        self.drawn = False
        self.event_handled = False

    def on_enter(self) -> None:
        self.entered = True

    def on_exit(self) -> None:
        self.exited = True

    def cleanup(self) -> None:
        self.cleaned = True

    def on_pause(self) -> None:
        self.paused = True

    def on_resume(self) -> None:
        self.resumed = True

    def handle_event(self, event: object) -> None:
        self.event_handled = True

    def update(self, dt: float) -> None:
        self.updated = True

    def draw(self, surface: object) -> None:
        self.drawn = True


class TestGameMode:
    def test_gamemode_enum_values(self) -> None:
        assert GameMode.HUMAN_VS_HUMAN is not None
        assert GameMode.HUMAN_VS_AI is not None
        assert GameMode.AI_VS_AI is not None
        assert len(GameMode) == 3


class TestI18n:
    def test_traducao_chaves_existentes(self) -> None:
        assert t("mode.human_vs_human") == "2 Jogadores (Local)"
        assert t("mode.human_vs_ai") == "Jogador vs IA"
        assert t("mode.ai_vs_ai") == "IA vs IA"
        assert t("level.iniciante") == "Iniciante"

    def test_fallback_chave_inexistente(self) -> None:
        assert t("chave.inexistente") == "chave.inexistente"
        assert t("chave.inexistente", default="Padrão") == "Padrão"

    def test_formatacao_com_kwargs(self) -> None:
        result = t("chave.format", default="Olá {nome}!", nome="XadTitans")
        assert result == "Olá XadTitans!"


class TestSceneManager:
    def test_inicializacao_vazia(self) -> None:
        sm = SceneManager()
        assert sm.current is None
        assert sm.count == 0

    def test_push_pop(self) -> None:
        sm = SceneManager()
        s1 = MockScene("s1")
        sm.push(s1)

        assert sm.current is s1
        assert sm.count == 1
        assert s1.entered is True

        popped = sm.pop()
        assert popped is s1
        assert sm.current is None
        assert sm.count == 0
        assert s1.exited is True
        assert s1.cleaned is True

    def test_push_pausa_anterior_e_resume_ao_pop(self) -> None:
        sm = SceneManager()
        s1 = MockScene("s1")
        s2 = MockScene("s2")

        sm.push(s1)
        sm.push(s2)

        assert s1.paused is True
        assert s2.entered is True
        assert sm.current is s2

        sm.pop()
        assert sm.current is s1
        assert s1.resumed is True

    def test_switch(self) -> None:
        sm = SceneManager()
        s1 = MockScene("s1")
        s2 = MockScene("s2")

        sm.push(s1)
        sm.switch(s2)

        assert sm.current is s2
        assert sm.count == 1
        assert s1.exited is True
        assert s1.cleaned is True
        assert s2.entered is True

    def test_clear(self) -> None:
        sm = SceneManager()
        s1 = MockScene("s1")
        s2 = MockScene("s2")

        sm.push(s1)
        sm.push(s2)
        sm.clear()

        assert sm.current is None
        assert sm.count == 0
        assert s1.cleaned is True
        assert s2.cleaned is True

    def test_comportamento_pilha_vazia_nao_lanca_excecao(self) -> None:
        sm = SceneManager()
        assert sm.pop() is None
        # Não deve estourar erro ao chamar update/draw/handle_event em pilha vazia
        sm.update(0.016)
        sm.draw(MagicMock())
        sm.handle_event(MagicMock())

    def test_delegacao_eventos_update_draw(self) -> None:
        sm = SceneManager()
        s1 = MockScene("s1")
        sm.push(s1)

        sm.handle_event(MagicMock())
        sm.update(0.016)
        sm.draw(MagicMock())

        assert s1.event_handled is True
        assert s1.updated is True
        assert s1.drawn is True

    def test_integracao_com_game_scene(self) -> None:
        """Verifica se GameScene funciona com o SceneManager."""
        from xadtitans.ui.scenes.game_scene import GameScene

        _screen()
        sm = SceneManager()
        scene = GameScene()
        sm.push(scene)

        assert sm.current is scene
        sm.update(0.016)
        assert sm.count == 1
