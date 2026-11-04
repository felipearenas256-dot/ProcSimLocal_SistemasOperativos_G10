# Requerimientos funcionales y no funcionales

**Proyecto:** ProcSim Local · **Asignatura:** Sistemas Operativos · **Grupo:** 10

Prioridad: **Alta** = obligatorio para el prototipo · **Media** = importante · **Baja** = deseable.

---

## 1. Requerimientos funcionales

### Módulo A · Gestión de procesos

| ID | Requerimiento | Función | Prioridad |
|---|---|---|---|
| RF-01 | El sistema debe permitir crear un proceso indicando nombre, prioridad y tiempo de ráfaga, y asignarle un PID único. | F1 | Alta |
| RF-02 | El sistema debe mostrar la lista de procesos activos con su PID, nombre, estado y prioridad. | F1 | Alta |
| RF-03 | El sistema debe permitir finalizar un proceso y pasarlo al estado *terminado*. | F1 | Alta |
| RF-04 | El sistema debe mostrar el PCB del proceso seleccionado (PID, estado, contador de programa, prioridad y registros) y actualizarlo en cada paso de la simulación. | F2 | Alta |
| RF-05 | El sistema debe animar las transiciones entre los estados nuevo, listo, ejecución, bloqueado y terminado, indicando el motivo de cada transición. | F3 | Alta |

### Módulo B · Hilos y modos de ejecución

| ID | Requerimiento | Función | Prioridad |
|---|---|---|---|
| RF-06 | El sistema debe permitir crear varios hilos dentro de un proceso y mostrar una línea de tiempo por hilo. | F4 | Alta |
| RF-07 | El sistema debe mostrar qué comparten los hilos de un proceso (memoria, archivos abiertos) y qué tiene cada uno (pila, registros), comparándolo con procesos independientes. | F4 | Media |
| RF-08 | El sistema debe simular una llamada al sistema (`read()`) y una interrupción de E/S, mostrando paso a paso el cambio de modo usuario a modo kernel y el regreso. | F5 | Alta |

### Módulo C · Concurrencia

| ID | Requerimiento | Función | Prioridad |
|---|---|---|---|
| RF-09 | El sistema debe ejecutar dos o más hilos reales que incrementen un contador compartido sin protección, y mostrar el valor esperado frente al valor real. | F6 | Alta |
| RF-10 | El sistema debe permitir repetir el escenario anterior con mutex (`Lock`) o semáforo (`Semaphore`) y comparar los resultados. | F7 | Alta |
| RF-11 | El sistema debe reproducir un interbloqueo entre dos hilos y dos recursos, y mostrar el grafo de espera circular. | F8 | Alta |
| RF-12 | El sistema debe reproducir la inanición de un hilo de baja prioridad y mostrar el tiempo de espera de cada hilo. | F9 | Alta |

### Funciones comunes a todos los escenarios

| ID | Requerimiento | Prioridad |
|---|---|---|
| RF-13 | El sistema debe ofrecer un menú para elegir cualquiera de los 9 escenarios. | Alta |
| RF-14 | El sistema debe permitir configurar los parámetros del escenario (número de procesos o hilos, prioridad, ráfaga, mecanismo de sincronización y velocidad) y validar que los valores sean correctos antes de iniciar. | Alta |
| RF-15 | El sistema debe permitir iniciar, pausar, avanzar paso a paso, cambiar la velocidad y reiniciar la simulación. | Alta |
| RF-16 | El sistema debe mostrar una bitácora en pantalla con cada evento (tiempo, tipo, proceso o hilo, estado anterior y nuevo, mensaje). | Alta |
| RF-17 | El sistema debe guardar cada ejecución y sus eventos en la base de datos local SQLite. | Alta |
| RF-18 | El sistema debe permitir consultar el historial de ejecuciones guardadas. | Media |
| RF-19 | El sistema debe permitir exportar la bitácora de una ejecución a un archivo `.txt`. | Alta |
| RF-20 | El sistema debe mostrar una explicación breve del concepto teórico de cada escenario. | Media |

## 2. Requerimientos no funcionales

| ID | Tipo | Requerimiento |
|---|---|---|
| RNF-01 | Plataforma | La aplicación debe funcionar en Windows 10 y Windows 11 de 64 bits. |
| RNF-02 | Disponibilidad | Debe funcionar sin conexión a internet y sin servidor: todo se ejecuta y se guarda en el equipo local. |
| RNF-03 | Portabilidad | Debe poder distribuirse como un ejecutable `.exe` (PyInstaller) que no requiera instalar Python. |
| RNF-04 | Usabilidad | Un estudiante debe poder ejecutar un escenario en pocos pasos: elegir, configurar e iniciar. La interfaz debe estar en español. |
| RNF-05 | Usabilidad | La interfaz debe leerse bien al proyectarse en clase (tamaño de letra y contraste adecuados). |
| RNF-06 | Rendimiento | La interfaz debe seguir respondiendo mientras corre la simulación; los hilos de la simulación no deben bloquear la ventana. |
| RNF-07 | Rendimiento | La aplicación debe iniciar en menos de 5 segundos en un equipo con los requisitos mínimos. |
| RNF-08 | Confiabilidad | El escenario de interbloqueo no debe congelar la aplicación: el sistema debe detectar la espera y permitir reiniciar. |
| RNF-09 | Confiabilidad | La simulación debe ser repetible: con los mismos parámetros debe mostrar el mismo tipo de resultado. |
| RNF-10 | Seguridad | La aplicación no debe crear, modificar ni terminar procesos reales del equipo del usuario. |
| RNF-11 | Integridad de datos | La base de datos debe usar llaves primarias, llaves foráneas y restricciones (`CHECK`) para mantener datos consistentes. |
| RNF-12 | Mantenibilidad | El código debe seguir el patrón Modelo-Vista-Controlador: la Vista no debe contener lógica de simulación. |
| RNF-13 | Mantenibilidad | El código debe estar documentado y seguir la guía de estilo PEP 8. |
| RNF-14 | Calidad | El motor de simulación debe tener casos de prueba con `unittest`. |
| RNF-15 | Control de versiones | El avance del proyecto debe registrarse con commits descriptivos en el repositorio de GitHub. |

## 3. Requerimientos de hardware y software

### 3.1 Para usar la aplicación

| Recurso | Mínimo | Recomendado |
|---|---|---|
| Sistema operativo | Windows 10 de 64 bits | Windows 11 de 64 bits |
| Procesador | Doble núcleo, 2 GHz | Cuatro núcleos o más |
| Memoria RAM | 4 GB | 8 GB |
| Espacio en disco | 200 MB libres | 500 MB libres |
| Pantalla | 1366 × 768 | 1920 × 1080 o proyector |
| Software | Ninguno si se usa el `.exe`; Python 3.12 si se ejecuta desde el código fuente | Igual |
| Internet | No requerido | No requerido |

### 3.2 Para desarrollar

| Recurso | Uso |
|---|---|
| Python 3.12 (incluye Tkinter, `threading`, `sqlite3` y `unittest`) | Lenguaje y bibliotecas del proyecto. |
| PyInstaller | Generar el ejecutable `.exe`. |
| Visual Studio Code | Editor de código. |
| Git y GitHub | Control de versiones y repositorio público. |
| DB Browser for SQLite (opcional) | Revisar el contenido de `procsim.db`. |
| Draw.io (opcional) | Editar diagramas. |
