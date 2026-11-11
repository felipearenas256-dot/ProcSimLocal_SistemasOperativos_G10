"""Escenarios de simulación F1 a F9.

Cada escenario:
  * declara sus parámetros (para que la interfaz arme el formulario y el
    controlador los valide);
  * se ejecuta en un hilo trabajador con ejecutar(), llamando a
    control.punto_control() en cada paso (pausa, paso a paso, velocidad);
  * expone estado(), una instantánea que la interfaz dibuja;
  * devuelve un Resultado (esperado vs. real).
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field

from nucleo.hilos import HiloSimulado, LineaTiempo, esperar_hilos
from nucleo.proceso import Planificador, TERMINADO
from nucleo.registro import Registro
from nucleo.sincronizacion import (ControlEjecucion, GrafoEspera, RecursoConPrioridad,
                                   SimulacionDetenida, adquirir, crear_mecanismo)


# =============================================================================
# Base
# =============================================================================
@dataclass
class Parametro:
    clave: str
    etiqueta: str
    tipo: str                    # "int", "float" u "opcion"
    defecto: object
    minimo: float | None = None
    maximo: float | None = None
    opciones: tuple = ()
    ayuda: str = ""

    def convertir(self, valor) -> object:
        if self.tipo == "opcion":
            if valor not in self.opciones:
                raise ValueError(f"{self.etiqueta}: elija una de {', '.join(self.opciones)}.")
            return valor
        try:
            numero = int(str(valor).strip()) if self.tipo == "int" else float(str(valor).strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"{self.etiqueta}: debe ser un número{' entero' if self.tipo == 'int' else ''}.") from None
        if (self.minimo is not None and numero < self.minimo) or (self.maximo is not None and numero > self.maximo):
            raise ValueError(f"{self.etiqueta}: debe estar entre {self.minimo:g} y {self.maximo:g}.")
        return numero


@dataclass
class Resultado:
    esperado: str
    real: str
    resumen: str
    correcto: bool | None = None          # True = coincide con lo esperado, False = falla (lo que se quería mostrar)
    datos: dict = field(default_factory=dict)


class Escenario:
    codigo = ""
    nombre = ""
    modulo = ""
    vista = ""
    explicacion = ""
    parametros: list[Parametro] = []

    def __init__(self, valores: dict, control: ControlEjecucion, registro: Registro) -> None:
        self.valores = self.validar(valores)
        self.control = control
        self.registro = registro
        self._lock = threading.Lock()

    @classmethod
    def validar(cls, valores: dict) -> dict:
        limpio = {}
        for p in cls.parametros:
            limpio[p.clave] = p.convertir(valores.get(p.clave, p.defecto))
        return limpio

    @property
    def mecanismo(self) -> str:
        return "ninguno"

    def ejecutar(self) -> Resultado:
        raise NotImplementedError

    def estado(self) -> dict:
        return {}

    # datos para la base de datos ---------------------------------------------------
    def procesos_bd(self) -> list[dict]:
        """[{pid, nombre, prioridad, rafaga, pc, estado, hilos: [{tid, nombre, prioridad, estado, espera}]}]"""
        return []

    def recursos_bd(self) -> tuple[list[dict], list[dict]]:
        """(recursos [{nombre, tipo, instancias}], asignaciones [{hilo, recurso, tipo, tiempo}])"""
        return [], []


# =============================================================================
# Módulo A · Gestión de procesos (F1, F2, F3)
# =============================================================================
class _EscenarioPlanificador(Escenario):
    modulo = "A"
    vista = "procesos"
    parametros = [
        Parametro("procesos", "Procesos iniciales", "int", 4, 0, 8, ayuda="0 a 8; puede crear más durante la simulación"),
        Parametro("quantum", "Quantum (tics)", "int", 2, 1, 5),
        Parametro("prob_es", "Probabilidad de E/S (%)", "int", 20, 0, 60),
        Parametro("semilla", "Semilla", "int", 7, 0, 9999, ayuda="misma semilla = misma simulación"),
    ]
    MAX_TICS = 400

    def __init__(self, valores, control, registro) -> None:
        super().__init__(valores, control, registro)
        v = self.valores
        self.planificador = Planificador(registro, quantum=v["quantum"], prob_es=v["prob_es"] / 100,
                                         semilla=v["semilla"])
        rng = random.Random(v["semilla"])
        for i in range(v["procesos"]):
            self.planificador.crear_proceso(f"P{i + 1}", rng.randint(1, 4), rng.randint(3, 8))

    def ejecutar(self) -> Resultado:
        pl = self.planificador
        tics = 0
        # si no hay procesos, espera a que el usuario cree alguno (F1)
        while pl.activos() == 0 and not pl.procesos:
            self.control.punto_control(0.5)
        while tics < self.MAX_TICS:
            self.control.punto_control()
            tics += 1
            if not pl.tic():
                break
        procs = pl.instantanea()
        terminados = sum(1 for p in procs if p["estado"] == TERMINADO)
        normales = [p for p in procs if p["rafaga_restante"] == 0]
        espera = sum(p["tiempo_espera"] for p in normales) / len(normales) if normales else 0
        return Resultado(
            esperado=f"{len(procs)} procesos terminados",
            real=f"{terminados} terminados en {tics} tics",
            resumen=(f"Cambios de contexto: {pl.cambios_contexto} · espera promedio en listos: "
                     f"{espera:.1f} tics · finalizados por el usuario: {len(procs) - len(normales)}"),
            correcto=terminados == len(procs),
            datos={"tics": tics, "cambios_contexto": pl.cambios_contexto, "espera_promedio": espera},
        )

    def estado(self) -> dict:
        return {"procesos": self.planificador.instantanea(), "en_cpu": self.planificador.en_cpu,
                "ultima_transicion": self.planificador.ultima_transicion, "tiempo": self.registro.tiempo,
                "quantum": self.planificador.quantum}

    def procesos_bd(self) -> list[dict]:
        return [{"pid": p["pid"], "nombre": p["nombre"], "prioridad": p["prioridad"], "rafaga": p["rafaga_total"],
                 "pc": int(p["contador_programa"], 16), "estado": p["estado"], "hilos": []}
                for p in self.planificador.instantanea()]


class EscenarioProcesos(_EscenarioPlanificador):
    codigo = "F1"
    nombre = "Crear y finalizar procesos"
    explicacion = ("Un proceso es un programa en ejecución. Al crearlo (fork), el sistema operativo le asigna un PID "
                   "y un PCB, y lo pone en estado NUEVO. Puede crear procesos con nombre, prioridad (1 = más alta) "
                   "y ráfaga de CPU, o finalizarlos en cualquier momento (kill): pasan a TERMINADO.")


class EscenarioPCB(_EscenarioPlanificador):
    codigo = "F2"
    nombre = "Consultar el PCB"
    explicacion = ("El PCB (bloque de control de proceso) es la ficha que el sistema operativo guarda de cada "
                   "proceso: PID, estado, contador de programa, prioridad, registros y tiempos. En cada cambio de "
                   "contexto se guarda el PCB del proceso que sale y se carga el del que entra. Seleccione un "
                   "proceso de la lista para ver su PCB actualizado en vivo.")


class EscenarioCicloVida(_EscenarioPlanificador):
    codigo = "F3"
    nombre = "Ciclo de vida"
    explicacion = ("Modelo de cinco estados. NUEVO → LISTO al ser admitido; LISTO → EJECUCIÓN cuando el "
                   "planificador lo despacha; EJECUCIÓN → LISTO por fin de quantum o porque llega uno de mayor "
                   "prioridad; EJECUCIÓN → BLOQUEADO al pedir E/S; BLOQUEADO → LISTO cuando la E/S termina; "
                   "EJECUCIÓN → TERMINADO al completar su ráfaga.")


# =============================================================================
# Módulo B · Hilos y modos de ejecución (F4, F5)
# =============================================================================
class EscenarioHilos(Escenario):
    codigo = "F4"
    nombre = "Hilos de un proceso"
    modulo = "B"
    vista = "hilos"
    explicacion = ("Los hilos de un mismo proceso comparten su memoria (código, datos y archivos abiertos), pero cada "
                   "uno tiene su propia pila y sus propios registros. Primero se crean hilos dentro de un proceso: "
                   "todos escriben en la misma memoria. Luego se repite con procesos independientes: cada uno solo "
                   "ve su propia copia. Los hilos son reales: cada uno tiene un TID nativo de Windows.")
    parametros = [
        Parametro("hilos", "Número de hilos", "int", 3, 2, 6),
        Parametro("iteraciones", "Iteraciones por hilo", "int", 5, 2, 12),
    ]

    def __init__(self, valores, control, registro) -> None:
        super().__init__(valores, control, registro)
        self.linea = LineaTiempo()
        self.hilos: list[HiloSimulado] = []
        self.memoria_compartida: dict = {"datos": []}
        self.memorias_independientes: dict[str, dict] = {}
        self.fase = "preparando"

    def _trabajo(self, grupo: str):
        def trabajo(h: HiloSimulado) -> None:
            for i in range(self.valores["iteraciones"]):
                self.control.punto_control(0.6)
                t0 = self.linea.ahora()
                with self._lock:
                    h.memoria["datos"].append(f"{h.nombre}·{i + 1}")
                h.empujar(i + 1)
                self.control.esperar(0.25)
                self.linea.agregar(h.nombre, t0, self.linea.ahora(), grupo)
                self.registro.registrar("mem", f"escribe dato {i + 1} · la memoria que ve tiene "
                                               f"{len(h.memoria['datos'])} datos · su pila tiene {len(h.pila)}",
                                        pid=h.pid, hilo=h.nombre)
        return trabajo

    def ejecutar(self) -> Resultado:
        n, k = self.valores["hilos"], self.valores["iteraciones"]
        # Fase 1: un proceso con n hilos que comparten memoria
        self.fase = "hilos"
        self.registro.registrar("fork", f"proceso P1 creado con {n} hilos", pid=1)
        grupo1 = [HiloSimulado(f"H{i + 1}", self.memoria_compartida, self._trabajo("hilos"), self.registro, pid=1)
                  for i in range(n)]
        with self._lock:
            self.hilos.extend(grupo1)
        for h in grupo1:
            h.start()
        esperar_hilos(grupo1, self.control)
        # Fase 2: n procesos independientes, cada uno con su propia memoria
        self.fase = "procesos"
        grupo2 = []
        for i in range(n):
            mem = {"datos": []}
            self.memorias_independientes[f"P{i + 2}"] = mem
            self.registro.registrar("fork", "proceso independiente con su propia memoria", pid=i + 2)
            grupo2.append(HiloSimulado(f"P{i + 2}", mem, self._trabajo("procesos"), self.registro, pid=i + 2))
        with self._lock:
            self.hilos.extend(grupo2)
        for h in grupo2:
            h.start()
        esperar_hilos(grupo2, self.control)
        self.fase = "terminado"
        compartidos = len(self.memoria_compartida["datos"])
        independientes = [len(m["datos"]) for m in self.memorias_independientes.values()]
        tids = {h.tid_nativo for h in grupo1}
        return Resultado(
            esperado=f"Memoria compartida con {n * k} datos; cada proceso independiente con {k}",
            real=f"Compartida: {compartidos} datos · independientes: {', '.join(map(str, independientes))}",
            resumen=(f"{len(tids)} hilos con TID nativo distinto dentro del mismo proceso. Cada hilo terminó con "
                     f"su propia pila de {k} elementos."),
            correcto=compartidos == n * k and all(x == k for x in independientes),
            datos={"compartidos": compartidos, "independientes": independientes},
        )

    def estado(self) -> dict:
        with self._lock:
            hilos = [{"nombre": h.nombre, "tid": h.tid_nativo, "estado": h.estado, "pila": len(h.pila),
                      "grupo": "hilos" if h.memoria is self.memoria_compartida else "procesos",
                      "memoria": len(h.memoria["datos"])} for h in self.hilos]
        return {"fase": self.fase, "hilos": hilos, "segmentos": self.linea.segmentos(),
                "ahora": self.linea.ahora(), "compartida": len(self.memoria_compartida["datos"]),
                "esperado_compartida": self.valores["hilos"] * self.valores["iteraciones"]}

    def procesos_bd(self) -> list[dict]:
        with self._lock:
            hilos = list(self.hilos)
        procesos = {1: {"pid": 1, "nombre": "P1 (con hilos)", "prioridad": 1, "rafaga": 1, "pc": 0,
                        "estado": "terminado", "hilos": []}}
        for h in hilos:
            if h.pid not in procesos:
                procesos[h.pid] = {"pid": h.pid, "nombre": f"P{h.pid} (independiente)", "prioridad": 1,
                                   "rafaga": 1, "pc": 0, "estado": "terminado", "hilos": []}
            procesos[h.pid]["hilos"].append({"tid": h.tid_nativo or 0, "nombre": h.nombre, "prioridad": 0,
                                             "estado": "terminado", "espera": 0})
        return list(procesos.values())


PASOS_MODOS = {
    "llamada read()": [
        ("usuario", "Proceso", "El programa ejecuta n = read(fd, buffer, 512) para leer un archivo."),
        ("usuario", "Biblioteca C", "El envoltorio de read() coloca el número de la llamada y los parámetros en registros."),
        ("kernel", "CPU", "Instrucción syscall (trap): el bit de modo cambia de 1 a 0. Ahora la CPU está en MODO KERNEL."),
        ("kernel", "Kernel", "Guarda el contexto del proceso (PC y registros) en su PCB."),
        ("kernel", "Kernel", "Busca la rutina en la tabla de llamadas al sistema y valida fd y buffer."),
        ("kernel", "Controlador de disco", "El kernel envía la orden de lectura al controlador del disco."),
        ("kernel", "Planificador", "El proceso pasa a BLOQUEADO y la CPU se asigna a otro proceso."),
        ("kernel", "Disco", "El disco termina la lectura y genera una INTERRUPCIÓN."),
        ("kernel", "Rutina de interrupción", "Copia los datos al buffer del proceso; el proceso pasa a LISTO."),
        ("kernel", "Planificador", "El proceso vuelve a ser despachado y se restaura su contexto."),
        ("usuario", "CPU", "Retorno de la llamada (sysret): el bit de modo vuelve a 1. MODO USUARIO."),
        ("usuario", "Proceso", "read() devuelve 512 y el programa usa los datos leídos."),
    ],
    "interrupción de teclado": [
        ("usuario", "Proceso", "Un proceso ejecuta su código normalmente en modo usuario."),
        ("usuario", "Teclado", "Se presiona una tecla: el controlador del teclado activa una línea de interrupción."),
        ("kernel", "CPU", "Al terminar la instrucción actual, la CPU atiende la interrupción y pasa a MODO KERNEL."),
        ("kernel", "CPU", "Guarda PC y registros y busca la rutina en el vector de interrupciones."),
        ("kernel", "Rutina de interrupción", "Lee el código de la tecla del controlador y lo guarda en un buffer del kernel."),
        ("kernel", "Kernel", "Despierta al proceso que esperaba el teclado (BLOQUEADO → LISTO)."),
        ("kernel", "CPU", "Restaura el contexto del proceso que fue interrumpido."),
        ("usuario", "CPU", "Retorno de interrupción (iret): vuelve a MODO USUARIO."),
        ("usuario", "Proceso", "El proceso continúa donde iba, sin notar la interrupción."),
    ],
}


class EscenarioModos(Escenario):
    codigo = "F5"
    nombre = "Modo usuario ↔ modo kernel"
    modulo = "B"
    vista = "modos"
    explicacion = ("La CPU tiene dos modos. En modo usuario los programas no pueden acceder directamente al hardware; "
                   "en modo kernel el sistema operativo tiene acceso total. Un programa entra al kernel de forma "
                   "controlada con una llamada al sistema (trap), y el hardware lo hace con una interrupción. "
                   "Al terminar, se regresa a modo usuario.")
    parametros = [Parametro("caso", "Caso", "opcion", "llamada read()", opciones=tuple(PASOS_MODOS))]

    def __init__(self, valores, control, registro) -> None:
        super().__init__(valores, control, registro)
        self.pasos = PASOS_MODOS[self.valores["caso"]]
        self.indice = -1

    def ejecutar(self) -> Resultado:
        cambios = 0
        modo = "usuario"
        for i, (nuevo_modo, actor, texto) in enumerate(self.pasos):
            self.control.punto_control(1.6)
            self.indice = i
            if nuevo_modo != modo:
                cambios += 1
                self.registro.registrar("modo", f"cambio de modo · {actor}", anterior=modo, nuevo=nuevo_modo)
                modo = nuevo_modo
            self.registro.registrar("sys" if modo == "kernel" else "user", f"{i + 1}. {actor}: {texto}")
        self.indice = len(self.pasos)
        en_kernel = sum(1 for m, _, _ in self.pasos if m == "kernel")
        return Resultado(
            esperado="Entra a modo kernel y regresa a modo usuario (2 cambios de modo)",
            real=f"{cambios} cambios de modo · {en_kernel} de {len(self.pasos)} pasos en modo kernel",
            resumen="El proceso solo toca el hardware a través del kernel; al final vuelve a modo usuario.",
            correcto=cambios == 2 and modo == "usuario",
            datos={"cambios": cambios},
        )

    def estado(self) -> dict:
        return {"pasos": self.pasos, "indice": self.indice, "caso": self.valores["caso"]}


# =============================================================================
# Módulo C · Concurrencia (F6, F7, F8, F9)
# =============================================================================
class EscenarioCarrera(Escenario):
    codigo = "F6"
    nombre = "Condición de carrera"
    modulo = "C"
    vista = "carrera"
    explicacion = ("Varios hilos incrementan un contador compartido. Incrementar son tres pasos: leer el valor, sumarle "
                   "1 y escribirlo. Si el sistema operativo cambia de hilo entre la lectura y la escritura, otro hilo "
                   "lee el mismo valor viejo y una de las dos actualizaciones se pierde. El resultado depende del "
                   "orden de ejecución: eso es una condición de carrera.")
    parametros = [
        Parametro("hilos", "Número de hilos", "int", 2, 2, 8),
        Parametro("incrementos", "Incrementos por hilo", "int", 20, 1, 500),
    ]

    def __init__(self, valores, control, registro) -> None:
        super().__init__(valores, control, registro)
        self.fases: list[dict] = []           # una por cada corrida (sin / con protección)
        self.actual: dict | None = None

    def _corrida(self, titulo: str, mecanismo_nombre: str, permisos: int = 1) -> dict:
        n, m = self.valores["hilos"], self.valores["incrementos"]
        mecanismo = crear_mecanismo(mecanismo_nombre, permisos)
        datos = {"titulo": titulo, "mecanismo": mecanismo_nombre, "permisos": permisos, "contador": 0,
                 "esperado": n * m, "por_hilo": {f"H{i + 1}": 0 for i in range(n)}, "esperas": 0,
                 "terminado": False}
        self.actual = datos
        self.fases.append(datos)
        memoria = {"contador": 0}
        detallado = m <= 30                    # con muchos incrementos no se registra cada lectura

        def trabajo(h: HiloSimulado) -> None:
            for _ in range(m):
                if mecanismo is not None:
                    if not mecanismo.acquire(blocking=False):
                        datos["esperas"] += 1
                        if detallado:
                            self.registro.registrar("wait", f"espera el {mecanismo_nombre} (otro hilo está en la "
                                                            "sección crítica)", hilo=h.nombre)
                        adquirir(mecanismo, self.control)
                try:
                    valor = memoria["contador"]                 # 1. leer
                    if detallado:
                        self.registro.registrar("read", f"lee contador = {valor}", hilo=h.nombre)
                    self.control.punto_control(0.15)            # aquí puede ocurrir el cambio de contexto
                    memoria["contador"] = valor + 1             # 2. sumar y 3. escribir
                    datos["contador"] = memoria["contador"]
                    datos["por_hilo"][h.nombre] += 1
                    if detallado:
                        self.registro.registrar("write", f"escribe contador = {valor + 1}", hilo=h.nombre)
                finally:
                    if mecanismo is not None:
                        mecanismo.release()

        hilos = [HiloSimulado(f"H{i + 1}", memoria, trabajo, self.registro, pid=1) for i in range(n)]
        for h in hilos:
            h.start()
        esperar_hilos(hilos, self.control)
        datos["terminado"] = True
        perdidas = datos["esperado"] - datos["contador"]
        tipo = "carrera" if perdidas else "ok"
        self.registro.registrar(tipo, f"{titulo}: esperado {datos['esperado']} · real {datos['contador']} · "
                                      f"perdidas {perdidas}")
        return datos

    def ejecutar(self) -> Resultado:
        d = self._corrida("Sin protección", "ninguno")
        perdidas = d["esperado"] - d["contador"]
        return Resultado(
            esperado=f"contador = {d['esperado']}",
            real=f"contador = {d['contador']}",
            resumen=(f"Se perdieron {perdidas} actualizaciones ({perdidas / d['esperado']:.0%}) porque los hilos "
                     "leyeron el mismo valor antes de que el otro escribiera." if perdidas else
                     "Esta vez no se perdió ninguna actualización; repita con más hilos o incrementos."),
            correcto=perdidas == 0,
            datos={"fases": self.fases},
        )

    def estado(self) -> dict:
        return {"fases": [dict(f, por_hilo=dict(f["por_hilo"])) for f in self.fases]}

    def procesos_bd(self) -> list[dict]:
        n = self.valores["hilos"]
        return [{"pid": 1, "nombre": "P1 (contador compartido)", "prioridad": 1, "rafaga": 1, "pc": 0,
                 "estado": "terminado",
                 "hilos": [{"tid": i + 1, "nombre": f"H{i + 1}", "prioridad": 0, "estado": "terminado", "espera": 0}
                           for i in range(n)]}]

    def recursos_bd(self):
        return [{"nombre": "contador", "tipo": "variable", "instancias": 1}], []


class EscenarioSeccionCritica(EscenarioCarrera):
    codigo = "F7"
    nombre = "Sección crítica"
    explicacion = ("La sección crítica es el código que usa el recurso compartido (leer, sumar y escribir el contador). "
                   "Con exclusión mutua solo un hilo puede estar dentro a la vez: los demás esperan. Un mutex (Lock) "
                   "o un semáforo binario (1 permiso) lo garantizan. Con un semáforo de 2 o más permisos, varios hilos "
                   "entran a la vez y la carrera vuelve a aparecer.")
    parametros = EscenarioCarrera.parametros + [
        Parametro("mecanismo", "Mecanismo", "opcion", "mutex", opciones=("mutex", "semaforo")),
        Parametro("permisos", "Permisos del semáforo", "int", 1, 1, 4, ayuda="solo para semáforo"),
    ]

    @property
    def mecanismo(self) -> str:
        return self.valores["mecanismo"]

    def ejecutar(self) -> Resultado:
        sin = self._corrida("Sin protección", "ninguno")
        mec = self.valores["mecanismo"]
        permisos = self.valores["permisos"] if mec == "semaforo" else 1
        etiqueta = "mutex" if mec == "mutex" else f"semáforo ({permisos} permiso{'s' if permisos > 1 else ''})"
        con = self._corrida(f"Con {etiqueta}", mec, permisos)
        ok = con["contador"] == con["esperado"]
        return Resultado(
            esperado=f"contador = {con['esperado']}",
            real=f"sin protección = {sin['contador']} · con {etiqueta} = {con['contador']}",
            resumen=(f"Con {etiqueta} el resultado es correcto: los hilos esperaron {con['esperas']} veces para "
                     "entrar a la sección crítica." if ok else
                     f"Con {etiqueta} varios hilos entran a la vez a la sección crítica, así que la carrera sigue."),
            correcto=ok,
            datos={"fases": self.fases},
        )

    def recursos_bd(self):
        return [{"nombre": "contador", "tipo": "variable", "instancias": 1},
                {"nombre": self.valores["mecanismo"], "tipo": "variable", "instancias": self.valores["permisos"]}], []


class EscenarioInterbloqueo(Escenario):
    codigo = "F8"
    nombre = "Interbloqueo"
    modulo = "C"
    vista = "interbloqueo"
    explicacion = ("Hay interbloqueo cuando se cumplen a la vez las cuatro condiciones de Coffman: exclusión mutua, "
                   "retener y esperar, no expropiación y espera circular. H1 toma R1 y pide R2; H2 toma R2 y pide R1: "
                   "ninguno puede avanzar. Prevención: si todos piden los recursos en el mismo orden global "
                   "(primero R1, luego R2) la espera circular no puede ocurrir.")
    parametros = [
        Parametro("estrategia", "Estrategia", "opcion", "sin prevención",
                  opciones=("sin prevención", "orden global de recursos")),
        Parametro("limite", "Tiempo de espera máximo (s)", "float", 4, 1, 15,
                  ayuda="después se detecta el bloqueo y se liberan los recursos"),
    ]

    def __init__(self, valores, control, registro) -> None:
        super().__init__(valores, control, registro)
        self.grafo = GrafoEspera()
        self.locks = {"R1": threading.Lock(), "R2": threading.Lock()}
        for r in self.locks:
            self.grafo.agregar_recurso(r)
        for h in ("H1", "H2"):
            self.grafo.agregar_hilo(h)
        self.ciclo: list[str] = []
        self.historial: list[dict] = []
        self.estados = {"H1": "nuevo", "H2": "nuevo"}
        self.completados: list[str] = []
        self.detectado_en: int | None = None

    def _anotar(self, hilo: str, recurso: str, tipo: str) -> None:
        self.historial.append({"hilo": hilo, "recurso": recurso, "tipo": tipo, "tiempo": self.registro.tiempo})

    def _pedir(self, hilo: str, recurso: str) -> bool:
        """Pide un recurso; espera hasta el límite (sin contar el tiempo en pausa)."""
        lock = self.locks[recurso]
        if lock.acquire(blocking=False):
            self.grafo.asignar(hilo, recurso)
            self._anotar(hilo, recurso, "retiene")
            self.registro.registrar("lock", f"obtiene {recurso}", hilo=hilo)
            return True
        self.grafo.solicitar(hilo, recurso)
        self._anotar(hilo, recurso, "espera")
        self.estados[hilo] = "bloqueado"
        self.registro.registrar("wait", f"pide {recurso}, pero lo tiene otro hilo: queda esperando", hilo=hilo,
                                anterior="ejecucion", nuevo="bloqueado")
        restante = self.valores["limite"]
        while restante > 0:
            self.control.verificar()
            t0 = time.monotonic()
            if lock.acquire(timeout=0.05):
                self.grafo.asignar(hilo, recurso)
                self._anotar(hilo, recurso, "retiene")
                self.estados[hilo] = "ejecucion"
                self.registro.registrar("lock", f"por fin obtiene {recurso}", hilo=hilo,
                                        anterior="bloqueado", nuevo="ejecucion")
                return True
            if not self.control.pausado:
                restante -= (time.monotonic() - t0) * self.control.velocidad
        self.grafo.cancelar_espera(hilo)
        self.registro.registrar("timeout", f"se cansa de esperar {recurso} y libera lo que tiene", hilo=hilo)
        return False

    def _trabajo(self, primero: str, segundo: str):
        def trabajo(h: HiloSimulado) -> None:
            self.estados[h.nombre] = "ejecucion"
            tomados = []
            try:
                if not self._pedir(h.nombre, primero):
                    return
                tomados.append(primero)
                self.control.punto_control(1.5)      # mientras tanto el otro hilo toma su primer recurso
                if not self._pedir(h.nombre, segundo):
                    return
                tomados.append(segundo)
                self.registro.registrar("exec", f"usa {primero} y {segundo} (sección crítica)", hilo=h.nombre)
                self.control.punto_control(1.0)
                self.completados.append(h.nombre)
            finally:
                for r in reversed(tomados):
                    self.grafo.liberar(h.nombre, r)
                    self.locks[r].release()
                    self._anotar(h.nombre, r, "libera")
                    self.registro.registrar("unlock", f"libera {r}", hilo=h.nombre)
                self.estados[h.nombre] = "terminado"
        return trabajo

    def ejecutar(self) -> Resultado:
        orden = self.valores["estrategia"] == "orden global de recursos"
        h1 = HiloSimulado("H1", {}, self._trabajo("R1", "R2"), self.registro, pid=1)
        h2 = HiloSimulado("H2", {}, self._trabajo("R1", "R2") if orden else self._trabajo("R2", "R1"),
                          self.registro, pid=1)
        h1.start()
        if orden:
            self.control.esperar(0.3)
        h2.start()
        # hilo monitor: detección de interbloqueo con el grafo de espera
        while h1.is_alive() or h2.is_alive():
            ciclo = self.grafo.detectar_ciclo()
            if ciclo and not self.ciclo:
                self.ciclo = ciclo
                self.detectado_en = self.registro.tiempo
                self.registro.registrar("deadlock", "INTERBLOQUEO detectado · espera circular: "
                                        + " → ".join(ciclo + [ciclo[0]]))
            time.sleep(0.05)
            self.control.verificar()
        hubo = bool(self.ciclo)
        return Resultado(
            esperado=("Interbloqueo: espera circular H1 → R2 → H2 → R1 → H1" if not orden
                      else "Sin interbloqueo: ambos hilos terminan"),
            real=(("Interbloqueo detectado (espera circular); se rompió por tiempo de espera"
                   + (f" y después terminó {', '.join(self.completados)}" if self.completados else ""))
                  if hubo else f"Sin interbloqueo · terminaron: {', '.join(self.completados) or 'ninguno'}"),
            resumen=("Cada hilo retenía un recurso y esperaba el del otro. Se rompió el bloqueo por tiempo de espera "
                     "(los hilos liberaron sus recursos)." if hubo else
                     "Pidiendo R1 antes que R2 nadie retiene R2 mientras espera R1: no hay espera circular."),
            correcto=hubo != orden,
            datos={"interbloqueo": hubo, "completados": list(self.completados)},
        )

    def estado(self) -> dict:
        return {"aristas": self.grafo.aristas(), "ciclo": list(self.ciclo), "estados": dict(self.estados),
                "estrategia": self.valores["estrategia"], "completados": list(self.completados)}

    @property
    def mecanismo(self) -> str:
        return "mutex"

    def procesos_bd(self) -> list[dict]:
        return [{"pid": 1, "nombre": "P1 (dos hilos, dos recursos)", "prioridad": 1, "rafaga": 1, "pc": 0,
                 "estado": "terminado",
                 "hilos": [{"tid": i + 1, "nombre": h, "prioridad": 0, "estado": "terminado", "espera": 0}
                           for i, h in enumerate(("H1", "H2"))]}]

    def recursos_bd(self):
        recursos = [{"nombre": r, "tipo": "dispositivo", "instancias": 1} for r in self.locks]
        asign = [a for a in self.historial if a["tipo"] in ("retiene", "espera")]
        return recursos, asign


class EscenarioInanicion(Escenario):
    codigo = "F9"
    nombre = "Inanición"
    modulo = "C"
    vista = "inanicion"
    explicacion = ("El recurso siempre se entrega al hilo de mejor prioridad (1 = más alta). Si los hilos de alta "
                   "prioridad lo piden una y otra vez, el hilo de baja prioridad nunca lo obtiene: sufre inanición, "
                   "aunque no hay interbloqueo. Solución: envejecimiento (aging). Cada vez que un hilo se queda "
                   "esperando, su prioridad mejora, hasta que le toca.")
    parametros = [
        Parametro("altos", "Hilos de alta prioridad", "int", 2, 2, 4),
        Parametro("rondas", "Asignaciones del recurso", "int", 12, 6, 40),
        Parametro("envejecimiento", "Envejecimiento (aging)", "opcion", "no", opciones=("no", "sí")),
    ]
    PRIORIDAD_ALTA, PRIORIDAD_BAJA = 1, 5

    def __init__(self, valores, control, registro) -> None:
        super().__init__(valores, control, registro)
        self.recurso = RecursoConPrioridad(envejecimiento=1.0 if self.valores["envejecimiento"] == "sí" else 0.0)
        nombres = [f"A{i + 1}" for i in range(self.valores["altos"])] + ["B1"]
        self.info = {n: {"prioridad": self.PRIORIDAD_ALTA if n.startswith("A") else self.PRIORIDAD_BAJA,
                         "accesos": 0, "espera": 0.0, "estado": "nuevo", "desde": None} for n in nombres}

    def _trabajo(self, h: HiloSimulado) -> None:
        info = self.info[h.nombre]
        while True:
            self.control.verificar()
            info["estado"] = "esperando"
            info["desde"] = time.monotonic()
            obtenido = self.recurso.solicitar(h.nombre, info["prioridad"], self.control)
            info["espera"] += (time.monotonic() - info["desde"]) * self.control.velocidad
            info["desde"] = None
            if not obtenido:
                info["estado"] = "terminado"
                if info["accesos"] == 0:
                    self.registro.registrar("starve", "terminó sin obtener nunca el recurso: INANICIÓN",
                                            hilo=h.nombre)
                return
            info["accesos"] += 1
            info["estado"] = "usando"
            self.registro.registrar("lock", f"obtiene el recurso (asignación {self.recurso.asignaciones})",
                                    hilo=h.nombre)
            try:
                self.control.punto_control(0.8)
            finally:
                info["estado"] = "listo"
                self.recurso.liberar(h.nombre)
            if self.recurso.asignaciones >= self.valores["rondas"]:
                self.recurso.cerrar()
            if h.nombre.startswith("B"):          # el hilo de baja prioridad solo necesita usarlo una vez
                info["estado"] = "terminado"
                return

    def ejecutar(self) -> Resultado:
        altos = [HiloSimulado(n, {}, self._trabajo, self.registro, pid=1, prioridad=self.PRIORIDAD_ALTA)
                 for n in self.info if n.startswith("A")]
        bajo = HiloSimulado("B1", {}, self._trabajo, self.registro, pid=1, prioridad=self.PRIORIDAD_BAJA)
        for h in altos:
            h.start()
        while self.recurso.asignaciones == 0:        # el bajo llega cuando el recurso ya está en uso
            self.control.verificar()
            time.sleep(0.01)
        bajo.start()
        esperar_hilos(altos + [bajo], self.control)
        b = self.info["B1"]
        aging = self.valores["envejecimiento"] == "sí"
        return Resultado(
            esperado=("B1 obtiene el recurso gracias al envejecimiento" if aging
                      else "B1 (prioridad baja) nunca obtiene el recurso"),
            real=(f"B1: {b['accesos']} acceso(s) · esperó {b['espera']:.1f} s · "
                  + ", ".join(f"{n}: {d['accesos']}" for n, d in self.info.items() if n != "B1")),
            resumen=("Con envejecimiento la prioridad de B1 mejoró en cada ronda hasta superar a los demás."
                     if b["accesos"] else
                     "Los hilos de alta prioridad siempre estaban esperando y siempre ganaron: B1 sufrió inanición."),
            correcto=bool(b["accesos"]) == aging,
            datos={"accesos_b1": b["accesos"]},
        )

    def estado(self) -> dict:
        ahora = time.monotonic()
        filas = []
        for n, d in self.info.items():
            espera = d["espera"] + ((ahora - d["desde"]) * self.control.velocidad if d["desde"] else 0)
            efectiva = self.recurso.prioridad_efectiva(n)
            filas.append({"nombre": n, "prioridad": d["prioridad"], "efectiva": efectiva, "accesos": d["accesos"],
                          "espera": espera, "estado": d["estado"]})
        return {"hilos": filas, "ocupado_por": self.recurso.ocupado_por, "asignaciones": self.recurso.asignaciones,
                "rondas": self.valores["rondas"], "envejecimiento": self.valores["envejecimiento"]}

    def procesos_bd(self) -> list[dict]:
        return [{"pid": 1, "nombre": "P1 (hilos con prioridades)", "prioridad": 1, "rafaga": 1, "pc": 0,
                 "estado": "terminado",
                 "hilos": [{"tid": i + 1, "nombre": n, "prioridad": d["prioridad"], "estado": "terminado",
                            "espera": round(d["espera"] * 1000)} for i, (n, d) in enumerate(self.info.items())]}]

    def recursos_bd(self):
        return [{"nombre": "recurso compartido", "tipo": "dispositivo", "instancias": 1}], []


ESCENARIOS: dict[str, type[Escenario]] = {e.codigo: e for e in (
    EscenarioProcesos, EscenarioPCB, EscenarioCicloVida, EscenarioHilos, EscenarioModos,
    EscenarioCarrera, EscenarioSeccionCritica, EscenarioInterbloqueo, EscenarioInanicion)}

MODULOS = {"A": "Gestión de procesos", "B": "Hilos y modos de ejecución", "C": "Concurrencia"}
