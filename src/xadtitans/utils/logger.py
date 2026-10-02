"""Logging centralizado do XadTitans.

Grava em ``<diretório de dados>/logs/xadtitans.log`` — o diretório de
dados vem de ``storage/paths.py`` (``%APPDATA%\\XadTitans`` no Windows,
com fallback local e suporte a ``XADTITANS_DATA`` para testes/CI).

Rotação automática via ``logging.handlers.RotatingFileHandler``
(biblioteca padrão): limita o tamanho do arquivo e mantém no máximo
``_BACKUP_COUNT`` arquivos antigos (``xadtitans.log.1``, ``.2``...),
funcionando no Windows.

O nível do log pode ser configurado pela variável de ambiente
``XADTITANS_LOG_LEVEL`` (DEBUG/INFO/WARNING/ERROR; padrão INFO).

Não registra dados sensíveis — apenas mensagens de diagnóstico.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logger: logging.Logger | None = None

_LOG_DIR_NAME = "logs"
_LOG_FILE = "xadtitans.log"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB por arquivo
_BACKUP_COUNT = 2  # xadtitans.log.1, xadtitans.log.2

_VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
_DEFAULT_LEVEL = "INFO"


def _log_level() -> int:
    """Nível do logger: variável ``XADTITANS_LOG_LEVEL`` (padrão INFO)."""
    level = os.environ.get("XADTITANS_LOG_LEVEL", _DEFAULT_LEVEL).upper()
    if level not in _VALID_LEVELS:
        level = _DEFAULT_LEVEL
    return getattr(logging, level)


def log_path() -> Path:
    """Caminho do arquivo de log (dentro do diretório de dados)."""
    return log_dir() / _LOG_FILE


def log_dir() -> Path:
    """Diretório de logs — dentro do diretório de dados (paths.py)."""
    from xadtitans.storage.paths import ensure_data_dir

    return ensure_data_dir() / _LOG_DIR_NAME


def get_logger() -> logging.Logger:
    """Retorna (e cria na primeira chamada) o logger do XadTitans."""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger("xadtitans")
    _logger.setLevel(_log_level())

    log_dir().mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path(),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    _logger.addHandler(handler)

    # Também loga no stderr para debug durante o desenvolvimento.
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    _logger.addHandler(stderr_handler)

    _logger.info("Logger iniciado → %s", log_path())
    return _logger


def reset_logger() -> None:
    """Fecha e remove os handlers atuais (uso em testes).

    A próxima chamada a ``get_logger()`` recria o logger com os
    parâmetros atuais do módulo (``_MAX_BYTES`` etc.).
    """
    global _logger
    if _logger is not None:
        for h in list(_logger.handlers):
            _logger.removeHandler(h)
            h.close()
    _logger = None
