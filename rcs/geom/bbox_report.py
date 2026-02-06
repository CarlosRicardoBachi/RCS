"""BBox report helpers for Render/Geom harness.

Dependency-free utilities used by `python -m rcs.svg.render_debug`.

Features
- Rank actionable statuses (WARN/FAIL/INVISIBLE) by severity and error.
- Generate reproducible CLI command per SVG.
- Compare a run against a baseline `_bbox_report.json` (regression detection).

Design constraints
- Must never raise: debug tooling should be robust.
- Keep output JSON-friendly.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


STATUS_SEVERITY: Dict[str, int] = {
    "PASS": 0,
    "WARN": 1,
    "FAIL": 2,
    "INVISIBLE": 3,
    # "NO_GEOM" is *not* a geometry mismatch; it usually means `svgelements` isn't installed.
    # Treat it as non-actionable by default.
    "NO_GEOM": -1,
}

ACTIONABLE_STATUSES = {"WARN", "FAIL", "INVISIBLE"}


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def norm_svg_key(svg: Any) -> str:
    """Normalize a svg identifier for report matching.

    Prefer stable paths in baselines; this uses normcase/normpath.
    """

    try:
        return os.path.normcase(os.path.normpath(str(svg)))
    except Exception:
        return str(svg)


def status_severity(status: Any) -> int:
    s = str(status or "").strip().upper()
    return int(STATUS_SEVERITY.get(s, 2))


def is_actionable(status: Any, *, include_no_geom: bool = False) -> bool:
    s = str(status or "").strip().upper()
    if include_no_geom and s == "NO_GEOM":
        return True
    return s in ACTIONABLE_STATUSES


def load_bbox_report(path: Path) -> List[Dict[str, Any]]:
    """Load a bbox report from json.

    Accepts either:
    - list[dict]
    - dict with key "items" -> list[dict]
    """

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [x for x in data["items"] if isinstance(x, dict)]
    return []


def build_repro_cmd(
    svg_path: str,
    *,
    out_dir: str,
    modes: List[str],
    size_px: int,
    render_scale: float,
    bbox_tol: float,
    bbox_warn: float,
    recursive: bool = False,
) -> str:
    """Generate a reproducible command line for a single svg file."""

    parts = [
        "python -m rcs.svg.render_debug",
        f'"{svg_path}"',
        f"--out \"{out_dir}\"",
        f"--modes {','.join(modes)}",
        f"--size {int(size_px)}",
        f"--scale {float(render_scale)}",
        f"--bbox-tol {float(bbox_tol)}",
        f"--bbox-warn {float(bbox_warn)}",
    ]
    if recursive:
        parts.append("--recursive")
    return " ".join(parts)


def rank_items(
    items: List[Dict[str, Any]],
    *,
    include_no_geom: bool = False,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Return a new list ranked by severity desc then error desc.

    Only actionable statuses are included by default.
    """

    def key(it: Dict[str, Any]) -> Tuple[int, float]:
        st = str(it.get("status") or "").strip().upper()
        sev = status_severity(st)
        err = _safe_float(it.get("max_abs_err_px"))
        # INVISIBLE should bubble up even if no err.
        if err is None:
            err_v = 1e9 if st == "INVISIBLE" else -1.0
        else:
            err_v = err
        return (sev, err_v)

    out = [
        dict(it)
        for it in items
        if is_actionable(it.get("status"), include_no_geom=include_no_geom)
    ]
    out.sort(key=key, reverse=True)

    if limit is not None:
        try:
            return out[: int(limit)]
        except Exception:
            return out
    return out


def compare_reports(
    *,
    baseline_items: List[Dict[str, Any]],
    current_items: List[Dict[str, Any]],
    err_eps: float = 0.5,
) -> Dict[str, Any]:
    """Compare baseline vs current and classify changes.

    Rules (default):
    - Skip any entry where baseline OR current is NO_GEOM (unknown geometry).
    - Regression if:
        - severity increased (PASS->WARN->FAIL->INVISIBLE)
        - OR same severity but `max_abs_err_px` increased by > err_eps
    - Improvement if the inverse.
    """

    def to_map(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        m: Dict[str, Dict[str, Any]] = {}
        for it in items:
            k = norm_svg_key(it.get("svg") or it.get("path") or "")
            if not k:
                continue
            m[k] = it
        return m

    bmap = to_map(baseline_items)
    cmap = to_map(current_items)

    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []
    unchanged: int = 0

    missing: List[str] = []
    new: List[str] = []

    for k, b in bmap.items():
        c = cmap.get(k)
        if c is None:
            missing.append(k)
            continue

        b_status = str(b.get("status") or "").upper()
        c_status = str(c.get("status") or "").upper()

        if b_status == "NO_GEOM" or c_status == "NO_GEOM":
            unchanged += 1
            continue

        b_sev = status_severity(b_status)
        c_sev = status_severity(c_status)
        b_err = _safe_float(b.get("max_abs_err_px"))
        c_err = _safe_float(c.get("max_abs_err_px"))

        delta_err: Optional[float] = None
        if b_err is not None and c_err is not None:
            delta_err = float(c_err - b_err)

        entry = {
            "svg": c.get("svg") or b.get("svg") or k,
            "baseline_status": b_status,
            "current_status": c_status,
            "baseline_max_abs_err_px": b_err,
            "current_max_abs_err_px": c_err,
            "delta_max_abs_err_px": delta_err,
        }

        if c_sev > b_sev:
            regressions.append(entry)
        elif c_sev < b_sev:
            improvements.append(entry)
        else:
            # same severity -> check error.
            if delta_err is not None and delta_err > float(err_eps):
                regressions.append(entry)
            elif delta_err is not None and delta_err < -float(err_eps):
                improvements.append(entry)
            else:
                unchanged += 1

    for k in cmap.keys():
        if k not in bmap:
            new.append(k)

    # Rank regressions: severity + delta
    def reg_key(it: Dict[str, Any]) -> Tuple[int, float]:
        sev = status_severity(it.get("current_status"))
        de = _safe_float(it.get("delta_max_abs_err_px"))
        if de is None:
            de_v = 1e9 if str(it.get("current_status") or "").upper() == "INVISIBLE" else 0.0
        else:
            de_v = de
        return (sev, de_v)

    regressions.sort(key=reg_key, reverse=True)

    return {
        "when": _dt.datetime.now().isoformat(timespec="seconds"),
        "counts": {
            "baseline": len(bmap),
            "current": len(cmap),
            "regressions": len(regressions),
            "improvements": len(improvements),
            "unchanged": unchanged,
            "new": len(new),
            "missing": len(missing),
        },
        "regressions": regressions,
        "improvements": improvements,
        "new": new,
        "missing": missing,
    }
