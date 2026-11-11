"""Pruebas del Módulo B: hilos de un proceso y modo usuario / kernel (F4, F5)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nucleo.escenarios import EscenarioHilos, EscenarioModos  # noqa: E402
from nucleo.registro import Registro  # noqa: E402
from nucleo.sincronizacion import ControlEjecucion  # noqa: E402


def crear(cls, **valores):
    return cls(valores, ControlEjecucion(retardo_base=0.002), Registro())


class PruebasHilos(unittest.TestCase):
    def test_memoria_compartida_vs_propia(self):
        e = crear(EscenarioHilos, hilos=4, iteraciones=3)
        r = e.ejecutar()
        self.assertEqual(r.datos["compartidos"], 12)            # los 4 hilos escriben en la misma memoria
        self.assertEqual(r.datos["independientes"], [3, 3, 3, 3])
        self.assertTrue(r.correcto)

    def test_hilos_nativos_distintos_y_pila_propia(self):
        e = crear(EscenarioHilos, hilos=3, iteraciones=2)
        e.ejecutar()
        del_proceso = [h for h in e.hilos if h.memoria is e.memoria_compartida]
        tids = {h.tid_nativo for h in del_proceso}
        self.assertEqual(len(tids), 3)
        self.assertTrue(all(len(h.pila) == 2 for h in del_proceso))

    def test_linea_de_tiempo(self):
        e = crear(EscenarioHilos, hilos=2, iteraciones=3)
        e.ejecutar()
        segs = e.estado()["segmentos"]
        self.assertEqual(len(segs), 2 * 3 * 2)                  # dos fases
        self.assertTrue(all(t1 >= t0 for _h, t0, t1, _g in segs))


class PruebasModos(unittest.TestCase):
    def test_read_cambia_dos_veces_de_modo(self):
        r = crear(EscenarioModos, caso="llamada read()").ejecutar()
        self.assertEqual(r.datos["cambios"], 2)
        self.assertTrue(r.correcto)

    def test_interrupcion(self):
        e = crear(EscenarioModos, caso="interrupción de teclado")
        r = e.ejecutar()
        self.assertEqual(r.datos["cambios"], 2)
        self.assertEqual(e.pasos[0][0], "usuario")
        self.assertEqual(e.pasos[-1][0], "usuario")

    def test_caso_invalido(self):
        with self.assertRaises(ValueError):
            crear(EscenarioModos, caso="otro")


if __name__ == "__main__":
    unittest.main()
