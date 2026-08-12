"""
SimpleNarrator — Leitor de textos híbrido (offline).
Ponto de entrada principal da aplicação.
"""

import logging
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)


def main():
    """Inicia a aplicação SimpleNarrator."""
    from ui.app import NarratorApp

    app = NarratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
