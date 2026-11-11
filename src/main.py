"""Punto de entrada de ProcSim Local.

Uso:
    python src/main.py                 # abre el simulador
    python src/main.py --bd otra.db    # usa otra base de datos
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from controlador import Controlador          # noqa: E402
from nucleo.base_datos import RUTA_POR_DEFECTO   # noqa: E402


def activar_dpi() -> None:
    """En Windows, evita que la ventana se vea borrosa en pantallas con escala."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="ProcSim Local · simulador de procesos, hilos y concurrencia")
    parser.add_argument("--bd", default=str(RUTA_POR_DEFECTO), help="ruta del archivo SQLite")
    args = parser.parse_args(argv)
    activar_dpi()
    from ui.ventana_principal import VentanaPrincipal
    app = VentanaPrincipal(Controlador(args.bd))
    app.mainloop()


if __name__ == "__main__":
    main()
