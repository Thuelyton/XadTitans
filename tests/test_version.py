"""Teste de fumaça da Fase 0: pacote importável e versão definida."""

import xadtitans


def test_pacote_importavel():
    assert xadtitans.__version__
    assert isinstance(xadtitans.__version__, str)
