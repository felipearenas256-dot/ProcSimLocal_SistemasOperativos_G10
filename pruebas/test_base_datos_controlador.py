"""Pruebas de integración: controlador + base de datos SQLite + bitácora."""
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from controlador import Controlador  # noqa: E402
from nucleo.base_datos import BaseDatos  # noqa: E402


class PruebasBaseDatos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name) / "prueba.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_esquema_y_escenarios(self):
        bd = BaseDatos(self.ruta)
        self.assertEqual(bd.contar("escenario"), 9)
        BaseDatos(self.ruta)                       # abrirla otra vez no duplica nada
        self.assertEqual(bd.contar("escenario"), 9)

    def test_llaves_foraneas(self):
        BaseDatos(self.ruta)
        con = sqlite3.connect(self.ruta)
        con.execute("PRAGMA foreign_keys = ON")
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO ejecucion (id_escenario) VALUES (999)")
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO ejecucion (id_escenario, mecanismo) VALUES (1, 'otro')")   # CHECK
        con.close()


class PruebasControlador(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name) / "prueba.db"
        self.c = Controlador(self.ruta, retardo_base=0.002)

    def tearDown(self):
        self.c.reiniciar()
        self.tmp.cleanup()

    def test_validacion(self):
        with self.assertRaises(ValueError):
            self.c.validar("F6", {"hilos": 50})
        with self.assertRaises(ValueError):
            self.c.validar("F6", {"hilos": "dos"})
        with self.assertRaises(ValueError):
            self.c.validar("F99", {})
        self.assertEqual(self.c.validar("F6", {"hilos": "3"})["hilos"], 3)

    def test_ejecucion_completa_se_guarda(self):
        self.c.iniciar("F8", {"limite": 1})
        self.c.esperar_fin(20)
        self.assertEqual(self.c.estado_ejecucion, "finalizada")
        fila = self.c.historial()[0]
        self.assertEqual(fila["codigo"], "F8")
        self.assertEqual(fila["estado"], "finalizada")
        self.assertEqual(fila["eventos"], len(self.c.registro))
        bd = self.c.bd
        self.assertEqual(bd.contar("hilo"), 2)
        self.assertEqual(bd.contar("recurso"), 2)
        self.assertGreaterEqual(bd.contar("asignacion"), 4)        # retiene x2 + espera x2
        eventos = self.c.eventos_guardados(fila["id_ejecucion"])
        self.assertIn("deadlock", [e["tipo"] for e in eventos])

    def test_procesos_se_guardan(self):
        self.c.iniciar("F1", {"procesos": 3})
        self.c.esperar_fin(30)
        self.assertEqual(self.c.bd.contar("proceso"), 3)

    def test_crear_proceso_en_vivo(self):
        self.c.iniciar("F1", {"procesos": 1}, pausado=True)
        pid = self.c.crear_proceso("Nuevo", 1, 2)
        self.assertEqual(pid, 101)
        with self.assertRaises(ValueError):
            self.c.crear_proceso("", 1, 2)
        self.c.reanudar()
        self.c.esperar_fin(30)
        self.assertEqual(self.c.bd.contar("proceso"), 2)

    def test_reiniciar_cancela_y_guarda(self):
        self.c.iniciar("F6", {"incrementos": 200}, pausado=True)
        self.c.paso()
        time.sleep(0.1)
        id_ejecucion = self.c.id_ejecucion
        self.c.reiniciar()
        self.assertFalse(self.c.en_curso)
        fila = next(f for f in self.c.historial() if f["id_ejecucion"] == id_ejecucion)
        self.assertEqual(fila["estado"], "cancelada")

    def test_no_inicia_dos_veces(self):
        self.c.iniciar("F5", {}, pausado=True)
        with self.assertRaises(RuntimeError):
            self.c.iniciar("F5", {})

    def test_exportar_bitacora(self):
        self.c.iniciar("F5", {})
        self.c.esperar_fin(20)
        ruta = Path(self.tmp.name) / "bitacora.txt"
        self.c.exportar_bitacora(ruta)
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn("ProcSim Local", texto)
        self.assertIn("F5", texto)
        self.assertIn("MODO KERNEL", texto)


if __name__ == "__main__":
    unittest.main()
