"""Controlador (MVC).

Valida los datos del usuario, inicia, pausa o reinicia la simulación, controla el
reloj (velocidad y paso a paso) y entrega a la vista el estado del modelo. La
simulación corre en un hilo trabajador para que la ventana no se congele.
"""
from __future__ import annotations

import threading
from pathlib import Path

from nucleo.base_datos import BaseDatos, RUTA_POR_DEFECTO
from nucleo.escenarios import ESCENARIOS, Escenario, Resultado
from nucleo.registro import Registro
from nucleo.sincronizacion import ControlEjecucion, SimulacionDetenida


class Controlador:
    def __init__(self, ruta_bd: str | Path = RUTA_POR_DEFECTO, retardo_base: float = 0.35) -> None:
        self.bd = BaseDatos(ruta_bd)
        self.retardo_base = retardo_base
        self.escenario: Escenario | None = None
        self.registro: Registro | None = None
        self.control: ControlEjecucion | None = None
        self.resultado: Resultado | None = None
        self.error: str | None = None
        self.id_ejecucion: int | None = None
        self.estado_ejecucion = "inactivo"         # inactivo, corriendo, finalizada, cancelada, error
        self._hilo: threading.Thread | None = None

    # ------------------------------------------------------------------ catálogo
    @staticmethod
    def escenarios() -> list[type[Escenario]]:
        return list(ESCENARIOS.values())

    @staticmethod
    def validar(codigo: str, valores: dict) -> dict:
        if codigo not in ESCENARIOS:
            raise ValueError(f"Escenario desconocido: {codigo}")
        return ESCENARIOS[codigo].validar(valores)

    # ------------------------------------------------------------------ ciclo de vida
    @property
    def en_curso(self) -> bool:
        return self._hilo is not None and self._hilo.is_alive()

    def iniciar(self, codigo: str, valores: dict, velocidad: float = 1.0, pausado: bool = False) -> None:
        if self.en_curso:
            raise RuntimeError("Ya hay una simulación en curso. Reiníciela primero.")
        valores = self.validar(codigo, valores)
        self.registro = Registro()
        self.control = ControlEjecucion(velocidad, self.retardo_base, pausado=pausado)
        self.escenario = ESCENARIOS[codigo](valores, self.control, self.registro)
        if not hasattr(self.escenario, "planificador"):
            # en los escenarios con hilos, cada punto de control es un tic del reloj
            self.control.on_paso = self.registro.avanzar_reloj
        self.resultado, self.error = None, None
        self.id_ejecucion = self.bd.iniciar_ejecucion(codigo, self.escenario.mecanismo, self.control.velocidad)
        self.registro.registrar("inicio", f"{codigo} · {self.escenario.nombre} · parámetros: "
                                + ", ".join(f"{k}={v}" for k, v in valores.items()))
        self.estado_ejecucion = "corriendo"
        self._hilo = threading.Thread(target=self._correr, name="simulacion", daemon=True)
        self._hilo.start()

    def _correr(self) -> None:
        estado = "finalizada"
        try:
            self.resultado = self.escenario.ejecutar()
            self.registro.registrar("fin", f"esperado: {self.resultado.esperado} · real: {self.resultado.real}")
        except SimulacionDetenida:
            estado = "cancelada"
            self.registro.registrar("fin", "simulación reiniciada por el usuario")
        except Exception as exc:                     # se muestra en la vista; no debe tumbar la app
            estado = "cancelada"
            self.error = f"{type(exc).__name__}: {exc}"
            self.registro.registrar("error", self.error)
        try:
            self.bd.finalizar_ejecucion(
                self.id_ejecucion, estado,
                self.resultado.esperado if self.resultado else None,
                self.resultado.real if self.resultado else None,
                self.escenario.procesos_bd(), self.escenario.recursos_bd(), self.registro.eventos())
        except Exception as exc:
            self.error = f"No se pudo guardar en la base de datos: {exc}"
        self.estado_ejecucion = "error" if self.error else estado

    def pausar(self) -> None:
        if self.control:
            self.control.pausar()

    def reanudar(self) -> None:
        if self.control:
            self.control.reanudar()

    def paso(self) -> None:
        if self.control:
            self.control.paso()

    def cambiar_velocidad(self, valor: float) -> None:
        if self.control:
            self.control.velocidad = valor

    def reiniciar(self, espera: float = 5.0) -> None:
        if self.control:
            self.control.detener()
        if self._hilo is not None:
            self._hilo.join(espera)
        self._hilo = None
        self.escenario = self.registro = self.control = self.resultado = None
        self.estado_ejecucion = "inactivo"

    def esperar_fin(self, tiempo: float | None = None) -> None:
        if self._hilo is not None:
            self._hilo.join(tiempo)

    # ------------------------------------------------------------------ F1 en vivo
    def crear_proceso(self, nombre: str, prioridad, rafaga) -> int:
        pl = getattr(self.escenario, "planificador", None)
        if pl is None or not self.en_curso:
            raise RuntimeError("Inicie primero un escenario del Módulo A.")
        return pl.crear_proceso(nombre, int(prioridad), int(rafaga)).pid

    def finalizar_proceso(self, pid: int) -> None:
        pl = getattr(self.escenario, "planificador", None)
        if pl is None or not self.en_curso:
            raise RuntimeError("Inicie primero un escenario del Módulo A.")
        pl.finalizar_proceso(int(pid))

    # ------------------------------------------------------------------ consultas
    def estado_vista(self) -> dict:
        return self.escenario.estado() if self.escenario else {}

    def exportar_bitacora(self, ruta: str | Path) -> Path:
        if not self.registro:
            raise RuntimeError("No hay bitácora para exportar.")
        enc = f"Escenario: {self.escenario.codigo} · {self.escenario.nombre} · ejecución #{self.id_ejecucion}"
        if self.resultado:
            enc += f"\nEsperado: {self.resultado.esperado}\nReal: {self.resultado.real}"
        return self.registro.exportar_txt(ruta, enc)

    def historial(self) -> list[dict]:
        return self.bd.historial()

    def eventos_guardados(self, id_ejecucion: int) -> list[dict]:
        return self.bd.eventos(id_ejecucion)
