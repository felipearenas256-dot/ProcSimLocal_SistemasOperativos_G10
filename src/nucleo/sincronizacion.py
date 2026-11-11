"""Mecanismos de sincronización y control de la simulación.

* ControlEjecucion: iniciar, pausar, paso a paso, velocidad y detener. Los hilos de
  la simulación llaman a punto_control() en cada paso.
* crear_mecanismo(): ninguno, mutex (threading.Lock) o semáforo (threading.Semaphore).
* GrafoEspera: grafo de asignación de recursos y detección de ciclos (interbloqueo).
* RecursoConPrioridad: recurso que siempre se entrega al hilo de mejor prioridad
  (provoca inanición) con envejecimiento opcional (la corrige).
"""
from __future__ import annotations

import itertools
import threading
import time


class SimulacionDetenida(Exception):
    """Se lanza en los hilos de la simulación cuando el usuario la reinicia."""


# =============================================================================
# Control de la ejecución
# =============================================================================
class ControlEjecucion:
    VELOCIDAD_MIN = 0.25
    VELOCIDAD_MAX = 8.0

    def __init__(self, velocidad: float = 1.0, retardo_base: float = 0.4, pausado: bool = False) -> None:
        self._cond = threading.Condition()
        self._pausado = pausado
        self._detenido = False
        self._pasos = 0
        self._velocidad = self._limitar(velocidad)
        self.retardo_base = retardo_base
        self.on_paso = None              # función opcional que se llama en cada punto de control

    @classmethod
    def _limitar(cls, v: float) -> float:
        return max(cls.VELOCIDAD_MIN, min(cls.VELOCIDAD_MAX, float(v)))

    # --- órdenes del usuario ----------------------------------------------------
    def pausar(self) -> None:
        with self._cond:
            self._pausado = True

    def reanudar(self) -> None:
        with self._cond:
            self._pausado = False
            self._cond.notify_all()

    def paso(self) -> None:
        """Deja avanzar exactamente un punto de control y vuelve a pausar."""
        with self._cond:
            self._pausado = True
            self._pasos += 1
            self._cond.notify_all()

    def detener(self) -> None:
        with self._cond:
            self._detenido = True
            self._cond.notify_all()

    @property
    def pausado(self) -> bool:
        return self._pausado

    @property
    def detenido(self) -> bool:
        return self._detenido

    @property
    def velocidad(self) -> float:
        return self._velocidad

    @velocidad.setter
    def velocidad(self, valor: float) -> None:
        self._velocidad = self._limitar(valor)

    # --- usados por los hilos de la simulación -------------------------------------
    def verificar(self) -> None:
        if self._detenido:
            raise SimulacionDetenida()

    def punto_control(self, factor: float = 1.0) -> None:
        """Espera si está en pausa (o consume un paso) y luego aplica el retardo."""
        with self._cond:
            while True:
                if self._detenido:
                    raise SimulacionDetenida()
                if not self._pausado:
                    break
                if self._pasos > 0:
                    self._pasos -= 1
                    break
                self._cond.wait(0.1)
        if self.on_paso:
            self.on_paso()
        self.esperar(factor)

    def esperar(self, factor: float = 1.0) -> None:
        """Duerme retardo_base * factor / velocidad, revisando si se detuvo."""
        fin = time.monotonic() + self.retardo_base * factor / self._velocidad
        while True:
            self.verificar()
            restante = fin - time.monotonic()
            if restante <= 0:
                time.sleep(0)            # cede la CPU a otros hilos
                return
            time.sleep(min(restante, 0.05))


# =============================================================================
# Mecanismos de exclusión mutua
# =============================================================================
MECANISMOS = ("ninguno", "mutex", "semaforo")


def crear_mecanismo(nombre: str, permisos: int = 1):
    if nombre == "ninguno":
        return None
    if nombre == "mutex":
        return threading.Lock()
    if nombre == "semaforo":
        return threading.Semaphore(permisos)
    raise ValueError(f"Mecanismo desconocido: {nombre}")


def adquirir(mecanismo, control: ControlEjecucion | None = None) -> None:
    """acquire() que se puede interrumpir si el usuario reinicia la simulación."""
    while not mecanismo.acquire(timeout=0.05):
        if control:
            control.verificar()


# =============================================================================
# Grafo de asignación de recursos (interbloqueo)
# =============================================================================
class GrafoEspera:
    """Aristas recurso → hilo (lo retiene) y hilo → recurso (lo espera)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.hilos: list[str] = []
        self.recursos: list[str] = []
        self._retiene: dict[str, str] = {}        # recurso -> hilo
        self._espera: dict[str, str] = {}         # hilo -> recurso

    def agregar_hilo(self, nombre: str) -> None:
        with self._lock:
            self.hilos.append(nombre)

    def agregar_recurso(self, nombre: str) -> None:
        with self._lock:
            self.recursos.append(nombre)

    def asignar(self, hilo: str, recurso: str) -> None:
        with self._lock:
            self._retiene[recurso] = hilo
            if self._espera.get(hilo) == recurso:
                del self._espera[hilo]

    def solicitar(self, hilo: str, recurso: str) -> None:
        with self._lock:
            self._espera[hilo] = recurso

    def cancelar_espera(self, hilo: str) -> None:
        with self._lock:
            self._espera.pop(hilo, None)

    def liberar(self, hilo: str, recurso: str) -> None:
        with self._lock:
            if self._retiene.get(recurso) == hilo:
                del self._retiene[recurso]

    def aristas(self) -> list[tuple[str, str, str]]:
        """Lista de (origen, destino, tipo) con tipo 'retiene' o 'espera'."""
        with self._lock:
            a = [(r, h, "retiene") for r, h in self._retiene.items()]
            a += [(h, r, "espera") for h, r in self._espera.items()]
            return a

    def detectar_ciclo(self) -> list[str]:
        """Devuelve los nodos de un ciclo (espera circular) o [] si no hay."""
        with self._lock:
            siguiente: dict[str, str] = {}
            for h, r in self._espera.items():
                siguiente[h] = r
            for r, h in self._retiene.items():
                siguiente[r] = h
        # cada nodo tiene a lo sumo una salida: basta seguir el camino
        for inicio in siguiente:
            camino: list[str] = []
            nodo = inicio
            while nodo in siguiente and nodo not in camino:
                camino.append(nodo)
                nodo = siguiente[nodo]
            if nodo in camino:
                return camino[camino.index(nodo):]
        return []


# =============================================================================
# Recurso con prioridad (inanición y envejecimiento)
# =============================================================================
class RecursoConPrioridad:
    """Recurso de una sola instancia que se entrega al hilo con mejor prioridad.

    Prioridad: 1 es la más alta. Con envejecimiento > 0, cada vez que un hilo se
    queda esperando mientras el recurso se entrega a otro, su prioridad efectiva
    mejora en `envejecimiento` puntos.
    """

    def __init__(self, envejecimiento: float = 0.0) -> None:
        self._cond = threading.Condition()
        self.envejecimiento = envejecimiento
        self.ocupado_por: str | None = None
        self._esperando: dict[str, list] = {}     # hilo -> [prioridad, rondas, orden_llegada]
        self._orden = itertools.count()
        self._cerrado = False
        self.asignaciones = 0

    def prioridad_efectiva(self, hilo: str) -> float | None:
        with self._cond:
            return self._efectiva(hilo) if hilo in self._esperando else None

    def _efectiva(self, hilo: str) -> float:
        prioridad, rondas, _ = self._esperando[hilo]
        return prioridad - self.envejecimiento * rondas

    def _elegido(self) -> str | None:
        if not self._esperando:
            return None
        return min(self._esperando, key=lambda h: (self._efectiva(h), self._esperando[h][2]))

    def solicitar(self, hilo: str, prioridad: int, control: ControlEjecucion | None = None) -> bool:
        """Bloquea hasta obtener el recurso. Devuelve False si el escenario se cerró."""
        with self._cond:
            self._esperando[hilo] = [prioridad, 0, next(self._orden)]
            while True:
                if self._cerrado or (control and control.detenido):
                    del self._esperando[hilo]
                    return False
                if self.ocupado_por is None and self._elegido() == hilo:
                    del self._esperando[hilo]
                    self.ocupado_por = hilo
                    self.asignaciones += 1
                    return True
                self._cond.wait(0.05)

    def liberar(self, hilo: str) -> None:
        with self._cond:
            if self.ocupado_por == hilo:
                self.ocupado_por = None
                for datos in self._esperando.values():
                    datos[1] += 1
                self._cond.notify_all()

    def cerrar(self) -> None:
        with self._cond:
            self._cerrado = True
            self._cond.notify_all()
