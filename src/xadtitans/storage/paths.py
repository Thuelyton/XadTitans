"""Resolução segura de diretórios de dados do XadTitans.

Fornece caminhos para configurações, estatísticas, autosave e PGN
dentro de ``%APPDATA%\\XadTitans`` (Windows) ou equivalente.
Utiliza fallback local caso o diretório de dados não possa ser criado.

Este módulo **não cria diretórios** durante a importação — apenas
resolve caminhos. Os diretórios são criados sob demanda pelas
camadas que efetivamente gravam dados.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Nome do diretório de dados ──────────────────────────
_APP_NAME = "XadTitans"

# ── Fallback: diretório local ao lado do projeto ────────
# paths.py está em <projeto>/src/xadtitans/storage/ → parents[3]
# é a raiz do projeto (nunca dentro de src/).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_FALLBACK = _PROJECT_ROOT / ".xadtitans_data"


def _resolve_data_dir() -> Path:
    """Resolve o diretório principal de dados.

    Prioridade:
      1. Variável de ambiente ``XADTITANS_DATA`` (para testes/CI).
      2. ``%APPDATA%\\XadTitans`` (Windows) ou ``~/.config/XadTitans``
         (Linux/Mac).
      3. Fallback local ``.xadtitans_data/`` ao lado do projeto.

    O diretório **não é criado** aqui — apenas o caminho é retornado.
    """
    # 1. Variável de ambiente explícita (testes/CI).
    env = os.environ.get("XADTITANS_DATA")
    if env:
        return Path(env)

    # 2. Diretório padrão do sistema.
    try:
        if os.name == "nt":
            base = os.environ.get("APPDATA")
            if base:
                return Path(base) / _APP_NAME
        else:
            return Path.home() / ".config" / _APP_NAME
    except Exception:  # noqa: BLE001
        # Não foi possível resolver o home — usar fallback local.
        return _LOCAL_FALLBACK

    # 3. Fallback local (ex.: Windows sem APPDATA definido).
    return _LOCAL_FALLBACK


# ── Diretório raiz de dados (resolvido uma vez) ─────────
DATA_DIR: Path = _resolve_data_dir()


def ensure_data_dir() -> Path:
    """Garante que o diretório de dados existe e retorna o caminho.

    Cria o diretório (e pais) se necessário. Em caso de falha de
    permissão, retorna o fallback local.
    """
    global DATA_DIR

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR
    except OSError:
        # Fallback local se não conseguir criar o diretório principal.
        DATA_DIR = _LOCAL_FALLBACK
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR


# ── Caminhos derivados ──────────────────────────────────

def settings_path() -> Path:
    """Caminho do arquivo ``settings.json``."""
    return DATA_DIR / "settings.json"


def stats_path() -> Path:
    """Caminho do arquivo ``stats.json``."""
    return DATA_DIR / "stats.json"


def autosave_path() -> Path:
    """Caminho do diretório de autosave (partida atual)."""
    return DATA_DIR / "autosave"


def autosave_file() -> Path:
    """Caminho do arquivo de autosave da partida atual."""
    return autosave_path() / "game.json"


def pgn_dir() -> Path:
    """Caminho do diretório de arquivos PGN salvos."""
    return DATA_DIR / "pgn"
