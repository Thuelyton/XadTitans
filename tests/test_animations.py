"""Testes do módulo de animações (ui/animations.py) — puro, sem pygame."""

from __future__ import annotations

import pytest

from xadtitans.ui.animations import (
    FADE,
    SLIDE,
    Anim,
    Animator,
    clamp01,
    ease_in_out_sine,
    ease_out_back,
    ease_out_cubic,
    linear,
)


class TestEasing:
    def test_limites(self) -> None:
        for fn in (linear, ease_out_cubic, ease_in_out_sine, ease_out_back):
            assert fn(-1.0) == pytest.approx(0.0, abs=1e-9)
            assert fn(0.0) == pytest.approx(0.0, abs=1e-9)
            assert fn(1.0) == pytest.approx(1.0)
            assert fn(2.0) == pytest.approx(1.0)

    def test_monotonia(self) -> None:
        for fn in (linear, ease_out_cubic, ease_in_out_sine):
            values = [fn(i / 100) for i in range(101)]
            assert values == sorted(values)

    def test_clamp(self) -> None:
        assert clamp01(-3.0) == 0.0
        assert clamp01(0.4) == 0.4
        assert clamp01(9.0) == 1.0

    def test_ease_out_cubic_desacelera(self) -> None:
        """Cresce mais no começo que no fim."""
        assert ease_out_cubic(0.25) > 0.5
        assert ease_out_cubic(0.25) - ease_out_cubic(0.15) > (
            ease_out_cubic(0.9) - ease_out_cubic(0.8)
        )


class TestAnim:
    def make_slide(self) -> Anim:
        return Anim(
            kind=SLIDE,
            sprite=(1, True),
            square=20,
            start=(0.0, 0.0),
            end=(100.0, 50.0),
            scale_start=1.0,
            scale_end=0.7,
            duration=2.0,
        )

    def test_nao_concluida_no_inicio(self) -> None:
        a = self.make_slide()
        assert not a.done
        assert a.pos == (0.0, 0.0)
        assert a.alpha == 1.0

    def test_interpolacao_no_meio(self) -> None:
        a = self.make_slide()
        a.elapsed = 1.0  # metade
        k = ease_out_cubic(0.5)
        assert a.pos[0] == pytest.approx(100.0 * k)
        assert a.scale == pytest.approx(1.0 + (0.7 - 1.0) * k)

    def test_concluida_no_fim(self) -> None:
        a = self.make_slide()
        a.elapsed = 2.0
        assert a.done
        assert a.pos == pytest.approx((100.0, 50.0))
        assert a.scale == pytest.approx(0.7)

    def test_duracao_zero_termina_imediato(self) -> None:
        a = Anim(kind=SLIDE, sprite=(1, True), square=0,
                 start=(0, 0), end=(10, 10), duration=0.0)
        assert a.done
        assert a.pos == (10.0, 10.0)

    def test_fade_esmaece(self) -> None:
        a = Anim(
            kind=FADE, sprite=(1, False), square=5,
            start=(4.0, 4.0), end=(4.0, 4.0), duration=1.0,
        )
        a.elapsed = 0.5
        assert 0.0 < a.alpha < 1.0
        a.elapsed = 1.0
        assert a.alpha == pytest.approx(0.0)


class TestAnimator:
    def test_update_remove_concluidas(self) -> None:
        anim = Animator()
        a = self._slide()
        anim.add(a)
        assert anim.active and anim.blocking
        for _ in range(20):
            anim.update(0.05)  # 1.0s no total >= duracao 0.4
        assert not anim.active
        assert not anim.blocking

    def test_fade_nao_bloqueia(self) -> None:
        anim = Animator()
        anim.add(
            Anim(kind=FADE, sprite=(1, False), square=5,
                 start=(0, 0), end=(0, 0), duration=0.3)
        )
        assert anim.active
        assert not anim.blocking  # só o deslize bloqueia entrada

    def test_by_square(self) -> None:
        anim = Animator()
        anim.add(self._slide())
        anim.add(
            Anim(kind=FADE, sprite=(1, False), square=8,
                 start=(0, 0), end=(0, 0), duration=0.3)
        )
        groups = anim.by_square()
        assert set(groups) == {20, 8}

    def test_clear(self) -> None:
        anim = Animator()
        anim.add(self._slide())
        anim.clear()
        assert not anim.active

    @staticmethod
    def _slide() -> Anim:
        return Anim(
            kind=SLIDE, sprite=(1, True), square=20,
            start=(0.0, 0.0), end=(10.0, 10.0), duration=0.4,
        )
