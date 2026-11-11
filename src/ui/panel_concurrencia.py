"""Paneles del módulo C · Concurrencia.

* PanelCarrera (F6, F7): contador compartido, valor esperado vs. real, por hilo.
* PanelInterbloqueo (F8): grafo de asignación de recursos y espera circular.
* PanelInanicion (F9): accesos y tiempo de espera por hilo.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui import tema as T


class _PanelCanvas(ttk.Frame):
    vacio = ""

    def __init__(self, padre, app) -> None:
        super().__init__(padre, style="Panel.TFrame")
        self.app = app
        self.canvas = tk.Canvas(self, bg=T.PANEL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)

    def limpiar(self) -> None:
        T.mensaje_vacio(self.canvas, self.vacio)

    def tam(self) -> tuple[int, int]:
        return max(self.canvas.winfo_width(), 700), max(self.canvas.winfo_height(), 320)


# =============================================================================
# F6 · F7
# =============================================================================
class PanelCarrera(_PanelCanvas):
    vacio = ("Inicie el escenario: varios hilos reales incrementarán el mismo contador. "
             "Use «Paso» para ver cómo se intercalan la lectura y la escritura.")

    def actualizar(self, estado: dict) -> None:
        fases = estado.get("fases")
        if not fases:
            self.limpiar()
            return
        c = self.canvas
        c.delete("all")
        w, h = self.tam()
        ancho = (w - 20) / len(fases)
        for i, f in enumerate(fases):
            self._tarjeta(10 + i * ancho, 10, 10 + (i + 1) * ancho - 10, h - 10, f)

    def _tarjeta(self, x0, y0, x1, y1, f: dict) -> None:
        c = self.canvas
        protegido = f["mecanismo"] != "ninguno"
        perdidas = f["esperado"] - f["contador"] if f["terminado"] else None
        ok = perdidas == 0
        col = T.VERDE if (f["terminado"] and ok) else (T.ROJO if f["terminado"] else T.AMARILLO)
        T.caja(c, x0, y0, x1, y1, r=12, fill=T.PANEL, outline=T.VERDE if protegido else T.ROJO, width=2)
        c.create_text(x0 + 16, y0 + 22, text=f["titulo"].upper(), anchor="w", font=T.FUENTE_N,
                      fill=T.VERDE if protegido else T.ROJO)
        c.create_text(x0 + 16, y0 + 62, text=f"contador = {f['contador']}", anchor="w", font=T.FUENTE_G, fill=col)
        c.create_text(x0 + 16, y0 + 96, text=f"esperado = {f['esperado']}  ({len(f['por_hilo'])} hilos × "
                                             f"{f['esperado'] // max(len(f['por_hilo']), 1)} incrementos)",
                      anchor="w", font=T.MONO, fill=T.SUAVE)
        bx0, bx1 = x0 + 110, x1 - 70
        y = y0 + 124
        for etiqueta, valor, color in (("esperado", f["esperado"], T.GRIS), ("real", f["contador"], col)):
            c.create_text(x0 + 16, y + 9, text=etiqueta, anchor="w", font=T.FUENTE_P, fill=T.TEXTO)
            c.create_rectangle(bx0, y, bx1, y + 18, fill=T.TENUE, outline="")
            c.create_rectangle(bx0, y, bx0 + (bx1 - bx0) * min(valor / max(f["esperado"], 1), 1), y + 18,
                               fill=color, outline="")
            c.create_text(bx1 + 8, y + 9, text=str(valor), anchor="w", font=T.MONO_N, fill=color)
            y += 26
        y += 8
        c.create_text(x0 + 16, y, text="Incrementos que cada hilo cree haber hecho", anchor="w", font=T.FUENTE_P,
                      fill=T.SUAVE)
        y += 16
        por_hilo_max = f["esperado"] / max(len(f["por_hilo"]), 1)
        for nombre, hechos in f["por_hilo"].items():
            c.create_text(x0 + 16, y + 7, text=nombre, anchor="w", font=T.MONO_P, fill=T.TEXTO)
            c.create_rectangle(bx0, y, bx1, y + 14, fill=T.TENUE, outline="")
            c.create_rectangle(bx0, y, bx0 + (bx1 - bx0) * min(hechos / max(por_hilo_max, 1), 1), y + 14,
                               fill=T.AZUL, outline="")
            c.create_text(bx1 + 8, y + 7, text=str(hechos), anchor="w", font=T.MONO_P, fill=T.AZUL)
            y += 19
            if y > y1 - 60:
                break
        y = y1 - 40
        if f["terminado"]:
            texto = (f"✔ Resultado correcto · los hilos esperaron {f['esperas']} veces para entrar"
                     if ok and protegido else "✔ Sin pérdidas en esta corrida" if ok else
                     f"✘ Se perdieron {perdidas} actualizaciones ({perdidas / max(f['esperado'], 1):.0%})")
        else:
            hechos = sum(f["por_hilo"].values())
            texto = (f"En curso… perdidas hasta ahora: {hechos - f['contador']}" if not protegido else
                     f"En curso… esperas por el {f['mecanismo']}: {f['esperas']}")
        c.create_text(x0 + 16, y + 10, text=texto, anchor="w", font=T.FUENTE_N, fill=col, width=x1 - x0 - 30)


# =============================================================================
# F8
# =============================================================================
class PanelInterbloqueo(_PanelCanvas):
    vacio = ("Inicie el escenario: H1 toma R1 y H2 toma R2; luego cada uno pide el recurso del otro. "
             "El grafo muestra quién retiene y quién espera cada recurso.")

    def actualizar(self, estado: dict) -> None:
        if not estado:
            self.limpiar()
            return
        c = self.canvas
        c.delete("all")
        w, h = self.tam()
        gw = w * 0.62                                     # ancho del grafo; a la derecha, Coffman
        pos = {"H1": (gw * 0.22, h * 0.5), "H2": (gw * 0.78, h * 0.5),
               "R1": (gw * 0.5, h * 0.2), "R2": (gw * 0.5, h * 0.8)}
        ciclo = set(estado["ciclo"])
        r = 34

        def borde(nodo, hacia):
            (x0, y0), (x1, y1) = pos[nodo], pos[hacia]
            d = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 or 1
            return x0 + (x1 - x0) / d * (r + 4), y0 + (y1 - y0) / d * (r + 4)

        for origen, destino, tipo in estado["aristas"]:
            en_ciclo = origen in ciclo and destino in ciclo
            col = T.ROJO if en_ciclo else (T.VERDE if tipo == "retiene" else T.AMARILLO)
            p0, p1 = borde(origen, destino), borde(destino, origen)
            T.flecha(c, [*p0, *p1], col, 4 if en_ciclo else 2.5, guiones=(6, 4) if tipo == "espera" else None)
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            c.create_text(mx, my - 12, text="retiene" if tipo == "retiene" else "espera", font=T.FUENTE_P, fill=col)

        for nodo, (x, y) in pos.items():
            if nodo.startswith("H"):
                est = estado["estados"].get(nodo, "nuevo")
                b, f = T.COLOR_ESTADO.get(est, (T.GRIS, T.TENUE))
                c.create_oval(x - r, y - r, x + r, y + r, fill=f, outline=T.ROJO if nodo in ciclo else b, width=3)
                c.create_text(x, y, text=nodo, font=T.FUENTE_N, fill=T.TEXTO)
                c.create_text(x, y + r + 14, text=T.NOMBRE_ESTADO.get(est, est), font=T.FUENTE_N, fill=b)
            else:
                c.create_rectangle(x - r, y - 24, x + r, y + 24, fill=T.TENUE,
                                   outline=T.ROJO if nodo in ciclo else T.GRIS, width=3)
                c.create_text(x, y, text=nodo, font=T.FUENTE_N, fill=T.TEXTO)

        if estado["ciclo"]:
            c.create_text(gw / 2, 18, text="INTERBLOQUEO · espera circular: " + " → ".join(
                estado["ciclo"] + [estado["ciclo"][0]]), font=T.FUENTE_N, fill=T.ROJO)
        elif estado["completados"]:
            c.create_text(gw / 2, 18, text="Sin interbloqueo · terminaron " + ", ".join(estado["completados"]),
                          font=T.FUENTE_N, fill=T.VERDE)
        c.create_text(12, h - 14, anchor="w", font=T.FUENTE_P, fill=T.SUAVE,
                      text="○ hilo   □ recurso   → retiene (recurso → hilo)   ⇢ espera (hilo → recurso)")

        # condiciones de Coffman
        x = gw + 20
        T.caja(c, x - 8, 20, w - 12, h - 30, r=12, fill=T.TENUE, outline=T.BORDE)
        c.create_text(x + 6, 42, text="Condiciones de Coffman", anchor="w", font=T.FUENTE_N, fill=T.TEXTO)
        circular = bool(estado["ciclo"])
        reten = any(t == "espera" for _o, _d, t in estado["aristas"]) or circular
        conds = [("Exclusión mutua", True, "cada recurso lo usa un hilo a la vez"),
                 ("Retener y esperar", reten, "retiene uno y pide otro"),
                 ("No expropiación", True, "nadie le quita el recurso a otro hilo"),
                 ("Espera circular", circular,
                  "H1 → R2 → H2 → R1 → H1" if circular else
                  ("evitada: orden global R1 → R2" if estado["estrategia"] != "sin prevención" else "aún no"))]
        y = 74
        for nombre, cumple, detalle in conds:
            c.create_text(x + 6, y, text=("✔ " if cumple else "✘ ") + nombre, anchor="w", font=T.FUENTE_N,
                          fill=T.ROJO if cumple else T.VERDE)
            c.create_text(x + 26, y + 18, text=detalle, anchor="w", font=T.FUENTE_P, fill=T.SUAVE,
                          width=w - x - 50)
            y += 50
        c.create_text(x + 6, y + 6, anchor="nw", font=T.FUENTE_P, fill=T.TEXTO, width=w - x - 30,
                      text="Si las cuatro se cumplen hay interbloqueo. Basta romper una para evitarlo.")


# =============================================================================
# F9
# =============================================================================
class PanelInanicion(_PanelCanvas):
    vacio = ("Inicie el escenario: los hilos de alta prioridad (A) piden el recurso una y otra vez; "
             "el hilo B1 tiene prioridad baja.")

    def actualizar(self, estado: dict) -> None:
        hilos = estado.get("hilos")
        if not hilos:
            self.limpiar()
            return
        c = self.canvas
        c.delete("all")
        w, h = self.tam()
        # recurso
        ocupado = estado["ocupado_por"]
        T.caja(c, 12, 12, w - 12, 70, r=12, fill=T.TENUE, outline=T.BORDE)
        c.create_text(28, 32, anchor="w", font=T.FUENTE_N, fill=T.TEXTO,
                      text=f"Recurso compartido · {'en uso por ' + ocupado if ocupado else 'libre'}")
        c.create_text(28, 54, anchor="w", font=T.FUENTE_P, fill=T.SUAVE,
                      text=f"Asignaciones {estado['asignaciones']} de {estado['rondas']} · envejecimiento: "
                           f"{estado['envejecimiento']} · prioridad 1 = la más alta")
        px0, px1 = w * 0.55, w - 30
        c.create_rectangle(px0, 44, px1, 58, fill=T.PANEL, outline=T.BORDE)
        c.create_rectangle(px0, 44, px0 + (px1 - px0) * min(estado["asignaciones"] / estado["rondas"], 1), 58,
                           fill=T.AZUL, outline="")
        # filas por hilo
        y = 96
        col_acc, col_esp = 230, w * 0.58
        ancho_barra = w * 0.30
        c.create_text(20, y, text="Hilo", anchor="w", font=T.FUENTE_P, fill=T.SUAVE)
        c.create_text(col_acc, y, text="Veces que obtuvo el recurso", anchor="w", font=T.FUENTE_P, fill=T.SUAVE)
        c.create_text(col_esp, y, text="Tiempo total esperando", anchor="w", font=T.FUENTE_P, fill=T.SUAVE)
        y += 18
        max_acc = max([d["accesos"] for d in hilos] + [1])
        max_esp = max([d["espera"] for d in hilos] + [0.1])
        for d in hilos:
            bajo = d["nombre"].startswith("B")
            col = T.ROJO if bajo else T.AZUL
            usando = d["nombre"] == ocupado
            T.caja(c, 12, y, w - 12, y + 52, r=10, fill="#fff7e6" if usando else T.PANEL,
                   outline=T.AMARILLO if usando else T.BORDE)
            c.create_text(24, y + 17, text=d["nombre"], anchor="w", font=T.FUENTE_N, fill=col)
            ef = d["efectiva"]
            prio = f"prioridad {d['prioridad']}" + (f" → efectiva {ef:g}" if ef is not None and ef != d["prioridad"]
                                                    else "")
            c.create_text(60, y + 17, text=prio, anchor="w", font=T.FUENTE_P, fill=T.SUAVE)
            c.create_text(24, y + 37, text=d["estado"], anchor="w", font=T.FUENTE_P,
                          fill=T.AMARILLO if usando else T.SUAVE)
            # accesos
            c.create_rectangle(col_acc, y + 12, col_acc + ancho_barra * 0.7, y + 26, fill=T.TENUE, outline="")
            c.create_rectangle(col_acc, y + 12, col_acc + ancho_barra * 0.7 * d["accesos"] / max_acc, y + 26,
                               fill=col, outline="")
            c.create_text(col_acc + ancho_barra * 0.7 + 8, y + 19, text=str(d["accesos"]), anchor="w",
                          font=T.MONO_N, fill=col)
            # espera
            c.create_rectangle(col_esp, y + 12, col_esp + ancho_barra, y + 26, fill=T.TENUE, outline="")
            c.create_rectangle(col_esp, y + 12, col_esp + ancho_barra * d["espera"] / max_esp, y + 26,
                               fill=T.AMARILLO, outline="")
            c.create_text(col_esp + ancho_barra + 8, y + 19, text=f"{d['espera']:.1f} s", anchor="w", font=T.MONO_N,
                          fill=T.AMARILLO)
            if bajo and d["accesos"] == 0 and d["estado"] == "terminado":
                c.create_text(col_acc, y + 41, text="✘ INANICIÓN: nunca obtuvo el recurso", anchor="w",
                              font=T.FUENTE_N, fill=T.ROJO)
            elif bajo and d["accesos"] > 0:
                c.create_text(col_acc, y + 41, text="✔ obtuvo el recurso", anchor="w", font=T.FUENTE_N,
                              fill=T.VERDE)
            y += 60
