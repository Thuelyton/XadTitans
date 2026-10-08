"""Testes da Fase 7.2 — empacotamento (ícone, versão, build script).

Cobrem os insumos do build sem executar o PyInstaller:
  - ícone ICO multiresolução (gerado de sprite próprio);
  - `xadtitans.__version__` como única fonte de verdade (1.0.0);
  - version-file determinístico e argumentos do `tools/build_exe.py`;
  - guarda de stdout/stderr do `main.py` para o modo `--windowed`.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from PIL import Image

import xadtitans

ROOT = Path(__file__).resolve().parent.parent
_ICO_SIZES = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}


def _load(path: Path, name: str):
    """Importa um módulo de arquivo (tools/*.py, main.py) para teste."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestIcone:
    def test_icone_existe_e_e_multiresolucao(self) -> None:
        ico = ROOT / "assets" / "icons" / "xadtitans.ico"
        assert ico.exists(), "ícone ausente — rode tools/gen_icon.py"
        with Image.open(ico) as img:
            assert img.format == "ICO"
            sizes = set(img.ico.sizes())
        assert _ICO_SIZES <= sizes, f"resoluções ausentes: {_ICO_SIZES - sizes}"

    def test_icone_deriva_de_sprite_proprio(self) -> None:
        """Origem é o sprite CC0 do rei branco (sem arte de terceiros)."""
        assert (ROOT / "assets" / "pieces" / "white_king.png").exists()
        assert (ROOT / "tools" / "gen_icon.py").exists()


class TestVersao:
    def test_versao_centralizada_1_0_0(self) -> None:
        assert xadtitans.__version__ == "1.0.0"

    def test_menu_exibe_versao_da_fonte_unica(self) -> None:
        from xadtitans.ui.scenes.menu_scene import version_label

        assert version_label() == f"v{xadtitans.__version__}" == "v1.0.0"

    def test_menu_renderiza_sem_quebrar(self) -> None:
        from xadtitans.ui.scenes.menu_scene import MenuScene

        pygame.init()
        surf = pygame.display.set_mode((1024, 768))
        MenuScene().draw(surf)  # não deve lançar (versão incluída)


class TestBuildScript:
    def test_versao_tuple(self) -> None:
        build = _load(ROOT / "tools" / "build_exe.py", "build_exe_test")
        assert build.version_tuple("1.0.0") == (1, 0, 0)

    def test_version_file_deterministico(self) -> None:
        build = _load(ROOT / "tools" / "build_exe.py", "build_exe_test")
        content = build.version_file_content(xadtitans.__version__)
        assert "filevers=(1, 0, 0, 0)" in content
        assert "prodvers=(1, 0, 0, 0)" in content
        assert f"OriginalFilename', '{build.APP_NAME}.exe'" in content
        assert "ProductVersion', '1.0.0'" in content
        # StringTable canônica (sem ela a string table do PE é malformada):
        assert "StringTable(" in content and "'040904b0'" in content
        # Determinístico: mesma versão → mesmo conteúdo.
        assert content == build.version_file_content("1.0.0")

    def test_build_args_obrigatorios(self) -> None:
        build = _load(ROOT / "tools" / "build_exe.py", "build_exe_test")
        args = build.build_args(Path("v.txt"))
        joined = " ".join(args)
        assert str(build.PYINSTALLER) in args  # .venv, não PATH global
        assert ".venv" in str(build.PYINSTALLER)
        assert "--onedir" in args and "--onefile" not in args
        assert "--windowed" in args
        assert "--noupx" in args
        assert "--paths" in args and str(build.ROOT / "src") in args
        assert f"{build.ROOT / 'assets'};assets" in args
        assert "--icon" in args and "xadtitans.ico" in joined
        assert "--exclude-module" in args
        assert args[-1] == str(build.ROOT / "main.py")  # ponto de entrada

    def test_assets_obrigatorios_incluem_visao_preta(self) -> None:
        build = _load(ROOT / "tools" / "build_exe.py", "build_exe_test")
        assert "assets/board/board_perspective_black.png" in build.REQUIRED_ASSETS
        assert "assets/board/squares_black.json" in build.REQUIRED_ASSETS


class TestStreamsWindowed:
    def test_ensure_streams_repara_stderr_none(self) -> None:
        """Modo --windowed do PyInstaller deixa sys.stderr = None.

        A guarda do main.py deve substituir por um stream válido antes
        de qualquer print/StreamHandler (erro fatal, logger).
        """
        main_mod = _load(ROOT / "main.py", "main_entry_test")
        saved_err, saved_out = sys.stderr, sys.stdout
        try:
            sys.stderr = None  # type: ignore[assignment]
            main_mod._ensure_streams()
            assert sys.stderr is not None
            print("ok", file=sys.stderr)  # não pode lançar
        finally:
            sys.stderr = saved_err
            sys.stdout = saved_out

    def test_ensure_streams_preserva_streams_normais(self) -> None:
        main_mod = _load(ROOT / "main.py", "main_entry_test")
        before_err, before_out = sys.stderr, sys.stdout
        main_mod._ensure_streams()
        assert sys.stderr is before_err and sys.stdout is before_out
