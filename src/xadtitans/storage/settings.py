"""Gerenciamento de ``settings.json`` do XadTitans.

Fornece leitura, escrita, atualização e recuperação automática
de configurações do jogo. Valores padrão são usados quando o
arquivo está ausente ou corrompido.

Formato do JSON::

    {
        "volume": 0.8,
        "animation_speed": 1.0,
        "fps": 30,
        "resolution": [1024, 768],
        "visual_hints": true
    }

Este módulo **não importa pygame** — é puro Python.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from xadtitans.storage.paths import settings_path

# ── Valores padrão ──────────────────────────────────────

DEFAULTS: dict[str, Any] = {
    "volume": 0.8,
    "animation_speed": 1.0,
    "fps": 30,
    "resolution": [1024, 768],
    "visual_hints": True,
}

# Tipos esperados para cada chave (para validação).
_TYPES: dict[str, type] = {
    "volume": (int, float),
    "animation_speed": (int, float),
    "fps": int,
    "resolution": list,
    "visual_hints": bool,
}

# Limites razoáveis.
_BOUNDS: dict[str, tuple[float, float]] = {
    "volume": (0.0, 1.0),
    "animation_speed": (0.1, 5.0),
    "fps": (15, 120),
}


def _valid_resolution(value: Any) -> bool:
    """Valida uma resolução: lista com dois inteiros positivos."""
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(
            isinstance(v, int) and not isinstance(v, bool) and v > 0
            for v in value
        )
    )


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    """Valida e normaliza um dicionário de configurações.

    Chaves desconhecidas são removidas. Tipos incorretos ou
    valores fora dos limites são substituídos pelos padrões.
    """
    result: dict[str, Any] = {}
    for key, default in DEFAULTS.items():
        value = data.get(key, default)

        # bool é subclasse de int — não vale para chaves numéricas.
        if key != "visual_hints" and isinstance(value, bool):
            result[key] = default
            continue

        # Tipo correto?
        expected = _TYPES[key]
        if not isinstance(value, expected):
            result[key] = default
            continue

        # Limite correto?
        if key in _BOUNDS:
            lo, hi = _BOUNDS[key]
            if not (lo <= value <= hi):  # type: ignore[operator]
                result[key] = default
                continue

        # resolution: dois inteiros positivos.
        if key == "resolution" and not _valid_resolution(value):
            result[key] = list(default)
            continue

        result[key] = value

    return result


class Settings:
    """Gerenciador de configurações com persistência em JSON.

    Uso::

        settings = Settings()
        settings.load()            # lê do arquivo (ou usa defaults)
        settings.set("volume", 0.5)
        settings.save()            # grava no arquivo
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or settings_path()
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._loaded = False

    @property
    def data(self) -> dict[str, Any]:
        """Cópia somente-leitura dos dados atuais."""
        return dict(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém o valor de uma configuração."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Define o valor de uma configuração (em memória)."""
        self._data[key] = value

    def set_many(self, updates: dict[str, Any]) -> None:
        """Define múltiplas configurações (em memória)."""
        self._data.update(updates)

    def reset(self) -> None:
        """Restaura todas as configurações para os valores padrão."""
        self._data = dict(DEFAULTS)
        self._loaded = True

    def load(self) -> dict[str, Any]:
        """Carrega configurações do arquivo.

        Se o arquivo não existir ou estiver corrompido, usa os
        valores padrão sem levantar exceção.

        Returns:
            Dicionário com as configurações carregadas.
        """
        try:
            text = self._path.read_text(encoding="utf-8")
            raw = json.loads(text)
            if not isinstance(raw, dict):
                raise TypeError("Esperado um objeto JSON")
            self._data = _validate(raw)
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            self._data = dict(DEFAULTS)

        self._loaded = True
        return self.data

    def save(self) -> None:
        """Grava as configurações no arquivo de forma atômica.

        Usa escrita em arquivo temporário + rename para evitar
        corrupção em caso de falha durante a gravação.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        content = json.dumps(self._data, indent=2, ensure_ascii=False)

        # Escrita atômica via arquivo temporário no mesmo diretório.
        fd, tmp_path = tempfile.mkstemp(
            dir=self._path.parent,
            suffix=".tmp",
            prefix="settings_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            # No Windows, rename falha se o destino já existe;
            # nesse caso, remove primeiro.
            try:
                Path(tmp_path).replace(self._path)
            except OSError:
                self._path.unlink(missing_ok=True)
                Path(tmp_path).rename(self._path)
        except BaseException:
            # Limpa o arquivo temporário em caso de erro.
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
            raise
