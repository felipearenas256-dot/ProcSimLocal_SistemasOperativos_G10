# ProcSim Local — Sistemas Operativos — Grupo 14

Simulador de escritorio de procesos, hilos y concurrencia para Windows.

| Asignatura | Grupo | Programa | Universidad | Fecha |
|---|---|---|---|---|
| Sistemas Operativos | 14 | Ingeniería de Software | Manuela Beltrán | Octubre 2026 |

## 1. Levantamiento de información

### Problemática
En la asignatura de Sistemas Operativos, los temas de procesos, hilos y concurrencia se estudian sobre todo en teoría: diapositivas, diagramas estáticos y ejercicios en papel. Esto genera varias dificultades:

- **Conceptos abstractos y difíciles de visualizar.** Los estados de un proceso, el bloque de control (PCB) o el cambio entre modo usuario y modo kernel ocurren dentro del sistema operativo y el estudiante no puede verlos.
- **Problemas de concurrencia que no se ven a simple vista.** La condición de carrera, el interbloqueo y la inanición dependen del orden en que se ejecutan los hilos. Es difícil entender por qué ocurren y cómo se corrigen sin verlos en acción.
- **Poca práctica.** Las herramientas reales para observar procesos son complejas, suelen requerir Linux, conocimientos avanzados o instalaciones especiales, y no están pensadas para enseñar.
- **Dificultad del docente para demostrar en clase.** No hay una herramienta sencilla con la que el docente pueda proyectar ejemplos paso a paso y repetirlos.

### Necesidad
Se necesita una **herramienta sencilla, local y visual** que permita a estudiantes y docentes:

- Ver cómo un sistema operativo crea, administra y termina procesos e hilos.
- Reproducir los problemas de concurrencia (condición de carrera, interbloqueo e inanición) y comparar el resultado sin protección contra el resultado usando mutex o semáforos.
- Controlar la simulación (iniciar, pausar, avanzar paso a paso, cambiar la velocidad y reiniciar) para analizar cada evento.
- Funcionar en Windows sin internet, sin servidor y sin instalaciones complejas.
- Guardar el historial de las simulaciones para revisarlas y exportarlas.

### Usuarios
| Usuario | Uso |
|---|---|
| Estudiante | Ejecuta escenarios y observa los resultados para entender los conceptos. |
| Docente | Proyecta ejemplos en clase y los repite paso a paso. |

## 2. Descripción del proyecto

### Objetivo
Desarrollar una aplicación de escritorio para Windows que simule, de forma visual e interactiva, cómo un sistema operativo **crea y administra procesos e hilos**, y cómo aparecen y se controlan los problemas de concurrencia: **condición de carrera, interbloqueo e inanición**.

### Funcionalidad
El simulador ofrece **9 funciones** organizadas en 3 módulos. En cada una, el usuario configura un escenario y la aplicación lo ejecuta y lo muestra en pantalla.

**Módulo A — Gestión de procesos:** cómo nace, vive y termina un proceso.

| # | Función | Descripción | Resultado en pantalla |
|---|---|---|---|---|
| F1 | Crear y finalizar procesos | Crear procesos con nombre, prioridad y tiempo de ráfaga; listarlos y terminarlos. | Lista de procesos activos |
| F2 | Consultar el PCB | Ver el bloque de control de cada proceso: PID, estado, contador de programa, prioridad y registros. | Ficha PCB actualizada en vivo |
| F3 | Ciclo de vida | Animar las transiciones entre nuevo, listo, ejecución, bloqueado y terminado. | Diagrama de estados animado |

**Módulo B — Hilos y modos de ejecución:** qué comparte un proceso con sus hilos y cuándo se entra al kernel.

| # | Función | Descripción | Resultado en pantalla |
|---|---|---|---|---|
| F4 | Hilos de un proceso | Crear varios hilos dentro de un proceso y compararlos con procesos independientes: memoria compartida frente a pila y registros propios. | Línea de tiempo por hilo |
| F5 | Modo usuario ↔ modo kernel | Simular una llamada al sistema (por ejemplo, `read()`) y una interrupción de E/S, mostrando el cambio de modo y el regreso. | Secuencia de pasos explicada |

**Módulo C — Concurrencia:** qué falla cuando varios hilos comparten recursos y cómo se corrige.

| # | Función | Descripción | Resultado en pantalla |
|---|---|---|---|---|
| F6 | Condición de carrera | Dos hilos incrementan un contador compartido sin protección. | Valor esperado vs. valor real |
| F7 | Sección crítica | Repetir el caso anterior usando mutex o semáforo. | Resultado correcto y comparación |
| F8 | Interbloqueo | Dos hilos retienen un recurso cada uno y esperan el del otro. | Grafo de espera circular |
| F9 | Inanición | Un hilo de baja prioridad nunca obtiene el recurso. | Tiempo de espera por hilo |

**En todos los escenarios:**
- **Controles:** iniciar, pausar, paso a paso, velocidad y reiniciar.
- **Bitácora** de eventos, que se guarda en la base de datos local y se puede exportar a `.txt`.
- **Explicación** breve del concepto teórico en pantalla.

### Arquitectura
Patrón **Modelo-Vista-Controlador (MVC)**:

- **Vista (`ui/`):** menú de escenarios, formularios de parámetros, lienzo de animación, panel PCB y panel de bitácora.
- **Controlador (`controlador.py`):** valida los datos, inicia, pausa o reinicia, controla el reloj de la simulación y envía los cambios a la vista.
- **Modelo (`nucleo/`):** motor de simulación con procesos, estados, hilos, sincronización, escenarios y registro de eventos.
- **Base de datos (`bd/`):** archivo SQLite local donde se guardan los escenarios, las ejecuciones y la bitácora de eventos.

### Entrada → Procesamiento → Salida
| Entrada | Procesamiento | Salida |
|---|---|---|
| Escenario elegido | Crea procesos y PCB | Diagrama de estados |
| N.º de procesos o hilos | Lanza hilos reales | Tabla PCB |
| Prioridad y ráfaga | Aplica reglas de estado | Línea de tiempo por hilo |
| Mecanismo: ninguno, mutex o semáforo | Detecta carrera, bloqueo o espera | Resultado esperado vs. real |
| Velocidad de animación | Registra cada evento en la base de datos | Bitácora exportable |

### Alcance
**Incluye**
- Prototipo funcional de escritorio, ejecutable en Windows.
- Las 9 funciones descritas en la funcionalidad.
- Hilos reales de Python en los escenarios de concurrencia.
- Base de datos local (SQLite) para guardar escenarios, ejecuciones y bitácora.
- Repositorio en GitHub, README y manual de usuario.
- Casos de prueba con capturas y análisis de resultados.

**No incluye**
- Crear o modificar un kernel real: los procesos son simulados.
- Gestión de memoria, sistema de archivos ni planificación avanzada.
- Versiones web, móvil, Linux o macOS.
- Inicio de sesión, base de datos en servidor o modo multiusuario.
- Control de los procesos reales del equipo del usuario.

## 3. Estructura del prototipo
### Front end
_Pendiente_
### Commits
_Pendiente_
### Base de datos
_Pendiente_
### Modelo relacional
_Pendiente_

## 4. Tecnologías
| Capa | Tecnología | Uso en el proyecto |
|---|---|---|
| Lenguaje | Python 3.12 | Lenguaje principal de la aplicación. |
| Interfaz (front end) | Tkinter + Canvas | Ventanas, formularios y animaciones de la simulación. |
| Concurrencia | `threading` · `Lock` · `Semaphore` | Hilos reales y mecanismos de sincronización en los escenarios. |
| Base de datos | SQLite (`sqlite3`) | Base de datos local en un solo archivo, sin servidor; viene incluida en Python. |
| Pruebas | `unittest` | Casos de prueba del motor de simulación. |
| Empaquetado | PyInstaller → `.exe` | Ejecutable para Windows sin instalar Python. |
| Control de versiones | Git + GitHub | Historial de cambios y commits del proyecto. |
| Editor | Visual Studio Code | Desarrollo del código. |
| Plataforma | Windows 10/11 | Ejecución local, sin internet. |

## Estructura de carpetas
```
ProcSimLocal_SistemasOperativos_G14/
├── main.py              # punto de entrada
├── controlador.py       # coordina vista y modelo
├── ui/                  # VISTA (Tkinter)
│   ├── ventana_principal.py
│   ├── panel_procesos.py
│   └── panel_concurrencia.py
├── nucleo/              # MODELO (motor de simulación)
│   ├── proceso.py
│   ├── pcb.py
│   ├── hilos.py
│   ├── sincronizacion.py
│   ├── escenarios.py
│   ├── registro.py
│   └── base_datos.py
├── bd/                  # script SQL y modelo relacional
│   └── modelo_relacional.sql
├── pruebas/             # casos de prueba
└── docs/                # documentación y manual
```
