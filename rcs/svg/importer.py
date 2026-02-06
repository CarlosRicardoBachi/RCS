# File: rcs/svg/importer.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.2.0
# Status: stable
# Date: 2026-01-15
# Purpose: Inspección/validación liviana de SVG para import.
# Notes: Bloque 2 implementa parse + normalizador completo.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from rcs.utils.errors import RcsValidationError


FORBIDDEN_TAGS = {
    "{http://www.w3.org/2000/svg}mask",
    "{http://www.w3.org/2000/svg}clipPath",
    "{http://www.w3.org/2000/svg}filter",
    "{http://www.w3.org/2000/svg}pattern",
}


@dataclass(frozen=True)
class SvgInspection:
    path: Path
    width: str | None
    height: str | None
    viewbox: str | None
    forbidden_found: list[str]


def inspect_svg(path: str | Path) -> SvgInspection:
    """Lee el SVG y detecta tags no soportados.

    Esto NO normaliza a paths todavía: solo da un error claro si el archivo
    trae features complejas (mask/clip/filter/pattern) que rompen el flujo "contours-only".
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # fallback común en Windows
        raw = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        raise RcsValidationError(f"No se pudo leer SVG: {p}") from e

    try:
        root = ET.fromstring(raw)
    except Exception as e:
        raise RcsValidationError(f"SVG inválido (XML malformado): {p}") from e

    if not _is_svg_root(root.tag):
        raise RcsValidationError(f"Archivo no parece SVG (root={root.tag!r}): {p}")

    forbidden_found: list[str] = []
    for el in root.iter():
        if el.tag in FORBIDDEN_TAGS:
            forbidden_found.append(_strip_ns(el.tag))

    return SvgInspection(
        path=p,
        width=root.attrib.get("width"),
        height=root.attrib.get("height"),
        viewbox=root.attrib.get("viewBox"),
        forbidden_found=forbidden_found,
    )


def validate_svg_supported(path: str | Path) -> None:
    """Valida la regla dura: SVG debe estar libre de features complejas."""
    info = inspect_svg(path)
    if info.forbidden_found:
        found = ", ".join(sorted(set(info.forbidden_found)))
        raise RcsValidationError(
            "SVG no soportado (tiene {}): Convertir a paths antes de usar.".format(found)
        )


def _is_svg_root(tag: str) -> bool:
    return tag == "svg" or tag.endswith("}svg")


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag
