"""XadTitans - ponto de entrada.

Abre a janela principal (1024×768) e fecha com Esc ou no X da janela.
"""

import sys
from pathlib import Path

# Garante que o pacote xadtitans/ é encontrado mesmo fora de um
# instalação em modo editable (pip install -e .).
_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from xadtitans.app import App


def main() -> int:
    app = App()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
