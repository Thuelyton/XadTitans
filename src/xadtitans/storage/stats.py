"""Gerenciamento de ``stats.json`` do XadTitans.

Armazena estatísticas de vitórias, derrotas e empates, segmentadas
por modo de jogo e nível de dificuldade (quando aplicável).

Formato do JSON::

    {
        "total": {"wins": 0, "losses": 0, "draws": 0},
        "by_mode": {
            "human_vs_human": {"wins": 0, "losses": 0, "draws": 0},
            "human_vs_ai":   {"wins": 0, "losses": 0, "draws": 0},
            "ai_vs_ai":      {"wins": 0, "losses": 0, "draws": 0}
        },
        "by_level": {
            "iniciante": {"wins": 0, "losses": 0, "draws": 0},
            "facil":     {"wins": 0, "losses": 0, "draws": 0},
            "medio":     {"wins": 0, "losses": 0, "draws": 0},
            "dificil":   {"wins": 0, "losses": 0, "draws": 0}
        }
    }

Este módulo **não importa pygame** — é puro Python.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from xadtitans.storage.paths import stats_path

# ── Chaves de resultado ─────────────────────────────────
_RESULT_KEYS = ("wins", "losses", "draws")

# ── Modos de jogo ───────────────────────────────────────
_MODE_KEYS = ("human_vs_human", "human_vs_ai", "ai_vs_ai")

# ── Níveis de dificuldade ───────────────────────────────
_LEVEL_KEYS = ("iniciante", "facil", "medio", "dificil")


def _empty_bucket() -> dict[str, int]:
    """Cria um bucket zerado para vitórias/derrotas/empates."""
    return {"wins": 0, "losses": 0, "draws": 0}


def _empty_stats() -> dict[str, Any]:
    """Cria a estrutura completa de estatísticas zerada."""
    return {
        "total": _empty_bucket(),
        "by_mode": {k: _empty_bucket() for k in _MODE_KEYS},
        "by_level": {k: _empty_bucket() for k in _LEVEL_KEYS},
    }


def _valid_count(value: Any) -> bool:
    """Valida um contador: inteiro não-negativo (bool não conta)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _merge_bucket(
    target: dict[str, int], source: Any,
) -> None:
    """Copia contadores válidos de ``source`` para ``target``."""
    if not isinstance(source, dict):
        return
    for key in _RESULT_KEYS:
        val = source.get(key, 0)
        if _valid_count(val):
            target[key] = val


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    """Valida e normaliza dados carregados de stats.json.

    Aceita parcialidade: campos ausentes recebem defaults.
    """
    result = _empty_stats()

    # Total.
    _merge_bucket(result["total"], data.get("total"))

    # Por modo.
    by_mode = data.get("by_mode")
    if isinstance(by_mode, dict):
        for mode in _MODE_KEYS:
            _merge_bucket(result["by_mode"][mode], by_mode.get(mode))

    # Por nível.
    by_level = data.get("by_level")
    if isinstance(by_level, dict):
        for level in _LEVEL_KEYS:
            _merge_bucket(result["by_level"][level], by_level.get(level))

    return result


class Stats:
    """Gerenciador de estatísticas com persistência em JSON.

    Uso::

        stats = Stats()
        stats.load()
        stats.record_win("human_vs_ai", level="medio")
        stats.save()
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or stats_path()
        self._data: dict[str, Any] = _empty_stats()

    @property
    def total(self) -> dict[str, int]:
        """Estatísticas totais (vistas por referência interna)."""
        return self._data["total"]

    @property
    def by_mode(self) -> dict[str, dict[str, int]]:
        """Estatísticas por modo de jogo."""
        return self._data["by_mode"]

    @property
    def by_level(self) -> dict[str, dict[str, int]]:
        """Estatísticas por nível de dificuldade."""
        return self._data["by_level"]

    def get_total(self) -> dict[str, int]:
        """Retorna cópia das estatísticas totais."""
        return dict(self._data["total"])

    def get_mode(self, mode: str) -> dict[str, int]:
        """Retorna cópia das estatísticas de um modo específico."""
        bucket = self._data["by_mode"].get(mode)
        if bucket is None:
            return _empty_bucket()
        return dict(bucket)

    def get_level(self, level: str) -> dict[str, int]:
        """Retorna cópia das estatísticas de um nível específico."""
        bucket = self._data["by_level"].get(level)
        if bucket is None:
            return _empty_bucket()
        return dict(bucket)

    def record_win(
        self, mode: str, *, level: str | None = None,
    ) -> None:
        """Registra uma vitória."""
        self._data["total"]["wins"] += 1
        if mode in _MODE_KEYS:
            self._data["by_mode"][mode]["wins"] += 1
        if level and level in _LEVEL_KEYS:
            self._data["by_level"][level]["wins"] += 1

    def record_loss(
        self, mode: str, *, level: str | None = None,
    ) -> None:
        """Registra uma derrota."""
        self._data["total"]["losses"] += 1
        if mode in _MODE_KEYS:
            self._data["by_mode"][mode]["losses"] += 1
        if level and level in _LEVEL_KEYS:
            self._data["by_level"][level]["losses"] += 1

    def record_draw(
        self, mode: str, *, level: str | None = None,
    ) -> None:
        """Registra um empate."""
        self._data["total"]["draws"] += 1
        if mode in _MODE_KEYS:
            self._data["by_mode"][mode]["draws"] += 1
        if level and level in _LEVEL_KEYS:
            self._data["by_level"][level]["draws"] += 1

    def load(self) -> dict[str, Any]:
        """Carrega estatísticas do arquivo.

        Se o arquivo não existir ou estiver corrompido, usa
        valores zerados sem levantar exceção.
        """
        try:
            text = self._path.read_text(encoding="utf-8")
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise TypeError("Esperado um objeto JSON")
            self._data = _validate(raw)
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            self._data = _empty_stats()

        return self.data

    @property
    def data(self) -> dict[str, Any]:
        """Cópia profunda dos dados atuais."""
        return json.loads(json.dumps(self._data))

    def save(self) -> None:
        """Grava as estatísticas no arquivo de forma atômica."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        content = json.dumps(self._data, indent=2, ensure_ascii=False)

        fd, tmp_path = tempfile.mkstemp(
            dir=self._path.parent,
            suffix=".tmp",
            prefix="stats_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            try:
                Path(tmp_path).replace(self._path)
            except OSError:
                self._path.unlink(missing_ok=True)
                Path(tmp_path).rename(self._path)
        except BaseException:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def reset(self) -> None:
        """Zera todas as estatísticas (em memória)."""
        self._data = _empty_stats()
