"""Camada de persistência do XadTitans.

Módulos:
  - ``paths``: resolução de diretórios de dados;
  - ``settings``: gerenciamento de ``settings.json``;
  - ``stats``: gerenciamento de ``stats.json``;
  - ``pgn``: leitura/gravação de partidas em PGN.
"""

from xadtitans.storage.paths import (
    DATA_DIR,
    autosave_file,
    autosave_path,
    ensure_data_dir,
    pgn_dir,
    settings_path,
    stats_path,
)
from xadtitans.storage.pgn import (
    export_game,
    get_result_string,
    list_pgn_files,
    load_game,
    parse_pgn_string,
    reconstruct_board,
    save_game,
)
from xadtitans.storage.settings import Settings
from xadtitans.storage.stats import Stats

__all__ = [
    "DATA_DIR",
    "Settings",
    "Stats",
    "autosave_file",
    "autosave_path",
    "ensure_data_dir",
    "export_game",
    "get_result_string",
    "list_pgn_files",
    "load_game",
    "parse_pgn_string",
    "pgn_dir",
    "reconstruct_board",
    "save_game",
    "settings_path",
    "stats_path",
]
