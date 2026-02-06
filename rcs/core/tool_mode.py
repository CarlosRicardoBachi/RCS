# File: rcs/core/tool_mode.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.4
# Status: wip
# Date: 2026-01-16
# Purpose: Modos de herramienta del lienzo (selección/zoom/rotación/escala/pan).
# Notes: Se persiste en settings.json (no forma parte del .RCS).

from __future__ import annotations

from enum import Enum


class ToolMode(str, Enum):
    """Modo activo del lienzo.

    - select: seleccionar + mover (drag). Scroll con rueda; Ctrl+rueda = zoom.
    - pick: solo seleccionar (drag no mueve). Útil para evitar arrastres.
    - zoom: rueda = zoom del lienzo
    - rotate: rueda = rotar objeto seleccionado / bajo cursor
    - scale: rueda = escalar objeto seleccionado / bajo cursor
    - pan: click+arrastre = mover vista (ScrollHandDrag)
    """

    SELECT = "select"
    PICK = "pick"
    ZOOM = "zoom"
    ROTATE = "rotate"
    SCALE = "scale"
    PAN = "pan"


def coerce_tool_mode(v: object, default: ToolMode = ToolMode.SELECT) -> ToolMode:
    try:
        s = str(v or "").strip().lower()
        for m in ToolMode:
            if m.value == s:
                return m
    except Exception:
        pass
    return default
