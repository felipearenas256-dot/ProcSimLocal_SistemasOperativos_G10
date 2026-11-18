"""Experimentos de la Fase III: ejecuta cada escenario varias veces y resume los resultados.

Uso:
    python src/experimentos.py                       # 10 repeticiones, imprime la tabla
    python src/experimentos.py -n 20 --salida documentacion/evidencias/resultados_experimentos.md

Los escenarios se ejecutan sin interfaz, con el mismo motor que usa la aplicación
(hilos reales del sistema operativo), y con un retardo base pequeño para que sea rápido.
"""
from __future__ import annotations

import argparse
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nucleo.escenarios import ESCENARIOS  # noqa: E402
from nucleo.registro import Registro  # noqa: E402
from nucleo.sincronizacion import ControlEjecucion  # noqa: E402

RETARDO = 0.002


def correr(codigo: str, **valores):
    """Ejecuta un escenario y devuelve (resultado, segundos, eventos registrados)."""
    registro = Registro()
    escenario = ESCENARIOS[codigo](valores, ControlEjecucion(retardo_base=RETARDO), registro)
    t0 = time.perf_counter()
    resultado = escenario.ejecutar()
    return resultado, time.perf_counter() - t0, len(registro)


def tabla(encabezado: list[str], filas: list[list]) -> list[str]:
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "|".join("---" for _ in encabezado) + "|"]
    lineas += ["| " + " | ".join(str(c) for c in f) + " |" for f in filas]
    return lineas


def pct(x: float) -> str:
    return f"{x:.0f} %"


# -----------------------------------------------------------------------------
def exp_planificador() -> list[str]:
    filas = []
    for quantum in range(1, 6):
        r, seg, ev = correr("F1", procesos=6, quantum=quantum, prob_es=20, semilla=7)
        d = r.datos
        filas.append([quantum, d["tics"], d["cambios_contexto"], f"{d['espera_promedio']:.2f}", ev])
    return ["### E1 · Planificador (F1–F3): efecto del quantum",
            "6 procesos, probabilidad de E/S 20 %, semilla 7 (resultado determinista).", "",
            *tabla(["Quantum", "Tics totales", "Cambios de contexto", "Espera promedio (tics)", "Eventos"], filas),
            ""]


def exp_hilos_modos() -> list[str]:
    filas = []
    for n in (2, 4, 6):
        r, _s, _e = correr("F4", hilos=n, iteraciones=5)
        filas.append([f"F4 · {n} hilos × 5 iteraciones", f"compartida = {r.datos['compartidos']} "
                      f"(esperado {n * 5}); propia = {r.datos['independientes']}", "sí" if r.correcto else "no"])
    for caso in ESCENARIOS["F5"].parametros[0].opciones:
        r, _s, _e = correr("F5", caso=caso)
        filas.append([f"F5 · {caso}", f"{r.datos['cambios']} cambios de modo usuario↔kernel",
                      "sí" if r.correcto else "no"])
    return ["### E2 · Hilos (F4) y modos de ejecución (F5)", "",
            *tabla(["Caso", "Resultado", "Coincide con la teoría"], filas), ""]


def exp_carrera(n: int) -> list[str]:
    filas = []
    for hilos in (2, 4, 8):
        contadores, con_carrera = [], 0
        esperado = hilos * 50
        for _ in range(n):
            r, _s, _e = correr("F6", hilos=hilos, incrementos=50)
            c = r.datos["fases"][0]["contador"]
            contadores.append(c)
            con_carrera += c < esperado
        perdida = 100 * (esperado - statistics.mean(contadores)) / esperado
        filas.append([hilos, esperado, f"{statistics.mean(contadores):.1f}", f"{min(contadores)}–{max(contadores)}",
                      pct(perdida), f"{con_carrera}/{n}"])
    return ["### E3 · Condición de carrera sin protección (F6)",
            f"50 incrementos por hilo, {n} repeticiones por fila.", "",
            *tabla(["Hilos", "Valor esperado", "Valor final promedio", "Mín–máx", "Actualizaciones perdidas",
                    "Corridas con carrera"], filas), ""]


def exp_seccion_critica(n: int) -> list[str]:
    filas = []
    for etiqueta, mecanismo, permisos in (("Mutex", "mutex", 1), ("Semáforo binario", "semaforo", 1),
                                          ("Semáforo con 2 permisos", "semaforo", 2)):
        correctas, finales, tiempos = 0, [], []
        for _ in range(n):
            r, seg, _e = correr("F7", hilos=4, incrementos=50, mecanismo=mecanismo, permisos=permisos)
            fase = r.datos["fases"][1]
            correctas += fase["contador"] == fase["esperado"]
            finales.append(fase["contador"])
            tiempos.append(seg)
        filas.append([etiqueta, f"{correctas}/{n}", f"{min(finales)}–{max(finales)}",
                      f"{statistics.mean(tiempos):.2f}"])
    return ["### E4 · Sección crítica protegida (F7)",
            f"4 hilos × 50 incrementos (esperado 200), {n} repeticiones por mecanismo.", "",
            *tabla(["Mecanismo", "Corridas con resultado correcto", "Valor final (mín–máx)",
                    "Duración promedio (s)"], filas), ""]


def exp_interbloqueo(n: int) -> list[str]:
    filas = []
    for estrategia in ("sin prevención", "orden global de recursos"):
        bloqueos, completos, tiempos = 0, 0, []
        for _ in range(n):
            r, seg, _e = correr("F8", estrategia=estrategia, limite=1)
            bloqueos += bool(r.datos["interbloqueo"])
            completos += len(r.datos["completados"]) == 2
            tiempos.append(seg)
        filas.append([estrategia, f"{bloqueos}/{n}", f"{completos}/{n}", f"{statistics.mean(tiempos):.2f}"])
    return ["### E5 · Interbloqueo (F8)",
            f"2 hilos y 2 recursos, tiempo de espera máximo 1 s, {n} repeticiones por estrategia.", "",
            *tabla(["Estrategia", "Interbloqueos detectados", "Ambos hilos terminan sin bloqueo",
                    "Duración promedio (s)"], filas), ""]


def exp_inanicion(n: int) -> list[str]:
    filas = []
    for rondas in (12, 24):
        for aging in ("no", "sí"):
            accesos = [correr("F9", altos=2, rondas=rondas, envejecimiento=aging)[0].datos["accesos_b1"]
                       for _ in range(n)]
            filas.append([rondas, aging, f"{statistics.mean(accesos):.1f}", f"{min(accesos)}–{max(accesos)}",
                          f"{sum(a == 0 for a in accesos)}/{n}"])
    return ["### E6 · Inanición y envejecimiento (F9)",
            f"2 hilos de alta prioridad y 1 de baja (B1), {n} repeticiones por fila.", "",
            *tabla(["Asignaciones del recurso", "Envejecimiento", "Accesos de B1 (promedio)", "Mín–máx",
                    "Corridas con inanición total"], filas), ""]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeticiones", type=int, default=10)
    ap.add_argument("--salida", type=Path, help="archivo Markdown donde guardar los resultados")
    args = ap.parse_args()

    t0 = time.perf_counter()
    lineas = ["# Resultados de los experimentos · ProcSim Local", "",
              f"- Fecha: {datetime.now():%Y-%m-%d %H:%M}",
              f"- Equipo: {platform.system()} {platform.release()} (build {platform.version()}), "
              f"Python {platform.python_version()}, {platform.machine()}",
              f"- Repeticiones por configuración: {args.repeticiones}",
              "- Comando: `python src/experimentos.py`", ""]
    for bloque in (exp_planificador(), exp_hilos_modos(), exp_carrera(args.repeticiones),
                   exp_seccion_critica(args.repeticiones), exp_interbloqueo(args.repeticiones),
                   exp_inanicion(args.repeticiones)):
        lineas += bloque
        print("\n".join(bloque), flush=True)
    lineas.append(f"Tiempo total de los experimentos: {time.perf_counter() - t0:.1f} s.")
    print(lineas[-1])
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print(f"Guardado en {args.salida}")


if __name__ == "__main__":
    main()
