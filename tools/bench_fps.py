"""Mede o desempenho de renderização do jogo (headless).

Roda N quadros completos (update + draw de uma partida em andamento,
com animações, destaques e painel lateral) e reporta o FPS médio.
A meta da Fase 3 é >= 30 FPS no PC alvo; este script mede o custo de
renderização (driver dummy, sem vsync) — se sobra folga grande aqui,
o alvo está garantido.

Uso:
    .venv/Scripts/python.exe tools/bench_fps.py [quadros]
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from xadtitans.config import WINDOW_HEIGHT, WINDOW_WIDTH
from xadtitans.ui.scenes.game_scene import GameScene


def main() -> int:
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

    scene = GameScene()
    surf = screen

    # Partida em andamento: peças movidas, peça selecionada
    # com lances legais visíveis e último lance destacado
    import chess

    for uci in ("e2e4", "e7e5", "g1f3", "b8c6"):
        scene._apply_move(chess.Move.from_uci(uci))
    scene.board_view.selected_square = chess.F3
    scene.board_view.legal_destinations = [
        m.to_square for m in scene.game.legal_moves_from(chess.F3)
    ]

    # Aquecimento (fontes/sprites em temperatura)
    for _ in range(30):
        scene.update(1 / 60)
        scene.draw(surf)

    t0 = time.perf_counter()
    # Sequência legal: cavalo branco alterna g5/f3; peões pretos
    # avançam pelos arquivos a, h, b (nada bloqueia).
    moves = (
        "f3g5", "a7a6", "g5f3", "a6a5", "f3g5", "h7h6",
        "g5f3", "h6h5", "f3g5", "b7b6", "g5f3", "b6b5",
    )
    for i in range(frames):
        # a cada 60 quadros, executa um lance (renderiza com animação)
        if i % 60 == 0 and i // 60 < len(moves):
            scene._apply_move(chess.Move.from_uci(moves[i // 60]))
        scene.update(1 / 60)
        scene.draw(surf)
    elapsed = time.perf_counter() - t0

    fps = frames / elapsed
    ms = elapsed / frames * 1000
    print(f"quadros: {frames}  tempo: {elapsed:.2f}s")
    print(f"FPS medio de renderizacao: {fps:6.1f}  ({ms:.2f} ms/quadro)")
    print("meta >= 30 FPS:", "OK" if fps >= 30 else "FALHOU")
    pygame.quit()
    return 0 if fps >= 30 else 1


if __name__ == "__main__":
    sys.exit(main())
