"""10 partidas AI vs AI headless — smoke E2E da Fase 6.6.

Verifica:
  - 0 movimentos ilegais
  - 0 exceções
  - 0 deadlocks (timeout por partida)
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

_TMP = tempfile.mkdtemp(prefix="xadtitans_aivai_")
os.environ["XADTITANS_DATA"] = _TMP
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "src"))

import chess
import pygame

from xadtitans.core.types import GameMode, Level
from xadtitans.ui.scenes.game_scene import GameScene

GAME_LIMIT = 10
MOVE_LIMIT = 300          # lances por partida (evita loops longos)
TIMEOUT_PER_GAME = 300.0  # segundos por partida

pygame.init()
pygame.display.set_mode((1024, 768))
surface = pygame.display.get_surface()

results = []
illegal_moves = 0
exceptions = 0
deadlocks = 0

print(f"Rodando {GAME_LIMIT} partidas AI vs AI (Iniciante)...\n")

for game_num in range(1, GAME_LIMIT + 1):
    try:
        scene = GameScene(
            game_mode=GameMode.AI_VS_AI,
            ai_level=Level.INICIANTE,
            ai_vs_ai_delay=0.0,
        )
        t0 = time.monotonic()
        timeout = False
        error = None
        illegal = False

        while (
            not scene.game.is_game_over()
            and len(scene.game.board.move_stack) < MOVE_LIMIT
        ):
            if time.monotonic() - t0 > TIMEOUT_PER_GAME:
                timeout = True
                break
            try:
                scene.update(1 / 60)
                scene.draw(surface)
                pygame.display.flip()
            except Exception as exc:  # noqa: BLE001
                error = repr(exc)
                exceptions += 1
                break

        plies = len(scene.game.board.move_stack)
        elapsed = time.monotonic() - t0

        # Verificar legalidade de todos os lances jogados
        probe = chess.Board()
        for i, mv in enumerate(scene.game.board.move_stack):
            if mv not in probe.legal_moves:
                illegal = True
                illegal_moves += 1
                error = f"lance ilegal: {mv.uci()} no lance {i+1}"
                break
            probe.push(mv)

        if timeout:
            deadlocks += 1
            status = "TIMEOUT"
        elif error:
            status = f"ERRO: {error}"
        elif scene.game.is_game_over():
            res = scene.game.result()
            status = f"OK ({res.status.name if res else '?'}, {plies} lances, {elapsed:.1f}s)"
        else:
            status = f"OK (interrompida, {plies} lances, {elapsed:.1f}s)"

        results.append((game_num, status))
        print(f"  Partida {game_num:2d}: {status}")

        scene._cancel_ai()

    except Exception as exc:  # noqa: BLE001
        exceptions += 1
        results.append((game_num, f"EXCECAO: {exc!r}"))
        print(f"  Partida {game_num:2d}: EXCECAO: {exc!r}")

print(f"\n{'='*60}")
print(f"Partidas: {GAME_LIMIT}")
print(f"Lances ilegais: {illegal_moves}")
print(f"Excecoes: {exceptions}")
print(f"Deadlocks (timeout): {deadlocks}")
total_ok = sum(1 for _, s in results if s.startswith("OK"))
print(f"OK: {total_ok}/{GAME_LIMIT}")
print(f"{'='*60}")

pygame.quit()
sys.exit(0 if illegal_moves == 0 and exceptions == 0 and deadlocks == 0 else 1)
