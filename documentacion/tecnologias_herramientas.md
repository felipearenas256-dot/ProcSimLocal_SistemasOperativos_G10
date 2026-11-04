# Relación de tecnologías y herramientas

**Proyecto:** ProcSim Local · **Asignatura:** Sistemas Operativos · **Grupo:** 10

---

## 1. Tecnologías del producto

| Capa | Tecnología | Versión | Uso en el proyecto | Por qué se eligió |
|---|---|---|---|---|
| Lenguaje | Python | 3.12 | Lenguaje principal de la aplicación. | Es sencillo de leer, se usa en la academia y trae en su biblioteca estándar todo lo que el proyecto necesita. |
| Interfaz (front end) | Tkinter + Canvas | Incluido en Python | Ventanas, formularios, controles y animaciones (diagrama de estados, línea de tiempo, grafo de espera). | No requiere instalación adicional y `Canvas` permite dibujar y animar figuras. |
| Concurrencia | `threading` (`Thread`, `Lock`, `Semaphore`) | Incluido en Python | Hilos reales y mecanismos de sincronización de los escenarios F4 y F6 a F9. | En Windows crea hilos nativos del sistema operativo, así los problemas de concurrencia son reales. |
| Comunicación entre hilos | `queue.Queue` | Incluido en Python | Pasar los eventos de los hilos de simulación a la interfaz. | Es segura para hilos y evita que la interfaz se congele. |
| Base de datos | SQLite (`sqlite3`) | 3.x, incluido en Python | Guardar escenarios, ejecuciones, procesos, hilos, recursos y eventos. | Es una base de datos relacional en un solo archivo local, sin servidor. |
| Pruebas | `unittest` | Incluido en Python | Casos de prueba del motor de simulación. | Es el marco de pruebas estándar de Python. |
| Empaquetado | PyInstaller | 6.x | Generar el ejecutable `.exe` para Windows. | Permite usar la aplicación sin instalar Python. |

## 2. Herramientas de trabajo

| Herramienta | Uso |
|---|---|
| Git | Control de versiones local y commits. |
| GitHub | Repositorio público del proyecto, historial de commits y documentación. |
| Visual Studio Code | Editor de código, con la extensión de Python. |
| DB Browser for SQLite | Revisar las tablas y los datos de `procsim.db`. |
| Draw.io | Edición de diagramas. |
| Microsoft Word / PDF | Documento técnico de la entrega. |

## 3. Entorno de ejecución

| Aspecto | Definición |
|---|---|
| Sistema operativo | Windows 10 / 11 de 64 bits. |
| Modo de ejecución | Desde el código (`python src/main.py`) o con el ejecutable `.exe`. |
| Conexión | Sin internet y sin servidor. |
| Virtualización | No es necesaria: la aplicación corre directamente en Windows. |
