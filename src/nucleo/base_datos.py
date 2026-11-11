"""Acceso a la base de datos local SQLite (procsim.db).

Guarda escenarios, ejecuciones, procesos, hilos, recursos, asignaciones y eventos.
El esquema está en src/bd/esquema.sql. Cada operación abre su propia conexión,
así se puede usar desde el hilo trabajador de la simulación sin compartir
conexiones entre hilos (sqlite3 no lo permite por defecto).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from nucleo.registro import Evento

RAIZ = Path(__file__).resolve().parents[2]
ESQUEMA = Path(__file__).resolve().parents[1] / "bd" / "esquema.sql"
RUTA_POR_DEFECTO = RAIZ / "procsim.db"

ESTADOS_VALIDOS = {"nuevo", "listo", "ejecucion", "bloqueado", "terminado"}


class BaseDatos:
    def __init__(self, ruta: str | Path = RUTA_POR_DEFECTO) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self._conexion() as con:
            con.executescript(ESQUEMA.read_text(encoding="utf-8"))

    @contextmanager
    def _conexion(self):
        con = sqlite3.connect(self.ruta, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    # ------------------------------------------------------------------ escritura
    def iniciar_ejecucion(self, codigo: str, mecanismo: str, velocidad: float) -> int:
        with self._conexion() as con:
            fila = con.execute("SELECT id_escenario FROM escenario WHERE codigo = ?", (codigo,)).fetchone()
            if fila is None:
                raise ValueError(f"Escenario desconocido: {codigo}")
            cur = con.execute("INSERT INTO ejecucion (id_escenario, mecanismo, velocidad) VALUES (?, ?, ?)",
                              (fila["id_escenario"], mecanismo, velocidad))
            return cur.lastrowid

    def finalizar_ejecucion(self, id_ejecucion: int, estado: str, esperado: str | None = None,
                            real: str | None = None, procesos: list[dict] | None = None,
                            recursos: tuple[list[dict], list[dict]] | None = None,
                            eventos: list[Evento] | None = None) -> None:
        """Guarda en una sola transacción el resultado y todo lo que pasó en la ejecución."""
        with self._conexion() as con:
            con.execute("""UPDATE ejecucion SET fecha_fin = datetime('now', 'localtime'), estado = ?,
                           resultado_esperado = ?, resultado_real = ? WHERE id_ejecucion = ?""",
                        (estado, esperado, real, id_ejecucion))
            ids_proceso: dict[int, int] = {}
            ids_hilo: dict[str, int] = {}
            for p in procesos or []:
                cur = con.execute("""INSERT INTO proceso (id_ejecucion, pid, nombre, prioridad, tiempo_rafaga,
                                     contador_programa, estado) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                  (id_ejecucion, p["pid"], p["nombre"], p["prioridad"], p["rafaga"], p["pc"],
                                   p["estado"] if p["estado"] in ESTADOS_VALIDOS else "terminado"))
                ids_proceso[p["pid"]] = cur.lastrowid
                for h in p.get("hilos", []):
                    cur = con.execute("""INSERT INTO hilo (id_proceso, tid, nombre, prioridad, estado, tiempo_espera)
                                         VALUES (?, ?, ?, ?, ?, ?)""",
                                      (ids_proceso[p["pid"]], h["tid"], h["nombre"], h["prioridad"],
                                       h["estado"], h["espera"]))
                    ids_hilo[h["nombre"]] = cur.lastrowid
            lista_recursos, asignaciones = recursos or ([], [])
            ids_recurso: dict[str, int] = {}
            for r in lista_recursos:
                cur = con.execute("INSERT INTO recurso (id_ejecucion, nombre, tipo, instancias) VALUES (?, ?, ?, ?)",
                                  (id_ejecucion, r["nombre"], r["tipo"], r["instancias"]))
                ids_recurso[r["nombre"]] = cur.lastrowid
            for a in asignaciones:
                if a["hilo"] in ids_hilo and a["recurso"] in ids_recurso:
                    con.execute("INSERT INTO asignacion (id_hilo, id_recurso, tipo, tiempo) VALUES (?, ?, ?, ?)",
                                (ids_hilo[a["hilo"]], ids_recurso[a["recurso"]], a["tipo"], a["tiempo"]))
            con.executemany(
                """INSERT INTO evento (id_ejecucion, id_proceso, id_hilo, tiempo, tipo, estado_anterior,
                   estado_nuevo, mensaje) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(id_ejecucion, ids_proceso.get(e.pid), ids_hilo.get(e.hilo), e.tiempo, e.tipo,
                  e.estado_anterior, e.estado_nuevo, e.mensaje) for e in (eventos or [])])

    # ------------------------------------------------------------------ consultas
    def historial(self, limite: int = 100) -> list[dict]:
        with self._conexion() as con:
            filas = con.execute(
                """SELECT x.id_ejecucion, e.codigo, e.nombre, x.fecha_inicio, x.fecha_fin, x.mecanismo,
                          x.velocidad, x.estado, x.resultado_esperado, x.resultado_real,
                          (SELECT COUNT(*) FROM evento v WHERE v.id_ejecucion = x.id_ejecucion) AS eventos
                   FROM ejecucion x JOIN escenario e ON e.id_escenario = x.id_escenario
                   ORDER BY x.id_ejecucion DESC LIMIT ?""", (limite,)).fetchall()
            return [dict(f) for f in filas]

    def eventos(self, id_ejecucion: int) -> list[dict]:
        with self._conexion() as con:
            filas = con.execute(
                """SELECT v.tiempo, v.tipo, p.pid, h.nombre AS hilo, v.estado_anterior, v.estado_nuevo, v.mensaje
                   FROM evento v LEFT JOIN proceso p ON p.id_proceso = v.id_proceso
                   LEFT JOIN hilo h ON h.id_hilo = v.id_hilo
                   WHERE v.id_ejecucion = ? ORDER BY v.id_evento""", (id_ejecucion,)).fetchall()
            return [dict(f) for f in filas]

    def contar(self, tabla: str) -> int:
        if tabla not in {"escenario", "ejecucion", "proceso", "hilo", "recurso", "asignacion", "evento"}:
            raise ValueError(tabla)
        with self._conexion() as con:
            return con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
