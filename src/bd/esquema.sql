-- =============================================================
-- ProcSim Local - Grupo 10 - Sistemas Operativos
-- Esquema de la base de datos local (SQLite 3)
-- Archivo de base de datos: procsim.db (se crea al iniciar la app)
-- =============================================================

PRAGMA foreign_keys = ON;

-- Catálogo de los 9 escenarios del simulador (F1 a F9).
CREATE TABLE IF NOT EXISTS escenario (
    id_escenario   INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo         TEXT    NOT NULL UNIQUE,          -- F1 ... F9
    nombre         TEXT    NOT NULL,
    modulo         TEXT    NOT NULL CHECK (modulo IN ('A', 'B', 'C')),
    descripcion    TEXT
);

-- Cada vez que el usuario ejecuta un escenario.
CREATE TABLE IF NOT EXISTS ejecucion (
    id_ejecucion       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_escenario       INTEGER NOT NULL REFERENCES escenario (id_escenario),
    fecha_inicio       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    fecha_fin          TEXT,
    mecanismo          TEXT    NOT NULL DEFAULT 'ninguno'
                       CHECK (mecanismo IN ('ninguno', 'mutex', 'semaforo')),
    velocidad          REAL    NOT NULL DEFAULT 1.0,
    resultado_esperado TEXT,
    resultado_real     TEXT,
    estado             TEXT    NOT NULL DEFAULT 'en_curso'
                       CHECK (estado IN ('en_curso', 'pausada', 'finalizada', 'cancelada'))
);

-- Procesos simulados de una ejecución (incluye los datos del PCB).
CREATE TABLE IF NOT EXISTS proceso (
    id_proceso          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ejecucion        INTEGER NOT NULL REFERENCES ejecucion (id_ejecucion) ON DELETE CASCADE,
    pid                 INTEGER NOT NULL,
    nombre              TEXT    NOT NULL,
    prioridad           INTEGER NOT NULL DEFAULT 0,
    tiempo_rafaga       INTEGER NOT NULL DEFAULT 1,
    contador_programa   INTEGER NOT NULL DEFAULT 0,
    estado              TEXT    NOT NULL DEFAULT 'nuevo'
                        CHECK (estado IN ('nuevo', 'listo', 'ejecucion', 'bloqueado', 'terminado')),
    UNIQUE (id_ejecucion, pid)
);

-- Hilos que pertenecen a un proceso.
CREATE TABLE IF NOT EXISTS hilo (
    id_hilo       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_proceso    INTEGER NOT NULL REFERENCES proceso (id_proceso) ON DELETE CASCADE,
    tid           INTEGER NOT NULL,
    nombre        TEXT    NOT NULL,
    prioridad     INTEGER NOT NULL DEFAULT 0,
    estado        TEXT    NOT NULL DEFAULT 'nuevo'
                  CHECK (estado IN ('nuevo', 'listo', 'ejecucion', 'bloqueado', 'terminado')),
    tiempo_espera INTEGER NOT NULL DEFAULT 0,          -- usado en F9 (inanición)
    UNIQUE (id_proceso, tid)
);

-- Recursos compartidos de una ejecución (contador, impresora, archivo...).
CREATE TABLE IF NOT EXISTS recurso (
    id_recurso    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ejecucion  INTEGER NOT NULL REFERENCES ejecucion (id_ejecucion) ON DELETE CASCADE,
    nombre        TEXT    NOT NULL,
    tipo          TEXT    NOT NULL CHECK (tipo IN ('variable', 'dispositivo', 'archivo')),
    instancias    INTEGER NOT NULL DEFAULT 1
);

-- Qué hilo retiene o espera qué recurso (grafo de espera de F8).
CREATE TABLE IF NOT EXISTS asignacion (
    id_asignacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_hilo       INTEGER NOT NULL REFERENCES hilo (id_hilo) ON DELETE CASCADE,
    id_recurso    INTEGER NOT NULL REFERENCES recurso (id_recurso) ON DELETE CASCADE,
    tipo          TEXT    NOT NULL CHECK (tipo IN ('retiene', 'espera')),
    tiempo        INTEGER NOT NULL
);

-- Bitácora: cada evento del motor de simulación.
CREATE TABLE IF NOT EXISTS evento (
    id_evento        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ejecucion     INTEGER NOT NULL REFERENCES ejecucion (id_ejecucion) ON DELETE CASCADE,
    id_proceso       INTEGER REFERENCES proceso (id_proceso) ON DELETE CASCADE,
    id_hilo          INTEGER REFERENCES hilo (id_hilo) ON DELETE CASCADE,
    tiempo           INTEGER NOT NULL,                  -- tic del reloj de simulación
    tipo             TEXT    NOT NULL,                  -- fork, exec, sys, wait, thread, carrera, mutex...
    estado_anterior  TEXT,
    estado_nuevo     TEXT,
    mensaje          TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evento_ejecucion ON evento (id_ejecucion, tiempo);

-- Datos iniciales: los 9 escenarios.
INSERT OR IGNORE INTO escenario (codigo, nombre, modulo, descripcion) VALUES
 ('F1', 'Crear y finalizar procesos', 'A', 'Crear procesos con nombre, prioridad y ráfaga; listarlos y terminarlos.'),
 ('F2', 'Consultar el PCB',           'A', 'Ver PID, estado, contador de programa, prioridad y registros.'),
 ('F3', 'Ciclo de vida',              'A', 'Transiciones entre nuevo, listo, ejecución, bloqueado y terminado.'),
 ('F4', 'Hilos de un proceso',        'B', 'Hilos con memoria compartida frente a procesos independientes.'),
 ('F5', 'Modo usuario y modo kernel', 'B', 'Llamada al sistema e interrupción de E/S con cambio de modo.'),
 ('F6', 'Condición de carrera',       'C', 'Dos hilos incrementan un contador compartido sin protección.'),
 ('F7', 'Sección crítica',            'C', 'El mismo caso protegido con mutex o semáforo.'),
 ('F8', 'Interbloqueo',               'C', 'Dos hilos retienen un recurso y esperan el del otro.'),
 ('F9', 'Inanición',                  'C', 'Un hilo de baja prioridad nunca obtiene el recurso.');
