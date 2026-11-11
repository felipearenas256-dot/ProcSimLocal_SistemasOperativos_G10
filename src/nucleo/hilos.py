"""Hilos reales del sistema operativo (threading.Thread).

En CPython sobre Windows, cada threading.Thread es un hilo nativo de Windows que
planifica el propio sistema operativo: get_native_id() devuelve su TID real.

* HiloSimulado: hilo con pila y registros propios que comparte la memoria del
  proceso al que pertenece.
* LineaTiempo: guarda los intervalos en que trabajó cada hilo (para la vista F4).
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from nucleo.registro import Registro
from nucleo.sincronizacion import SimulacionDetenida


class LineaTiempo:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.inicio = time.perf_counter()
        self._segmentos: list[tuple[str, float, float, str]] = []    # hilo, t0, t1, grupo

    def ahora(self) -> float:
        return time.perf_counter() - self.inicio

    def agregar(self, hilo: str, t0: float, t1: float, grupo: str = "") -> None:
        with self._lock:
            self._segmentos.append((hilo, t0, t1, grupo))

    def segmentos(self) -> list[tuple[str, float, float, str]]:
        with self._lock:
            return list(self._segmentos)


class HiloSimulado(threading.Thread):
    """Hilo real con pila y registros propios.

    `trabajo(hilo)` es la función que ejecuta; recibe el propio objeto para usar
    hilo.pila, hilo.registros y hilo.memoria (la del proceso, compartida).
    """

    def __init__(self, nombre: str, memoria: dict, trabajo: Callable[["HiloSimulado"], None],
                 registro: Registro, pid: int | None = None, prioridad: int = 0) -> None:
        super().__init__(name=nombre, daemon=True)
        self.nombre = nombre
        self.memoria = memoria                 # compartida con los demás hilos del proceso
        self.pila: list = []                   # propia
        self.registros = {"PC": 0, "SP": 0}    # propios
        self.prioridad = prioridad
        self.pid = pid
        self.tid_nativo: int | None = None
        self.estado = "nuevo"
        self.error: BaseException | None = None
        self._trabajo = trabajo
        self._registro = registro

    def run(self) -> None:
        self.tid_nativo = threading.get_native_id()
        self.estado = "ejecucion"
        self._registro.registrar("thread", f"inicia · TID nativo de Windows {self.tid_nativo}",
                                 pid=self.pid, hilo=self.nombre, anterior="nuevo", nuevo="ejecucion")
        try:
            self._trabajo(self)
            self.estado = "terminado"
            self._registro.registrar("thread", "termina", pid=self.pid, hilo=self.nombre,
                                     anterior="ejecucion", nuevo="terminado")
        except SimulacionDetenida:
            self.estado = "terminado"
        except BaseException as exc:          # se guarda para mostrarlo; no debe tumbar la app
            self.estado = "terminado"
            self.error = exc
            self._registro.registrar("error", f"{type(exc).__name__}: {exc}", pid=self.pid, hilo=self.nombre)

    def empujar(self, valor) -> None:
        self.pila.append(valor)
        self.registros["SP"] = len(self.pila)
        self.registros["PC"] += 4


def esperar_hilos(hilos: list[threading.Thread], control=None) -> None:
    """Espera a que terminen los hilos; si el usuario reinició, lo propaga."""
    for h in hilos:
        while h.is_alive():
            h.join(0.05)
    if control is not None and control.detenido:
        raise SimulacionDetenida()
