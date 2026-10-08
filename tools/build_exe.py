"""Build reproduzível do XadTitans (PyInstaller, onedir, windowed).

Fase 7.2 — executa o PyInstaller do `.venv` do projeto (nunca um
global do PATH) com argumentos fixos e documentados, gera o
version-file a partir de `xadtitans.__version__` (única fonte de
verdade) e valida o pacote gerado (assets incluídos, inclusive a
visão preta do tabuleiro).

Configuração:
  - Windows x64, onedir (não onefile), windowed (sem console);
  - nome `XadTitans`; `--paths src`; `--add-data assets;assets`;
  - `--icon assets/icons/xadtitans.ico`; version-file de build;
  - sem UPX; testes/.git/.venv/caches nunca entram (só `assets/`
    é adicionado como dado; o resto vem apenas da análise de imports
    de `main.py`).

Artefatos de build (`build/`, `dist/`, o version-file temporário)
estão no `.gitignore` e não são commitados.

Uso:
    .venv/Scripts/python.exe tools/build_exe.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
PYINSTALLER = VENV / "Scripts" / "pyinstaller.exe"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "XadTitans"

# Assets que OBRIGATORIAMENTE precisam existir antes (e depois) do build.
REQUIRED_ASSETS = (
    "assets/board/board_perspective.png",
    "assets/board/squares.json",
    "assets/board/board_perspective_black.png",
    "assets/board/squares_black.json",
    "assets/pieces/white_king.png",
    "assets/pieces/black_king.png",
    "assets/sounds/move.wav",
    "assets/sounds/click.wav",
    "assets/icons/xadtitans.ico",
)


def version_tuple(version: str) -> tuple[int, int, int]:
    """Converte ``X.Y.Z`` em tupla de 3 ints (para o version-file)."""
    parts = version.split(".")
    assert len(parts) == 3, f"versão inesperada: {version!r}"
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def version_file_content(version: str) -> str:
    """Conteúdo determinístico do version-file do PyInstaller.

    Gerado de ``xadtitans.__version__`` — nenhuma versão hardcoded.
    Formato canônico: o PyInstaller desserializa o arquivo com
    ``eval()`` no próprio módulo ``versioninfo`` (kwargs ``ffi=`` /
    ``kids=`` com ``StringFileInfo`` e ``VarFileInfo``). O nome da
    classe fixa é ``FixedFileInfo`` (PyInstaller 6.x — pinado em
    requirements-dev.txt).
    """
    major, minor, patch = version_tuple(version)
    return (
        "# UTF-8\n"
        "# gerado por tools/build_exe.py de xadtitans.__version__ — não editar\n"
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(\n"
        f"    filevers=({major}, {minor}, {patch}, 0),\n"
        f"    prodvers=({major}, {minor}, {patch}, 0),\n"
        "    mask=0x3f,\n"
        "    flags=0x0,\n"
        "    OS=0x40004,\n"
        "    fileType=0x1,\n"
        "    subtype=0x0,\n"
        "    date=(0, 0)),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable(\n"
        "        '040904b0',\n"
        "        [StringStruct('CompanyName', 'XadTitans'),\n"
        f"         StringStruct('FileDescription', 'XadTitans {version}'),\n"
        f"         StringStruct('FileVersion', '{version}.0'),\n"
        f"         StringStruct('InternalName', '{APP_NAME}'),\n"
        f"         StringStruct('OriginalFilename', '{APP_NAME}.exe'),\n"
        "         StringStruct('ProductName', 'XadTitans'),\n"
        f"         StringStruct('ProductVersion', '{version}')])\n"
        "    ]),\n"
        "    VarFileInfo([\n"
        "      VarStruct('Translation', [1033, 1200])\n"
        "    ])\n"
        "  ]\n"
        ")\n"
    )


def write_version_file(version: str) -> Path:
    """Grava o version-file (``utf-8-sig``: BOM garante o decode correto).

    Valida o conteúdo com o parser real do PyInstaller (round-trip) —
    garante que a string table será serializada corretamente no exe.
    """
    BUILD.mkdir(parents=True, exist_ok=True)
    path = BUILD / "file_version_info.txt"
    path.write_text(version_file_content(version), encoding="utf-8-sig")

    from PyInstaller.utils.win32 import versioninfo

    info = versioninfo.load_version_info_from_text_file(str(path))
    assert type(info).__name__ == "VSVersionInfo", info
    return path


def build_args(version_file: Path) -> list[str]:
    """Argumentos fixos e documentados do build."""
    return [
        str(PYINSTALLER),
        "--noconfirm",
        "--clean",
        "--name", APP_NAME,
        "--onedir",            # nunca onefile (checklist da Fase 7)
        "--windowed",          # sem console (jogo gráfico)
        "--noupx",             # sem UPX (menos falsos positivos de antivírus)
        "--paths", str(ROOT / "src"),
        "--add-data", f"{ROOT / 'assets'};assets",
        "--icon", str(ROOT / "assets" / "icons" / "xadtitans.ico"),
        "--version-file", str(version_file),
        "--distpath", str(DIST),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
        # Exclusões explícitas de defesa (não são importadas de qualquer
        # forma, mas garante ausência mesmo com imports acidentais):
        "--exclude-module", "tests",
        "--exclude-module", "pytest",
        str(ROOT / "main.py"),
    ]


def preflight() -> str:
    """Valida ambiente e assets; retorna a versão de `xadtitans`."""
    if not PYINSTALLER.exists():
        sys.exit(
            f"ERRO: PyInstaller do .venv não encontrado: {PYINSTALLER}\n"
            "Instale as dependências de desenvolvimento no .venv do projeto."
        )
    missing = [a for a in REQUIRED_ASSETS if not (ROOT / a).exists()]
    if missing:
        sys.exit(f"ERRO: assets obrigatórios ausentes: {missing}")

    sys.path.insert(0, str(ROOT / "src"))
    from xadtitans import __version__

    return __version__


def validate_package(version: str) -> None:
    """Confere o pacote gerado: exe + assets essenciais (incl. visão preta)."""
    exe = DIST / APP_NAME / f"{APP_NAME}.exe"
    if not exe.exists():
        sys.exit(f"ERRO: executável não gerado: {exe}")

    internal = DIST / APP_NAME / "_internal"
    expected = [
        internal / "assets" / a.split("assets/", 1)[1]
        for a in REQUIRED_ASSETS
        if not a.endswith(".ico")  # o .ico é embutido no exe, não copiado
    ]
    missing = [str(p) for p in expected if not p.exists()]
    if missing:
        sys.exit(f"ERRO: assets faltando no pacote: {missing}")

    size_mb = sum(
        f.stat().st_size for f in (DIST / APP_NAME).rglob("*") if f.is_file()
    ) / (1024 * 1024)
    print(f"\nBuild OK — {APP_NAME} {version}")
    print(f"  exe:      {exe}")
    print(f"  pacote:   {DIST / APP_NAME} ({size_mb:.1f} MB)")
    print(f"  assets:   {len(expected)} arquivos essenciais presentes")


def main() -> int:
    version = preflight()
    print(f"XadTitans {version} — build onedir/windowed (PyInstaller do .venv)")

    # Limpa artefatos anteriores para um build determinístico.
    for stale in (DIST / APP_NAME, BUILD / "pyinstaller"):
        shutil.rmtree(stale, ignore_errors=True)
    spec = BUILD / f"{APP_NAME}.spec"
    spec.unlink(missing_ok=True)

    vfile = write_version_file(version)
    cmd = build_args(vfile)
    print(f"\n> {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        sys.exit(f"ERRO: PyInstaller retornou {result.returncode}")

    validate_package(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
