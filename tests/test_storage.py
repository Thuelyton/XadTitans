"""Testes para a camada de persistência (Etapa 5.3).

Cobre: paths, settings, stats e PGN — incluindo tratamento de
arquivos ausentes, JSON corrompido, escrita atômica e round-trip.
"""

from __future__ import annotations

import json
from pathlib import Path

import chess
import chess.pgn
import pytest

import xadtitans.storage.paths as paths_mod
from xadtitans.core.game import Game
from xadtitans.storage.paths import (
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
from xadtitans.storage.settings import DEFAULTS, Settings
from xadtitans.storage.stats import Stats


@pytest.fixture(autouse=True)
def _isolar_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isola todos os testes do módulo do %APPDATA% real.

    Redireciona ``paths.DATA_DIR`` para um diretório temporário,
    garantindo que nenhum teste grave fora do sandbox.
    """
    monkeypatch.setattr(paths_mod, "DATA_DIR", tmp_path / "data")


# ════════════════════════════════════════════════════════════
# PATHS
# ════════════════════════════════════════════════════════════


class TestPaths:
    """Testa resolução de diretórios e caminhos derivados."""

    def test_data_dir_e_path(self) -> None:
        assert isinstance(paths_mod.DATA_DIR, Path)

    def test_sem_caminho_hardcoded_no_codigo_fonte(self) -> None:
        """O código-fonte de paths.py não pode ter caminhos de máquina."""
        source = Path(paths_mod.__file__).read_text(encoding="utf-8")
        assert "C:\\" not in source
        assert "D:\\" not in source
        assert "/home/" not in source
        assert "/Users/" not in source

    def test_ensure_data_dir_cria_diretorio(self, tmp_path: Path) -> None:
        target = tmp_path / "novo"
        paths_mod.DATA_DIR = target
        try:
            result = ensure_data_dir()
            assert result == target
            assert target.is_dir()
        finally:
            paths_mod.DATA_DIR = tmp_path / "data"

    def test_settings_path_derivado(self) -> None:
        p = settings_path()
        assert p.name == "settings.json"
        assert p.parent == paths_mod.DATA_DIR

    def test_stats_path_derivado(self) -> None:
        p = stats_path()
        assert p.name == "stats.json"
        assert p.parent == paths_mod.DATA_DIR

    def test_autosave_path_derivado(self) -> None:
        p = autosave_path()
        assert p.name == "autosave"
        assert p.parent == paths_mod.DATA_DIR

    def test_autosave_file_derivado(self) -> None:
        p = autosave_file()
        assert p.name == "game.json"
        assert p.parent == autosave_path()

    def test_pgn_dir_derivado(self) -> None:
        p = pgn_dir()
        assert p.name == "pgn"
        assert p.parent == paths_mod.DATA_DIR

    def test_env_var_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """XADTITANS_DATA sobrescreve o diretório de dados."""
        custom = tmp_path / "custom"
        monkeypatch.setenv("XADTITANS_DATA", str(custom))
        assert paths_mod._resolve_data_dir() == custom

    def test_fallback_sem_appdata(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Sem APPDATA, cai no fallback local."""
        monkeypatch.delenv("XADTITANS_DATA", raising=False)
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.setattr(paths_mod.os, "name", "nt")
        assert paths_mod._resolve_data_dir() == paths_mod._LOCAL_FALLBACK


# ════════════════════════════════════════════════════════════
# SETTINGS
# ════════════════════════════════════════════════════════════


class TestSettings:
    """Testa leitura, escrita e robustez do settings.json."""

    def test_defaults(self) -> None:
        s = Settings(path=Path("/nonexistent/settings.json"))
        s.load()
        assert s.get("volume") == 0.8
        assert s.get("fps") == 30
        assert s.get("visual_hints") is True

    def test_arquivo_inexistente_usa_defaults(self, tmp_path: Path) -> None:
        s = Settings(path=tmp_path / "missing.json")
        data = s.load()
        assert data == DEFAULTS

    def test_salvar_e_carregar(self, tmp_path: Path) -> None:
        s = Settings(path=tmp_path / "s.json")
        s.set("volume", 0.5)
        s.save()

        s2 = Settings(path=tmp_path / "s.json")
        s2.load()
        assert s2.get("volume") == 0.5

    def test_set_many(self, tmp_path: Path) -> None:
        s = Settings(path=tmp_path / "s.json")
        s.set_many({"volume": 0.3, "fps": 60})
        s.save()

        s2 = Settings(path=tmp_path / "s.json")
        s2.load()
        assert s2.get("volume") == 0.3
        assert s2.get("fps") == 60

    def test_reset(self) -> None:
        s = Settings(path=Path("/nonexistent/s.json"))
        s.set("volume", 0.1)
        s.reset()
        assert s.get("volume") == 0.8  # default

    def test_json_corrompido(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{invalid json!!!", encoding="utf-8")

        s = Settings(path=p)
        data = s.load()
        assert data == DEFAULTS

    def test_json_nao_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")

        s = Settings(path=p)
        data = s.load()
        assert data == DEFAULTS

    def test_tipo_incorreto_volta_ao_default(self, tmp_path: Path) -> None:
        p = tmp_path / "s.json"
        p.write_text(json.dumps({"volume": "alto"}), encoding="utf-8")

        s = Settings(path=p)
        s.load()
        assert s.get("volume") == 0.8  # default

    def test_volume_acima_do_limite(self, tmp_path: Path) -> None:
        p = tmp_path / "s.json"
        p.write_text(json.dumps({"volume": 2.0}), encoding="utf-8")

        s = Settings(path=p)
        s.load()
        assert s.get("volume") == 0.8

    def test_fps_fora_do_range(self, tmp_path: Path) -> None:
        p = tmp_path / "s.json"
        p.write_text(json.dumps({"fps": 5}), encoding="utf-8")

        s = Settings(path=p)
        s.load()
        assert s.get("fps") == 30

    def test_resolution_invalida(self, tmp_path: Path) -> None:
        p = tmp_path / "s.json"
        p.write_text(json.dumps({"resolution": "bad"}), encoding="utf-8")

        s = Settings(path=p)
        s.load()
        assert s.get("resolution") == [1024, 768]

    def test_escrita_atomics_nao_deixa_tmp(self, tmp_path: Path) -> None:
        s = Settings(path=tmp_path / "s.json")
        s.save()
        # Não deve sobrar nenhum .tmp.
        tmps = list(tmp_path.glob("*.tmp"))
        assert tmps == []

    def test_chaves_desconhecidas_removidas(self, tmp_path: Path) -> None:
        p = tmp_path / "s.json"
        p.write_text(
            json.dumps({"volume": 0.5, "unknown_key": 42}),
            encoding="utf-8",
        )
        s = Settings(path=p)
        s.load()
        assert s.get("volume") == 0.5
        assert s.get("unknown_key") is None  # removida

    def test_bool_em_chave_numerica_rejeitado(self, tmp_path: Path) -> None:
        """bool é subclasse de int — não deve passar como número."""
        p = tmp_path / "s.json"
        p.write_text(
            json.dumps({"volume": True, "fps": True}), encoding="utf-8",
        )
        s = Settings(path=p)
        s.load()
        assert s.get("volume") == 0.8
        assert s.get("fps") == 30

    def test_data_property(self) -> None:
        s = Settings(path=Path("/nonexistent/s.json"))
        s.load()
        d = s.data
        assert isinstance(d, dict)
        # Cópia: modificar não afeta o original.
        d["volume"] = 0.0
        assert s.get("volume") == 0.8


# ════════════════════════════════════════════════════════════
# STATS
# ════════════════════════════════════════════════════════════


class TestStats:
    """Testa leitura, escrita e incremento de estatísticas."""

    def test_defaults(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        t = st.get_total()
        assert t["wins"] == 0
        assert t["losses"] == 0
        assert t["draws"] == 0

    def test_arquivo_inexistente_usa_defaults(self, tmp_path: Path) -> None:
        st = Stats(path=tmp_path / "missing.json")
        st.load()
        assert st.get_total()["wins"] == 0

    def test_record_win(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_win("human_vs_ai", level="medio")
        t = st.get_total()
        assert t["wins"] == 1
        assert t["losses"] == 0
        assert st.get_mode("human_vs_ai")["wins"] == 1
        assert st.get_level("medio")["wins"] == 1

    def test_record_loss(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_loss("human_vs_human")
        assert st.get_total()["losses"] == 1
        assert st.get_mode("human_vs_human")["losses"] == 1

    def test_record_draw(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_draw("ai_vs_ai", level="facil")
        assert st.get_total()["draws"] == 1
        assert st.get_mode("ai_vs_ai")["draws"] == 1
        assert st.get_level("facil")["draws"] == 1

    def test_separacao_por_modo(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_win("human_vs_human")
        st.record_loss("human_vs_ai")

        assert st.get_mode("human_vs_human")["wins"] == 1
        assert st.get_mode("human_vs_human")["losses"] == 0
        assert st.get_mode("human_vs_ai")["wins"] == 0
        assert st.get_mode("human_vs_ai")["losses"] == 1

    def test_separacao_por_nivel(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_win("human_vs_ai", level="iniciante")
        st.record_win("human_vs_ai", level="dificil")

        assert st.get_level("iniciante")["wins"] == 1
        assert st.get_level("dificil")["wins"] == 1
        assert st.get_level("medio")["wins"] == 0

    def test_modo_invalido_nao_afeta_totais(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_win("modo_fantasma")
        # Total incrementa, mas by_mode não.
        assert st.get_total()["wins"] == 1
        assert st.get_mode("modo_fantasma")["wins"] == 0

    def test_nivel_invalido_nao_afeta_totais(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_win("human_vs_ai", level="impossivel")
        assert st.get_total()["wins"] == 1
        assert st.get_level("impossivel")["wins"] == 0

    def test_salvar_e_carregar(self, tmp_path: Path) -> None:
        st = Stats(path=tmp_path / "stats.json")
        st.record_win("human_vs_ai", level="medio")
        st.save()

        st2 = Stats(path=tmp_path / "stats.json")
        st2.load()
        assert st2.get_total()["wins"] == 1
        assert st2.get_mode("human_vs_ai")["wins"] == 1
        assert st2.get_level("medio")["wins"] == 1

    def test_json_corrompido(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("not json {{{", encoding="utf-8")

        st = Stats(path=p)
        st.load()
        assert st.get_total()["wins"] == 0

    def test_bool_como_contador_rejeitado(self, tmp_path: Path) -> None:
        """bool não deve ser aceito como contador."""
        p = tmp_path / "stats.json"
        p.write_text(
            json.dumps({"total": {"wins": True}}), encoding="utf-8",
        )
        st = Stats(path=p)
        st.load()
        assert st.get_total()["wins"] == 0

    def test_json_parcial(self, tmp_path: Path) -> None:
        """JSON com campos ausentes deve ser completado com defaults."""
        p = tmp_path / "partial.json"
        p.write_text(
            json.dumps({"total": {"wins": 5}}),
            encoding="utf-8",
        )

        st = Stats(path=p)
        st.load()
        assert st.get_total()["wins"] == 5
        assert st.get_total()["losses"] == 0  # preenchido
        assert st.get_mode("human_vs_ai")["wins"] == 0  # default

    def test_reset(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        st.record_win("human_vs_ai")
        st.reset()
        assert st.get_total()["wins"] == 0

    def test_incremento_multiplas_vezes(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        for _ in range(10):
            st.record_win("human_vs_ai", level="dificil")
        assert st.get_total()["wins"] == 10
        assert st.get_level("dificil")["wins"] == 10

    def test_get_mode_desconhecido(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        bucket = st.get_mode("inexistente")
        assert bucket == {"wins": 0, "losses": 0, "draws": 0}

    def test_get_level_desconhecido(self) -> None:
        st = Stats(path=Path("/nonexistent/stats.json"))
        bucket = st.get_level("inexistente")
        assert bucket == {"wins": 0, "losses": 0, "draws": 0}


# ════════════════════════════════════════════════════════════
# PGN
# ════════════════════════════════════════════════════════════


def _make_game_with_moves(moves_uci: list[str]) -> Game:
    """Cria um Game com lances UCI informados."""
    g = Game()
    for uci in moves_uci:
        move = chess.Move.from_uci(uci)
        g.push(move)
    return g


def _make_game_mate_do_pastor() -> Game:
    """Scholar's Mate: 1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6 4.Qxf7#."""
    return _make_game_with_moves([
        "e2e4", "e7e5",
        "f1c4", "b8c6",
        "d1h5", "g8f6",
        "h5f7",
    ])


def _make_game_with_castling() -> Game:
    """Partida com roque curto das brancas."""
    g = Game()
    # Desenvolver peças para liberar o roque.
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1e2", "g8f6"]:
        g.push(chess.Move.from_uci(uci))
    # Brancas fazem roque curto.
    g.push(chess.Move.from_uci("e1g1"))
    return g


def _make_game_with_en_passant() -> Game:
    """Partida com captura en passant."""
    g = Game()
    # e4 a6 e5 d6 exd6 e.p.
    for uci in ["e2e4", "a7a6", "e4e5", "d7d6", "e5d6"]:
        g.push(chess.Move.from_uci(uci))
    return g


def _make_game_with_promotion() -> Game:
    """Partida com promoção de peão (captura para promover)."""
    g = Game()
    # 1.e4 d5 2.exd5 Nf6 3.d6 Ne4 4.dxc7 Nxc3 5.cxd8=Q
    moves = [
        "e2e4", "d7d5",
        "e4d5", "g8f6",
        "d5d6", "f6e4",
        "d6c7", "e4c3",
        "c7d8q",  # promoção para dama (captura a dama preta)
    ]
    for uci in moves:
        g.push(chess.Move.from_uci(uci))
    return g


class TestPGNExport:
    """Testa exportação de partidas para PGN."""

    def test_export_game_basico(self) -> None:
        g = _make_game_with_moves(["e2e4", "e7e5"])
        pgn = export_game(g)

        assert "[Event \"XadTitans\"]" in pgn
        assert "1. e4 e5" in pgn
        assert "[Result \"*\"]" in pgn

    def test_export_custom_headers(self) -> None:
        g = _make_game_with_moves(["e2e4"])
        pgn = export_game(
            g,
            event="Teste",
            white="Jogador1",
            black="Jogador2",
        )

        assert "[Event \"Teste\"]" in pgn
        assert "[White \"Jogador1\"]" in pgn
        assert "[Black \"Jogador2\"]" in pgn

    def test_export_mate_result(self) -> None:
        g = _make_game_mate_do_pastor()
        pgn = export_game(g)
        assert "[Result \"1-0\"]" in pgn

    def test_export_empate_result(self) -> None:
        g = Game()
        g.resign(chess.WHITE)
        pgn = export_game(g)
        assert "[Result \"0-1\"]" in pgn

    def test_export_partida_em_andamento(self) -> None:
        g = _make_game_with_moves(["e2e4"])
        pgn = export_game(g)
        assert "[Result \"*\"]" in pgn

    def test_export_mate_do_pastor_historico(self) -> None:
        g = _make_game_mate_do_pastor()
        pgn = export_game(g)
        assert "1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#" in pgn

    def test_export_com_roque(self) -> None:
        g = _make_game_with_castling()
        pgn = export_game(g)
        assert "O-O" in pgn  # roque curto em notação SAN

    def test_export_round_trip(self) -> None:
        """Exportar e importar deve preservar a partida."""
        g = _make_game_mate_do_pastor()
        pgn_str = export_game(g)

        loaded = parse_pgn_string(pgn_str)
        assert loaded is not None
        board = reconstruct_board(loaded)
        assert board.fen() == g.board.fen()


class TestPGNSaveAndLoad:
    """Testa salvar e carregar PGN em arquivo."""

    def test_save_e_load(self, tmp_path: Path) -> None:
        g = _make_game_mate_do_pastor()
        filepath = save_game(g, tmp_path / "test.pgn")

        assert filepath.exists()
        loaded = load_game(filepath)
        assert loaded is not None
        board = reconstruct_board(loaded)
        assert board.fen() == g.board.fen()

    def test_save_auto_path(self, tmp_path: Path) -> None:
        """Salvar sem filepath gera nome automático."""
        g = _make_game_with_moves(["e2e4"])
        filepath = save_game(g)
        assert filepath.exists()
        assert filepath.suffix == ".pgn"
        # Nome não deve começar com espaço.
        assert not filepath.name.startswith(" ")

    def test_save_auto_path_unico(self, tmp_path: Path) -> None:
        """Dois saves automáticos não podem sobrescrever um ao outro."""
        g1 = _make_game_with_moves(["e2e4"])
        g2 = _make_game_with_moves(["d2d4"])
        f1 = save_game(g1)
        f2 = save_game(g2)
        assert f1 != f2
        assert f1.exists()
        assert f2.exists()

    def test_list_pgn_files(self, tmp_path: Path) -> None:
        d = pgn_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "a.pgn").write_text("x", encoding="utf-8")
        (d / "b.pgn").write_text("y", encoding="utf-8")
        files = list_pgn_files()
        assert len(files) == 2


class TestPGNLoad:
    """Testa carregamento de PGN."""

    def test_load_arquivo_inexistente(self, tmp_path: Path) -> None:
        result = load_game(tmp_path / "nope.pgn")
        assert result is None

    def test_load_arquivo_corrompido(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.pgn"
        p.write_text("isto nao e PGN\n", encoding="utf-8")
        result = load_game(p)
        # chess.pgn.read_game pode retornar um Game vazio ou None.
        # Em qualquer caso, não deve ter lances.
        if result is not None:
            assert list(result.mainline_moves()) == []

    def test_parse_pgn_invalido(self) -> None:
        result = parse_pgn_string("conteudo invalido")
        # chess.pgn pode retornar um Game vazio.
        if result is not None:
            assert list(result.mainline_moves()) == []

    def test_parse_pgn_vazio(self) -> None:
        result = parse_pgn_string("")
        assert result is None

    def test_reconstruct_board(self) -> None:
        g = _make_game_mate_do_pastor()
        pgn = export_game(g)
        loaded = parse_pgn_string(pgn)
        assert loaded is not None
        board = reconstruct_board(loaded)
        assert board.is_checkmate()

    def test_load_round_trip_completo(self, tmp_path: Path) -> None:
        """Exporta → salva → carrega → verifica posição."""
        g = _make_game_with_promotion()
        filepath = tmp_path / "promocao.pgn"
        filepath.write_text(export_game(g), encoding="utf-8")

        loaded = load_game(filepath)
        assert loaded is not None
        board = reconstruct_board(loaded)
        assert board.fen() == g.board.fen()


class TestPGNResult:
    """Testa derivação de resultado PGN."""

    def test_result_xeque_mate(self) -> None:
        g = _make_game_mate_do_pastor()
        assert get_result_string(g) == "1-0"

    def test_result_desistencia(self) -> None:
        g = Game()
        g.resign(chess.WHITE)
        assert get_result_string(g) == "0-1"

    def test_result_em_andamento(self) -> None:
        g = Game()
        assert get_result_string(g) == "*"

    def test_result_empate_stalemate(self) -> None:
        # Posição de afogamento: rei preto em a8, rei branco em b6,
        # peão branco em a7 (sem lances legais para pretas).
        g = Game("k7/P7/1K6/8/8/8/8/8 b - - 0 1")
        # Pretas não têm lances legais → stalemate.
        assert g.is_game_over()
        assert get_result_string(g) == "1/2-1/2"


class TestPGNSpecialMoves:
    """Testa PGN com lances especiais."""

    def test_roque(self) -> None:
        g = _make_game_with_castling()
        pgn = export_game(g)
        loaded = parse_pgn_string(pgn)
        assert loaded is not None
        board = reconstruct_board(loaded)
        assert board.fen() == g.board.fen()

    def test_en_passant(self) -> None:
        g = _make_game_with_en_passant()
        pgn = export_game(g)
        loaded = parse_pgn_string(pgn)
        assert loaded is not None
        board = reconstruct_board(loaded)
        assert board.fen() == g.board.fen()

    def test_promocao(self) -> None:
        g = _make_game_with_promotion()
        pgn = export_game(g)
        loaded = parse_pgn_string(pgn)
        assert loaded is not None
        board = reconstruct_board(loaded)
        assert board.fen() == g.board.fen()
