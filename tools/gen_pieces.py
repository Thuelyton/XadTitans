"""Gera os sprites finais das peças (assets/pieces/*.png).

Desenho procedural com Pillow: peças "torneadas" com gradiente,
brilho especular e contorno — estilo inspirado no Chess Titans,
mas 100% próprio (licença CC0 / domínio do projeto).

Uso:
    .venv/Scripts/python.exe tools/gen_pieces.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 256          # tamanho do canvas
CX = 128         # centro horizontal
ANCHOR_Y = 244   # y do "pé" da peça (ponto de apoio no tabuleiro)

PIECE_NAMES = ["pawn", "knight", "bishop", "rook", "queen", "king"]

# Paletas: (topo, base, contorno, brilho)
PALETTE = {
    True: {   # brancas (marfim)
        "top": (250, 240, 214),
        "bottom": (198, 170, 122),
        "outline": (94, 74, 50),
        "shine": (255, 255, 255),
    },
    False: {  # pretas (grafite)
        "top": (84, 86, 96),
        "bottom": (30, 30, 36),
        "outline": (8, 8, 10),
        "shine": (168, 174, 190),
    },
}


# ── helpers de desenho ─────────────────────────────────

def _ellipse(d: ImageDraw.ImageDraw, cx: int, cy: int, rx: int, ry: int) -> None:
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)


def _base(d: ImageDraw.ImageDraw, foot_hw: int, skirt_hw: int) -> None:
    """Base padrão: pé + saia elípticos (todos as peças têm)."""
    _ellipse(d, CX, 224, foot_hw, 11)                 # pé
    d.polygon(
        [(CX - foot_hw, 224), (CX + foot_hw, 224),
         (CX + skirt_hw, 236), (CX - skirt_hw, 236)],
        fill=255,
    )
    _ellipse(d, CX, 236, skirt_hw, 12)                # saia
    _ellipse(d, CX, 214, foot_hw - 6, 6)              # vinco do pé


def _lathe(
    d: ImageDraw.ImageDraw, profile: list[tuple[int, int]]
) -> None:
    """Corpo de revolução: perfil [(y, meia-largura)] de cima p/ baixo."""
    left = [(CX - hw, y) for y, hw in profile]
    right = [(CX + hw, y) for y, hw in reversed(profile)]
    d.polygon(left + right, fill=255)
    y_b, hw_b = profile[-1]
    _ellipse(d, CX, y_b, hw_b, max(6, hw_b // 3))     # fundo curvo


# ── silhuetas por peça ─────────────────────────────────

def _mask_pawn(d: ImageDraw.ImageDraw) -> None:
    _ellipse(d, CX, 84, 34, 34)                       # cabeça (esfera)
    _ellipse(d, CX, 122, 23, 11)                      # colar
    _lathe(d, [(128, 13), (188, 19)])                 # haste cônica
    _base(d, 34, 52)


def _mask_rook(d: ImageDraw.ImageDraw) -> None:
    # Ameias: 4 merlões simétricos (vãos em 101-107, 125-131, 149-155)
    for mx in (82, 107, 131, 155):
        d.rectangle((mx, 40, mx + 20, 70), fill=255)
    d.rectangle((82, 70, 174, 80), fill=255)      # colar da coroa
    _lathe(d, [(80, 46), (200, 48)])              # corpo cilíndrico
    _base(d, 44, 60)


def _mask_bishop(d: ImageDraw.ImageDraw) -> None:
    _ellipse(d, CX, 36, 10, 10)                       # bolinha do topo
    _ellipse(d, CX, 80, 30, 42)                       # mitra
    d.line((116, 58, 142, 102), fill=0, width=7)      # fenda diagonal
    _ellipse(d, CX, 128, 25, 11)                      # colar
    _lathe(d, [(134, 13), (196, 19)])                 # haste
    _base(d, 36, 54)


def _mask_knight(d: ImageDraw.ImageDraw) -> None:
    # Cabeça de cavalo (silhueta) voltada para a esquerda
    d.polygon(
        [
            (78, 222), (82, 178), (88, 148), (95, 126),   # peito/frente
            (58, 108), (54, 94), (76, 86),                # focinho
            (90, 76),                                     # lábio sup.
            (98, 46), (106, 62), (114, 42), (124, 60),    # orelhas
            (134, 72), (152, 88), (164, 116),             # crina
            (172, 152), (174, 222),                       # dorso
        ],
        fill=255,
    )
    _ellipse(d, CX, 224, 46, 10)                       # pescoço/base
    _base(d, 42, 58)


def _mask_queen(d: ImageDraw.ImageDraw) -> None:
    # Coroa com 5 pontas + bolinhas
    d.polygon(
        [
            (90, 88), (88, 44), (99, 70), (110, 42), (121, 70),
            (132, 40), (143, 70), (154, 42), (165, 70), (168, 44),
            (168, 88),
        ],
        fill=255,
    )
    for bx in (88, 110, 132, 154, 168):
        _ellipse(d, bx, 42, 8, 8)
    _ellipse(d, CX, 92, 30, 9)                        # faixa da coroa
    _ellipse(d, CX, 112, 25, 10)                      # colar
    _lathe(d, [(120, 16), (196, 24)])                 # haste
    _base(d, 40, 58)


def _mask_king(d: ImageDraw.ImageDraw) -> None:
    # Cruz no topo
    d.rectangle((122, 24, 134, 68), fill=255)
    d.rectangle((104, 36, 152, 48), fill=255)
    _ellipse(d, CX, 84, 40, 12)                       # faixa da coroa
    _ellipse(d, CX, 72, 34, 12)                       # domo
    _ellipse(d, CX, 106, 26, 10)                      # colar
    _lathe(d, [(114, 17), (198, 25)])                 # haste
    _base(d, 42, 60)


_MASKS = {
    "pawn": _mask_pawn,
    "rook": _mask_rook,
    "bishop": _mask_bishop,
    "knight": _mask_knight,
    "queen": _mask_queen,
    "king": _mask_king,
}


# ── sombreamento ───────────────────────────────────────

def _vertical_gradient(top: tuple, bottom: tuple) -> Image.Image:
    """Gradiente L vertical 0→255 mapeado em cor RGBA."""
    grad = Image.linear_gradient("L").resize((S, S))  # 0 topo → 255 base
    luts = []
    for ch in range(3):
        luts.append(
            grad.point(
                lambda v, t=top[ch], b=bottom[ch]: int(t + (b - t) * v / 255)
            )
        )
    return Image.merge("RGB", luts).convert("RGBA")


def _render(mask: Image.Image, is_white: bool) -> Image.Image:
    """Silhueta + gradiente + brilho especular + contorno.

    Todo o sombreamento é feito em RGB; o alfa final vem do
    ``mask`` — bordas suaves e simétricas, sem "vazamento" dos
    paste de brilho/contorno no canal alfa.
    """
    pal = PALETTE[is_white]

    body = _vertical_gradient(pal["top"], pal["bottom"]).convert("RGB")
    sprite = Image.new("RGB", (S, S), (0, 0, 0))
    sprite.paste(body, (0, 0), mask)

    # Brilho especular (elipse borrada no quadrante sup-esquerdo)
    spec = Image.new("L", (S, S), 0)
    sd = ImageDraw.Draw(spec)
    sd.ellipse((60, 36, 150, 130), fill=255)
    spec = spec.filter(ImageFilter.GaussianBlur(18))
    spec = ImageChops.multiply(spec, mask)
    shine = Image.new("RGB", (S, S), pal["shine"])
    sprite.paste(shine, (0, 0), spec.point(lambda v: int(v * 0.30)))

    # Oclusão suave na base (escurece o pé)
    shade = Image.new("L", (S, S), 0)
    shd = ImageDraw.Draw(shade)
    shd.ellipse((20, 170, 236, 250), fill=255)
    shade = shade.filter(ImageFilter.GaussianBlur(20))
    shade = ImageChops.multiply(shade, mask)
    dark = Image.new("RGB", (S, S), (0, 0, 0))
    sprite.paste(dark, (0, 0), shade.point(lambda v: int(v * 0.25)))

    # Contorno
    edges = mask.filter(ImageFilter.FIND_EDGES).filter(
        ImageFilter.GaussianBlur(0.6)
    )
    outline = Image.new("RGB", (S, S), pal["outline"])
    sprite.paste(outline, (0, 0), edges.point(lambda v: min(255, v * 2)))

    rgba = sprite.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def _eye(sprite: Image.Image) -> None:
    """Olho do cavalo (detalhe por cima do sombreamento)."""
    d = ImageDraw.Draw(sprite)
    d.ellipse((99, 90, 108, 99), fill=(30, 26, 22, 255))


def generate(out_dir: Path) -> list[Path]:
    """Gera os 12 sprites; retorna os caminhos criados."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in PIECE_NAMES:
        for is_white in (True, False):
            mask = Image.new("L", (S, S), 0)
            d = ImageDraw.Draw(mask)
            _MASKS[name](d)
            sprite = _render(mask, is_white)
            if name == "knight":
                _eye(sprite)
            path = out_dir / f"{'white' if is_white else 'black'}_{name}.png"
            sprite.save(path)
            paths.append(path)
    return paths


def _preview(out_dir: Path, paths: list[Path]) -> Path:
    """Folha de contato para inspeção visual (não é asset do jogo)."""
    cols, rows, cell = 6, 2, 260
    sheet = Image.new("RGBA", (cols * cell, rows * cell + 40), (90, 80, 66, 255))
    d = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        x = (i % cols) * cell
        y = (i // cols) * cell
        # xadrez de fundo p/ contraste
        for r in range(8):
            for c in range(8):
                col = (120, 100, 80) if (r + c) % 2 else (150, 130, 105)
                d.rectangle((x + c * 20, y + r * 20,
                             x + c * 20 + 20, y + r * 20 + 20), fill=col)
        sheet.paste(Image.open(path), (x, y), Image.open(path))
    p = out_dir / "_preview.png"
    sheet.save(p)
    return p


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out = root / "assets" / "pieces"
    made = generate(out)
    prev = _preview(out, made)
    print(f"{len(made)} sprites em {out}")
    print(f"preview: {prev}")
    sys.exit(0)
