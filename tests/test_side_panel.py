"""Testes do painel lateral (ui/widgets/side_panel.py) — partes puras."""

from __future__ import annotations

from xadtitans.ui.widgets.side_panel import format_move_pairs


class TestFormatMovePairs:
    def test_vazio(self) -> None:
        assert format_move_pairs([]) == []

    def test_uma_jogada(self) -> None:
        assert format_move_pairs(["e4"]) == ["1. e4"]

    def test_par_completo(self) -> None:
        assert format_move_pairs(["e4", "e5"]) == ["1. e4 e5"]

    def test_impares_e_pares(self) -> None:
        sans = ["e4", "e5", "Nf3", "Nc6", "Bb5"]
        assert format_move_pairs(sans) == [
            "1. e4 e5",
            "2. Nf3 Nc6",
            "3. Bb5",
        ]

    def test_numeracao(self) -> None:
        sans = [f"m{i}" for i in range(10)]
        lines = format_move_pairs(sans)
        assert lines[0].startswith("1. ")
        assert lines[4].startswith("5. ")
        assert len(lines) == 5
