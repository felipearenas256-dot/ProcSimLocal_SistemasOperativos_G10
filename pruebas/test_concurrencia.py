"""Pruebas del Módulo C: carrera, sección crítica, interbloqueo e inanición (F6 a F9)."""
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nucleo.escenarios import (EscenarioCarrera, EscenarioInanicion, EscenarioInterbloqueo,  # noqa: E402
                               EscenarioSeccionCritica)
from nucleo.registro import Registro  # noqa: E402
from nucleo.sincronizacion import (ControlEjecucion, GrafoEspera, RecursoConPrioridad,  # noqa: E402
                                   SimulacionDetenida, crear_mecanismo)

RAPIDO = 0.002          # retardo base pequeño para que las pruebas sean rápidas


def correr(cls, **valores):
    return cls(valores, ControlEjecucion(retardo_base=RAPIDO), Registro()).ejecutar()


class PruebasCarrera(unittest.TestCase):
    def test_sin_proteccion_pierde_actualizaciones(self):
        r = correr(EscenarioCarrera, hilos=3, incrementos=30)
        fase = r.datos["fases"][0]
        self.assertEqual(fase["esperado"], 90)
        self.assertLess(fase["contador"], 90)          # hubo condición de carrera
        self.assertFalse(r.correcto)

    def test_mutex_da_resultado_correcto(self):
        r = correr(EscenarioSeccionCritica, hilos=3, incrementos=30, mecanismo="mutex")
        sin, con = r.datos["fases"]
        self.assertLess(sin["contador"], sin["esperado"])
        self.assertEqual(con["contador"], con["esperado"])
        self.assertTrue(r.correcto)

    def test_semaforo_binario_correcto(self):
        r = correr(EscenarioSeccionCritica, hilos=3, incrementos=20, mecanismo="semaforo", permisos=1)
        self.assertEqual(r.datos["fases"][1]["contador"], 60)

    def test_semaforo_con_dos_permisos_no_protege(self):
        r = correr(EscenarioSeccionCritica, hilos=4, incrementos=20, mecanismo="semaforo", permisos=2)
        self.assertLess(r.datos["fases"][1]["contador"], 80)

    def test_crear_mecanismo(self):
        self.assertIsNone(crear_mecanismo("ninguno"))
        self.assertIsInstance(crear_mecanismo("mutex"), type(threading.Lock()))
        self.assertIsInstance(crear_mecanismo("semaforo", 2), threading.Semaphore)
        with self.assertRaises(ValueError):
            crear_mecanismo("otro")


class PruebasGrafoEspera(unittest.TestCase):
    def test_detecta_espera_circular(self):
        g = GrafoEspera()
        g.asignar("H1", "R1")
        g.asignar("H2", "R2")
        g.solicitar("H1", "R2")
        self.assertEqual(g.detectar_ciclo(), [])
        g.solicitar("H2", "R1")
        self.assertEqual(set(g.detectar_ciclo()), {"H1", "R2", "H2", "R1"})

    def test_sin_ciclo_al_liberar(self):
        g = GrafoEspera()
        g.asignar("H1", "R1")
        g.asignar("H2", "R2")
        g.solicitar("H1", "R2")
        g.solicitar("H2", "R1")
        g.cancelar_espera("H2")
        g.liberar("H2", "R2")
        self.assertEqual(g.detectar_ciclo(), [])


class PruebasInterbloqueo(unittest.TestCase):
    def test_sin_prevencion_hay_interbloqueo(self):
        r = correr(EscenarioInterbloqueo, estrategia="sin prevención", limite=1)
        self.assertTrue(r.datos["interbloqueo"])
        self.assertEqual(r.datos["completados"], [])

    def test_orden_global_lo_previene(self):
        r = correr(EscenarioInterbloqueo, estrategia="orden global de recursos", limite=1)
        self.assertFalse(r.datos["interbloqueo"])
        self.assertEqual(sorted(r.datos["completados"]), ["H1", "H2"])


class PruebasInanicion(unittest.TestCase):
    def test_baja_prioridad_sufre_inanicion(self):
        r = correr(EscenarioInanicion, altos=2, rondas=10, envejecimiento="no")
        self.assertEqual(r.datos["accesos_b1"], 0)

    def test_envejecimiento_la_corrige(self):
        r = correr(EscenarioInanicion, altos=2, rondas=12, envejecimiento="sí")
        self.assertGreaterEqual(r.datos["accesos_b1"], 1)

    def test_recurso_elige_mejor_prioridad(self):
        rec = RecursoConPrioridad()
        self.assertTrue(rec.solicitar("X", 1))         # libre: lo obtiene de inmediato
        resultados = []
        hilos = [threading.Thread(target=lambda n=n, p=p: resultados.append(n) if rec.solicitar(n, p) else None)
                 for n, p in (("baja", 5), ("alta", 1))]
        for h in hilos:
            h.start()
        import time
        time.sleep(0.2)
        rec.liberar("X")
        time.sleep(0.2)
        self.assertEqual(resultados, ["alta"])
        rec.cerrar()
        for h in hilos:
            h.join(1)


class PruebasControl(unittest.TestCase):
    def test_paso_a_paso(self):
        c = ControlEjecucion(retardo_base=0, pausado=True)
        pasos = []
        t = threading.Thread(target=lambda: [c.punto_control() or pasos.append(i) for i in range(3)], daemon=True)
        t.start()
        t.join(0.3)
        self.assertEqual(pasos, [])              # en pausa no avanza
        c.paso()
        t.join(0.3)
        self.assertEqual(pasos, [0])             # un paso = un punto de control
        c.reanudar()
        t.join(1)
        self.assertEqual(pasos, [0, 1, 2])

    def test_detener_lanza_excepcion(self):
        c = ControlEjecucion(retardo_base=0)
        c.detener()
        with self.assertRaises(SimulacionDetenida):
            c.punto_control()

    def test_velocidad_limitada(self):
        c = ControlEjecucion()
        c.velocidad = 100
        self.assertEqual(c.velocidad, ControlEjecucion.VELOCIDAD_MAX)
        c.velocidad = 0
        self.assertEqual(c.velocidad, ControlEjecucion.VELOCIDAD_MIN)


if __name__ == "__main__":
    unittest.main()
