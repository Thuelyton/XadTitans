"""XadTitans - ponto de entrada.

Abre a janela principal (1024×768) e fecha com Esc ou no X da janela.
Erros fatais são registrados no log com uma mensagem amigável
(nunca um traceback cru para o usuário).
"""

import os
import sys
from pathlib import Path

# Garante que o pacote xadtitans/ é encontrado mesmo fora de um
# instalação em modo editable (pip install -e .).
_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)


def _ensure_streams() -> None:
    """Modo windowed: PyInstaller define ``sys.stdout/stderr = None``.

    Sem isso, ``print(file=sys.stderr)`` no handler de erro fatal e o
    ``StreamHandler`` do logger (que captura ``sys.stderr``) quebrariam
    exatamente quando mais são necessários. Aponta os streams ausentes
    para ``os.devnull`` (sem efeito no console de desenvolvimento).
    """
    # O handle deve durar o processo inteiro (stream global do app);
    # abrir com context manager o fecharia — por isso o noqa SIM115.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


_ensure_streams()

from xadtitans.app import App
from xadtitans.i18n import t
from xadtitans.utils.logger import get_logger


def main() -> int:
    try:
        app = App()
    except Exception:  # noqa: BLE001 — handler global de inicialização
        # Falha na inicialização (janela, assets, configurações...):
        # registra o traceback completo e mostra mensagem amigável.
        get_logger().exception("Erro fatal ao iniciar o aplicativo")
        print(f"{t('error.title')}: {t('error.fatal')}", file=sys.stderr)
        return 1
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
