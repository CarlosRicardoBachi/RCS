"""svgelements adapter for document bbox (debug tooling).

This module is intentionally optional: if `svgelements` is not installed,
callers must keep working (returning `available: False`).

Extra metadata we expose (when available)
- document size (`doc_size`) in user units/px as returned by svgelements
- viewbox (`viewbox`) in user units

These are useful to align geometry bbox into the same viewport used by QtSvg
during rasterization.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        # Length-like objects might store a numeric `.value`
        try:
            return float(getattr(v, "value"))
        except Exception:
            return None


def _extract_viewbox(svg: Any) -> Optional[list[float]]:
    # svgelements tends to expose `viewbox` (lowercase). Keep robust.
    vb = getattr(svg, "viewbox", None) or getattr(svg, "viewBox", None)
    if vb is None:
        return None
    # Common representations:
    # - tuple/list (x, y, w, h)
    # - object with x/y/width/height
    if isinstance(vb, (list, tuple)) and len(vb) >= 4:
        try:
            return [float(vb[0]), float(vb[1]), float(vb[2]), float(vb[3])]
        except Exception:
            return None
    try:
        x = _safe_float(getattr(vb, "x", None))
        y = _safe_float(getattr(vb, "y", None))
        w = _safe_float(getattr(vb, "width", None))
        h = _safe_float(getattr(vb, "height", None))
        if None in (x, y, w, h):
            return None
        return [float(x), float(y), float(w), float(h)]
    except Exception:
        return None


def compute_document_bbox(
    svg_path: str,
    *,
    ppi: float = 96.0,
    width: Optional[float] = None,
    height: Optional[float] = None,
    reify: bool = True,
) -> Dict[str, Any]:
    """Compute SVG document bbox using `svgelements` if available.

    Returns a dict like:
    - available: bool
    - bbox: (x0, y0, x1, y1) or None
    - doc_size: [w, h] (optional)
    - viewbox: [x, y, w, h] (optional)
    - error: str (optional)
    """

    try:
        from svgelements import SVG  # type: ignore
    except Exception as e:
        return {"available": False, "bbox": None, "error": f"{type(e).__name__}: {e}"}

    try:
        svg = SVG.parse(svg_path, ppi=float(ppi), width=width, height=height, reify=bool(reify))

        # BBox: tuple(x0, y0, x1, y1) in svgelements' coordinate system.
        bbox = None
        try:
            b = svg.bbox(with_stroke=False)  # type: ignore
            if b is not None:
                bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
        except Exception:
            # Fallback: older versions might expose `.bbox` property
            try:
                b = svg.bbox  # type: ignore
                if b is not None:
                    bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
            except Exception:
                bbox = None

        doc_w = _safe_float(getattr(svg, "width", None))
        doc_h = _safe_float(getattr(svg, "height", None))
        doc_size = None
        if doc_w is not None and doc_h is not None:
            doc_size = [float(doc_w), float(doc_h)]

        viewbox = _extract_viewbox(svg)

        return {
            "available": True,
            "bbox": bbox,
            "doc_size": doc_size,
            "viewbox": viewbox,
        }
    except Exception as e:
        return {"available": True, "bbox": None, "error": f"{type(e).__name__}: {e}"}
