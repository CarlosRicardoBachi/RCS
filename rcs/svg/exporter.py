# File: rcs/svg/exporter.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.2.0
# Status: stable
# Date: 2026-01-15
# Purpose: Export SVG base en mm (contours-only) para pipeline.
# Notes: Bloque 4 incorporará export completo de objetos.
from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from rcs.core.models import Project
from rcs.utils.errors import RcsValidationError, RcsIOError


def export_project_svg(project: Project, out_path: str | Path) -> Path:
    """Exporta un SVG base en mm.

    En v0.1.0 solo exporta el canvas (sin objetos). Esto permite validar escala
    y compatibilidad general de unidades en tu pipeline.
    """
    if project.objects:
        raise RcsValidationError(
            "Export aún no soporta objetos (se habilita en Bloque 4)."
        )

    p = Path(out_path)
    if p.suffix.lower() != ".svg":
        p = p.with_suffix(".svg")

    w, h = project.canvas_mm
    svg = Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "width": f"{w}mm",
            "height": f"{h}mm",
            "viewBox": f"0 0 {w} {h}",
        },
    )

    # Regla dura (contornos-only): no rellenar.
    # Se deja preparado para Bloque 4 donde se insertarán paths normalizados.
    SubElement(svg, "g", {"id": "RCS_EXPORT", "fill": "none", "stroke": "black"})

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        xml = tostring(svg, encoding="unicode")
        p.write_text(xml, encoding="utf-8")
        return p
    except Exception as e:
        raise RcsIOError(f"No se pudo exportar SVG: {p}") from e
