"""ProcSim Simple · lógica de las 4 demostraciones (sin interfaz).

1. Planificador Round Robin: estados de los procesos.
2. Condición de carrera: varios hilos suman a un contador, con o sin mutex.
3. Interbloqueo: dos hilos piden dos recursos en orden cruzado.
4. Inanición: un recurso que siempre se entrega al de mayor prioridad.
"""
import threading
import time

# ---------------------------------------------------------------------------
# 1. Planificador Round Robin
# ---------------------------------------------------------------------------
NUEVO, LISTO, EJECUCION, TERMINADO = "NUEVO", "LISTO", "EJECUCIÓN", "TERMINADO"


class Proceso:
    def __init__(self, pid, nombre, rafaga):
        self.pid = pid
        self.nombre = nombre
        self.rafaga = rafaga          # tics de CPU que necesita
        self.restante = rafaga
        self.estado = NUEVO


class Planificador:
    """Round Robin: cada proceso usa la CPU como máximo `quantum` tics y vuelve a la cola."""

    def __init__(self, quantum=2):
        self.quantum = quantum
        self.procesos = []
        self.cola = []                # PIDs en estado LISTO, en orden
        self.en_cpu = None            # proceso en EJECUCIÓN
        self.usado = 0                # tics que lleva en la CPU
        self.tiempo = 0
        self.siguiente_pid = 1

    def crear(self, nombre, rafaga):
        if rafaga < 1:
            raise ValueError("La ráfaga debe ser al menos 1.")
        p = Proceso(self.siguiente_pid, nombre, rafaga)
        self.siguiente_pid += 1
        self.procesos.append(p)
        return p

    def terminado(self):
        return all(p.estado == TERMINADO for p in self.procesos)

    def tic(self):
        """Avanza un tic y devuelve la lista de eventos que ocurrieron."""
        self.tiempo += 1
        eventos = []
        for p in self.procesos:                       # 1. admitir los nuevos
            if p.estado == NUEVO:
                p.estado = LISTO
                self.cola.append(p)
                eventos.append(f"{p.nombre}: NUEVO → LISTO")
        if self.en_cpu:                                # 2. ejecutar un tic
            p = self.en_cpu
            p.restante -= 1
            self.usado += 1
            if p.restante == 0:
                p.estado = TERMINADO
                eventos.append(f"{p.nombre}: EJECUCIÓN → TERMINADO")
                self.en_cpu = None
            elif self.usado >= self.quantum and self.cola:
                p.estado = LISTO
                self.cola.append(p)
                eventos.append(f"{p.nombre}: se acabó el quantum → LISTO")
                self.en_cpu = None
        if self.en_cpu is None and self.cola:          # 3. despachar el siguiente
            p = self.cola.pop(0)
            p.estado = EJECUCION
            self.en_cpu = p
            self.usado = 0
            eventos.append(f"{p.nombre}: LISTO → EJECUCIÓN (cambio de contexto)")
        return eventos


# ---------------------------------------------------------------------------
# 2. Condición de carrera
# ---------------------------------------------------------------------------
def carrera(hilos=4, incrementos=100, usar_mutex=False):
    """Varios hilos reales suman 1 al mismo contador. Devuelve (esperado, real)."""
    estado = {"contador": 0}
    mutex = threading.Lock()

    def sumar():
        for _ in range(incrementos):
            if usar_mutex:
                mutex.acquire()
            valor = estado["contador"]        # 1. leer
            time.sleep(0.0001)                # aquí Windows puede pasar a otro hilo
            estado["contador"] = valor + 1    # 2. escribir
            if usar_mutex:
                mutex.release()

    lista = [threading.Thread(target=sumar) for _ in range(hilos)]
    for h in lista:
        h.start()
    for h in lista:
        h.join()
    return hilos * incrementos, estado["contador"]


# ---------------------------------------------------------------------------
# 3. Interbloqueo
# ---------------------------------------------------------------------------
def interbloqueo(orden_global=False, espera_max=1.0):
    """H1 pide R1 y luego R2; H2 pide R2 y luego R1 (o R1 y luego R2 con orden global).

    Devuelve (hubo_interbloqueo, bitacora).
    """
    r1, r2 = threading.Lock(), threading.Lock()
    bitacora, bloqueados = [], []
    bloqueo_bitacora = threading.Lock()

    def anotar(texto):
        with bloqueo_bitacora:
            bitacora.append(texto)

    def trabajo(nombre, primero, segundo, n1, n2):
        primero.acquire()
        anotar(f"{nombre} obtiene {n1}")
        time.sleep(0.2)                                   # da tiempo a que el otro tome su recurso
        anotar(f"{nombre} pide {n2}...")
        if segundo.acquire(timeout=espera_max):
            anotar(f"{nombre} obtiene {n2}, trabaja y libera ambos")
            segundo.release()
        else:
            anotar(f"{nombre} lleva {espera_max} s esperando {n2}: INTERBLOQUEO")
            bloqueados.append(nombre)
        primero.release()

    if orden_global:     # los dos piden en el mismo orden: R1 y después R2
        h2 = threading.Thread(target=trabajo, args=("H2", r1, r2, "R1", "R2"))
    else:                # orden cruzado: espera circular
        h2 = threading.Thread(target=trabajo, args=("H2", r2, r1, "R2", "R1"))
    h1 = threading.Thread(target=trabajo, args=("H1", r1, r2, "R1", "R2"))
    h1.start()
    h2.start()
    h1.join()
    h2.join()
    return bool(bloqueados), bitacora


# ---------------------------------------------------------------------------
# 4. Inanición
# ---------------------------------------------------------------------------
def inanicion(rondas=10, envejecimiento=False):
    """A1 y A2 tienen prioridad 1 (alta) y B1 prioridad 5 (baja); 1 = más alta.

    En cada ronda el recurso se entrega al hilo con mejor prioridad efectiva.
    Con envejecimiento, el que espera mejora 1 punto por ronda.
    Devuelve (veces que lo obtuvo cada hilo, bitacora).
    """
    prioridad = {"A1": 1, "A2": 1, "B1": 5}
    espera = {h: 0 for h in prioridad}            # rondas que lleva esperando
    accesos = {h: 0 for h in prioridad}
    bitacora = []
    for r in range(1, rondas + 1):
        efectiva = {h: prioridad[h] - (espera[h] if envejecimiento else 0) for h in prioridad}
        # gana la mejor prioridad efectiva; en empate, el que lleva más tiempo esperando
        ganador = min(prioridad, key=lambda h: (efectiva[h], -espera[h]))
        accesos[ganador] += 1
        bitacora.append(f"Ronda {r}: gana {ganador} (prioridades efectivas: "
                        + ", ".join(f"{h}={v}" for h, v in efectiva.items()) + ")")
        for h in prioridad:
            espera[h] = 0 if h == ganador else espera[h] + 1
    return accesos, bitacora
