"""Ventana principal de ProcSim Local.

Menú de escenarios, formulario de parámetros, controles de simulación (iniciar,
pausar, paso a paso, velocidad, reiniciar), panel del escenario, resultado,
bitácora de eventos e historial guardado en la base de datos.

La vista nunca ejecuta lógica de simulación: todo pasa por el Controlador. Los
eventos llegan por una cola y se leen cada pocos milisegundos con after().
"""
from __future__ import annotations

import queue
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from controlador import Controlador
from entorno import info_entorno
from nucleo.escenarios import MODULOS
from ui import tema as T
from ui.panel_concurrencia import PanelCarrera, PanelInanicion, PanelInterbloqueo
from ui.panel_procesos import PanelHilos, PanelModos, PanelPlanificador

PANELES = {"procesos": PanelPlanificador, "hilos": PanelHilos, "modos": PanelModos,
           "carrera": PanelCarrera, "interbloqueo": PanelInterbloqueo, "inanicion": PanelInanicion}
INTERVALO_MS = 80
MAX_LINEAS_BITACORA = 4000


class VentanaPrincipal(tk.Tk):
    def __init__(self, controlador: Controlador) -> None:
        super().__init__()
        self.controlador = controlador
        self.title("ProcSim Local · Simulador de procesos, hilos y concurrencia")
        self.geometry("1440x960")
        self.minsize(1200, 800)
        self.configure(bg=T.FONDO)
        self._estilos()
        self.escenario_cls = None
        self.widgets_param: dict[str, tk.Widget] = {}
        self.paneles: dict[str, ttk.Frame] = {}
        self.panel_actual = None
        self._corriendo_antes = False

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self._cabecera()
        self._menu_lateral()
        self._area_principal()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.seleccionar("F1")
        self.after(INTERVALO_MS, self._sondear)

    # ------------------------------------------------------------------ estilos
    def _estilos(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", font=T.FUENTE, background=T.FONDO, foreground=T.TEXTO)
        s.configure("TFrame", background=T.FONDO)
        s.configure("Panel.TFrame", background=T.PANEL)
        s.configure("Tarjeta.TFrame", background=T.TENUE)
        s.configure("Lateral.TFrame", background=T.PANEL)
        s.configure("Panel.TLabel", background=T.PANEL)
        s.configure("Lateral.TLabel", background=T.PANEL, foreground=T.SUAVE, font=T.FUENTE_P)
        s.configure("Seccion.TLabel", background=T.PANEL, font=T.FUENTE_N)
        s.configure("Clave.TLabel", background=T.TENUE, foreground=T.SUAVE, font=T.FUENTE_P)
        s.configure("Valor.TLabel", background=T.TENUE, font=T.MONO)
        s.configure("Titulo.TLabel", background=T.FONDO, font=T.FUENTE_T)
        s.configure("Explicacion.TLabel", background=T.FONDO, foreground=T.SUAVE)
        s.configure("Param.TLabel", background=T.FONDO, foreground=T.SUAVE, font=T.FUENTE_P)
        s.configure("Estado.TLabel", background=T.FONDO, foreground=T.SUAVE, font=T.FUENTE_N)
        s.configure("TButton", padding=(10, 4))
        s.configure("Primario.TButton", background=T.VERDE, foreground="white", font=T.FUENTE_N)
        s.map("Primario.TButton", background=[("disabled", "#9fd8b8"), ("active", "#17864a")])
        s.configure("Menu.Treeview", rowheight=28, font=T.FUENTE, background=T.PANEL, fieldbackground=T.PANEL)
        s.configure("Menu.Treeview.Heading", font=T.FUENTE_N)
        s.map("Menu.Treeview", background=[("selected", "#dcfce7")], foreground=[("selected", T.TEXTO)])
        s.configure("Treeview", rowheight=24, font=T.FUENTE_P)
        s.configure("Treeview.Heading", font=T.FUENTE_P)

    # ------------------------------------------------------------------ estructura
    def _cabecera(self) -> None:
        cab = tk.Frame(self, bg=T.OSCURO, height=54)
        cab.grid(row=0, column=0, columnspan=2, sticky="ew")
        for texto, color, pad in (("Proc", "white", (18, 0)), ("Sim", "#4ade80", 0), ("Local", "white", (6, 0))):
            tk.Label(cab, text=texto, bg=T.OSCURO, fg=color, font=("Segoe UI", 18, "bold"), padx=0,
                     bd=0).pack(side="left", padx=pad)
        tk.Label(cab, text="   simulador de procesos, hilos y concurrencia", bg=T.OSCURO, fg="#94a3b8",
                 font=T.FUENTE).pack(side="left", pady=(6, 0))
        tk.Label(cab, text="Sistemas Operativos · Grupo 10", bg=T.OSCURO, fg="#94a3b8",
                 font=T.MONO_P).pack(side="right", padx=18)

    def _menu_lateral(self) -> None:
        lat = ttk.Frame(self, style="Lateral.TFrame", padding=(10, 12))
        lat.grid(row=1, column=0, sticky="ns")
        lat.rowconfigure(1, weight=1)
        ttk.Label(lat, text="ESCENARIOS", style="Lateral.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.menu = ttk.Treeview(lat, show="tree", style="Menu.Treeview", selectmode="browse", height=14)
        self.menu.column("#0", width=300)
        cortos = {"A": "Procesos", "B": "Hilos y modos", "C": "Concurrencia"}
        for mod in MODULOS:
            self.menu.insert("", "end", iid=f"mod{mod}", text=f"Módulo {mod} · {cortos[mod]}", open=True)
        for cls in self.controlador.escenarios():
            self.menu.insert(f"mod{cls.modulo}", "end", iid=cls.codigo, text=f"{cls.codigo}  {cls.nombre}")
        self.menu.grid(row=1, column=0, sticky="nsew")
        self.menu.bind("<<TreeviewSelect>>", self._al_elegir)
        ttk.Button(lat, text="Historial de ejecuciones", command=self.abrir_historial).grid(row=2, column=0,
                                                                                         sticky="ew", pady=(10, 4))
        ttk.Button(lat, text="Entorno del sistema", command=self.mostrar_entorno).grid(row=3, column=0, sticky="ew")
        ttk.Label(lat, text=f"Base de datos:\n{self.controlador.bd.ruta.name}", style="Lateral.TLabel",
                  justify="left").grid(row=4, column=0, sticky="w", pady=(10, 0))

    def _area_principal(self) -> None:
        main = ttk.Frame(self, padding=(14, 10, 14, 10))
        main.grid(row=1, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)

        tit = ttk.Frame(main)
        tit.grid(row=0, column=0, sticky="ew")
        self.l_codigo = tk.Label(tit, text="F1", font=T.MONO_N, fg="white", bg=T.AZUL, padx=8, pady=2)
        self.l_codigo.pack(side="left")
        self.l_titulo = ttk.Label(tit, text="", style="Titulo.TLabel")
        self.l_titulo.pack(side="left", padx=10)
        self.l_modulo = ttk.Label(tit, text="", style="Param.TLabel")
        self.l_modulo.pack(side="left", pady=(6, 0))
        self.l_estado = ttk.Label(tit, text="", style="Estado.TLabel")
        self.l_estado.pack(side="right")

        self.l_explicacion = ttk.Label(main, text="", style="Explicacion.TLabel", wraplength=1000, justify="left")
        self.l_explicacion.grid(row=1, column=0, sticky="ew", pady=(6, 8))
        main.bind("<Configure>", lambda e: self.l_explicacion.configure(wraplength=max(e.width - 40, 400)))

        self.f_param = ttk.Frame(main)
        self.f_param.grid(row=2, column=0, sticky="ew")

        barra = ttk.Frame(main)
        barra.grid(row=3, column=0, sticky="ew", pady=(10, 8))
        self.b_iniciar = ttk.Button(barra, text="▶  Iniciar", style="Primario.TButton", command=self.iniciar)
        self.b_iniciar.pack(side="left")
        self.b_pausa = ttk.Button(barra, text="❚❚  Pausar", command=self.pausar_reanudar)
        self.b_pausa.pack(side="left", padx=(8, 0))
        self.b_paso = ttk.Button(barra, text="⏭  Paso", command=self.paso)
        self.b_paso.pack(side="left", padx=(8, 0))
        self.b_reiniciar = ttk.Button(barra, text="↺  Reiniciar", command=self.reiniciar)
        self.b_reiniciar.pack(side="left", padx=(8, 0))
        ttk.Label(barra, text="Velocidad", style="Param.TLabel").pack(side="left", padx=(22, 6))
        self.v_velocidad = tk.DoubleVar(value=1.0)
        ttk.Scale(barra, from_=0.25, to=4.0, variable=self.v_velocidad, length=160,
                  command=self._velocidad).pack(side="left")
        self.l_velocidad = ttk.Label(barra, text="1.0×", style="Param.TLabel", width=5)
        self.l_velocidad.pack(side="left", padx=(6, 0))
        self.b_exportar = ttk.Button(barra, text="⤓  Exportar bitácora .txt", command=self.exportar)
        self.b_exportar.pack(side="right")

        self.contenedor = ttk.Frame(main, style="Panel.TFrame", padding=6)
        self.contenedor.grid(row=4, column=0, sticky="nsew")
        self.contenedor.columnconfigure(0, weight=1)
        self.contenedor.rowconfigure(0, weight=1)

        res = tk.Frame(main, bg=T.PANEL, highlightbackground=T.BORDE, highlightthickness=1)
        res.grid(row=5, column=0, sticky="ew", pady=(6, 6))
        res.columnconfigure(1, weight=1)
        tk.Label(res, text="ESPERADO", bg=T.PANEL, fg=T.SUAVE, font=T.FUENTE_P).grid(row=0, column=0, padx=(12, 8),
                                                                                    pady=(5, 0), sticky="w")
        self.l_esperado = tk.Label(res, text="—", bg=T.PANEL, fg=T.TEXTO, font=T.FUENTE_N, anchor="w")
        self.l_esperado.grid(row=0, column=1, sticky="ew", pady=(5, 0))
        tk.Label(res, text="REAL", bg=T.PANEL, fg=T.SUAVE, font=T.FUENTE_P).grid(row=1, column=0, padx=(12, 8),
                                                                                sticky="w")
        self.l_real = tk.Label(res, text="—", bg=T.PANEL, fg=T.TEXTO, font=T.FUENTE_N, anchor="w")
        self.l_real.grid(row=1, column=1, sticky="ew", padx=(0, 12))
        self.l_resumen = tk.Label(res, text="", bg=T.PANEL, fg=T.SUAVE, font=T.FUENTE_P, anchor="w", justify="left")
        self.l_resumen.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 5))

        bit = ttk.Frame(main)
        bit.grid(row=6, column=0, sticky="ew")
        bit.columnconfigure(0, weight=1)
        self.l_bitacora = ttk.Label(bit, text="BITÁCORA DE EVENTOS", style="Param.TLabel")
        self.l_bitacora.grid(row=0, column=0, sticky="w")
        self.t_bitacora = tk.Text(bit, height=5, bg=T.OSCURO, fg="#e2e8f0", insertbackground="white",
                                  font=T.MONO_P, relief="flat", padx=10, pady=6, wrap="none")
        self.t_bitacora.grid(row=1, column=0, sticky="ew")
        sb = ttk.Scrollbar(bit, command=self.t_bitacora.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.t_bitacora.configure(yscrollcommand=sb.set, state="disabled")
        for tipo, color in T.COLOR_EVENTO.items():
            self.t_bitacora.tag_configure(tipo, foreground=color)
        self.t_bitacora.tag_configure("tiempo", foreground="#64748b")

    # ------------------------------------------------------------------ escenario
    def _al_elegir(self, _e=None) -> None:
        sel = self.menu.selection()
        if not sel or sel[0].startswith("mod"):
            return
        if self.escenario_cls and sel[0] == self.escenario_cls.codigo:
            return
        if self.controlador.en_curso and not messagebox.askyesno(
                "Cambiar de escenario", "Hay una simulación en curso. ¿Reiniciarla y cambiar de escenario?",
                parent=self):
            self.menu.selection_set(self.escenario_cls.codigo)
            return
        self.seleccionar(sel[0])

    def seleccionar(self, codigo: str) -> None:
        self.controlador.reiniciar()
        cls = next(c for c in self.controlador.escenarios() if c.codigo == codigo)
        self.escenario_cls = cls
        if self.menu.selection() != (codigo,):
            self.menu.selection_set(codigo)
        self.l_codigo.configure(text=cls.codigo, bg=T.COLOR_MODULO[cls.modulo])
        self.l_titulo.configure(text=cls.nombre)
        self.l_modulo.configure(text=f"Módulo {cls.modulo} · {MODULOS[cls.modulo]}")
        self.l_explicacion.configure(text=cls.explicacion)
        self._formulario(cls)
        if self.panel_actual is not None:
            self.panel_actual.grid_remove()
        if cls.vista not in self.paneles:
            self.paneles[cls.vista] = PANELES[cls.vista](self.contenedor, self)
        self.panel_actual = self.paneles[cls.vista]
        self.panel_actual.grid(row=0, column=0, sticky="nsew")
        self.after(30, self.panel_actual.limpiar)
        self._limpiar_resultado()
        self._limpiar_bitacora()
        self._actualizar_botones()

    def _formulario(self, cls) -> None:
        for w in self.f_param.winfo_children():
            w.destroy()
        self.widgets_param.clear()
        for i, p in enumerate(cls.parametros):
            caja = ttk.Frame(self.f_param)
            caja.grid(row=0, column=i, sticky="w", padx=(0, 18))
            ttk.Label(caja, text=p.etiqueta, style="Param.TLabel").pack(anchor="w")
            if p.tipo == "opcion":
                w = ttk.Combobox(caja, values=list(p.opciones), state="readonly", width=max(map(len, p.opciones)) + 2)
                w.set(p.defecto)
            else:
                paso = 1 if p.tipo == "int" else 0.5
                w = ttk.Spinbox(caja, from_=p.minimo, to=p.maximo, increment=paso, width=8)
                w.set(p.defecto)
            w.pack(anchor="w")
            self.widgets_param[p.clave] = w
            if p.ayuda:
                ttk.Label(caja, text=p.ayuda, style="Param.TLabel", foreground="#8a93a6",
                          font=("Segoe UI", 8)).pack(anchor="w")

    def _valores(self) -> dict:
        return {k: w.get() for k, w in self.widgets_param.items()}

    # ------------------------------------------------------------------ controles
    def iniciar(self, pausado: bool = False) -> bool:
        if self.controlador.en_curso:
            return False
        try:
            self.controlador.reiniciar()
            self._limpiar_bitacora()
            self._limpiar_resultado()
            self.panel_actual.limpiar()
            self.controlador.iniciar(self.escenario_cls.codigo, self._valores(), self.v_velocidad.get(), pausado)
        except ValueError as exc:
            messagebox.showwarning("Parámetros no válidos", str(exc), parent=self)
            return False
        self._corriendo_antes = True
        self._actualizar_botones()
        return True

    def pausar_reanudar(self) -> None:
        c = self.controlador.control
        if not c or not self.controlador.en_curso:
            return
        self.controlador.reanudar() if c.pausado else self.controlador.pausar()
        self._actualizar_botones()

    def paso(self) -> None:
        if not self.controlador.en_curso:
            if not self.iniciar(pausado=True):
                return
        self.controlador.paso()
        self._actualizar_botones()

    def reiniciar(self) -> None:
        self.controlador.reiniciar()
        self._corriendo_antes = False
        self.panel_actual.limpiar()
        self._limpiar_resultado()
        self._actualizar_botones()

    def _velocidad(self, _v=None) -> None:
        v = self.v_velocidad.get()
        self.l_velocidad.configure(text=f"{v:.2g}×")
        self.controlador.cambiar_velocidad(v)

    def exportar(self) -> None:
        if not self.controlador.registro:
            messagebox.showinfo("Exportar bitácora", "Primero ejecute un escenario.", parent=self)
            return
        nombre = f"bitacora_{self.escenario_cls.codigo}_{datetime.now():%Y%m%d_%H%M%S}.txt"
        ruta = filedialog.asksaveasfilename(parent=self, title="Exportar bitácora", initialfile=nombre,
                                            defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if ruta:
            self.controlador.exportar_bitacora(ruta)
            messagebox.showinfo("Exportar bitácora", f"Bitácora guardada en:\n{ruta}", parent=self)

    def _actualizar_botones(self) -> None:
        corriendo = self.controlador.en_curso
        c = self.controlador.control
        self.b_iniciar.state(["disabled"] if corriendo else ["!disabled"])
        self.b_pausa.state(["!disabled"] if corriendo else ["disabled"])
        self.b_pausa.configure(text="▶  Reanudar" if (c and c.pausado) else "❚❚  Pausar")
        self.b_reiniciar.state(["!disabled"] if self.controlador.escenario else ["disabled"])
        self.b_exportar.state(["!disabled"] if self.controlador.registro else ["disabled"])
        estado = self.controlador.estado_ejecucion
        if corriendo:
            texto = "● En pausa" if c.pausado else f"● Ejecutando · {c.velocidad:.2g}×"
        else:
            texto = {"finalizada": "✔ Finalizada y guardada",
                     "cancelada": "■ Reiniciada", "error": "✘ Error"}.get(estado, "Listo para iniciar")
        if self.controlador.id_ejecucion and estado != "inactivo":
            texto += f" · #{self.controlador.id_ejecucion}"
        self.l_estado.configure(text=texto)

    # ------------------------------------------------------------------ resultado y bitácora
    def _limpiar_resultado(self) -> None:
        self.l_esperado.configure(text="—")
        self.l_real.configure(text="—", fg=T.TEXTO)
        self.l_resumen.configure(text="")

    def _mostrar_resultado(self) -> None:
        r = self.controlador.resultado
        if self.controlador.error:
            self.l_real.configure(text=self.controlador.error, fg=T.ROJO)
            return
        if r is None:
            return
        self.l_esperado.configure(text=r.esperado)
        self.l_real.configure(text=r.real, fg=T.VERDE if r.correcto else T.ROJO)
        self.l_resumen.configure(text=r.resumen)

    def _limpiar_bitacora(self) -> None:
        self.t_bitacora.configure(state="normal")
        self.t_bitacora.delete("1.0", "end")
        self.t_bitacora.configure(state="disabled")
        self.l_bitacora.configure(text="BITÁCORA DE EVENTOS")

    def _agregar_eventos(self, eventos) -> None:
        t = self.t_bitacora
        t.configure(state="normal")
        for e in eventos:
            linea = e.como_linea()
            t.insert("end", linea[:7], "tiempo")
            t.insert("end", linea[7:] + "\n", e.tipo if e.tipo in T.COLOR_EVENTO else "")
        lineas = int(t.index("end-1c").split(".")[0])
        if lineas > MAX_LINEAS_BITACORA:
            t.delete("1.0", f"{lineas - MAX_LINEAS_BITACORA}.0")
        t.see("end")
        t.configure(state="disabled")
        if self.controlador.registro:
            self.l_bitacora.configure(text=f"BITÁCORA DE EVENTOS · {len(self.controlador.registro)} eventos · "
                                           f"t = {self.controlador.registro.tiempo}")

    # ------------------------------------------------------------------ sondeo
    def _sondear(self) -> None:
        try:
            reg = self.controlador.registro
            if reg is not None:
                nuevos = []
                try:
                    while len(nuevos) < 400:
                        nuevos.append(reg.cola.get_nowait())
                except queue.Empty:
                    pass
                if nuevos:
                    self._agregar_eventos(nuevos)
                if self.controlador.escenario is not None:
                    self.panel_actual.actualizar(self.controlador.estado_vista())
            if self._corriendo_antes and not self.controlador.en_curso:
                self._corriendo_antes = False
                if self.controlador.escenario is not None:
                    self.panel_actual.actualizar(self.controlador.estado_vista())
                self._mostrar_resultado()
            self._actualizar_botones()
        finally:
            self.after(INTERVALO_MS, self._sondear)

    # ------------------------------------------------------------------ ventanas
    def abrir_historial(self) -> None:
        VentanaHistorial(self, self.controlador)

    def mostrar_entorno(self) -> None:
        info = "\n".join(f"{k}: {v}" for k, v in info_entorno().items())
        messagebox.showinfo("Entorno del sistema", info, parent=self)

    def _cerrar(self) -> None:
        self.controlador.reiniciar(espera=2)
        self.destroy()


class VentanaHistorial(tk.Toplevel):
    """Ejecuciones guardadas en SQLite y sus eventos."""

    def __init__(self, padre, controlador: Controlador) -> None:
        super().__init__(padre)
        self.controlador = controlador
        self.title("Historial de ejecuciones · base de datos SQLite")
        self.geometry("1100x620")
        self.configure(bg=T.FONDO)
        cols = ("id", "codigo", "nombre", "inicio", "mecanismo", "estado", "esperado", "real", "eventos")
        self.tabla = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c, titulo, ancho in zip(cols, ("#", "F", "Escenario", "Inicio", "Mecanismo", "Estado", "Esperado", "Real",
                                           "Eventos"), (45, 40, 170, 140, 80, 85, 220, 260, 60)):
            self.tabla.heading(c, text=titulo, anchor="w")
            self.tabla.column(c, width=ancho, anchor="w", stretch=c in ("esperado", "real"))
        self.tabla.pack(fill="x", padx=10, pady=(10, 6))
        self.tabla.bind("<<TreeviewSelect>>", self._ver)
        self.texto = tk.Text(self, bg=T.OSCURO, fg="#e2e8f0", font=T.MONO_P, relief="flat", padx=10, pady=6)
        self.texto.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for f in controlador.historial():
            self.tabla.insert("", "end", iid=str(f["id_ejecucion"]),
                              values=(f["id_ejecucion"], f["codigo"], f["nombre"], f["fecha_inicio"], f["mecanismo"],
                                      f["estado"], f["resultado_esperado"] or "", f["resultado_real"] or "",
                                      f["eventos"]))
        if not self.tabla.get_children():
            self.texto.insert("end", "Todavía no hay ejecuciones guardadas.")

    def _ver(self, _e=None) -> None:
        sel = self.tabla.selection()
        if not sel:
            return
        self.texto.delete("1.0", "end")
        for e in self.controlador.eventos_guardados(int(sel[0])):
            sujeto = e["hilo"] or (f"P{e['pid']}" if e["pid"] is not None else "-")
            linea = f"[{e['tiempo']:04d}] {e['tipo']:<9} {sujeto:<6} {e['mensaje']}"
            if e["estado_anterior"] or e["estado_nuevo"]:
                linea += f"  ({(e['estado_anterior'] or '-').upper()} → {(e['estado_nuevo'] or '-').upper()})"
            self.texto.insert("end", linea + "\n")
