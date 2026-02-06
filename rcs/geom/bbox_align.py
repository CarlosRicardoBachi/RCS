"""Geometry bbox alignment helpers for Render/Geom harness.

Problem
- QtSvg rasterizes into a target rect (here: square `render_px x render_px`).
- `svgelements` bbox may be expressed in a different coordinate system:
  * viewBox user units
  * viewport pixel units (based on SVG width/height)
  * millimeters/inches converted via PPI

So a *systematic* offset/scale mismatch can produce huge bbox errors (e.g. ~200px)
for every SVG, making the harness unusable.

Approach
- Generate a few plausible affine mappings (scale + translate) from the geometry
  coordinate system into the Qt target viewport.
- Score candidates against the observed Qt alpha bbox and pick the best.

This is debug-only tooling: it must be robust and never raise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .bbox_compare import compare_bboxes


BBoxXYXYTuple = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _Transform:
    kind: str
    scale_x: float
    scale_y: float
    tx: float
    ty: float


def _map_bbox(b: BBoxXYXYTuple, t: _Transform) -> BBoxXYXYTuple:
    x0, y0, x1, y1 = b
    return (
        float(x0 * t.scale_x + t.tx),
        float(y0 * t.scale_y + t.ty),
        float(x1 * t.scale_x + t.tx),
        float(y1 * t.scale_y + t.ty),
    )


def _keep_aspect_transform(
    *,
    src_x: float,
    src_y: float,
    src_w: float,
    src_h: float,
    dst_w: float,
    dst_h: float,
    kind: str,
) -> Optional[_Transform]:
    if src_w <= 1e-9 or src_h <= 1e-9 or dst_w <= 1e-9 or dst_h <= 1e-9:
        return None
    s = min(dst_w / src_w, dst_h / src_h)
    # Centered letterbox, matching Qt.KeepAspectRatio behavior.
    tx = (dst_w - src_w * s) * 0.5 - src_x * s
    ty = (dst_h - src_h * s) * 0.5 - src_y * s
    return _Transform(kind=kind, scale_x=s, scale_y=s, tx=float(tx), ty=float(ty))


def _stretch_transform(
    *,
    src_x: float,
    src_y: float,
    src_w: float,
    src_h: float,
    dst_w: float,
    dst_h: float,
    kind: str,
) -> Optional[_Transform]:
    if src_w <= 1e-9 or src_h <= 1e-9 or dst_w <= 1e-9 or dst_h <= 1e-9:
        return None
    sx = dst_w / src_w
    sy = dst_h / src_h
    tx = -src_x * sx
    ty = -src_y * sy
    return _Transform(kind=kind, scale_x=float(sx), scale_y=float(sy), tx=float(tx), ty=float(ty))


def _as_viewbox(v: Any) -> Optional[Tuple[float, float, float, float]]:
    if v is None:
        return None
    if isinstance(v, (list, tuple)) and len(v) >= 4:
        try:
            x, y, w, h = float(v[0]), float(v[1]), float(v[2]), float(v[3])
            return (x, y, w, h)
        except Exception:
            return None
    return None


def _as_size(v: Any) -> Optional[Tuple[float, float]]:
    if v is None:
        return None
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        try:
            return (float(v[0]), float(v[1]))
        except Exception:
            return None
    return None


def align_geom_bbox_to_qt(
    qt_alpha_bbox: Optional[Tuple[int, int, int, int]],
    geom_bbox_xyxy: Any,
    *,
    render_px: int,
    qtsvg_viewbox: Any = None,
    svge_viewbox: Any = None,
    svge_doc_size: Any = None,
    tol_abs_px: float = 3.0,
    warn_abs_px: float = 8.0,
) -> Tuple[Any, Dict[str, Any]]:
    """Return (best_geom_bbox_xyxy, align_info).

    If qt_alpha_bbox is None or geom bbox missing, returns inputs and a minimal info dict.
    """
    info: Dict[str, Any] = {"chosen": "raw", "candidates": []}

    if qt_alpha_bbox is None:
        info["note"] = "qt alpha bbox missing; cannot score candidates"
        return geom_bbox_xyxy, info

    # Normalize geom bbox input to xyxy tuple.
    try:
        gb = geom_bbox_xyxy
        if gb is None:
            info["note"] = "geom bbox missing"
            return geom_bbox_xyxy, info
        if isinstance(gb, (list, tuple)) and len(gb) >= 4:
            gb_xyxy: BBoxXYXYTuple = (float(gb[0]), float(gb[1]), float(gb[2]), float(gb[3]))
        else:
            info["note"] = "geom bbox invalid"
            return geom_bbox_xyxy, info
    except Exception:
        info["note"] = "geom bbox coercion failed"
        return geom_bbox_xyxy, info

    dst_w = float(render_px)
    dst_h = float(render_px)

    candidates: List[Tuple[_Transform, BBoxXYXYTuple]] = []

    # Candidate 0: raw (no transform)
    candidates.append((_Transform(kind="raw", scale_x=1.0, scale_y=1.0, tx=0.0, ty=0.0), gb_xyxy))

    # Candidate 1: QtSvg viewBox -> target (keep aspect)
    vb_qt = _as_viewbox(qtsvg_viewbox)
    if vb_qt is not None:
        x, y, w, h = vb_qt
        t = _keep_aspect_transform(src_x=x, src_y=y, src_w=w, src_h=h, dst_w=dst_w, dst_h=dst_h, kind="qtsvg_viewbox_keep")
        if t is not None:
            candidates.append((t, _map_bbox(gb_xyxy, t)))
        t2 = _stretch_transform(src_x=x, src_y=y, src_w=w, src_h=h, dst_w=dst_w, dst_h=dst_h, kind="qtsvg_viewbox_stretch")
        if t2 is not None:
            candidates.append((t2, _map_bbox(gb_xyxy, t2)))

    # Candidate 2: svgelements viewBox -> target
    vb_svge = _as_viewbox(svge_viewbox)
    if vb_svge is not None:
        x, y, w, h = vb_svge
        t = _keep_aspect_transform(src_x=x, src_y=y, src_w=w, src_h=h, dst_w=dst_w, dst_h=dst_h, kind="svge_viewbox_keep")
        if t is not None:
            candidates.append((t, _map_bbox(gb_xyxy, t)))
        t2 = _stretch_transform(src_x=x, src_y=y, src_w=w, src_h=h, dst_w=dst_w, dst_h=dst_h, kind="svge_viewbox_stretch")
        if t2 is not None:
            candidates.append((t2, _map_bbox(gb_xyxy, t2)))

    # Candidate 3: svgelements doc size (viewport) -> target
    sz = _as_size(svge_doc_size)
    if sz is not None:
        w, h = sz
        t = _keep_aspect_transform(src_x=0.0, src_y=0.0, src_w=w, src_h=h, dst_w=dst_w, dst_h=dst_h, kind="svge_docsize_keep")
        if t is not None:
            candidates.append((t, _map_bbox(gb_xyxy, t)))
        t2 = _stretch_transform(src_x=0.0, src_y=0.0, src_w=w, src_h=h, dst_w=dst_w, dst_h=dst_h, kind="svge_docsize_stretch")
        if t2 is not None:
            candidates.append((t2, _map_bbox(gb_xyxy, t2)))

    best = (float("inf"), candidates[0][0], candidates[0][1])

    for t, mapped in candidates:
        try:
            rep = compare_bboxes(
                qt_alpha_bbox,
                mapped,
                tol_abs_px=float(tol_abs_px),
                warn_abs_px=float(warn_abs_px),
            )
            err = rep.get("max_abs_err_px")
            err_f = float(err) if err is not None else float("inf")
        except Exception:
            err_f = float("inf")
            rep = {"status": "?", "max_abs_err_px": None}

        info["candidates"].append(
            {
                "kind": t.kind,
                "max_abs_err_px": rep.get("max_abs_err_px"),
                "status": rep.get("status"),
                "transform": {"scale_x": t.scale_x, "scale_y": t.scale_y, "tx": t.tx, "ty": t.ty},
            }
        )
        if err_f < best[0]:
            best = (err_f, t, mapped)

    _, t_best, mapped_best = best
    info["chosen"] = t_best.kind
    info["transform"] = {"scale_x": t_best.scale_x, "scale_y": t_best.scale_y, "tx": t_best.tx, "ty": t_best.ty}
    info["render_px"] = int(render_px)

    return mapped_best, info
