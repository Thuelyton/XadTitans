"""Configuração global do XadTitans.

Resolução, FPS, cores e geometria do tabuleiro.
Todo cálculo de layout fica aqui para que todos os módulos
usem os mesmos valores.
"""

# ── Janela ──────────────────────────────────────────────
WINDOW_TITLE = "XadTitans"
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS_DEFAULT = 30

# ── Geometria do tabuleiro ──────────────────────────────
COORD_MARGIN = 30          # espaço para as coordenadas (a-h, 1-8)
SIDE_PANEL_WIDTH = 288     # painel lateral (jogadas + capturadas, Fase 3)

# Geometria PLANA (provisória da Fase 1): usada pelas funções puras de
# conversão pixel<->casa e pelos testes delas.
_BOARD_MAX = min(
    WINDOW_WIDTH - 2 * COORD_MARGIN - SIDE_PANEL_WIDTH,
    WINDOW_HEIGHT - 2 * COORD_MARGIN,
)
SQUARE_SIZE = _BOARD_MAX // 8
BOARD_SIZE = SQUARE_SIZE * 8
BOARD_X = (WINDOW_WIDTH - SIDE_PANEL_WIDTH - BOARD_SIZE) // 2
BOARD_Y = (WINDOW_HEIGHT - BOARD_SIZE) // 2

# ── Tabuleiro em perspectiva (Fase 3) ─────────────────
# assets/board/board_perspective.png é gerado por tools/gen_board.py
# neste tamanho exato; squares.json traz o polígono, centro e escala
# de cada casa dentro da imagem.
BOARD_IMG_W = 720
BOARD_IMG_H = 696
BOARD_AREA_W = WINDOW_WIDTH - SIDE_PANEL_WIDTH  # área à esquerda
BOARD_PERSP_X = (BOARD_AREA_W - BOARD_IMG_W) // 2
BOARD_PERSP_Y = (WINDOW_HEIGHT - BOARD_IMG_H) // 2

# ── Painel lateral ─────────────────────────────────────
PANEL_X = BOARD_AREA_W + 8
PANEL_W = SIDE_PANEL_WIDTH - 16

# ── Cores do tabuleiro ──────────────────────────────────
COLOR_BG = (48, 46, 43)
COLOR_LIGHT_SQ = (240, 217, 181)
COLOR_DARK_SQ = (181, 136, 99)
COLOR_COORD = (160, 160, 160)
COLOR_LAST_MOVE_LIGHT = (205, 210, 106)
COLOR_LAST_MOVE_DARK = (170, 162, 58)
COLOR_SELECTED_LIGHT = (186, 202, 43)
COLOR_SELECTED_DARK = (170, 186, 32)
COLOR_LEGAL_DOT = (100, 100, 100)
COLOR_LEGAL_CAPTURE = (100, 100, 100)
COLOR_CHECK_GLOW = (235, 64, 52, 120)
