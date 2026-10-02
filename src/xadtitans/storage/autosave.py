"""Autosave da partida em andamento (JSON versionado).

Salva o estado completo necessário para retomar a partida:
posição (histórico de lances), modo, lado/cor, dificuldade,
configuração do relógio, tempos restantes, turno (derivado da
posição), perspectiva do tabuleiro e o histórico de tempos do
relógio (necessário para restaurar o Undo corretamente).

Formato::

    {
        "version": 1,
        "mode": "human_vs_human" | "human_vs_ai" | "ai_vs_ai",
        "ai_color": "white" | "black" | null,
        "ai_level": "iniciante" | "facil" | "medio" | "dificil",
        "clock_minutes": 0,
        "clock_increment": 0,
        "white_time": 300.0,
        "black_time": 300.0,
        "flipped": false,
        "moves": ["e2e4", "e7e5"],
        "clock_history": [[300.0, 300.0], [302.0, 300.0]]
    }

Gravação atômica (arquivo temporário + rename), igual a
``settings.py``.  Arquivos corrompidos/incompatíveis são movidos
para quarentena (``corrupt_<stamp>.json``) e o problema é
registrado no log — nunca destruídos silenciosamente.

Este módulo **não importa pygame** — é puro Python.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import chess

from xadtitans.storage.paths import autosave_file
from xadtitans.utils.logger import get_logger

# ── Versão do formato ───────────────────────────────────
SAVE_VERSION = 1

# Valores válidos (nomes em minúsculas, como no restante do storage).
_MODES = ("human_vs_human", "human_vs_ai", "ai_vs_ai")
_LEVELS = ("iniciante", "facil", "medio", "dificil")
_AI_COLORS = ("white", "black")

# Campos obrigatórios (além de "version" e "moves").
_REQUIRED = (
    "mode",
    "ai_color",
    "ai_level",
    "clock_minutes",
    "clock_increment",
    "white_time",
    "black_time",
    "flipped",
)


# ── gravação ────────────────────────────────────────────

def save_state(data: dict[str, Any]) -> None:
    """Grava o estado da partida em ``autosave/game.json`` (atômico).

    Raises:
        OSError: se não for possível gravar.
    """
    target = autosave_file()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        {"version": SAVE_VERSION, **data},
        indent=2,
        ensure_ascii=False,
    )

    # Escrita atômica: temporário no mesmo diretório + replace.
    fd, tmp_name = tempfile.mkstemp(
        dir=target.parent, suffix=".tmp", prefix="autosave_"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        try:
            tmp_path.replace(target)
        except OSError:
            # No Windows, replace falha se o destino estiver travado.
            target.unlink(missing_ok=True)
            tmp_path.rename(target)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def delete_autosave() -> None:
    """Remove o autosave (partida finalizada ou nova partida)."""
    autosave_file().unlink(missing_ok=True)


def autosave_exists() -> bool:
    """True se existe arquivo de autosave."""
    return autosave_file().exists()


# ── leitura e validação ─────────────────────────────────

def load_state() -> dict[str, Any] | None:
    """Carrega e valida o autosave.

    Returns:
        Dicionário normalizado do estado, ou ``None`` se não houver
        autosave ou se ele for inválido/incompatível (nesse caso o
        arquivo é movido para quarentena e o erro é registrado no log).
    """
    target = autosave_file()
    if not target.exists():
        return None

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        _quarantine(target, f"não foi possível ler o JSON ({exc.__class__.__name__})")
        return None

    state = _validate(raw)
    if state is None:
        _quarantine(target, "estrutura/versionamento inválidos")
        return None
    return state


def _quarantine(target: Path, reason: str) -> None:
    """Move o autosave corrompido para a quarentena e registra no log."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    quarantined = target.parent / f"corrupt_{stamp}.json"
    try:
        target.rename(quarantined)
        get_logger().warning(
            "Autosave inválido (%s) — movido para quarentena: %s",
            reason,
            quarantined.name,
        )
    except OSError:
        # Renomear falhou (ex.: arquivo travado): remover é melhor
        # do que deixar o usuário preso com um save quebrado.
        try:
            target.unlink(missing_ok=True)
            get_logger().warning(
                "Autosave inválido (%s) — removido (renomear falhou)", reason
            )
        except OSError:
            get_logger().warning(
                "Autosave inválido (%s) — não foi possível remover", reason
            )


def _validate(raw: Any) -> dict[str, Any] | None:
    """Valida e normaliza o conteúdo do autosave.

    Returns:
        Estado normalizado ou ``None`` se algo estiver errado
        (versão incompatível, campos ausentes, tipos errados,
        valores impossíveis ou lances ilegais).
    """
    if not isinstance(raw, dict):
        return None

    # Versão: só a atual é aceita (compatibilidade falsa, nunca).
    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        return None
    if version != SAVE_VERSION:
        get_logger().warning(
            "Autosave com versão %s (esperada: %s)", version, SAVE_VERSION
        )
        return None

    for key in _REQUIRED:
        if key not in raw:
            return None

    # ── campos escalares ──
    mode = raw["mode"]
    if mode not in _MODES:
        return None

    ai_color = raw["ai_color"]
    if ai_color is not None and ai_color not in _AI_COLORS:
        return None
    if mode != "human_vs_ai":
        ai_color = None  # só faz sentido no modo vs IA

    ai_level = raw["ai_level"]
    if ai_level not in _LEVELS:
        return None

    clock_minutes = raw["clock_minutes"]
    if isinstance(clock_minutes, bool) or not isinstance(clock_minutes, int):
        return None
    if clock_minutes < 0:
        return None

    clock_increment = raw["clock_increment"]
    if isinstance(clock_increment, bool) or not isinstance(clock_increment, int):
        return None
    if clock_increment < 0:
        return None

    white_time = _valid_time(raw["white_time"])
    black_time = _valid_time(raw["black_time"])
    if white_time is None or black_time is None:
        return None
    if clock_minutes == 0:
        # Sem relógio, tempos não fazem sentido.
        white_time = 0.0
        black_time = 0.0

    flipped = raw["flipped"]
    if not isinstance(flipped, bool):
        return None

    # ── lances: replay completo a partir da posição inicial ──
    moves = raw.get("moves")
    if not isinstance(moves, list) or not all(isinstance(m, str) for m in moves):
        return None

    board = chess.Board()
    for uci in moves:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return None
        if move not in board.legal_moves:
            return None
        board.push(move)

    # Autosave de partida já finalizada não deve existir — rejeita
    # (o board só cobre os finais derivados das regras).
    if board.is_game_over():
        get_logger().warning("Autosave rejeitado: posição já finalizada")
        return None

    # ── histórico do relógio (auxiliar para o Undo) ──
    clock_history = _valid_clock_history(raw.get("clock_history"), len(moves))

    return {
        "mode": mode,
        "ai_color": ai_color,
        "ai_level": ai_level,
        "clock_minutes": clock_minutes,
        "clock_increment": clock_increment,
        "white_time": white_time,
        "black_time": black_time,
        "flipped": flipped,
        "moves": moves,
        "clock_history": clock_history,
    }


def _valid_time(value: Any) -> float | None:
    """Tempo restante: número não-negativo (bool não conta)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if value < 0 else float(value)
    return None


def _valid_clock_history(
    value: Any, n_moves: int
) -> list[tuple[float, float]] | None:
    """Histórico de tempos do relógio (um par por lance).

    Aceita ``None``/ausente. Se estiver malformado ou com tamanho
    incompatível, retorna ``None`` (o Undo apenas perde a restauração
    exata do relógio — nada crítico).
    """
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != n_moves:
        return None
    history: list[tuple[float, float]] = []
    for entry in value:
        if not isinstance(entry, list) or len(entry) != 2:
            return None
        w = _valid_time(entry[0])
        b = _valid_time(entry[1])
        if w is None or b is None:
            return None
        history.append((w, b))
    return history
