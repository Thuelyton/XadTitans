"""Gera os sons do jogo (assets/sounds/*.wav) — sintetizados, próprios.

Nada de áudio de terceiros: cada som é uma pequena síntese
(osciladores + ruído + envelope exponencial) gravada em WAV PCM
16 bits mono 44,1 kHz pelo módulo padrão ``wave``.

Uso:
    .venv/Scripts/python.exe tools/gen_sounds.py
"""

from __future__ import annotations

import math
import random
import struct
import sys
import wave
from pathlib import Path

RATE = 44100
AMP = 0.42  # amplitude geral (0..1)


def _env(t: float, dur: float, attack: float = 0.004) -> float:
    """Envelope: ataque rápido + decaimento exponencial."""
    if t < attack:
        return t / attack
    tau = max(dur / 5.0, 0.01)
    return math.exp(-(t - attack) / tau)


def _tone(
    freq: float,
    dur: float,
    harmonics: list[tuple[float, float]] | None = None,
) -> list[float]:
    """Tono com harmônicos [(multiplicador, peso), ...]."""
    harmonics = harmonics or [(1.0, 1.0)]
    n = int(dur * RATE)
    return [
        sum(w * math.sin(2 * math.pi * freq * m * i / RATE) for m, w in harmonics)
        for i in range(n)
    ]


def _noise(dur: float, lowpass: float = 0.25) -> list[float]:
    """Ruído branco filtrado simples (média móvel)."""
    rng = random.Random(7)
    n = int(dur * RATE)
    raw = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    win = max(1, int(lowpass * RATE / 1000))
    out = []
    acc = sum(raw[:win])
    for i in range(n):
        acc += raw[i] if i + win < n else 0
        acc -= raw[i - win] if i >= win else 0
        out.append(acc / win / 0.6)
    return out


def _mix(*layers: tuple[list[float], float]) -> list[float]:
    """Soma camadas (sinal, ganho) já no mesmo comprimento."""
    n = max(len(sig) for sig, _ in layers)
    out = [0.0] * n
    for sig, gain in layers:
        for i, v in enumerate(sig):
            out[i] += v * gain
    return out


def _apply_env(sig: list[float], dur: float, attack: float = 0.004) -> list[float]:
    return [v * _env(i / RATE, dur, attack) for i, v in enumerate(sig)]


def _write(path: Path, sig: list[float]) -> None:
    data = bytearray()
    for v in sig:
        v = max(-1.0, min(1.0, v)) * AMP
        data += struct.pack("<h", int(v * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(data))


# ── receitas ───────────────────────────────────────────

def snd_click() -> list[float]:
    return _apply_env(_tone(2200.0, 0.03, [(1.0, 1.0), (2.7, 0.3)]), 0.03)


def snd_move() -> list[float]:
    dur = 0.09
    body = _tone(190.0, dur, [(1.0, 1.0), (2.0, 0.4), (3.0, 0.15)])
    knock = _noise(0.02, 4.0)
    return _apply_env(_mix((body, 1.0), (knock, 0.5)), dur)


def snd_capture() -> list[float]:
    dur = 0.16
    body = _tone(110.0, dur, [(1.0, 1.0), (1.5, 0.5), (2.2, 0.25)])
    thud = _noise(0.07, 2.5)
    return _apply_env(_mix((body, 1.0), (thud, 0.8)), dur, attack=0.002)


def snd_check() -> list[float]:
    beep = _apply_env(_tone(880.0, 0.09, [(1.0, 1.0), (2.0, 0.2)]), 0.09)
    gap = [0.0] * int(0.06 * RATE)
    return beep + gap + beep


def snd_game_over() -> list[float]:
    notes = (523.25, 659.25, 783.99)  # dó-mi-sol
    out: list[float] = []
    for f in notes:
        out += _apply_env(
            _tone(f, 0.22, [(1.0, 1.0), (2.0, 0.25)]), 0.22, attack=0.01
        )
    return out


_SOUNDS = {
    "click": snd_click,
    "move": snd_move,
    "capture": snd_capture,
    "check": snd_check,
    "game_over": snd_game_over,
}


def generate(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, recipe in _SOUNDS.items():
        path = out_dir / f"{name}.wav"
        _write(path, recipe())
        paths.append(path)
    return paths


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out = root / "assets" / "sounds"
    made = generate(out)
    for p in made:
        ms = p.stat().st_size / (RATE * 2) * 1000
        print(f"ok: {p} ({ms:.0f} ms)")
    sys.exit(0)
