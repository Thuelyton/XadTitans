"""XadTitans - ponto de entrada.

Abre a janela principal (1024×768) e fecha com Esc ou no X da janela.
Erros fatais são registrados no log com uma mensagem amigável
(nunca um traceback cru para o usuário).
"""

import sys
from pathlib import Path

# Garante que o pacote xadtitans/ é encontrado mesmo fora de um
# instalação em modo editable (pip install -e .).
_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

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
