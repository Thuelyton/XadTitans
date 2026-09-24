"""Resolução de caminhos de assets.

No desenvolvimento, os caminhos são relativos à raiz do projeto.
Dentro de um executável PyInstaller (--onedir), os arquivos ficam
em ``sys._MEIPASS``.  Esta função unifica os dois cenários.
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str | Path) -> Path:
    """Retorna o caminho absoluto para *relative* respeitando o
    ambiente de execução (dev ou PyInstaller).
    """
    base: Path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)          # type: ignore[attr-defined]
    else:
        # Raiz do repositório (uma pasta acima de src/)
        base = Path(__file__).resolve().parent.parent.parent
    return base / Path(relative)
