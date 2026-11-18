"""ProcSim Simple · ventana con 4 pestañas. Ejecutar:  python version_simple/app.py"""
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import logica

COLORES = {logica.NUEVO: "#dbe8ff", logica.LISTO: "#d9f2df", logica.EJECUCION: "#ffe9b3", logica.TERMINADO: "#f6d5d5"}


def bitacora(padre):
    t = tk.Text(padre, height=12, font=("Consolas", 10), bg="#1d2330", fg="#e6e6e6")
    t.pack(fill="both", expand=True, padx=10, pady=(4, 10))
    return t


def escribir(texto_widget, lineas, limpiar=False):
    if limpiar:
        texto_widget.delete("1.0", "end")
    for linea in lineas:
        texto_widget.insert("end", linea + "\n")
    texto_widget.see("end")


def en_segundo_plano(widget, funcion, al_terminar):
    """Corre `funcion` en un hilo aparte (la ventana no se congela) y, cuando termina,
    llama a `al_terminar(resultado)` desde el hilo de la ventana (Tkinter lo exige)."""
    resultado = []
    threading.Thread(target=lambda: resultado.append(funcion()), daemon=True).start()

    def revisar():
        if resultado:
            al_terminar(*resultado[0])
        else:
            widget.after(50, revisar)
    widget.after(50, revisar)


def explicacion(padre, texto):
    ttk.Label(padre, text=texto, wraplength=820, justify="left").pack(anchor="w", padx=10, pady=8)


# ---------------------------------------------------------------- 1. Procesos
class PestanaProcesos(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        explicacion(self, "Un proceso pasa por los estados NUEVO → LISTO → EJECUCIÓN → TERMINADO. "
                          "El planificador Round Robin le da la CPU a cada proceso por un quantum (2 tics) y lo "
                          "devuelve a la cola de LISTOS: así todos avanzan por turnos.")
        fila = ttk.Frame(self)
        fila.pack(anchor="w", padx=10)
        ttk.Label(fila, text="Nombre").pack(side="left")
        self.nombre = ttk.Entry(fila, width=12)
        self.nombre.pack(side="left", padx=4)
        ttk.Label(fila, text="Ráfaga (tics)").pack(side="left")
        self.rafaga = ttk.Spinbox(fila, from_=1, to=10, width=5)
        self.rafaga.set(3)
        self.rafaga.pack(side="left", padx=4)
        ttk.Button(fila, text="Crear proceso", command=self.crear).pack(side="left", padx=4)
        ttk.Button(fila, text="Siguiente tic ▶", command=self.tic).pack(side="left", padx=4)
        ttk.Button(fila, text="Ejecutar todo", command=self.todo).pack(side="left", padx=4)
        ttk.Button(fila, text="Reiniciar", command=self.reiniciar).pack(side="left", padx=4)
        self.tabla = ttk.Treeview(self, columns=("pid", "nombre", "rafaga", "restante", "estado"),
                                  show="headings", height=7)
        for col, txt in zip(self.tabla["columns"], ("PID", "Nombre", "Ráfaga", "Restante", "Estado")):
            self.tabla.heading(col, text=txt)
            self.tabla.column(col, width=120, anchor="center")
        for estado, color in COLORES.items():
            self.tabla.tag_configure(estado, background=color)
        self.tabla.pack(fill="x", padx=10, pady=8)
        self.reloj = ttk.Label(self, text="")
        self.reloj.pack(anchor="w", padx=10)
        self.log = bitacora(self)
        self.reiniciar()

    def reiniciar(self):
        self.pl = logica.Planificador(quantum=2)
        for nombre, rafaga in (("Navegador", 3), ("Editor", 2), ("Música", 4)):
            self.pl.crear(nombre, rafaga)
        escribir(self.log, ["Se crearon 3 procesos. Pulse «Siguiente tic»."], limpiar=True)
        self.refrescar()

    def crear(self):
        nombre = self.nombre.get().strip() or f"P{self.pl.siguiente_pid}"
        try:
            p = self.pl.crear(nombre, int(self.rafaga.get()))
        except ValueError as e:
            messagebox.showwarning("Dato no válido", str(e))
            return
        escribir(self.log, [f"Creado {p.nombre} (PID {p.pid}) en estado NUEVO"])
        self.refrescar()

    def tic(self):
        if self.pl.terminado():
            escribir(self.log, ["Todos los procesos terminaron."])
            return
        eventos = self.pl.tic()
        escribir(self.log, [f"[t={self.pl.tiempo}] {e}" for e in eventos] or [f"[t={self.pl.tiempo}] sigue en CPU"])
        self.refrescar()

    def todo(self):
        if not self.pl.terminado():
            self.tic()
            self.after(400, self.todo)

    def refrescar(self):
        self.tabla.delete(*self.tabla.get_children())
        for p in self.pl.procesos:
            self.tabla.insert("", "end", values=(p.pid, p.nombre, p.rafaga, p.restante, p.estado), tags=(p.estado,))
        cpu = self.pl.en_cpu.nombre if self.pl.en_cpu else "libre"
        self.reloj.config(text=f"Tiempo: {self.pl.tiempo} tics · CPU: {cpu} · "
                               f"Cola de listos: {[p.nombre for p in self.pl.cola]}")


# ---------------------------------------------------------------- 2. Carrera
class PestanaCarrera(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        explicacion(self, "Varios hilos REALES suman 1 al mismo contador. Sumar son tres pasos: leer, sumar y "
                          "escribir. Sin protección, dos hilos leen el mismo valor y una suma se pierde "
                          "(condición de carrera). Con un MUTEX solo un hilo a la vez entra a la sección crítica.")
        fila = ttk.Frame(self)
        fila.pack(anchor="w", padx=10)
        ttk.Label(fila, text="Hilos").pack(side="left")
        self.hilos = ttk.Spinbox(fila, from_=2, to=8, width=5)
        self.hilos.set(4)
        self.hilos.pack(side="left", padx=4)
        ttk.Label(fila, text="Sumas por hilo").pack(side="left")
        self.sumas = ttk.Spinbox(fila, from_=10, to=500, increment=10, width=6)
        self.sumas.set(100)
        self.sumas.pack(side="left", padx=4)
        ttk.Button(fila, text="Sin protección", command=lambda: self.correr(False)).pack(side="left", padx=4)
        ttk.Button(fila, text="Con mutex", command=lambda: self.correr(True)).pack(side="left", padx=4)
        self.resultado = ttk.Label(self, text="", font=("Segoe UI", 14, "bold"))
        self.resultado.pack(anchor="w", padx=10, pady=10)
        self.log = bitacora(self)

    def correr(self, mutex):
        n, m = int(self.hilos.get()), int(self.sumas.get())
        self.resultado.config(text="Ejecutando…", foreground="black")
        en_segundo_plano(self, lambda: (mutex, *logica.carrera(n, m, mutex)), self.mostrar)

    def mostrar(self, mutex, esperado, real):
        perdidas = esperado - real
        modo = "CON mutex" if mutex else "SIN protección"
        color = "#1f9d55" if perdidas == 0 else "#c0392b"
        self.resultado.config(text=f"{modo}: esperado {esperado} · real {real}", foreground=color)
        escribir(self.log, [f"{modo}: esperado {esperado}, real {real}, se perdieron {perdidas} sumas"
                            + (" → CONDICIÓN DE CARRERA" if perdidas else " → resultado correcto")])


# ---------------------------------------------------------------- 3. Interbloqueo
class PestanaInterbloqueo(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        explicacion(self, "H1 toma R1 y pide R2; H2 toma R2 y pide R1. Cada uno espera el recurso que tiene el "
                          "otro: ESPERA CIRCULAR → interbloqueo. Para no congelar el programa, cada hilo espera "
                          "como máximo 1 segundo. Solución: ORDEN GLOBAL, todos piden R1 antes que R2.")
        fila = ttk.Frame(self)
        fila.pack(anchor="w", padx=10)
        ttk.Button(fila, text="Provocar interbloqueo", command=lambda: self.correr(False)).pack(side="left", padx=4)
        ttk.Button(fila, text="Con orden global (solución)", command=lambda: self.correr(True)).pack(side="left", padx=4)
        self.resultado = ttk.Label(self, text="", font=("Segoe UI", 14, "bold"))
        self.resultado.pack(anchor="w", padx=10, pady=10)
        self.log = bitacora(self)

    def correr(self, orden):
        self.resultado.config(text="Ejecutando…", foreground="black")
        en_segundo_plano(self, lambda: (orden, *logica.interbloqueo(orden)), self.mostrar)

    def mostrar(self, orden, hubo, lineas):
        titulo = "Con orden global" if orden else "Sin prevención"
        self.resultado.config(text=f"{titulo}: " + ("INTERBLOQUEO detectado" if hubo else "sin interbloqueo"),
                              foreground="#c0392b" if hubo else "#1f9d55")
        escribir(self.log, [f"--- {titulo} ---"] + lineas)


# ---------------------------------------------------------------- 4. Inanición
class PestanaInanicion(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        explicacion(self, "A1 y A2 tienen prioridad alta (1) y B1 prioridad baja (5). El recurso siempre se "
                          "entrega al de mejor prioridad, así que B1 nunca lo obtiene: INANICIÓN. Solución: "
                          "ENVEJECIMIENTO, cada ronda que un hilo espera su prioridad mejora 1 punto.")
        fila = ttk.Frame(self)
        fila.pack(anchor="w", padx=10)
        ttk.Button(fila, text="Sin envejecimiento", command=lambda: self.correr(False)).pack(side="left", padx=4)
        ttk.Button(fila, text="Con envejecimiento (solución)", command=lambda: self.correr(True)).pack(side="left", padx=4)
        self.resultado = ttk.Label(self, text="", font=("Segoe UI", 14, "bold"))
        self.resultado.pack(anchor="w", padx=10, pady=10)
        self.log = bitacora(self)

    def correr(self, aging):
        accesos, lineas = logica.inanicion(10, aging)
        titulo = "Con envejecimiento" if aging else "Sin envejecimiento"
        self.resultado.config(text=f"{titulo}: " + ", ".join(f"{h} = {n}" for h, n in accesos.items()),
                              foreground="#1f9d55" if accesos["B1"] else "#c0392b")
        escribir(self.log, [f"--- {titulo} ---"] + lineas
                 + [f"B1 obtuvo el recurso {accesos['B1']} veces" + ("" if accesos["B1"] else " → INANICIÓN")])


def main():
    raiz = tk.Tk()
    raiz.title("ProcSim Simple · Sistemas Operativos · Grupo 10")
    raiz.geometry("900x620")
    ttk.Label(raiz, text="ProcSim Simple", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=12, pady=(10, 0))
    pestanas = ttk.Notebook(raiz)
    pestanas.pack(fill="both", expand=True, padx=8, pady=8)
    for clase, nombre in ((PestanaProcesos, "1. Procesos"), (PestanaCarrera, "2. Condición de carrera"),
                          (PestanaInterbloqueo, "3. Interbloqueo"), (PestanaInanicion, "4. Inanición")):
        pestanas.add(clase(pestanas), text=nombre)
    raiz.mainloop()


if __name__ == "__main__":
    main()
