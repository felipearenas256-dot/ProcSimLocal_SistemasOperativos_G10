"""Clase PCB (bloque de control de proceso).

Guarda lo que el sistema operativo necesita para administrar un proceso y para
reanudarlo después de un cambio de contexto: PID, estado, contador de programa,
prioridad, registros de CPU y contabilidad de tiempos.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DIRECCION_BASE = 0x4000      # dirección simulada donde inicia el código de cada proceso
TAMANO_INSTRUCCION = 4       # bytes por instrucción simulada


@dataclass
class PCB:
    pid: int
    prioridad: int                       # 1 = prioridad más alta
    rafaga_total: int                    # instrucciones (tics de CPU) que necesita
    estado: str = "nuevo"
    contador_programa: int = DIRECCION_BASE
    registros: dict = field(default_factory=lambda: {"AX": 0, "BX": 0, "CX": 0, "DX": 0})
    rafaga_restante: int = -1
    tiempo_cpu: int = 0                  # tics en ejecución
    tiempo_espera: int = 0               # tics en la cola de listos
    cambios_contexto: int = 0

    def __post_init__(self) -> None:
        if self.rafaga_restante < 0:
            self.rafaga_restante = self.rafaga_total

    def ejecutar_instruccion(self) -> None:
        """Simula una instrucción: avanza el PC y modifica los registros."""
        self.contador_programa += TAMANO_INSTRUCCION
        self.registros["AX"] += 1                                   # acumulador
        self.registros["BX"] = (self.registros["BX"] + self.pid) % 256
        self.registros["CX"] = self.rafaga_restante - 1             # contador de ciclo
        self.registros["DX"] = self.contador_programa & 0xFF
        self.rafaga_restante -= 1
        self.tiempo_cpu += 1

    @property
    def progreso(self) -> float:
        return 1 - self.rafaga_restante / self.rafaga_total if self.rafaga_total else 1.0

    def como_dict(self) -> dict:
        return {
            "pid": self.pid,
            "estado": self.estado,
            "contador_programa": f"0x{self.contador_programa:04X}",
            "prioridad": self.prioridad,
            "registros": dict(self.registros),
            "rafaga_total": self.rafaga_total,
            "rafaga_restante": self.rafaga_restante,
            "tiempo_cpu": self.tiempo_cpu,
            "tiempo_espera": self.tiempo_espera,
            "cambios_contexto": self.cambios_contexto,
        }
