"""Paneles de los módulos A y B.

* PanelPlanificador (F1, F2, F3): diagrama de estados animado, lista de procesos
  con crear / finalizar y ficha PCB en vivo.
* PanelHilos (F4): línea de tiempo por hilo y memoria compartida vs. propia.
* PanelModos (F5): carriles de modo usuario / modo kernel paso a paso.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ui import tema as T

ESTADOS_DIAGRAMA = {          # posición relativa (x) y fila
    "nuevo": (0.10, 0), "listo": (0.36, 0), "ejecucion": (0.64, 0), "terminado": (0.90, 0), "bloqueado": (0.64, 1),
}


# =============================================================================
# F1 · F2 · F3
# =============================================================================
class PanelPlanificador(ttk.Frame):
    def __init__(self, padre, app) -> None:
        super().__init__(padre, style="Panel.TFrame")
        self.app = app
        self.pid_seleccionado: int | None = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.canvas = tk.Canvas(self, height=226, bg=T.PANEL, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 4))

        # --- lista de procesos (F1) --------------------------------------------------
        izq = ttk.Frame(self, style="Panel.TFrame")
        izq.grid(row=1, column=0, sticky="nsew", padx=(4, 6))
        izq.rowconfigure(1, weight=1)
        izq.columnconfigure(0, weight=1)
        ttk.Label(izq, text="Procesos", style="Seccion.TLabel").grid(row=0, column=0, sticky="w")
        cols = ("pid", "nombre", "prioridad", "rafaga", "estado", "espera", "cpu")
        self.tabla = ttk.Treeview(izq, columns=cols, show="headings", height=4, selectmode="browse")
        for c, titulo, ancho in zip(cols, ("PID", "Nombre", "Prior.", "Ráfaga", "Estado", "Espera", "CPU"),
                                    (55, 110, 55, 70, 90, 60, 50)):
            self.tabla.heading(c, text=titulo)
            self.tabla.column(c, width=ancho, anchor="center" if c != "nombre" else "w", stretch=c == "nombre")
        for est, (borde, relleno) in T.COLOR_ESTADO.items():
            self.tabla.tag_configure(est, background=relleno)
        self.tabla.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(izq, command=self.tabla.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.bind("<<TreeviewSelect>>", self._seleccionar)

        # --- PCB (F2) y formulario (F1) a la derecha ---------------------------------
        der = ttk.Frame(self, style="Tarjeta.TFrame", padding=(12, 8))
        der.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(6, 4), pady=4)
        der.columnconfigure(1, weight=1)
        self.l_pcb = ttk.Label(der, text="PCB", style="Seccion.TLabel", background=T.TENUE)
        self.l_pcb.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.campos = {}
        for i, (clave, titulo) in enumerate([("pid", "PID · nombre"), ("estado", "Estado"),
                                             ("contador_programa", "Contador de programa"),
                                             ("prioridad", "Prioridad"), ("registros", "Registros"),
                                             ("rafaga", "Ráfaga restante"), ("tiempos", "CPU · espera"),
                                             ("cambios", "Cambios de contexto")], start=1):
            ttk.Label(der, text=titulo, style="Clave.TLabel").grid(row=i, column=0, sticky="w", pady=1)
            v = ttk.Label(der, text="—", style="Valor.TLabel", font=T.MONO_P)
            v.grid(row=i, column=1, sticky="w", padx=(10, 0), pady=0)
            self.campos[clave] = v
        self.barra = ttk.Progressbar(der, maximum=1.0)
        self.barra.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(4, 6))

        ttk.Label(der, text="Nuevo proceso (fork)", style="Seccion.TLabel", background=T.TENUE).grid(
            row=11, column=0, columnspan=2, sticky="w")
        form = ttk.Frame(der, style="Tarjeta.TFrame")
        form.grid(row=12, column=0, columnspan=2, sticky="w", pady=(2, 4))
        for col, texto in enumerate(("Nombre", "Prioridad", "Ráfaga")):
            ttk.Label(form, text=texto, style="Clave.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 8))
        self.e_nombre = ttk.Entry(form, width=12)
        self.e_nombre.insert(0, "Editor")
        self.e_nombre.grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.e_prio = ttk.Spinbox(form, from_=1, to=10, width=5)
        self.e_prio.set(2)
        self.e_prio.grid(row=1, column=1, sticky="w", padx=(0, 8))
        self.e_rafaga = ttk.Spinbox(form, from_=1, to=50, width=5)
        self.e_rafaga.set(5)
        self.e_rafaga.grid(row=1, column=2, sticky="w")
        botones = ttk.Frame(der, style="Tarjeta.TFrame")
        botones.grid(row=13, column=0, columnspan=2, sticky="w")
        ttk.Button(botones, text="+ Crear proceso", command=self._crear).pack(side="left", padx=(0, 6))
        ttk.Button(botones, text="✕ Finalizar", command=self._finalizar).pack(side="left")

    # ------------------------------------------------------------------ acciones
    def _seleccionar(self, _evento=None) -> None:
        sel = self.tabla.selection()
        self.pid_seleccionado = int(sel[0]) if sel else None

    def _crear(self) -> None:
        try:
            pid = self.app.controlador.crear_proceso(self.e_nombre.get(), self.e_prio.get(), self.e_rafaga.get())
            self.pid_seleccionado = pid
        except (ValueError, RuntimeError) as exc:
            messagebox.showwarning("Crear proceso", str(exc), parent=self)

    def _finalizar(self) -> None:
        if self.pid_seleccionado is None:
            messagebox.showinfo("Finalizar proceso", "Seleccione un proceso de la lista.", parent=self)
            return
        try:
            self.app.controlador.finalizar_proceso(self.pid_seleccionado)
        except (ValueError, RuntimeError) as exc:
            messagebox.showwarning("Finalizar proceso", str(exc), parent=self)

    # ------------------------------------------------------------------ dibujo
    def limpiar(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        self.pid_seleccionado = None
        self.actualizar({})

    def actualizar(self, estado: dict) -> None:
        procesos = estado.get("procesos", [])
        self._dibujar_diagrama(procesos, estado.get("ultima_transicion"))
        self._actualizar_tabla(procesos)
        pid = self.pid_seleccionado if self.pid_seleccionado is not None else estado.get("en_cpu")
        proc = next((p for p in procesos if p["pid"] == pid), None)
        self._actualizar_pcb(proc)

    def _actualizar_tabla(self, procesos: list[dict]) -> None:
        existentes = set(self.tabla.get_children())
        for p in procesos:
            iid = str(p["pid"])
            fila = (f"P{p['pid']}", p["nombre"], p["prioridad"], f"{p['rafaga_restante']}/{p['rafaga_total']}",
                    T.NOMBRE_ESTADO[p["estado"]], p["tiempo_espera"], p["tiempo_cpu"])
            if iid in existentes:
                self.tabla.item(iid, values=fila, tags=(p["estado"],))
            else:
                self.tabla.insert("", "end", iid=iid, values=fila, tags=(p["estado"],))
        if self.pid_seleccionado is not None and str(self.pid_seleccionado) in self.tabla.get_children():
            if self.tabla.selection() != (str(self.pid_seleccionado),):
                self.tabla.selection_set(str(self.pid_seleccionado))

    def _actualizar_pcb(self, p: dict | None) -> None:
        if p is None:
            self.l_pcb.configure(text="PCB · seleccione un proceso")
            for v in self.campos.values():
                v.configure(text="—")
            self.barra.configure(value=0)
            return
        self.l_pcb.configure(text=f"PCB de P{p['pid']}")
        r = p["registros"]
        valores = {
            "pid": f"{p['pid']} · {p['nombre']}", "estado": T.NOMBRE_ESTADO[p["estado"]].upper(),
            "contador_programa": p["contador_programa"], "prioridad": f"{p['prioridad']} (1 = más alta)",
            "registros": f"AX={r['AX']} BX={r['BX']} CX={r['CX']} DX={r['DX']}",
            "rafaga": f"{p['rafaga_restante']} de {p['rafaga_total']}",
            "tiempos": f"{p['tiempo_cpu']} tics CPU · {p['tiempo_espera']} en listos",
            "cambios": p["cambios_contexto"],
        }
        for k, v in valores.items():
            self.campos[k].configure(text=str(v))
        self.campos["estado"].configure(foreground=T.COLOR_ESTADO[p["estado"]][0])
        self.barra.configure(value=p["progreso"])

    def _centro(self, estado: str) -> tuple[float, float]:
        w = max(self.canvas.winfo_width(), 600)
        fx, fila = ESTADOS_DIAGRAMA[estado]
        return fx * w, 58 if fila == 0 else 168

    def _dibujar_diagrama(self, procesos: list[dict], ultima) -> None:
        c = self.canvas
        c.delete("all")
        bw, bh = min(76, max(self.canvas.winfo_width(), 600) * 0.085), 46                          # medio ancho, medio alto de cada estado
        cen = {e: self._centro(e) for e in ESTADOS_DIAGRAMA}

        def color(a, b):
            return (T.AMARILLO, 3) if ultima == (a, b) else (T.GRIS, 2)

        (nx, ny), (lx, ly), (ex, ey), (tx, ty), (bx, by) = (cen[e] for e in
                                                             ("nuevo", "listo", "ejecucion", "terminado", "bloqueado"))
        arcos = [
            ("nuevo", "listo", [nx + bw, ny, lx - bw, ly], "admitir", ((nx + lx) / 2, ny - 10)),
            ("listo", "ejecucion", [lx + bw, ly - 14, ex - bw, ey - 14], "despachar", ((lx + ex) / 2, ly - 47)),
            ("ejecucion", "listo", [ex - bw, ey + 14, lx + bw, ly + 14], "interrupción", ((lx + ex) / 2, ly + 63)),
            ("ejecucion", "terminado", [ex + bw, ey, tx - bw, ty], "salir", ((ex + tx) / 2, ey - 10)),
            ("ejecucion", "bloqueado", [ex, ey + bh + 6, ex, by - bh + 8], "espera E/S", (ex + 44, (ey + by) / 2 + 3)),
            ("bloqueado", "listo", [bx - bw, by, lx, by, lx, ly + bh + 6], "E/S lista", (lx + 40, by - 10)),
        ]
        for a, b, pts, texto, (txx, tyy) in arcos:
            col, ancho = color(a, b)
            T.flecha(c, pts, col, ancho)
            c.create_text(txx, tyy, text=texto, fill=col if col != T.GRIS else T.SUAVE, font=T.FUENTE_P)

        por_estado: dict[str, list[dict]] = {e: [] for e in ESTADOS_DIAGRAMA}
        for p in procesos:
            por_estado[p["estado"]].append(p)
        for est, (x, y) in cen.items():
            borde, relleno = T.COLOR_ESTADO[est]
            T.caja(c, x - bw, y - bh + 8, x + bw, y + bh - 8 + 14, r=14, fill=relleno, outline=borde, width=2)
            c.create_text(x, y - bh + 22, text=T.NOMBRE_ESTADO[est].upper(), fill=borde, font=T.MONO_N)
            lista = por_estado[est]
            por_fila = max(2, int((2 * bw - 12) // 36))
            for i, p in enumerate(lista[:por_fila * 2]):
                cx = x - bw + 8 + (i % por_fila) * 36
                cy = y - 6 + (i // por_fila) * 22
                sel = p["pid"] == self.pid_seleccionado
                c.create_rectangle(cx, cy, cx + 32, cy + 18, fill=borde if est == "ejecucion" else T.PANEL,
                                   outline=T.TEXTO if sel else borde, width=2 if sel else 1)
                c.create_text(cx + 16, cy + 9, text=f"P{p['pid']}", font=T.MONO_P,
                              fill=T.PANEL if est == "ejecucion" else T.TEXTO)
            if len(lista) > por_fila * 2:
                c.create_text(x + bw - 14, y + bh - 2, text=f"+{len(lista) - por_fila * 2}", fill=borde,
                              font=T.FUENTE_P)
        if not procesos:
            c.create_text(cen["listo"][0] + 90, 200, text="Inicie el escenario para ver los procesos moverse entre estados.",
                          fill=T.SUAVE, font=T.FUENTE, anchor="w")


# =============================================================================
# F4
# =============================================================================
class PanelHilos(ttk.Frame):
    def __init__(self, padre, app) -> None:
        super().__init__(padre, style="Panel.TFrame")
        self.app = app
        self.canvas = tk.Canvas(self, bg=T.PANEL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)

    def limpiar(self) -> None:
        T.mensaje_vacio(self.canvas, "Inicie el escenario: primero un proceso con varios hilos que comparten memoria, "
                                     "luego procesos independientes con memoria propia.")

    def actualizar(self, estado: dict) -> None:
        if not estado.get("hilos"):
            self.limpiar()
            return
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 700)
        izq, der = 190, w - 230
        hilos = estado["hilos"]
        segs = estado["segmentos"]
        tmax = max([estado["ahora"]] + [s[2] for s in segs]) or 1
        escala = (der - izq) / tmax
        y = 22
        tid_por_hilo = {h["nombre"]: h for h in hilos}
        for grupo, titulo, col in (("hilos", "Proceso P1 · hilos que COMPARTEN memoria", T.AZUL),
                                   ("procesos", "Procesos independientes · cada uno con SU memoria", T.MORADO)):
            del_grupo = [h for h in hilos if h["grupo"] == grupo]
            if not del_grupo:
                continue
            c.create_text(12, y, text=titulo, anchor="w", font=T.FUENTE_N, fill=col)
            y += 22
            for h in del_grupo:
                tid = f"TID {h['tid']}" if h["tid"] else "TID —"
                c.create_text(12, y + 9, text=f"{h['nombre']} · {tid}", anchor="w", font=T.MONO_P, fill=T.TEXTO)
                c.create_text(izq - 8, y + 9, text=f"pila {h['pila']}", anchor="e", font=T.MONO_P, fill=T.SUAVE)
                c.create_rectangle(izq, y, der, y + 18, fill=T.TENUE, outline="")
                for nombre, t0, t1, _g in segs:
                    if nombre == h["nombre"]:
                        c.create_rectangle(izq + t0 * escala, y + 2, izq + max(t1 * escala, t0 * escala + 2), y + 16,
                                           fill=col, outline="")
                est = T.NOMBRE_ESTADO.get(h["estado"], h["estado"])
                c.create_text(der + 8, y + 9, text=est, anchor="w", font=T.FUENTE_P,
                              fill=T.COLOR_ESTADO.get(h["estado"], (T.SUAVE,))[0])
                y += 24
            y += 6
            # memoria del grupo
            if grupo == "hilos":
                total, maximo = estado["compartida"], estado["esperado_compartida"]
                c.create_text(12, y + 9, text="Memoria de P1", anchor="w", font=T.FUENTE_N, fill=T.TEXTO)
                self._barra_memoria(izq, der, y, total, maximo, col)
                c.create_text(der + 8, y + 9, text=f"{total} datos (de todos)", anchor="w", font=T.FUENTE_P, fill=col)
                y += 34
            else:
                for h in del_grupo:
                    maximo = estado["esperado_compartida"]
                    c.create_text(12, y + 9, text=f"Memoria de {h['nombre']}", anchor="w", font=T.FUENTE_P,
                                  fill=T.TEXTO)
                    self._barra_memoria(izq, der, y, h["memoria"], maximo, col)
                    c.create_text(der + 8, y + 9, text=f"{h['memoria']} datos (solo suyos)", anchor="w",
                                  font=T.FUENTE_P, fill=col)
                    y += 24
                y += 10
        c.create_line(izq, y, der, y, fill=T.BORDE)
        c.create_text(izq, y + 12, text="0 s", anchor="w", font=T.FUENTE_P, fill=T.SUAVE)
        c.create_text(der, y + 12, text=f"{tmax:.1f} s", anchor="e", font=T.FUENTE_P, fill=T.SUAVE)
        c.create_text((izq + der) / 2, y + 12, text="tiempo real (cada barra = el hilo trabajando)",
                      font=T.FUENTE_P, fill=T.SUAVE)
        if tid_por_hilo:
            tids = {h["tid"] for h in hilos if h["grupo"] == "hilos" and h["tid"]}
            c.create_text(12, y + 34, anchor="w", font=T.FUENTE_P, fill=T.SUAVE,
                          text=f"Los {len(tids)} hilos de P1 tienen TID nativos distintos: Windows los planifica "
                               "como hilos reales del sistema operativo.")

    def _barra_memoria(self, izq, der, y, valor, maximo, col) -> None:
        c = self.canvas
        c.create_rectangle(izq, y + 2, der, y + 16, outline=T.BORDE, fill=T.PANEL)
        if maximo:
            c.create_rectangle(izq, y + 2, izq + (der - izq) * min(valor / maximo, 1), y + 16, fill=col,
                               outline="")


# =============================================================================
# F5
# =============================================================================
class PanelModos(ttk.Frame):
    def __init__(self, padre, app) -> None:
        super().__init__(padre, style="Panel.TFrame")
        self.app = app
        self.canvas = tk.Canvas(self, height=190, bg=T.PANEL, highlightthickness=0)
        self.canvas.pack(fill="x", padx=4, pady=4)
        cols = ("n", "modo", "actor", "texto")
        self.tabla = ttk.Treeview(self, columns=cols, show="headings", height=8)
        for c, titulo, ancho in zip(cols, ("#", "Modo", "Quién", "Qué pasa"), (40, 90, 160, 700)):
            self.tabla.heading(c, text=titulo, anchor="w")
            self.tabla.column(c, width=ancho, anchor="w", stretch=c == "texto")
        self.tabla.tag_configure("usuario", background="#e8f6ee")
        self.tabla.tag_configure("kernel", background="#f1eafd")
        self.tabla.tag_configure("pendiente", foreground="#9aa3b2")
        self.tabla.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._caso = None

    def limpiar(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        self._caso = None
        T.mensaje_vacio(self.canvas, "Inicie el escenario y use «Paso» para recorrer la llamada al sistema.")

    def actualizar(self, estado: dict) -> None:
        pasos = estado.get("pasos")
        if not pasos:
            self.limpiar()
            return
        indice = estado["indice"]
        if self._caso != estado["caso"]:
            self.tabla.delete(*self.tabla.get_children())
            for i, (modo, actor, texto) in enumerate(pasos):
                self.tabla.insert("", "end", iid=str(i), values=(i + 1, modo, actor, texto))
            self._caso = estado["caso"]
        for i, (modo, _a, _t) in enumerate(pasos):
            self.tabla.item(str(i), tags=(modo,) if i <= indice else ("pendiente",))
        if 0 <= indice < len(pasos):
            self.tabla.selection_set(str(indice))
            self.tabla.see(str(indice))
        self._dibujar(pasos, indice)

    def _dibujar(self, pasos, indice) -> None:
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 700)
        izq, der = 190, w - 30
        carriles = {"usuario": (30, 82, T.VERDE, "#e8f6ee", "MODO USUARIO", "bit de modo = 1"),
                    "kernel": (104, 156, T.MORADO, "#f1eafd", "MODO KERNEL", "bit de modo = 0")}
        for modo, (y0, y1, col, relleno, titulo, bit) in carriles.items():
            T.caja(c, 10, y0, der + 10, y1, r=10, fill=relleno, outline=col)
            c.create_text(24, (y0 + y1) / 2 - 8, text=titulo, anchor="w", font=T.FUENTE_N, fill=col)
            c.create_text(24, (y0 + y1) / 2 + 10, text=bit, anchor="w", font=T.MONO_P, fill=T.SUAVE)
        n = len(pasos)
        paso_x = (der - izq) / max(n - 1, 1)
        puntos = []
        for i, (modo, _a, _t) in enumerate(pasos):
            y0, y1, *_ = carriles[modo]
            puntos.append((izq + i * paso_x, (y0 + y1) / 2))
        for i in range(1, n):
            hecho = i <= indice
            c.create_line(*puntos[i - 1], *puntos[i], fill=T.AMARILLO if hecho else T.BORDE, width=3 if hecho else 2)
        for i, (x, y) in enumerate(puntos):
            modo = pasos[i][0]
            col = carriles[modo][2]
            r = 15 if i == indice else 11
            hecho = i <= indice
            c.create_oval(x - r, y - r, x + r, y + r, fill=col if hecho else T.PANEL, outline=col, width=2)
            c.create_text(x, y, text=str(i + 1), font=T.FUENTE_N if i == indice else T.FUENTE_P,
                          fill=T.PANEL if hecho else col)
        if 0 <= indice < n:
            modo = pasos[indice][0]
            c.create_text(izq, 176, anchor="w", font=T.FUENTE_N, fill=carriles[modo][2],
                          text=f"Paso {indice + 1}: {pasos[indice][1]} — CPU en {carriles[modo][4].lower()}")
        elif indice >= n:
            c.create_text(izq, 176, anchor="w", font=T.FUENTE_N, fill=T.VERDE,
                          text="Terminado: el proceso volvió a modo usuario.")
