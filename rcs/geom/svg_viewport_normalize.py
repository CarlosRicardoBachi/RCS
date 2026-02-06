# File: rcs/geom/svg_viewport_normalize.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.40
# Status: stable
# Date: 2026-01-24
# Purpose: Normalización de viewport SVG (contrato reusable).
# Notes:
# - La meta es producir un "truth" consistente para QtSvg (render), svgelements (geom) y futuro backend (Skia).
# - Este módulo NO toca la UI; lo usa el harness y luego lo usará el runtime de la app.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Any, Literal


_Unit = Literal["px", "mm", "cm", "in", "pt", "pc", "percent", "unknown"]

# CSS pixels per inch (spec de facto usada por la mayoría de engines).
CSS_PPI = 96.0


@dataclass(frozen=True)
class NormalizedViewport:
    """Contrato de normalización de viewport.

    - doc_w/doc_h: tamaño lógico del documento en *px* (CSS px).
    - viewbox: tuple(x,y,w,h) en unidades de usuario (svg user units).
    - ppi: pixels-per-inch estimado (cuando hay unidades físicas).
    - units: unidad original detectada para width/height.
    - raw: valores crudos (debug).
    """
    doc_w: float
    doc_h: float
    viewbox: tuple[float, float, float, float] | None
    ppi: float
    units: _Unit
    raw: dict[str, Any]


_len_re = re.compile(r"^\s*([+-]?(?:\d+\.?\d*|\d*\.?\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)\s*$")


def _parse_length(s: str | None) -> tuple[float | None, _Unit]:
    if not s:
        return None, "unknown"
    m = _len_re.match(s)
    if not m:
        return None, "unknown"
    v = float(m.group(1))
    u = (m.group(2) or "").lower()
    if u == "":
        # En SVG, width/height sin unidad se interpreta como px (CSS px).
        return v, "px"
    if u == "%":
        return v, "percent"
    if u in {"px", "mm", "cm", "in", "pt", "pc"}:
        return v, u  # type: ignore[return-value]
    return v, "unknown"


def _to_inches(v: float, u: _Unit) -> float | None:
    if u == "in":
        return v
    if u == "cm":
        return v / 2.54
    if u == "mm":
        return v / 25.4
    if u == "pt":
        return v / 72.0
    if u == "pc":
        return v / 6.0  # 1pc = 12pt = 1/6 in
    return None


def _parse_viewbox(s: str | None) -> tuple[float, float, float, float] | None:
    if not s:
        return None
    parts = re.split(r"[\s,]+", s.strip())
    if len(parts) != 4:
        return None
    try:
        x, y, w, h = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return (x, y, w, h)


def normalize_svg_viewport(svg_path: Path) -> NormalizedViewport:
    """Normaliza el viewport de un SVG y devuelve un contrato estable.

    Heurística (pragmática, pero consistente):
    1) Si hay width/height numéricos:
       - Convertimos a doc_w/doc_h en px (CSS px) usando CSS_PPI cuando hay unidades físicas.
    2) Si NO hay width/height, pero hay viewBox:
       - doc_w/doc_h = viewBox w/h (asumimos user units ~ px).
    3) Si no hay nada: doc_w/doc_h = 0 (caso inválido; el caller lo marca).

    ppi:
    - Si width/height están en unidades físicas y viewBox existe, estimamos ppi por eje:
      ppi_x = viewBox_w / width_in_inches, ppi_y similar; usamos promedio si es coherente.
    - Si no, CSS_PPI.
    """
    p = Path(svg_path)
    raw: dict[str, Any] = {"path": str(p)}
    try:
        data = p.read_bytes()
    except Exception as e:
        return NormalizedViewport(0.0, 0.0, None, CSS_PPI, "unknown", {"error": str(e), **raw})

    try:
        # Parse XML sin resolver entidades externas.
        root = ET.fromstring(data)
    except Exception as e:
        return NormalizedViewport(0.0, 0.0, None, CSS_PPI, "unknown", {"error": str(e), **raw})

    # Normalizar namespace
    tag = root.tag
    raw["root_tag"] = tag

    w_raw = root.get("width")
    h_raw = root.get("height")
    vb_raw = root.get("viewBox")

    raw.update({"width": w_raw, "height": h_raw, "viewBox": vb_raw})

    w_val, w_u = _parse_length(w_raw)
    h_val, h_u = _parse_length(h_raw)
    units = w_u if w_u != "unknown" else h_u

    vb = _parse_viewbox(vb_raw)

    # doc_w/doc_h en px
    doc_w = 0.0
    doc_h = 0.0

    if w_val is not None and h_val is not None and w_u not in {"percent"} and h_u not in {"percent"}:
        # Convertir unidades físicas a px con CSS_PPI (si aplica)
        if w_u == "px" or w_u == "unknown":
            doc_w = float(w_val)
        else:
            inches = _to_inches(float(w_val), w_u)
            doc_w = float(w_val) if inches is None else float(inches * CSS_PPI)

        if h_u == "px" or h_u == "unknown":
            doc_h = float(h_val)
        else:
            inches = _to_inches(float(h_val), h_u)
            doc_h = float(h_val) if inches is None else float(inches * CSS_PPI)

    elif vb is not None:
        # Sin width/height confiables: usar viewBox como tamaño lógico.
        doc_w = float(vb[2])
        doc_h = float(vb[3])

    ppi = CSS_PPI
    if vb is not None:
        # Estimar ppi si hay unidades físicas (width/height en mm/cm/in/pt/pc)
        w_in = _to_inches(float(w_val), w_u) if (w_val is not None) else None
        h_in = _to_inches(float(h_val), h_u) if (h_val is not None) else None
        ppis = []
        if w_in and w_in > 0:
            ppis.append(float(vb[2]) / float(w_in))
        if h_in and h_in > 0:
            ppis.append(float(vb[3]) / float(h_in))
        if ppis:
            # Si difieren mucho, igual devolvemos el promedio (caller puede WARN).
            ppi = sum(ppis) / len(ppis)

    return NormalizedViewport(doc_w, doc_h, vb, float(ppi), units, raw)
