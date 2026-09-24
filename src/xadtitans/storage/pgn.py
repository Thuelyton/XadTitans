"""Leitura e gravação de partidas em formato PGN.

Utiliza ``python-chess.pgn`` para exportação e importação de partidas.
Fornece uma API simples para gravar partidas do XadTitans e carregá-las
de volta, incluindo headers, histórico de lances e resultado.

Este módulo **não importa pygame** — é puro Python.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import TYPE_CHECKING

import chess
import chess.pgn

from xadtitans.storage.paths import pgn_dir

if TYPE_CHECKING:
    from xadtitans.core.game import Game


def export_game(
    game: Game,
    *,
    event: str = "XadTitans",
    site: str = "Local",
    white: str = "Brancas",
    black: str = "Pretas",
    result: str | None = None,
) -> str:
    """Exporta uma partida para o formato PGN (string).

    Args:
        game: Instância de ``Game`` com o histórico de lances.
        event: Nome do evento/torneio.
        site: Local da partida.
        white: Nome do jogador de brancas.
        black: Nome do jogador de pretas.
        result: Resultado PGN (``"1-0"``, ``"0-1"``, ``"1/2-1/2"``,
            ``"*"``). Se ``None``, é derivado do estado do jogo.

    Returns:
        String PGN completa.
    """
    pgn_game = chess.pgn.Game()

    # Headers.
    pgn_game.headers["Event"] = event
    pgn_game.headers["Site"] = site
    pgn_game.headers["Round"] = "1"

    # Resultado.
    if result is None:
        result = _derive_result(game)
    pgn_game.headers["Result"] = result

    # Nomes dos jogadores (podem ser sobrescritos depois).
    pgn_game.headers["White"] = white
    pgn_game.headers["Black"] = black

    # Reconstruir a partida a partir do histórico de lances.
    node = pgn_game
    for move in game.board.move_stack:
        node = node.add_variation(move)

    return str(pgn_game) + "\n"


def save_game(
    game: Game,
    filepath: Path | str | None = None,
    *,
    event: str = "XadTitans",
    white: str = "Brancas",
    black: str = "Pretas",
) -> Path:
    """Salva uma partida em arquivo PGN.

    Se ``filepath`` não for informado, gera um nome automático
    no diretório de PGNs.

    Returns:
        Caminho do arquivo salvo.
    """
    pgn_content = export_game(
        game, event=event, white=white, black=black,
    )

    if filepath is None:
        target_dir = pgn_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        # Nome automático com data/hora; sufixo numérico evita
        # sobrescrever partidas salvas no mesmo segundo.
        stamp = time.strftime("%Y%m%d_%H%M%S")
        filepath = target_dir / f"partida_{stamp}.pgn"
        counter = 2
        while filepath.exists():
            filepath = target_dir / f"partida_{stamp}_{counter}.pgn"
            counter += 1
    else:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

    filepath.write_text(pgn_content, encoding="utf-8")
    return filepath


def load_game(
    filepath: Path | str,
) -> chess.pgn.Game | None:
    """Carrega uma partida de um arquivo PGN.

    Returns:
        Objeto ``chess.pgn.Game`` ou ``None`` se o arquivo não
        existir ou não puder ser parseado.
    """
    filepath = Path(filepath)
    try:
        text = filepath.read_text(encoding="utf-8")
        return chess.pgn.read_game(io.StringIO(text))
    except (OSError, ValueError):
        return None


def parse_pgn_string(pgn_text: str) -> chess.pgn.Game | None:
    """Analisa uma string PGN e retorna o jogo.

    Returns:
        Objeto ``chess.pgn.Game`` ou ``None`` se o PGN for inválido.
    """
    try:
        return chess.pgn.read_game(io.StringIO(pgn_text))
    except (ValueError, UnicodeDecodeError):
        return None


def reconstruct_board(pgn_game: chess.pgn.Game) -> chess.Board:
    """Reconstrói a posição final de uma partida PGN.

    Returns:
        ``chess.Board`` na posição final da partida.
    """
    board = pgn_game.board()
    for move in pgn_game.mainline_moves():
        board.push(move)
    return board


def get_result_string(game: Game) -> str:
    """Deriva o resultado PGN a partir do estado do jogo.

    Returns:
        ``"1-0"``, ``"0-1"``, ``"1/2-1/2"`` ou ``"*"``.
    """
    return _derive_result(game)


def _derive_result(game: Game) -> str:
    """Deriva o resultado PGN a partir do estado do jogo."""
    result = game.result()
    if result is None:
        return "*"
    if result.is_draw:
        return "1/2-1/2"
    if result.winner is chess.WHITE:
        return "1-0"
    return "0-1"


def list_pgn_files() -> list[Path]:
    """Lista todos os arquivos PGN no diretório de PGNs."""
    d = pgn_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.pgn"))
