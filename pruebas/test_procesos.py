"""Pruebas del Módulo A: PCB, estados de proceso y planificador (F1, F2, F3)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nucleo.pcb import DIRECCION_BASE, PCB  # noqa: E402
from nucleo.proceso import (BLOQUEADO, EJECUCION, LISTO, NUEVO, TERMINADO, Planificador,  # noqa: E402
                            Proceso, TransicionInvalida)
from nucleo.registro import Registro  # noqa: E402


class PruebasPCB(unittest.TestCase):
    def test_pcb_inicial(self):
        pcb = PCB(pid=100, prioridad=2, rafaga_total=5)
        self.assertEqual(pcb.estado, "nuevo")
        self.assertEqual(pcb.contador_programa, DIRECCION_BASE)
        self.assertEqual(pcb.rafaga_restante, 5)

    def test_instruccion_avanza_pc_y_registros(self):
        pcb = PCB(pid=100, prioridad=2, rafaga_total=5)
        pcb.ejecutar_instruccion()
        self.assertEqual(pcb.contador_programa, DIRECCION_BASE + 4)
        self.assertEqual(pcb.registros["AX"], 1)
        self.assertEqual(pcb.rafaga_restante, 4)
        self.assertEqual(pcb.tiempo_cpu, 1)
        self.assertEqual(pcb.como_dict()["contador_programa"], "0x4004")


class PruebasEstados(unittest.TestCase):
    def test_transiciones_validas(self):
        p = Proceso(1, "P", 1, 3)
        self.assertEqual(p.cambiar_estado(LISTO), "admitir")
        self.assertEqual(p.cambiar_estado(EJECUCION), "despachar")
        self.assertEqual(p.cambiar_estado(BLOQUEADO), "espera E/S")
        self.assertEqual(p.cambiar_estado(LISTO), "E/S lista")
        p.cambiar_estado(EJECUCION)
        self.assertEqual(p.cambiar_estado(TERMINADO), "salir")

    def test_transicion_invalida(self):
        p = Proceso(1, "P", 1, 3)
        with self.assertRaises(TransicionInvalida):
            p.cambiar_estado(EJECUCION)          # nuevo -> ejecución no existe
        p.cambiar_estado(LISTO)
        with self.assertRaises(TransicionInvalida):
            p.cambiar_estado(BLOQUEADO)          # listo -> bloqueado no existe

    def test_finalizar_por_usuario(self):
        p = Proceso(1, "P", 1, 3)
        self.assertEqual(p.cambiar_estado(TERMINADO, finalizado_por_usuario=True), "finalizado por el usuario")


class PruebasPlanificador(unittest.TestCase):
    def nuevo(self, **kw):
        self.registro = Registro()
        return Planificador(self.registro, **kw)

    def test_crear_asigna_pid_y_valida(self):
        pl = self.nuevo()
        a = pl.crear_proceso("A", 1, 3)
        b = pl.crear_proceso("B", 2, 4)
        self.assertEqual((a.pid, b.pid), (100, 101))
        self.assertEqual(a.estado, NUEVO)
        for args in (("", 1, 3), ("X", 0, 3), ("X", 11, 3), ("X", 1, 0), ("X", 1, 51)):
            with self.assertRaises(ValueError):
                pl.crear_proceso(*args)

    def test_todos_terminan(self):
        pl = self.nuevo(prob_es=0.3)
        for i in range(5):
            pl.crear_proceso(f"P{i}", 1 + i % 3, 3 + i)
        for _ in range(300):
            if not pl.tic():
                break
        self.assertEqual(pl.activos(), 0)
        for p in pl.instantanea():
            self.assertEqual(p["estado"], TERMINADO)
            self.assertEqual(p["rafaga_restante"], 0)
            self.assertEqual(p["tiempo_cpu"], p["rafaga_total"])

    def test_solo_uno_en_cpu(self):
        pl = self.nuevo(prob_es=0.2)
        for i in range(4):
            pl.crear_proceso(f"P{i}", 2, 4)
        while pl.tic():
            en_ejecucion = [p for p in pl.instantanea() if p["estado"] == EJECUCION]
            self.assertLessEqual(len(en_ejecucion), 1)

    def test_prioridad_expropia(self):
        pl = self.nuevo(prob_es=0)
        baja = pl.crear_proceso("baja", 5, 10)
        pl.tic()          # admite
        pl.tic()          # baja entra a CPU
        self.assertEqual(pl.en_cpu, baja.pid)
        alta = pl.crear_proceso("alta", 1, 2)
        pl.tic()          # admite alta
        pl.tic()          # baja es expropiada y entra alta
        self.assertEqual(pl.en_cpu, alta.pid)
        self.assertIn("preempt", [e.tipo for e in self.registro.eventos()])

    def test_quantum_turna_iguales(self):
        pl = self.nuevo(prob_es=0, quantum=2)
        pl.crear_proceso("A", 3, 6)
        pl.crear_proceso("B", 3, 6)
        orden = []
        while pl.tic():
            if pl.en_cpu is not None and (not orden or orden[-1] != pl.en_cpu):
                orden.append(pl.en_cpu)
        self.assertGreaterEqual(len(orden), 4)         # A, B, A, B...
        self.assertNotEqual(orden[0], orden[1])

    def test_misma_semilla_misma_simulacion(self):
        def correr():
            pl = self.nuevo(prob_es=0.3, semilla=42)
            for i in range(4):
                pl.crear_proceso(f"P{i}", 1 + i % 2, 5)
            while pl.tic():
                pass
            return [(e.tiempo, e.tipo, e.pid) for e in self.registro.eventos()]
        self.assertEqual(correr(), correr())

    def test_finalizar_proceso(self):
        pl = self.nuevo(prob_es=0)
        p = pl.crear_proceso("A", 1, 10)
        pl.tic()
        pl.tic()
        pl.finalizar_proceso(p.pid)
        self.assertEqual(pl.procesos[p.pid].estado, TERMINADO)
        self.assertIsNone(pl.en_cpu)
        with self.assertRaises(ValueError):
            pl.finalizar_proceso(p.pid)
        with self.assertRaises(ValueError):
            pl.finalizar_proceso(999)


if __name__ == "__main__":
    unittest.main()
