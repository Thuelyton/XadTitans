"""Configuração global da suíte de testes.

1. Isola o diretório de dados do XadTitans em um diretório temporário
   por sessão, **antes de qualquer import de xadtitans**: nenhum teste
   lê ou grava em ``%APPDATA%`` real (settings, autosave, PGN, logs).

2. Limpa o estado persistente (autosave, PGNs, settings, stats)
   antes e depois de **cada** teste — os testes não podem poluir uns
   aos outros via arquivos em disco. O log não é apagado: é só
   anexo (append) e cada teste verifica apenas o que escreveu.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile

import pytest

# Deve executar antes do primeiro import de xadtitans (paths.py resolve
# DATA_DIR no momento da importação).
_TMP_DATA_DIR = tempfile.mkdtemp(prefix="xadtitans_test_data_")
os.environ["XADTITANS_DATA"] = _TMP_DATA_DIR


def _cleanup_session() -> None:
    shutil.rmtree(_TMP_DATA_DIR, ignore_errors=True)


atexit.register(_cleanup_session)


def _clear_persistent_state() -> None:
    """Apaga autosave, PGNs, settings e stats do diretório isolado."""
    from xadtitans.storage import paths

    for sub in ("autosave", "pgn"):
        target = paths.DATA_DIR / sub
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    for name in ("settings.json", "stats.json"):
        (paths.DATA_DIR / name).unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _isolated_persistent_state():
    """Estado persistente limpo antes e depois de cada teste."""
    _clear_persistent_state()
    yield
    _clear_persistent_state()
