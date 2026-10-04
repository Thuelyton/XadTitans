"""Profiling de renderização e memória do XadTitans (headless).

Mede, de forma reproduzível e sem intervenção manual:
  - FPS / frame time (média, p50, p95, máximo) por cenário;
  - custo por componente do draw (fill, tabuleiro, destaques,
    peças, painel lateral, overlays, flip);
  - perfil cProfile de uma sessão completa (menu → partida →
    fim de partida);
  - memória: tracemalloc (alocações Python) + RSS (Windows);
  - teste de churn de cenas (criar/sair/recriar GameScene) para
    verificar estabilização de memória (não confunde aumento
    pontual inicial com vazamento).

Cenários: menu, partida estática, partida com seleção + lances
legais + último lance, partida durante animação, fim de partida.

Limitação documentada: driver de vídeo dummy (sem GPU/vsync). Os
custos de blit/flip absoluto diferem de hardware real, mas a
atribuição relativa entre componentes (Python vs C) é
representativa — mesma premissa de tools/bench_fps.py. O custo de
CPU da IA NÃO é medido aqui (foi medido na Fase 6.4); os cenários
usam HUMAN_VS_HUMAN para isolar renderização.

Uso:
    .venv/Scripts/python.exe tools/profile_render.py
    .venv/Scripts/python.exe tools/profile_render.py --frames 300
    .venv/Scripts/python.exe tools/profile_render.py --only game_selected
"""

from __future__ import annotations

import argparse
import cProfile
import ctypes
import gc
import io
import os
import pstats
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

# Isolar dados (autosave/settings) ANTES de importar xadtitans.
_TMP_DATA = tempfile.mkdtemp(prefix="xadtitans_profile_")
os.environ.setdefault("XADTITANS_DATA", _TMP_DATA)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import chess
import pygame

from xadtitans.config import (
    COLOR_BG,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from xadtitans.core.types import GameMode
from xadtitans.ui.animations import Animator  # noqa: F401
from xadtitans.ui.board_view import BoardView
from xadtitans.ui.scene_manager import SceneManager
from xadtitans.ui.scenes.endgame_scene import EndgameScene
from xadtitans.ui.scenes.game_scene import GameScene
from xadtitans.ui.scenes.menu_scene import MenuScene

# ══════════════════════════════════════════════════════════
# Memória
# ══════════════════════════════════════════════════════════

def rss_bytes() -> int:
    """RSS do processo em bytes (Windows via psapi; 0 se indisponível)."""
    if sys.platform != "win32":
        return 0

    class PMC(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_uint32),
            ("PageFaultCount", ctypes.c_uint32),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PMC()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(
        handle, ctypes.byref(counters), counters.cb
    )
    return counters.WorkingSetSize if ok else 0


def _mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


# ══════════════════════════════════════════════════════════
# Cenários
# ══════════════════════════════════════════════════════════

_OPENING_MOVES = ("e2e4", "e7e5", "g1f3", "b8c6")


def _build_game() -> GameScene:
    """GameScene HvH com relógio e 4 lances aplicados."""
    scene = GameScene(game_mode=GameMode.HUMAN_VS_HUMAN, clock_minutes=10)
    for uci in _OPENING_MOVES:
        scene._apply_move(chess.Move.from_uci(uci))
    # Animações terminam antes da medição
    scene.animator.clear()
    return scene


def _select_piece(scene: GameScene, sq: int) -> None:
    """Seleciona casa com lances legais visíveis (representativo de uso)."""
    scene.board_view.selected_square = sq
    scene.board_view.legal_destinations = [
        m.to_square for m in scene.game.legal_moves_from(sq)
    ]


def _scenario_menu(sm: SceneManager) -> MenuScene:
    from xadtitans.audio import AudioManager

    return MenuScene(sm, AudioManager())


def _scenario_game_static() -> GameScene:
    return _build_game()


def _scenario_game_selected() -> GameScene:
    scene = _build_game()
    _select_piece(scene, chess.F3)  # cavalo com lances alternando g5/f3
    return scene


def _scenario_game_hover_check() -> GameScene:
    """Seleção + hover + xeque (pulso) — máximo de destaques."""
    scene = _scenario_game_selected()
    scene.board_view.hover_square = chess.G5
    scene.board_view.check_square = chess.E8
    return scene


def _scenario_endgame(sm: SceneManager) -> tuple[GameScene, EndgameScene]:
    game = _build_game()
    # Simula fim de partida (brancas vencem por desistência)
    game.game.resign(chess.WHITE)
    return game, EndgameScene(game, sm)


SCENARIOS = {
    "menu": "MenuScene (título, botões, fontes)",
    "game_static": "GameScene partida estática (peças + painel)",
    "game_selected": "GameScene com seleção + lances legais + último lance",
    "game_hover_check": "Seleção + hover + xeque (pulso) — máximo de destaques",
    "game_anim": "GameScene durante animação de lance (slide + fade)",
    "endgame": "Fim de partida (overlay + véu translúcido)",
}


# ══════════════════════════════════════════════════════════
# Medição de frame
# ══════════════════════════════════════════════════════════

def _measure_frames(update, draw, flip, frames: int, warmup: int) -> list[float]:
    """Roda warmup + frames medidos; retorna tempos de frame (segundos).

    Cada frame: update(dt fixo) → draw → flip (custo total de quadro).
    """
    dt = 1 / 60
    for _ in range(warmup):
        update(dt)
        draw()
        flip()
    times: list[float] = []
    for _ in range(frames):
        t0 = time.perf_counter()
        update(dt)
        draw()
        flip()
        times.append(time.perf_counter() - t0)
    return times


def _stats(times: list[float]) -> dict[str, float]:
    ordered = sorted(times)
    n = len(ordered)
    return {
        "mean": statistics.fmean(times) * 1000,
        "p50": ordered[n // 2] * 1000,
        "p95": ordered[min(n - 1, int(n * 0.95))] * 1000,
        "max": ordered[-1] * 1000,
        "fps": 1.0 / statistics.fmean(times),
    }


def _print_frame_table(results: dict[str, dict[str, float]]) -> None:
    print(f"{'Cenário':<20} {'FPS':>7} {'mean ms':>8} {'p50':>7} "
          f"{'p95':>7} {'max ms':>8}")
    print("-" * 60)
    for name, s in results.items():
        print(f"{name:<20} {s['fps']:>7.1f} {s['mean']:>8.2f} "
              f"{s['p50']:>7.2f} {s['p95']:>7.2f} {s['max']:>8.2f}")
    print()


# ══════════════════════════════════════════════════════════
# Atribuição por componente (fases do draw)
# ══════════════════════════════════════════════════════════

def _measure_components(scene: GameScene, screen: pygame.Surface,
                        frames: int) -> list[tuple[str, int, float, float, float]]:
    """Tempo cada fase do draw de GameScene/BoardView sobre a mesma cena.

    Retorna lista de (componente, chamadas, tempo_total, tempo_ médio,
    % do frame) — o frame de referência é a soma de todas as fases.
    """
    bv = scene.board_view
    phases: list[tuple[str, object]] = [
        ("fill (bg)", lambda: screen.fill(COLOR_BG)),
        ("board_view: imagem do tabuleiro",
         lambda: screen.blit(bv._board_img, (0, 0))),  # offset puro p/ medição
        ("board_view: último lance", lambda: bv._draw_last_move(screen)),
        ("board_view: seleção", lambda: bv._draw_selected(screen)),
        ("board_view: xeque (pulso)", lambda: bv._draw_check(screen)),
        ("board_view: lances legais", lambda: bv._draw_legal(screen)),
        ("board_view: hover", lambda: bv._draw_hover(screen)),
        ("board_view: peças estáticas",
         lambda: _draw_static_pieces(bv, screen)),
        ("painel lateral (fontes/SAN)", lambda: scene.side_panel.draw(
            screen, scene.game, clock=scene.clock)),
        ("overlays (dica/promoção/IA)", lambda: (
            scene._draw_hint(screen),
            scene._draw_promotion_dialog(screen),
            scene._draw_thinking(screen),
            scene._draw_hint_searching(screen),
            scene._draw_draw_request(screen),
        )),
    ]

    # Zera o estado de destaque variável entre fases
    totals = {name: 0.0 for name, _ in phases}
    dt = 1 / 60
    for _ in range(frames):
        scene.update(dt)
        for name, fn in phases:
            t0 = time.perf_counter()
            fn()
            totals[name] += time.perf_counter() - t0

    frame_total = sum(totals.values())
    rows = []
    for name, _ in phases:
        t = totals[name]
        rows.append((name, frames, t, t / frames, 100.0 * t / frame_total))
    rows.append(("display.flip", frames, 0.0, 0.0, 0.0))  # preenchido depois
    return rows


def _draw_static_pieces(bv: BoardView, surface: pygame.Surface) -> None:
    """Somente as peças estáticas (sem animações) — igual a BoardView.draw."""
    anims: dict = {}
    for sq in bv._map.draw_order():
        if sq in anims:
            continue
        piece = bv.board.piece_at(sq)
        if piece is not None:
            bv._draw_piece(surface, piece, sq)


def _measure_flip(screen: pygame.Surface, frames: int) -> float:
    t0 = time.perf_counter()
    for _ in range(frames):
        pygame.display.flip()
    return time.perf_counter() - t0


def _print_component_table(rows, flip_total: float, frames: int) -> None:
    # Substitui a linha placeholder de flip pelo total medido
    rows = [(n, c, (flip_total if n == "display.flip" else t),
             (flip_total / frames if n == "display.flip" else m),
             p) for n, c, t, m, p in rows]
    frame_total = sum(t for _, _, t, _, _ in rows)
    rows = [(n, c, t, m, 100.0 * t / frame_total)
            for n, c, t, m, _ in rows]
    print(f"{'Componente':<38} {'Chamadas':>9} {'Total s':>8} "
          f"{'Méd ms':>8} {'% frame':>8}")
    print("-" * 76)
    for name, calls, total, mean_ms, pct in rows:
        print(f"{name:<38} {calls:>9} {total:>8.3f} "
              f"{mean_ms * 1000:>8.3f} {pct:>7.1f}%")
    print(f"{'TOTAL (frame)':<38} {frames:>9} {frame_total:>8.3f} "
          f"{frame_total / frames * 1000:>8.3f} {100.0:>7.1f}%")
    print()


# ══════════════════════════════════════════════════════════
# Sessão cProfile
# ══════════════════════════════════════════════════════════

def _profile_session(frames: int) -> None:
    """Sessão guiada sob cProfile: menu → partida → fim de partida."""
    sm = SceneManager()
    menu = _scenario_menu(sm)
    sm.push(menu)
    profiler = cProfile.Profile()
    dt = 1 / 60
    screen = pygame.display.get_surface()

    profiler.enable()
    for _ in range(30):
        menu.update(dt)
        menu.draw(screen)

    game = _build_game()
    sm.push(game)
    _select_piece(game, chess.F3)
    moves = ("f3g5", "a7a6", "g5f3", "a6a5", "f3g5", "h7h6")
    for i in range(frames):
        if i % 40 == 0 and i // 40 < len(moves):
            game._apply_move(chess.Move.from_uci(moves[i // 40]))
            if i % 80 == 0:
                _select_piece(game, chess.F3)
        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    # Encerra a partida para o overlay ter resultado válido
    game.game.resign(chess.BLACK)
    endgame = EndgameScene(game, sm)
    sm.push(endgame)
    for _ in range(30):
        endgame.update(dt)
        endgame.draw(screen)
        pygame.display.flip()
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(18)
    print("=== cProfile da sessão (cumulative, top 18) ===")
    print(stream.getvalue())

    stream2 = io.StringIO()
    stats.stream = stream2
    stats.sort_stats("tottime")
    stats.print_stats(12)
    print("=== cProfile da sessão (tottime, top 12) ===")
    print(stream2.getvalue())


# ══════════════════════════════════════════════════════════
# Memória: sessão longa + churn de cenas
# ══════════════════════════════════════════════════════════

def _memory_session(frames: int) -> None:
    """Sessão longa de partida: crescimento de memória durante uso."""
    gc.collect()
    tracemalloc.start()
    rss0 = rss_bytes()
    py0 = tracemalloc.get_traced_memory()[0]

    scene = _build_game()
    _select_piece(scene, chess.F3)
    moves = (
        "f3g5", "a7a6", "g5f3", "a6a5", "f3g5", "h7h6", "g5f3", "h6h5",
        "f3g5", "b7b6", "g5f3", "b6b5", "f3g5", "a5a4", "g5f3", "a4a3",
    )
    screen = pygame.display.get_surface()
    dt = 1 / 60
    applied = 0
    checkpoints = {frames // 4, frames // 2, (3 * frames) // 4}
    for i in range(frames):
        if i % 60 == 0 and applied < len(moves):
            scene._apply_move(chess.Move.from_uci(moves[applied]))
            applied += 1
            if applied % 2 == 0:
                _select_piece(scene, chess.F3)
        scene.update(dt)
        scene.draw(screen)
        pygame.display.flip()
        if i + 1 in checkpoints:
            gc.collect()
            cur = tracemalloc.get_traced_memory()[0]
            print(f"  frame {i + 1:>5}: py={_mb(cur - py0):>8} "
                  f"RSS delta={_mb(rss_bytes() - rss0):>8}")

    gc.collect()
    scene.on_exit()
    del scene
    gc.collect()
    py1 = tracemalloc.get_traced_memory()[0]
    rss1 = rss_bytes()
    print(f"Sessão de {frames} frames com {applied} lances:")
    print(f"  memória Python: {_mb(py0)} → {_mb(py1)} "
          f"(crescimento {_mb(py1 - py0)})")
    print(f"  RSS: {_mb(rss0)} → {_mb(rss1)} "
          f"(crescimento {_mb(rss1 - rss0)})")
    tracemalloc.stop()
    print()


def _memory_churn(cycles: int, frames_per_cycle: int = 10) -> None:
    """Criar/sair/recriar GameScene repetidamente: a memória estabiliza?"""
    gc.collect()
    tracemalloc.start()
    rss_values: list[int] = []
    py_values: list[int] = []
    screen = pygame.display.get_surface()
    dt = 1 / 60

    for cycle in range(1, cycles + 1):
        scene = _build_game()
        _select_piece(scene, chess.F3)
        for _ in range(frames_per_cycle):
            scene.update(dt)
            scene.draw(screen)
            pygame.display.flip()
        scene.on_exit()
        del scene
        gc.collect()
        py_values.append(tracemalloc.get_traced_memory()[0])
        rss_values.append(rss_bytes())
        if cycle in (1, 5, 10, cycles // 2, cycles):
            print(f"  ciclo {cycle:>3}: py={_mb(py_values[-1]):>9} "
                  f"RSS={_mb(rss_values[-1]):>9}")

    # Estabilização: compara ciclo 5 (pós-aquecimento) com o último.
    ref = min(4, cycles - 1)
    d_py = py_values[-1] - py_values[ref]
    d_rss = rss_values[-1] - rss_values[ref] if rss_values[0] else 0
    span = cycles - 1 - ref
    print(f"Churn de {cycles} ciclos "
          f"(GameScene criada → {frames_per_cycle} frames → sair):")
    print(f"  Python: {_mb(py_values[ref])} (ciclo {ref + 1}) → "
          f"{_mb(py_values[-1])} (ciclo {cycles}) — delta "
          f"{d_py / max(span, 1) / 1024:.1f} KB/ciclo")
    if rss_values[0]:
        print(f"  RSS:    {_mb(rss_values[ref])} → {_mb(rss_values[-1])} "
              f"— delta {d_rss / max(span, 1) / 1024:.1f} KB/ciclo")
    print("  Critério: delta médio < 50 KB/ciclo após o ciclo 5 = estabilizou")
    tracemalloc.stop()
    print()


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Profile de render/memória")
    parser.add_argument("--frames", type=int, default=240,
                        help="quadros medidos por cenário (padrão 240)")
    parser.add_argument("--warmup", type=int, default=30,
                        help="quadros de aquecimento (padrão 30)")
    parser.add_argument("--only", default=None,
                        help="roda só um cenário (nome)")
    parser.add_argument("--no-memory", action="store_true",
                        help="pula as medições de memória")
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    print(f"Driver de vídeo: {os.environ.get('SDL_VIDEODRIVER')} "
          f"(headless; ver docstring sobre limitações)\n")

    # ── Etapa 3: baseline de FPS por cenário ────────────
    print("=== FPS / frame time por cenário ===")
    results: dict[str, dict[str, float]] = {}
    builders = {
        "menu": lambda: _scenario_menu(SceneManager()),
        "game_static": lambda: _scenario_game_static(),
        "game_selected": lambda: _scenario_game_selected(),
        "game_hover_check": lambda: _scenario_game_hover_check(),
        "game_anim": lambda: _make_anim_scene(),
        "endgame": lambda: _scenario_endgame(SceneManager()),
    }
    for name, build in builders.items():
        if args.only and name != args.only:
            continue
        built = build()
        if name == "endgame":
            game, overlay = built
            times = _measure_frames(
                overlay.update,
                lambda g=game, o=overlay: (g.draw(screen), o.draw(screen)),
                pygame.display.flip, args.frames, args.warmup,
            )
        elif name == "game_anim":
            scene = built
            times = _measure_anim_frames(scene, screen, args.frames)
        else:
            scene = built
            times = _measure_frames(
                scene.update, lambda s=scene: s.draw(screen),
                pygame.display.flip, args.frames, args.warmup,
            )
        results[name] = _stats(times)
    _print_frame_table(results)

    # ── Etapa 2: atribuição por componente ───────────────
    if not args.only or args.only == "game_selected":
        print("=== Custo por componente (GameScene com seleção) ===")
        print("Fases chamadas sequencialmente sobre a mesma cena; o flip")
        print("é medido à parte (driver dummy é barato — ver limitação).\n")
        scene = _scenario_game_selected()
        rows = _measure_components(scene, screen, args.frames)
        flip_total = _measure_flip(screen, args.frames)
        _print_component_table(rows, flip_total, args.frames)

    # ── cProfile da sessão ───────────────────────────────
    if not args.only:
        _profile_session(max(120, args.frames // 2))

    # ── Etapa 4: memória ─────────────────────────────────
    if not args.no_memory and not args.only:
        print("=== Memória: sessão longa de partida ===")
        _memory_session(max(600, args.frames * 3))
        print("=== Memória: churn de cenas (GameScene) ===")
        _memory_churn(30)

    pygame.quit()
    return 0


def _make_anim_scene() -> GameScene:
    """Cena com animação recém-disparada (para medir frames animados)."""
    scene = _build_game()
    scene._apply_move(chess.Move.from_uci("f3g5"))
    return scene


def _measure_anim_frames(scene: GameScene, screen: pygame.Surface,
                         frames: int) -> list[float]:
    """Mede frames enquanto houver animação ativa (com reforço periódico)."""
    dt = 1 / 60
    times: list[float] = []
    moves = ["a7a6", "g5f3", "a6a5", "f3g5"]
    idx = 0
    for i in range(frames):
        # Reanima a cada 20 frames para manter a carga representativa
        if i % 20 == 0 and idx < len(moves):
            scene.animator.clear()
            scene._apply_move(chess.Move.from_uci(moves[idx]))
            idx += 1
        t0 = time.perf_counter()
        scene.update(dt)
        scene.draw(screen)
        pygame.display.flip()
        times.append(time.perf_counter() - t0)
    return times


if __name__ == "__main__":
    sys.exit(main())
