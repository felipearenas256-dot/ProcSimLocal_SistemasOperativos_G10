"""Verificación del entorno de ejecución de ProcSim Local.

Uso:  python src/entorno.py

Muestra el sistema operativo, la versión de Python y de las bibliotecas que usa
el proyecto, y comprueba que threading crea hilos nativos del sistema operativo.
"""
from __future__ import annotations

import os
import platform
import sqlite3
import sys
import threading

VERSION_MINIMA = (3, 10)


def info_entorno() -> dict:
    try:
        import tkinter
        tk_version = f"{tkinter.TkVersion}"
    except ImportError:              # pragma: no cover - solo si Python se instaló sin Tk
        tk_version = "no disponible"
    tids = set()

    def registrar():
        tids.add(threading.get_native_id())

    hilos = [threading.Thread(target=registrar) for _ in range(3)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return {
        "Sistema operativo": f"{platform.system()} {platform.release()} (build {platform.version()})",
        "Arquitectura": platform.machine(),
        "Procesadores lógicos": os.cpu_count(),
        "Python": platform.python_version(),
        "Intérprete": platform.python_implementation(),
        "Tkinter (Tk)": tk_version,
        "SQLite": sqlite3.sqlite_version,
        "Hilos nativos de prueba": f"{len(tids)} TID distintos: {', '.join(map(str, sorted(tids)))}",
        "PID de este proceso": os.getpid(),
    }


def verificar() -> list[str]:
    """Devuelve la lista de problemas encontrados (vacía si todo está bien)."""
    problemas = []
    if sys.version_info < VERSION_MINIMA:
        problemas.append(f"Se necesita Python {'.'.join(map(str, VERSION_MINIMA))} o superior.")
    info = info_entorno()
    if info["Tkinter (Tk)"] == "no disponible":
        problemas.append("Tkinter no está instalado (reinstale Python marcando 'tcl/tk and IDLE').")
    if platform.system() != "Windows":
        problemas.append("ProcSim Local está pensado para Windows 10/11 (puede funcionar en otros sistemas).")
    return problemas


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("ProcSim Local · verificación del entorno")
    print("-" * 60)
    for clave, valor in info_entorno().items():
        print(f"{clave:<26}{valor}")
    print("-" * 60)
    problemas = verificar()
    if problemas:
        for p in problemas:
            print("AVISO:", p)
    else:
        print("Entorno correcto: se puede ejecutar  python src/main.py")
    return 0 if sys.version_info >= VERSION_MINIMA else 1


if __name__ == "__main__":
    raise SystemExit(main())
