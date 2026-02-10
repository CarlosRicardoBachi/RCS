"""
HOTFIX: GMPR - asegurar que el SVG embebido se reconstruya primero
y actúe como sistema de referencia (mm), antes de restaurar rasters relativos.

Contexto del bug (observado):
- En GMPR se importa raster (OK) pero el SVG embebido no aparece.
- Importar SVG desde archivo funciona.
- El tamaño/posición vienen del SVG; el raster es relativo a ese SVG.

Este hotfix NO cambia el formato GMPR. Solo garantiza orden + disponibilidad del SVG root.
"""

from __future__ import annotations

import base64
import gzip
import io


def _decode_svg_embedded(svg_embedded: dict) -> bytes:
    """
    svg_embedded esperado (GMPR v5 observado):
      {
        "filename": "...",
        "sha1": "...",
        "encoding": "gzip+base64",
        "bytes": <int>,
        "data": "<base64...>"
      }
    """
    enc = (svg_embedded.get("encoding") or "").lower().strip()
    data = svg_embedded.get("data")
    if not data:
        raise ValueError("svg_embedded.data vacío")

    raw = base64.b64decode(data)

    if "gzip" in enc:
        return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()

    # fallback: si no viene gzip, devolvemos bytes tal cual
    return raw


def _create_svg_root_item_from_bytes(app, svg_bytes: bytes):
    """
    IMPORTANTE (regla del proyecto):
    - NO inventar pipeline nuevo.
    - Usar el MISMO pipeline que ya funciona al importar SVG desde archivo.

    Conectores típicos (probables):
      - app.create_svg_item_from_bytes(bytes)
      - app.svg_importer.from_bytes(bytes)
      - app.svg.from_bytes(bytes)
      - loader.svg_from_bytes(bytes)

    Ajustá esta función para apuntar al constructor real del repo.
    """
    if hasattr(app, "create_svg_item_from_bytes"):
        return app.create_svg_item_from_bytes(svg_bytes)

    if hasattr(app, "svg_importer") and hasattr(app.svg_importer, "from_bytes"):
        return app.svg_importer.from_bytes(svg_bytes)

    if hasattr(app, "svg") and hasattr(app.svg, "from_bytes"):
        return app.svg.from_bytes(svg_bytes)

    raise RuntimeError(
        "HOTFIX GMPR: no se encontró el constructor real de SVG desde bytes. "
        "Conectar _create_svg_root_item_from_bytes() al pipeline real del repo."
    )


def apply_hotfix_for_gmpr_import(app) -> None:
    """
    Hook: ejecutar 1 vez al inicio (antes de abrir/importar GMPR).

    Estrategia:
    - Interceptar el método real que carga GMPR (loader/importer).
    - En el dict GMPR retornado, crear el SVG root desde svg_embedded y guardarlo en:
        gmpr_data['_rcs_svg_root_item']
      para que el resto del pipeline pueda usarlo como referencia.
    - Marcar idempotencia con '_rcs_svg_root_built'.
    """
    # localizar objeto "loader" de tu app (adaptable)
    loader = None
    for attr in ("gmpr_loader", "project_loader", "loader", "io"):
        if hasattr(app, attr):
            loader = getattr(app, attr)
            break
    if loader is None:
        raise RuntimeError("HOTFIX GMPR: no se encontró loader/importer en app. Conectar apply_hotfix_for_gmpr_import().")

    # localizar función que carga GMPR (adaptable)
    target_fn_name = None
    for cand in ("load_gmpr", "open_gmpr", "import_gmpr", "load_project_gmpr"):
        if hasattr(loader, cand):
            target_fn_name = cand
            break
    if target_fn_name is None:
        raise RuntimeError("HOTFIX GMPR: no se encontró función GMPR (load_gmpr/open_gmpr/import_gmpr/...).")

    original_fn = getattr(loader, target_fn_name)

    def wrapped_load_gmpr(*args, **kwargs):
        gmpr_data = original_fn(*args, **kwargs)
        if not isinstance(gmpr_data, dict):
            return gmpr_data

        svg_embedded = gmpr_data.get("svg_embedded")
        if not svg_embedded:
            return gmpr_data

        if gmpr_data.get("_rcs_svg_root_built"):
            return gmpr_data

        try:
            svg_bytes = _decode_svg_embedded(svg_embedded)
        except Exception as e:
            gmpr_data.setdefault("_rcs_hotfix_warnings", []).append(f"svg_embedded decode failed: {e}")
            return gmpr_data

        try:
            svg_root_item = _create_svg_root_item_from_bytes(app, svg_bytes)
        except Exception as e:
            gmpr_data.setdefault("_rcs_hotfix_warnings", []).append(f"svg_root create failed: {e}")
            return gmpr_data

        gmpr_data["_rcs_svg_root_item"] = svg_root_item
        gmpr_data["_rcs_svg_root_built"] = True
        return gmpr_data

    setattr(loader, target_fn_name, wrapped_load_gmpr)
