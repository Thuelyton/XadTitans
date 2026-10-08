"""Gera o ícone do aplicativo (assets/icons/xadtitans.ico).

Origem: sprite próprio `assets/pieces/white_king.png` (CC0, gerado por
``tools/gen_pieces.py``) — sem arte de terceiros, sem dependência nova
(Pillow já é requisito de desenvolvimento).

O rei é recortado pela bounding box do alfa, centralizado numa tela
256×256 transparente com margem, e salvo como ICO multiresolução
(16, 24, 32, 48, 64, 128 e 256 px) — formato aceito pelo Windows e
pelo ``--icon`` do PyInstaller.

Uso:
    .venv/Scripts/python.exe tools/gen_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

# Resoluções exigidas para um bom ícone de janela/tarefa/explorer.
_SIZES = (16, 24, 32, 48, 64, 128, 256)

_CANVAS = 256
_MARGIN = 0.88  # fração do canvas ocupada pela peça


def generate(src: Path, out: Path) -> Path:
    """Cria o ICO multiresolução a partir do sprite do rei branco."""
    out.parent.mkdir(parents=True, exist_ok=True)

    piece = Image.open(src).convert("RGBA")
    # Recorta pela bounding box do alfa (o sprite 256px tem folga).
    bbox = piece.getbbox()
    if bbox is not None:
        piece = piece.crop(bbox)

    # Centraliza na tela 256×256 com margem proporcional.
    scale = min(_CANVAS * _MARGIN / piece.width, _CANVAS * _MARGIN / piece.height)
    new_w = max(1, round(piece.width * scale))
    new_h = max(1, round(piece.height * scale))
    piece = piece.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (_CANVAS, _CANVAS), (0, 0, 0, 0))
    canvas.paste(piece, ((_CANVAS - new_w) // 2, (_CANVAS - new_h) // 2), piece)

    # save com a lista de tamanhos → PIL grava todas as resoluções.
    canvas.save(out, format="ICO", sizes=[(s, s) for s in _SIZES])
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    src = root / "assets" / "pieces" / "white_king.png"
    ico = generate(src, root / "assets" / "icons" / "xadtitans.ico")

    # Sanidade: o ICO abre e contém todas as resoluções esperadas.
    # (``ico.sizes()`` retorna tuplas (l, a).)
    with Image.open(ico) as img:
        found = set(img.ico.sizes())
    missing = {(s, s) for s in _SIZES} - found
    assert not missing, f"resoluções ausentes no ICO: {missing}"
    print(f"ok: {ico} ({ico.stat().st_size} bytes, tamanhos {sorted(found)})")
    sys.exit(0)
