"""Logging em arquivo para o XadTitans.

Grava em ``<APPDATA>/XadTitans/logs/xadtitans.log`` (Windows)
ou em ``~/.xadtitans/logs/xadtitans.log`` como plano B.
"""

from __future__ import annotations

import logging
from pathlib import Path

_logger: logging.Logger | None = None

_APP_NAME = "XadTitans"
_LOG_DIR_NAME = "logs"
_LOG_FILE = "xadtitans.log"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_BACKUP_COUNT = 2


def _data_dir() -> Path:
    """Pasta de dados do usuário (%APPDATA%/XadTitans ou equivalente)."""
    import os

    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / _APP_NAME
    return Path.home() / f".{_APP_NAME.lower()}"


def get_logger() -> logging.Logger:
    """Retorna (e cria na primeira chamada) o logger do XadTitans."""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger("xadtitans")
    _logger.setLevel(logging.DEBUG)

    log_dir = _data_dir() / _LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / _LOG_FILE

    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(
        log_path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    _logger.addHandler(handler)

    # Também loga no stderr para debug durante desenvolvimento
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    _logger.addHandler(stderr_handler)

    _logger.info("Logger iniciado → %s", log_path)
    return _logger
