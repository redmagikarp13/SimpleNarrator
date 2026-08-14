"""
SimpleNarrator — Leitor de textos híbrido (offline).
Ponto de entrada principal da aplicação.
"""

import io
import sys
import logging

# Garantir proteção contra sys.stdout/stderr nulos em GUI (pythonw / PyInstaller) e encoding UTF-8
class SafeStream:
    def __init__(self, target):
        self.target = target

    def write(self, s):
        if self.target is not None:
            try:
                self.target.write(s)
            except (UnicodeEncodeError, UnicodeError):
                try:
                    if hasattr(self.target, "buffer"):
                        self.target.buffer.write(s.encode("utf-8", errors="replace"))
                    else:
                        self.target.write(s.encode("ascii", errors="replace").decode("ascii"))
                except Exception:
                    pass
            except Exception:
                pass

    def flush(self):
        if self.target is not None and hasattr(self.target, "flush"):
            try:
                self.target.flush()
            except Exception:
                pass

if sys.stdout is None:
    sys.stdout = io.StringIO()
else:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = io.StringIO()
else:
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Suprimir logs de debug verbosos de pacotes externos que contêm fonemas unicode IPA ou COM Windows
logging.getLogger("piper").setLevel(logging.WARNING)
logging.getLogger("piper.voice").setLevel(logging.WARNING)
logging.getLogger("comtypes").setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(SafeStream(sys.stdout)),
    ],
)

from ui.app import NarratorApp


def main():
    """Inicia a aplicação SimpleNarrator."""
    app = NarratorApp()
    app.mainloop()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # Evitar que execuções acidentais via linha de comando ou subprocessos abram a GUI
    if len(sys.argv) > 1 and (sys.argv[1] in ("-m", "-c") or sys.argv[1].startswith("-")):
        sys.exit(0)

    main()
