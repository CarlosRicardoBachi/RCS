# File: rcs/svg/qpath_render.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.2.9
# Status: hotfix
# Date: 2026-01-15
# Purpose: Render seguro (sin QtSvg) de SVG -> QPainterPath en mm.
# Notes:
#   - Evita QSvgRenderer/QGraphicsSvgItem por cierres nativos en Windows con algunos SVG.
#   - Soporta paths (d) y usa svgelements para parseo robusto.
#   - Si el SVG es complejo o no se puede parsear, devuelve un path vacío.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PySide6.QtGui import QPainterPath


_NUM_RE = re.compile(r"^\s*([+-]?(?:\d+\.?\d*|\d*\.?\d+))(?:\s*([a-zA-Z%]+))?\s*$")


@dataclass(frozen=True)
class SvgMeta:
    width_mm: float | None
    height_mm: float | None
    viewbox: tuple[float, float, float, float] | None  # x,y,w,h


def load_svg_as_qpath_mm(svg_path: str | Path) -> QPainterPath:
    """Carga un SVG y devuelve un QPainterPath en coordenadas mm.

    Restricción MVP (Bloque 2): sólo paths.
    - Ignora fills/colores.
    - Ignora stroke-width.

    Si no se puede parsear, devuelve QPainterPath vacío.
    """
    p = Path(svg_path)
    meta = _read_meta(p)

    # Escala de user units -> mm usando viewBox (si existe) + width/height mm (si existen)
    vb = meta.viewbox
    if vb:
        vb_x, vb_y, vb_w, vb_h = vb
        sx = (meta.width_mm / vb_w) if (meta.width_mm and vb_w) else 1.0
        sy = (meta.height_mm / vb_h) if (meta.height_mm and vb_h) else 1.0
    else:
        vb_x, vb_y, vb_w, vb_h = 0.0, 0.0, 0.0, 0.0
        sx, sy = 1.0, 1.0

    # Parse XML y extraer d de <path>
    try:
        raw = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = p.read_text(encoding="utf-8-sig", errors="replace")

    try:
        root = ET.fromstring(raw)
    except Exception:
        return QPainterPath()

    # svgelements parsea el atributo d de forma robusta.
    try:
        from svgelements import Path as SvgPath
    except Exception:
        # Sin svgelements no podemos parsear d de forma segura.
        return QPainterPath()

    out = QPainterPath()
    started = False

    for el in root.iter():
        tag = el.tag
        if not isinstance(tag, str):
            continue
        if not (tag == "path" or tag.endswith("}path")):
            continue

        d = el.attrib.get("d")
        if not d:
            continue

        try:
            sp = SvgPath(d)
            # Convertir arcs a cubics si el lib lo soporta
            if hasattr(sp, "approximate_arcs_with_cubics"):
                sp = sp.approximate_arcs_with_cubics()
        except Exception:
            continue

        # Convertir segmentos a QPainterPath
        q = _svgpath_to_qpath_mm(sp, vb_x, vb_y, sx, sy)
        if q.isEmpty():
            continue

        if not started:
            out = q
            started = True
        else:
            out.addPath(q)

    return out if started else QPainterPath()


def _svgpath_to_qpath_mm(sp, vb_x: float, vb_y: float, sx: float, sy: float) -> QPainterPath:
    """Convierte un svgelements.Path a QPainterPath en mm."""
    q = QPainterPath()

    # svgelements puede devolver segmentos con .end/.start
    current_set = False

    def map_pt(pt):
        # pt puede ser complejo o tener x/y
        try:
            x = float(pt.x)
            y = float(pt.y)
        except Exception:
            x = float(getattr(pt, "real", 0.0))
            y = float(getattr(pt, "imag", 0.0))
        mx = (x - vb_x) * sx
        my = (y - vb_y) * sy
        return mx, my

    # Tipos comunes (si están disponibles)
    try:
        from svgelements import Move, Line, CubicBezier, QuadraticBezier, Close, Arc
    except Exception:
        Move = Line = CubicBezier = QuadraticBezier = Close = Arc = object

    for seg in sp:
        # Move
        if isinstance(seg, Move):
            ex, ey = map_pt(seg.end)
            q.moveTo(ex, ey)
            current_set = True
            continue

        # si no hubo move previo, anclamos en el start
        if not current_set:
            sx0, sy0 = map_pt(seg.start)
            q.moveTo(sx0, sy0)
            current_set = True

        if isinstance(seg, Line):
            ex, ey = map_pt(seg.end)
            q.lineTo(ex, ey)
        elif isinstance(seg, CubicBezier):
            c1x, c1y = map_pt(seg.control1)
            c2x, c2y = map_pt(seg.control2)
            ex, ey = map_pt(seg.end)
            q.cubicTo(c1x, c1y, c2x, c2y, ex, ey)
        elif isinstance(seg, QuadraticBezier):
            cx, cy = map_pt(seg.control)
            ex, ey = map_pt(seg.end)
            q.quadTo(cx, cy, ex, ey)
        elif isinstance(seg, Close):
            q.closeSubpath()
        else:
            # Fallback genérico: sampleo (incluye Arc si no fue aproximado)
            try:
                # Algunas clases tienen .point(t)
                steps = 12
                for i in range(1, steps + 1):
                    t = i / steps
                    pt = seg.point(t)
                    ex, ey = map_pt(pt)
                    q.lineTo(ex, ey)
            except Exception:
                # último recurso: end
                try:
                    ex, ey = map_pt(seg.end)
                    q.lineTo(ex, ey)
                except Exception:
                    pass

    return q


def _read_meta(svg_path: Path) -> SvgMeta:
    try:
        raw = svg_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = svg_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return SvgMeta(None, None, None)

    try:
        root = ET.fromstring(raw)
    except Exception:
        return SvgMeta(None, None, None)

    width_mm = _parse_length_mm(root.attrib.get("width"))
    height_mm = _parse_length_mm(root.attrib.get("height"))

    vb_attr = root.attrib.get("viewBox") or root.attrib.get("viewbox")
    viewbox = _parse_viewbox(vb_attr) if vb_attr else None

    # si no hay viewBox pero hay width/height: asumimos viewBox = 0 0 w h (en mismas unidades)
    if viewbox is None and width_mm and height_mm:
        viewbox = (0.0, 0.0, float(width_mm), float(height_mm))

    return SvgMeta(width_mm=width_mm, height_mm=height_mm, viewbox=viewbox)


def _parse_viewbox(vb: str | None) -> tuple[float, float, float, float] | None:
    if not vb:
        return None
    parts = [p for p in re.split(r"[\s,]+", vb.strip()) if p]
    if len(parts) != 4:
        return None
    try:
        x, y, w, h = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
    except Exception:
        return None
    if w == 0 or h == 0:
        return None
    return (x, y, w, h)


def _parse_length_mm(v: str | None) -> float | None:
    if not v:
        return None
    m = _NUM_RE.match(v)
    if not m:
        return None
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()

    # unidades comunes
    if unit in ("mm", ""):
        return num
    if unit == "cm":
        return num * 10.0
    if unit in ("in", "inch"):
        return num * 25.4
    if unit == "px":
        # SVG/CSS: 96 dpi (convención). Lo mantenemos como aproximación.
        return num * 25.4 / 96.0

    # cualquier otra unidad: mejor no adivinar
    return None
