"""Colores, fuentes y utilidades de dibujo compartidas por la interfaz."""
from __future__ import annotations

import tkinter as tk

FONDO = "#f4f6f9"
PANEL = "#ffffff"
BORDE = "#d9dee6"
TEXTO = "#1f2430"
SUAVE = "#5b6475"
TENUE = "#eef1f5"
VERDE = "#1f9d55"
AZUL = "#2563eb"
AMARILLO = "#b7791f"
MORADO = "#7c3aed"
ROJO = "#c53030"
GRIS = "#6b7280"
OSCURO = "#151a23"

# color de borde y de relleno de cada estado de proceso
COLOR_ESTADO = {
    "nuevo": (AZUL, "#e8effd"),
    "listo": (VERDE, "#e8f6ee"),
    "ejecucion": (AMARILLO, "#fdf4e3"),
    "bloqueado": (MORADO, "#f1eafd"),
    "terminado": (ROJO, "#fdecec"),
}
NOMBRE_ESTADO = {"nuevo": "nuevo", "listo": "listo", "ejecucion": "ejecución", "bloqueado": "bloqueado",
                 "terminado": "terminado"}
COLOR_MODULO = {"A": AZUL, "B": MORADO, "C": ROJO}

# colores de la bitácora por tipo de evento
COLOR_EVENTO = {
    "fork": "#7dd3fc", "admit": "#86efac", "exec": "#fcd34d", "preempt": "#fdba74", "wait": "#c4b5fd",
    "irq": "#86efac", "exit": "#fca5a5", "kill": "#f87171", "thread": "#7dd3fc", "mem": "#cbd5e1",
    "modo": "#fcd34d", "sys": "#c4b5fd", "user": "#86efac", "read": "#cbd5e1", "write": "#cbd5e1",
    "carrera": "#f87171", "ok": "#86efac", "lock": "#86efac", "unlock": "#94a3b8", "deadlock": "#f87171",
    "timeout": "#fdba74", "starve": "#f87171", "inicio": "#ffffff", "fin": "#ffffff", "error": "#f87171",
}

FUENTE = ("Segoe UI", 10)
FUENTE_N = ("Segoe UI", 10, "bold")
FUENTE_P = ("Segoe UI", 9)
FUENTE_T = ("Segoe UI", 15, "bold")
FUENTE_G = ("Segoe UI", 22, "bold")
MONO = ("Consolas", 10)
MONO_P = ("Consolas", 9)
MONO_N = ("Consolas", 10, "bold")


def caja(canvas: tk.Canvas, x0, y0, x1, y1, r=10, **kw):
    """Rectángulo con esquinas redondeadas."""
    puntos = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
              x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return canvas.create_polygon(puntos, smooth=True, **kw)


def flecha(canvas: tk.Canvas, puntos, color=GRIS, ancho=2, guiones=None):
    return canvas.create_line(*puntos, fill=color, width=ancho, arrow=tk.LAST, arrowshape=(10, 12, 4),
                              dash=guiones)


def mensaje_vacio(canvas: tk.Canvas, texto: str) -> None:
    canvas.delete("all")
    w, h = canvas.winfo_width(), canvas.winfo_height()
    canvas.create_text(w / 2, h / 2, text=texto, fill=SUAVE, font=FUENTE, width=max(200, w - 80), justify="center")
