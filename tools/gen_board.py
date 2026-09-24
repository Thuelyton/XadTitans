"""Gera o tabuleiro em perspectiva (estilo Chess Titans).

Saídas (em assets/board/):
  - board_perspective.png : tabuleiro + moldura de madeira
  - squares.json          : polígono, centro e escala de cada casa

A projeção é de câmera pinhole real (câmera atrás da borda das brancas,
eixo paralelo ao chão): um ponto do plano do tabuleiro (x_b, z_b) vai para

    d        = 1 + 0.075 * z_b          (profundidade)
    screen_x = CX + 70 * x_b / d
    screen_y = -740 + 1360 / d

O campo de jogo é x_b ∈ [-4, 4] (a→h), z_b ∈ [0, 8] (1→8);
a moldura é o mesmo plano estendido (x ±4.6, z -0.6..8.6).

Uso:
    .venv/Scripts/python.exe tools/gen_board.py
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ── projeção (ver docstring) ───────────────────────────
_CX = 360.0
_K = 1360.0
_YC = -740.0
_C = 70.0
_DZ = 0.075
_RIM_X = 4.6
_RIM_Z_NEAR = -0.6
_RIM_Z_FAR = 8.6

# ── cores ──────────────────────────────────────────────
_WOOD_LIGHT = (196, 141, 90)     # moldura clara
_WOOD_DARK = (120, 78, 44)       # moldura escura (topo)
_CELL_LIGHT = (232, 208, 168)    # casa clara
_CELL_DARK = (156, 108, 72)      # casa escura
_CELL_EDGE = (92, 62, 38)
_INNER_SHADE = (40, 24, 12)      # sombra interna da moldura


def _d(z: float) -> float:
    return 1.0 + _DZ * z


def _project(x_b: float, z_b: float) -> tuple[float, float]:
    d = _d(z_b)
    return (_CX + _C * x_b / d, _YC + _K / d)


def _poly(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [tuple(round(v, 2) for v in p) for p in points]  # type: ignore[misc]


def _quad(x0: float, x1: float, z0: float, z1: float) -> list[tuple[float, float]]:
    """Quadrilátero projetado do retângulo do plano (x0..x1, z0..z1)."""
    return [
        _project(x0, z0), _project(x1, z0),
        _project(x1, z1), _project(x0, z1),
    ]


def _depth_shade(color: tuple[int, int, int], z: float) -> tuple[int, int, int]:
    """Escurece casas distantes (z alto) para dar profundidade."""
    f = 1.0 - 0.10 * z / 8.0
    return tuple(int(c * f) for c in color)  # type: ignore[misc]


def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for cand in (
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _masked_overlay(img: Image.Image, overlay: Image.Image, mask: Image.Image) -> None:
    """Compõe ``overlay`` sobre ``img`` restrito a ``mask`` (L)."""
    alpha = ImageChops.multiply(overlay.getchannel("A"), mask)
    overlay.putalpha(alpha)
    img.alpha_composite(overlay)


def generate(out_dir: Path, width: int, height: int) -> tuple[Path, Path]:
    """Gera PNG + JSON; retorna os caminhos."""
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── moldura (plano estendido) ──────────────────────
    rim = _quad(-_RIM_X, _RIM_X, _RIM_Z_NEAR, _RIM_Z_FAR)
    d.polygon(rim, fill=_WOOD_LIGHT)

    # Gradiente vertical da moldura: mais escura no topo (longe)
    rim_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ro = ImageDraw.Draw(rim_overlay)
    y_top = rim[2][1]
    y_bot = rim[0][1]
    steps = 60
    for i in range(steps):
        t = i / steps
        y0 = y_top + (y_bot - y_top) * t
        y1 = y_top + (y_bot - y_top) * (t + 1 / steps) + 1
        alpha = int(110 * (1.0 - t))
        col = (
            _WOOD_DARK[0], _WOOD_DARK[1], _WOOD_DARK[2], alpha
        )
        ro.rectangle((0, y0, width, y1), fill=col)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(rim, fill=255)
    _masked_overlay(img, rim_overlay, mask)

    # Textura de veios da madeira (ruído semeado, sutil)
    rng = random.Random(42)
    grain = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for _ in range(2600):
        x = rng.uniform(0, width)
        y = rng.uniform(y_top, y_bot)
        ln = rng.uniform(4, 26)
        dark = rng.random() < 0.5
        col = (70, 45, 25, 40) if dark else (255, 230, 200, 26)
        gd.line((x, y, x + ln * 0.4, y + ln), fill=col, width=1)
    grain = grain.filter(ImageFilter.GaussianBlur(0.6))
    _masked_overlay(img, grain, mask)

    # ── casas do campo de jogo ─────────────────────────
    squares: list[dict] = []
    raw_w: list[float] = []
    for r in range(8):        # rank 1..8 (z = r .. r+1)
        for f in range(8):    # file a..h (x = -4+f .. -4+f+1)
            x0, x1 = -4.0 + f, -4.0 + f + 1
            z0, z1 = float(r), float(r + 1)
            quad = _quad(x0, x1, z0, z1)
            base = _CELL_LIGHT if (f + r) % 2 else _CELL_DARK
            d.polygon(quad, fill=_depth_shade(base, (z0 + z1) / 2))
            d.line(quad + [quad[0]], fill=_CELL_EDGE, width=1)

            cx = sum(p[0] for p in quad) / 4.0
            cy = sum(p[1] for p in quad) / 4.0
            w_near = quad[1][0] - quad[0][0]
            w_far = quad[2][0] - quad[3][0]
            raw_w.append((w_near + w_far) / 2.0)
            squares.append(
                {
                    "square": r * 8 + f,  # chess.A1 == 0
                    "polygon": _poly(quad),
                    "center": [round(cx, 2), round(cy, 2)],
                }
            )

    # Escala relativa à fileira 1 (a mais próxima = 1.0)
    ref_w = raw_w[0]
    for sq, w in zip(squares, raw_w, strict=True):
        sq["scale"] = round(w / ref_w, 4)

    # Sombra interna: moldura projeta sombra sobre as casas de cima
    shade_poly = _quad(-4, 4, 0, 1.6)
    inner = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(inner).polygon(
        shade_poly, fill=_INNER_SHADE + (110,)
    )
    blur_zone = Image.new("L", (width, height), 0)
    ImageDraw.Draw(blur_zone).polygon(shade_poly, fill=255)
    blur_zone = blur_zone.filter(ImageFilter.GaussianBlur(6))
    _masked_overlay(img, inner, blur_zone)

    # Bisel claro na borda interna da moldura (lado de cá)
    d.line(
        [_project(-4, 0), _project(4, 0)],
        fill=(255, 235, 205, 120), width=2,
    )

    # ── coordenadas gravadas na moldura ────────────────
    font = _load_font(20)
    for f, letter in enumerate("abcdefgh"):
        x_b = -4.0 + f + 0.5
        px, py = _project(x_b, -0.32)
        d.text(
            (px, py), letter, font=font, fill=(60, 38, 20, 200),
            anchor="mm",
        )
    for r in range(8):
        z_b = r + 0.5
        px, py = _project(-4.31, z_b)
        d.text(
            (px, py), str(r + 1), font=font, fill=(60, 38, 20, 200),
            anchor="mm",
        )

    png_path = out_dir / "board_perspective.png"
    img.save(png_path)

    data = {
        "image": "board_perspective.png",
        "width": width,
        "height": height,
        "projection": {
            "cx": _CX, "k": _K, "yc": _YC, "c": _C, "dz": _DZ,
        },
        "squares": squares,
    }
    json_path = out_dir / "squares.json"
    json_path.write_text(
        json.dumps(data, indent=1), encoding="utf-8"
    )
    return png_path, json_path


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from xadtitans.config import BOARD_IMG_H, BOARD_IMG_W

    root = Path(__file__).resolve().parent.parent
    out = root / "assets" / "board"
    png, js = generate(out, BOARD_IMG_W, BOARD_IMG_H)

    # Sanidade: tudo dentro da imagem, 64 casas, escala decrescente
    data = json.loads(js.read_text(encoding="utf-8"))
    assert len(data["squares"]) == 64
    for sq in data["squares"]:
        for x, y in sq["polygon"]:
            assert 0 <= x < data["width"], sq
            assert 0 <= y < data["height"], sq
    by_rank = sorted(
        data["squares"], key=lambda s: s["square"]
    )
    scales = [by_rank[r * 8]["scale"] for r in range(8)]
    assert scales == sorted(scales, reverse=True), scales
    assert math.isclose(scales[0], 1.0, rel_tol=0.02), scales[0]
    print(f"ok: {png}")
    print(f"ok: {js} (64 casas, escalas {scales[0]:.3f}..{scales[-1]:.3f})")
