"""Procesos simulados, sus estados y el planificador de CPU.

Modelo de cinco estados: nuevo, listo, ejecución, bloqueado y terminado.
El planificador usa prioridades (1 = la más alta) con quantum: entre procesos de
la misma prioridad se turna la CPU (round robin).
"""
from __future__ import annotations

import random
import threading
from collections import deque

from nucleo.pcb import PCB
from nucleo.registro import Registro

NUEVO, LISTO, EJECUCION, BLOQUEADO, TERMINADO = "nuevo", "listo", "ejecucion", "bloqueado", "terminado"
ESTADOS = (NUEVO, LISTO, EJECUCION, BLOQUEADO, TERMINADO)

# transición -> motivo (las de la teoría)
TRANSICIONES = {
    (NUEVO, LISTO): "admitir",
    (LISTO, EJECUCION): "despachar",
    (EJECUCION, LISTO): "interrupción",
    (EJECUCION, BLOQUEADO): "espera E/S",
    (BLOQUEADO, LISTO): "E/S lista",
    (EJECUCION, TERMINADO): "salir",
}
# el usuario puede finalizar un proceso desde cualquier estado activo
FINALIZABLES = (NUEVO, LISTO, EJECUCION, BLOQUEADO)

PRIORIDAD_MIN, PRIORIDAD_MAX = 1, 10
RAFAGA_MIN, RAFAGA_MAX = 1, 50


class TransicionInvalida(Exception):
    pass


class Proceso:
    def __init__(self, pid: int, nombre: str, prioridad: int, rafaga: int) -> None:
        self.nombre = nombre
        self.pcb = PCB(pid=pid, prioridad=prioridad, rafaga_total=rafaga)
        self.es_restante = 0             # tics que faltan para terminar la E/S

    @property
    def pid(self) -> int:
        return self.pcb.pid

    @property
    def estado(self) -> str:
        return self.pcb.estado

    def cambiar_estado(self, nuevo: str, finalizado_por_usuario: bool = False) -> str:
        """Valida y aplica una transición. Devuelve el motivo."""
        actual = self.pcb.estado
        if finalizado_por_usuario and nuevo == TERMINADO and actual in FINALIZABLES:
            motivo = "finalizado por el usuario"
        elif (actual, nuevo) in TRANSICIONES:
            motivo = TRANSICIONES[(actual, nuevo)]
        else:
            raise TransicionInvalida(f"P{self.pid}: no se puede pasar de {actual} a {nuevo}")
        self.pcb.estado = nuevo
        return motivo

    def como_dict(self) -> dict:
        d = self.pcb.como_dict()
        d["nombre"] = self.nombre
        d["progreso"] = round(self.pcb.progreso, 3)
        d["es_restante"] = self.es_restante
        return d


class Planificador:
    """Planificador por prioridad con quantum. Avanza un tic a la vez."""

    def __init__(self, registro: Registro, quantum: int = 2, prob_es: float = 0.2,
                 duracion_es: int = 3, semilla: int = 7, pid_inicial: int = 100) -> None:
        self.registro = registro
        self.quantum = quantum
        self.prob_es = prob_es
        self.duracion_es = duracion_es
        self._rng = random.Random(semilla)
        self._siguiente_pid = pid_inicial
        self._lock = threading.RLock()
        self.procesos: dict[int, Proceso] = {}
        self.cola_listos: deque[int] = deque()
        self.en_cpu: int | None = None
        self._quantum_usado = 0
        self.cambios_contexto = 0
        self.ultima_transicion: tuple[str, str] | None = None

    # ------------------------------------------------------------------ F1
    def crear_proceso(self, nombre: str, prioridad: int, rafaga: int) -> Proceso:
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El proceso necesita un nombre.")
        if not PRIORIDAD_MIN <= int(prioridad) <= PRIORIDAD_MAX:
            raise ValueError(f"La prioridad debe estar entre {PRIORIDAD_MIN} y {PRIORIDAD_MAX}.")
        if not RAFAGA_MIN <= int(rafaga) <= RAFAGA_MAX:
            raise ValueError(f"La ráfaga debe estar entre {RAFAGA_MIN} y {RAFAGA_MAX}.")
        with self._lock:
            p = Proceso(self._siguiente_pid, nombre, int(prioridad), int(rafaga))
            self._siguiente_pid += 1
            self.procesos[p.pid] = p
            self.registro.registrar("fork", f"{nombre} creado · prioridad {p.pcb.prioridad} · ráfaga {rafaga}",
                                    pid=p.pid, nuevo=NUEVO)
            return p

    def finalizar_proceso(self, pid: int) -> None:
        with self._lock:
            p = self.procesos.get(pid)
            if p is None:
                raise ValueError(f"No existe el proceso P{pid}.")
            if p.estado == TERMINADO:
                raise ValueError(f"P{pid} ya está terminado.")
            if pid in self.cola_listos:
                self.cola_listos.remove(pid)
            if self.en_cpu == pid:
                self.en_cpu = None
            self._mover(p, TERMINADO, tipo="kill", por_usuario=True)

    # ------------------------------------------------------------------ F3
    def _mover(self, p: Proceso, nuevo: str, tipo: str, detalle: str = "", por_usuario: bool = False) -> None:
        anterior = p.estado
        motivo = p.cambiar_estado(nuevo, finalizado_por_usuario=por_usuario)
        self.ultima_transicion = (anterior, nuevo)
        texto = motivo + (f" · {detalle}" if detalle else "")
        self.registro.registrar(tipo, texto, pid=p.pid, anterior=anterior, nuevo=nuevo)

    def _mejor_listo(self) -> int | None:
        if not self.cola_listos:
            return None
        # menor número de prioridad; a igual prioridad, el que llegó primero
        return min(self.cola_listos, key=lambda pid: (self.procesos[pid].pcb.prioridad,
                                                      list(self.cola_listos).index(pid)))

    def tic(self) -> bool:
        """Avanza un tic del reloj. Devuelve True mientras queden procesos activos."""
        with self._lock:
            self.registro.avanzar_reloj()
            # 1. admitir los procesos nuevos
            for p in self.procesos.values():
                if p.estado == NUEVO:
                    self._mover(p, LISTO, "admit")
                    self.cola_listos.append(p.pid)
            # 2. avanzar la E/S de los bloqueados
            for p in self.procesos.values():
                if p.estado == BLOQUEADO:
                    p.es_restante -= 1
                    if p.es_restante <= 0:
                        self._mover(p, LISTO, "irq", "el dispositivo terminó")
                        self.cola_listos.append(p.pid)
            # 3. ejecutar una instrucción del proceso en CPU
            if self.en_cpu is not None:
                p = self.procesos[self.en_cpu]
                p.pcb.ejecutar_instruccion()
                self._quantum_usado += 1
                mejor = self._mejor_listo()
                if p.pcb.rafaga_restante <= 0:
                    self._mover(p, TERMINADO, "exit", f"usó {p.pcb.tiempo_cpu} tics de CPU")
                    self.en_cpu = None
                elif self._rng.random() < self.prob_es:
                    p.es_restante = self.duracion_es
                    self._mover(p, BLOQUEADO, "wait", f"pide E/S por {self.duracion_es} tics")
                    self.en_cpu = None
                elif mejor is not None and self.procesos[mejor].pcb.prioridad < p.pcb.prioridad:
                    self._mover(p, LISTO, "preempt", f"llegó P{mejor} con mayor prioridad")
                    self.cola_listos.append(p.pid)
                    self.en_cpu = None
                elif (self._quantum_usado >= self.quantum and mejor is not None
                      and self.procesos[mejor].pcb.prioridad == p.pcb.prioridad):
                    self._mover(p, LISTO, "preempt", f"fin del quantum ({self.quantum})")
                    self.cola_listos.append(p.pid)
                    self.en_cpu = None
            # 4. despachar si la CPU está libre
            if self.en_cpu is None:
                pid = self._mejor_listo()
                if pid is not None:
                    self.cola_listos.remove(pid)
                    p = self.procesos[pid]
                    p.pcb.cambios_contexto += 1
                    self.cambios_contexto += 1
                    self._mover(p, EJECUCION, "exec", "cambio de contexto: se carga su PCB")
                    self.en_cpu = pid
                    self._quantum_usado = 0
            # 5. contabilidad de espera
            for pid in self.cola_listos:
                self.procesos[pid].pcb.tiempo_espera += 1
            return self.activos() > 0

    # ------------------------------------------------------------------ consultas
    def activos(self) -> int:
        with self._lock:
            return sum(1 for p in self.procesos.values() if p.estado != TERMINADO)

    def instantanea(self) -> list[dict]:
        with self._lock:
            return [p.como_dict() for p in self.procesos.values()]
