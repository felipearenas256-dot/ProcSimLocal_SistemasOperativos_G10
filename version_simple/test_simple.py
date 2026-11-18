"""Pruebas de ProcSim Simple. Ejecutar:  python -m unittest version_simple/test_simple.py -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import logica  # noqa: E402


class Pruebas(unittest.TestCase):
    def test_round_robin_termina_todos(self):
        pl = logica.Planificador(quantum=2)
        pl.crear("A", 3)
        pl.crear("B", 2)
        while not pl.terminado():
            pl.tic()
        self.assertTrue(all(p.estado == logica.TERMINADO for p in pl.procesos))

    def test_un_solo_proceso_en_cpu(self):
        pl = logica.Planificador()
        for i in range(3):
            pl.crear(f"P{i}", 3)
        for _ in range(5):
            pl.tic()
            self.assertLessEqual(sum(p.estado == logica.EJECUCION for p in pl.procesos), 1)

    def test_rafaga_invalida(self):
        with self.assertRaises(ValueError):
            logica.Planificador().crear("X", 0)

    def test_carrera_pierde_sumas(self):
        esperado, real = logica.carrera(4, 50, usar_mutex=False)
        self.assertLess(real, esperado)

    def test_mutex_da_resultado_exacto(self):
        esperado, real = logica.carrera(4, 50, usar_mutex=True)
        self.assertEqual(real, esperado)

    def test_interbloqueo_y_su_solucion(self):
        self.assertTrue(logica.interbloqueo(orden_global=False, espera_max=0.5)[0])
        self.assertFalse(logica.interbloqueo(orden_global=True, espera_max=0.5)[0])

    def test_inanicion_y_envejecimiento(self):
        self.assertEqual(logica.inanicion(10, envejecimiento=False)[0]["B1"], 0)
        self.assertGreaterEqual(logica.inanicion(10, envejecimiento=True)[0]["B1"], 1)


if __name__ == "__main__":
    unittest.main()
