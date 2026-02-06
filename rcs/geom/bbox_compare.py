"""BBox comparison helpers (Render/Geom harness).

Purpose
- Compare an *observed* bbox from a QtSvg raster render (alpha bbox) against an
  independent geometry bbox (typically `svgelements`).
- Produce a JSON-serializable report with tolerances and a simple status.

Design constraints
- No heavy deps.
- Must never raise (debug tooling should be robust).

Notes
- Alpha bbox includes any rasterized stroke/halo; geometry bbox might not.
  Keep tolerances loose initially; the goal is to catch *big* divergences.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class BBoxXYXY:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self) -> float:
        return float(self.x1 - self.x0)

    @property
    def h(self) -> float:
        return float(self.y1 - self.y0)

    def as_list(self) -> List[float]:
        return [float(self.x0), float(self.y0), float(self.x1), float(self.y1)]


def bbox_from_alpha_bbox(alpha_bbox: Optional[Tuple[int, int, int, int]]) -> Optional[BBoxXYXY]:
    """Convert alpha bbox (x,y,w,h) -> xyxy bbox."""

    if not alpha_bbox:
        return None
    try:
        x, y, w, h = alpha_bbox
        if w <= 0 or h <= 0:
            return None
        return BBoxXYXY(float(x), float(y), float(x + w), float(y + h))
    except Exception:
        return None


def bbox_from_xyxy_tuple(xyxy: Any) -> Optional[BBoxXYXY]:
    """Coerce (x0,y0,x1,y1) to BBoxXYXY."""

    if xyxy is None:
        return None
    if isinstance(xyxy, (list, tuple)) and len(xyxy) == 4:
        try:
            x0, y0, x1, y1 = xyxy
            return BBoxXYXY(float(x0), float(y0), float(x1), float(y1))
        except Exception:
            return None
    return None


def compare_bboxes(
    qt_alpha_bbox: Optional[Tuple[int, int, int, int]],
    geom_bbox_xyxy: Any,
    *,
    tol_abs_px: float = 3.0,
    warn_abs_px: float = 8.0,
) -> Dict[str, Any]:
    """Compare bboxes and return a JSON-serializable report.

    Status:
    - PASS: max_abs_err <= tol_abs_px
    - WARN: tol_abs_px < max_abs_err <= warn_abs_px
    - FAIL: max_abs_err > warn_abs_px
    - NO_GEOM: missing geometry bbox
    - INVISIBLE: Qt alpha bbox missing (render produced no alpha)
    """

    notes: List[str] = []

    qt_bbox = bbox_from_alpha_bbox(qt_alpha_bbox)
    geom_bbox = bbox_from_xyxy_tuple(geom_bbox_xyxy)

    if geom_bbox is None:
        return {
            "status": "NO_GEOM",
            "tol_abs_px": float(tol_abs_px),
            "warn_abs_px": float(warn_abs_px),
            "qt_bbox_xyxy": qt_bbox.as_list() if qt_bbox else None,
            "geom_bbox_xyxy": None,
            "max_abs_err_px": None,
            "diff": None,
            "notes": ["geometry bbox not available"],
        }

    if qt_bbox is None:
        return {
            "status": "INVISIBLE",
            "tol_abs_px": float(tol_abs_px),
            "warn_abs_px": float(warn_abs_px),
            "qt_bbox_xyxy": None,
            "geom_bbox_xyxy": geom_bbox.as_list(),
            "max_abs_err_px": None,
            "diff": None,
            "notes": ["QtSvg alpha bbox missing (likely invisible render)"]
        }

    dx0 = float(qt_bbox.x0 - geom_bbox.x0)
    dy0 = float(qt_bbox.y0 - geom_bbox.y0)
    dx1 = float(qt_bbox.x1 - geom_bbox.x1)
    dy1 = float(qt_bbox.y1 - geom_bbox.y1)
    dw = float(qt_bbox.w - geom_bbox.w)
    dh = float(qt_bbox.h - geom_bbox.h)

    max_abs = max(abs(dx0), abs(dy0), abs(dx1), abs(dy1))

    # Small heuristics to help reading the report.
    if geom_bbox.w <= 1e-6 or geom_bbox.h <= 1e-6:
        notes.append("geom bbox degenerate")
    if qt_bbox.w <= 1e-6 or qt_bbox.h <= 1e-6:
        notes.append("qt bbox degenerate")

    if max_abs <= float(tol_abs_px):
        status = "PASS"
    elif max_abs <= float(warn_abs_px):
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "status": status,
        "tol_abs_px": float(tol_abs_px),
        "warn_abs_px": float(warn_abs_px),
        "qt_bbox_xyxy": qt_bbox.as_list(),
        "geom_bbox_xyxy": geom_bbox.as_list(),
        "max_abs_err_px": float(max_abs),
        "diff": {
            "dx0": dx0,
            "dy0": dy0,
            "dx1": dx1,
            "dy1": dy1,
            "dw": dw,
            "dh": dh,
        },
        "notes": notes,
    }
