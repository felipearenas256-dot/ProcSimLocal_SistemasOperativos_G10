# Resultados de los experimentos · ProcSim Local

- Fecha: 2026-11-17 23:46
- Equipo: Windows 11 (build 10.0.26200), Python 3.12.10, AMD64
- Repeticiones por configuración: 10
- Comando: `python src/experimentos.py`

### E1 · Planificador (F1–F3): efecto del quantum
6 procesos, probabilidad de E/S 20 %, semilla 7 (resultado determinista).

| Quantum | Tics totales | Cambios de contexto | Espera promedio (tics) | Eventos |
|---|---|---|---|---|
| 1 | 34 | 20 | 10.33 | 60 |
| 2 | 34 | 18 | 10.17 | 56 |
| 3 | 34 | 15 | 10.17 | 50 |
| 4 | 34 | 15 | 10.17 | 50 |
| 5 | 34 | 15 | 10.17 | 50 |

### E2 · Hilos (F4) y modos de ejecución (F5)

| Caso | Resultado | Coincide con la teoría |
|---|---|---|
| F4 · 2 hilos × 5 iteraciones | compartida = 10 (esperado 10); propia = [5, 5] | sí |
| F4 · 4 hilos × 5 iteraciones | compartida = 20 (esperado 20); propia = [5, 5, 5, 5] | sí |
| F4 · 6 hilos × 5 iteraciones | compartida = 30 (esperado 30); propia = [5, 5, 5, 5, 5, 5] | sí |
| F5 · llamada read() | 2 cambios de modo usuario↔kernel | sí |
| F5 · interrupción de teclado | 2 cambios de modo usuario↔kernel | sí |

### E3 · Condición de carrera sin protección (F6)
50 incrementos por hilo, 10 repeticiones por fila.

| Hilos | Valor esperado | Valor final promedio | Mín–máx | Actualizaciones perdidas | Corridas con carrera |
|---|---|---|---|---|---|
| 2 | 100 | 50.0 | 50–50 | 50 % | 10/10 |
| 4 | 200 | 50.0 | 50–50 | 75 % | 10/10 |
| 8 | 400 | 50.0 | 50–50 | 88 % | 10/10 |

### E4 · Sección crítica protegida (F7)
4 hilos × 50 incrementos (esperado 200), 10 repeticiones por mecanismo.

| Mecanismo | Corridas con resultado correcto | Valor final (mín–máx) | Duración promedio (s) |
|---|---|---|---|
| Mutex | 10/10 | 200–200 | 3.91 |
| Semáforo binario | 10/10 | 200–200 | 3.91 |
| Semáforo con 2 permisos | 0/10 | 100–100 | 2.34 |

### E5 · Interbloqueo (F8)
2 hilos y 2 recursos, tiempo de espera máximo 1 s, 10 repeticiones por estrategia.

| Estrategia | Interbloqueos detectados | Ambos hilos terminan sin bloqueo | Duración promedio (s) |
|---|---|---|---|
| sin prevención | 10/10 | 0/10 | 1.07 |
| orden global de recursos | 0/10 | 10/10 | 0.06 |

### E6 · Inanición y envejecimiento (F9)
2 hilos de alta prioridad y 1 de baja (B1), 10 repeticiones por fila.

| Asignaciones del recurso | Envejecimiento | Accesos de B1 (promedio) | Mín–máx | Corridas con inanición total |
|---|---|---|---|---|
| 12 | no | 0.0 | 0–0 | 10/10 |
| 12 | sí | 1.0 | 1–1 | 0/10 |
| 24 | no | 0.0 | 0–0 | 10/10 |
| 24 | sí | 1.0 | 1–1 | 0/10 |

Tiempo total de los experimentos: 151.6 s.
