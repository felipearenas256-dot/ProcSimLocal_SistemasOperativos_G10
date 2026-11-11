"""Registro de eventos: recibe cada cambio del motor de simulación.

Cada evento queda:
  * en memoria (lista ordenada), para exportarlo a .txt y guardarlo en la base de datos;
  * en una cola segura para hilos (queue.Queue), que la interfaz revisa periódicamente.

Los hilos de la simulación nunca tocan la interfaz directamente: Tkinter solo
puede actualizarse desde el hilo principal.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Evento:
    tiempo: int                      # tic del reloj de simulación
    tipo: str                        # fork, exec, wait, sys, thread, carrera, mutex, deadlock...
    mensaje: str
    pid: int | None = None
    hilo: str | None = None
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    marca: float = field(default_factory=time.perf_counter)

    @property
    def sujeto(self) -> str:
        if self.hilo:
            return self.hilo
        if self.pid is not None:
            return f"P{self.pid}"
        return "-"

    def como_linea(self) -> str:
        linea = f"[{self.tiempo:04d}] {self.tipo:<9} {self.sujeto:<6} {self.mensaje}"
        if self.estado_anterior or self.estado_nuevo:
            linea += f"  ({(self.estado_anterior or '-').upper()} → {(self.estado_nuevo or '-').upper()})"
        return linea


class Registro:
    """Bitácora de una ejecución, segura para usar desde varios hilos."""

    def __init__(self) -> None:
        self._eventos: list[Evento] = []
        self._lock = threading.Lock()
        self._tic = 0
        self.cola: queue.Queue[Evento] = queue.Queue()

    # --- reloj de simulación -------------------------------------------------
    def avanzar_reloj(self) -> int:
        with self._lock:
            self._tic += 1
            return self._tic

    @property
    def tiempo(self) -> int:
        with self._lock:
            return self._tic

    # --- eventos ---------------------------------------------------------------
    def registrar(self, tipo: str, mensaje: str, *, pid: int | None = None, hilo: str | None = None,
                  anterior: str | None = None, nuevo: str | None = None) -> Evento:
        with self._lock:
            evento = Evento(self._tic, tipo, mensaje, pid, hilo, anterior, nuevo)
            self._eventos.append(evento)
        self.cola.put(evento)
        return evento

    def eventos(self) -> list[Evento]:
        with self._lock:
            return list(self._eventos)

    def __len__(self) -> int:
        with self._lock:
            return len(self._eventos)

    def exportar_txt(self, ruta: str | Path, encabezado: str = "") -> Path:
        ruta = Path(ruta)
        lineas = ["ProcSim Local · bitácora de eventos",
                  f"Exportado: {datetime.now():%Y-%m-%d %H:%M:%S}"]
        if encabezado:
            lineas.append(encabezado)
        lineas.append("-" * 72)
        lineas += [e.como_linea() for e in self.eventos()]
        lineas.append("-" * 72)
        lineas.append(f"Total de eventos: {len(self)}")
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return ruta
