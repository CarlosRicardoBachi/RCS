# File: rcs/svg/render_debug.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.37
# Status: stable
# Date: 2026-01-24
# Purpose: Harness CLI para debug de render SVG -> PNG (sin UI).
# Notes:
# - Reproduce rápido: render crudo QtSvg + stylize "thumb" + stylize "canvas".
# - No toca el flujo principal de la app; es una herramienta opt-in.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import os
import sys
import time
import datetime
from typing import Any

from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QRectF, Qt
from PySide6.QtSvg import QSvgRenderer

from rcs.geom.svgelements_bbox import compute_document_bbox
from rcs.svg.thumbs import ThumbCache
from rcs.geom.bbox_compare import compare_bboxes
from rcs.geom.bbox_align import align_geom_bbox_to_qt
from rcs.geom.bbox_report import (
    build_repro_cmd,
    compare_reports,
    load_bbox_report,
    rank_items,
)

# Nota: NO importamos rcs.ui.canvas_view al tope para evitar overhead/ciclos.
# Se importa de forma perezosa solo si el usuario pide el modo "canvas".


@dataclass(frozen=True)
class RenderResult:
    kind: str
    out_png: Path
    size_px: int
    render_scale: int
    alpha_nonzero: int
    alpha_bbox: tuple[int, int, int, int] | None
    notes: dict[str, Any]


def _ensure_qt_app() -> None:
    """Crea una app Qt mínima si no existe (necesaria para algunos plugins)."""
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        QGuiApplication(sys.argv[:1] or ["rcs-render-debug"])


def _alpha_stats(img: QImage, *, threshold: int = 1) -> tuple[int, tuple[int, int, int, int] | None]:
    """(cantidad de pixeles con alpha>=threshold, bbox). Bbox como (x,y,w,h) o None."""
    if img.isNull():
        return 0, None

    # Forzamos formato estable para leer bytes.
    if img.format() != QImage.Format_ARGB32_Premultiplied:
        img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)

    w = int(img.width())
    h = int(img.height())
    if w <= 0 or h <= 0:
        return 0, None

    bpl = int(img.bytesPerLine())
    nbytes = bpl * h

    # Qt6/PySide6: `QImage.bits()` puede devolver `memoryview` (sin `setsize`).
    # PyQt/PySide viejos: puede devolver un puntero con `setsize`.
    try:
        bits = img.bits()
    except Exception:
        return 0, None

    try:
        if hasattr(bits, "setsize"):
            bits.setsize(nbytes)  # type: ignore[attr-defined]
    except Exception:
        # Si el backend no permite setsize, seguimos.
        pass

    try:
        buf = bits if isinstance(bits, memoryview) else memoryview(bits)
    except Exception:
        return 0, None

    if len(buf) < nbytes:
        # fallback seguro (pero más lento): copiar a bytes
        try:
            buf = memoryview(bytes(buf))
        except Exception:
            return 0, None

    nonzero = 0
    minx = miny = 10**9
    maxx = maxy = -1

    # ARGB32 premultiplied en little-endian: BGRA (A en offset 3)
    for y in range(h):
        row = buf[y * bpl : y * bpl + (w * 4)]
        for x in range(w):
            a = row[x * 4 + 3]
            if a >= threshold:
                nonzero += 1
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y

    if nonzero <= 0 or maxx < minx or maxy < miny:
        return 0, None

    return nonzero, (int(minx), int(miny), int(maxx - minx + 1), int(maxy - miny + 1))


def _render_qtsvg_raw(svg_path: Path, *, size_px: int, render_scale: int) -> QImage:
    """Render crudo con QtSvg a un cuadrado size_px*render_scale (luego el caller escala si quiere)."""
    render_px = max(32, min(int(size_px) * int(render_scale), 1024))

    img = QImage(render_px, render_px, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)

    r = QSvgRenderer(str(svg_path.resolve()))
    if not r.isValid():
        # Imagen vacía; el caller lo reporta.
        return img

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    target = QRectF(0, 0, render_px, render_px)
    r.render(p, target)
    p.end()
    return img


def _apply_thumb_style(raw: QImage, *, render_scale: int) -> QImage:
    """Reusa el stylize del sistema de miniaturas (ThumbCache)."""
    from rcs.svg.thumbs import ThumbCache  # import local para no cargar todo si no hace falta

    tc = ThumbCache()
    # método "privado" a propósito: esto es un harness interno
    out = tc._stylize_preview_image(raw, render_scale=render_scale)  # type: ignore[attr-defined]
    return out


def _apply_canvas_style(raw: QImage, *, theme_id: str) -> QImage:
    """Reusa el stylize del canvas (hotfix anti-transparencia incluido)."""
    from rcs.ui import canvas_view as cv  # import perezoso
    return cv._stylize_preview_image(raw, theme_id=theme_id)  # type: ignore[attr-defined]


def _save(img: QImage, out_png: Path, *, size_px: int) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if not img.isNull() and int(img.width()) != int(size_px):
        img = img.scaled(int(size_px), int(size_px), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    img.save(str(out_png))


def _render_one(
    svg_path: Path,
    *,
    out_dir: Path,
    size_px: int,
    render_scale: int,
    theme_id: str,
    modes: set[str],
    bbox_tol: float,
    bbox_warn: float,
) -> tuple[list[RenderResult], dict[str, Any]]:
    results: list[RenderResult] = []

    # Notes compartidas: info geom independiente (svgelements) + viewbox QtSvg.
    render_px = max(32, min(int(size_px) * int(render_scale), 1024))
    try:
        r_meta = QSvgRenderer(str(svg_path.resolve()))
        qtsvg_viewbox = r_meta.viewBoxF()
        qtsvg_info = {
            "valid": bool(r_meta.isValid()),
            "has_viewbox": bool(not qtsvg_viewbox.isNull()),
            "viewbox": [float(qtsvg_viewbox.x()), float(qtsvg_viewbox.y()), float(qtsvg_viewbox.width()), float(qtsvg_viewbox.height())],
        }
    except Exception as e:
        qtsvg_info = {"error": f"{type(e).__name__}: {e}"}

    svgelements_info = compute_document_bbox(
        str(svg_path.resolve()),
        ppi=96.0,
        width=float(render_px),
        height=float(render_px),
        reify=True,
    )

    raw = _render_qtsvg_raw(svg_path, size_px=size_px, render_scale=render_scale)
    raw_nonzero, raw_alpha_bbox = _alpha_stats(raw, threshold=1)

    geom_bbox_xyxy = None
    geom_viewbox = None
    geom_doc_size = None
    if isinstance(svgelements_info, dict):
        geom_bbox_xyxy = svgelements_info.get("bbox")
        geom_viewbox = svgelements_info.get("viewbox")
        geom_doc_size = svgelements_info.get("doc_size")

    # Align geometry bbox into the same viewport used by QtSvg rasterization.
    # This prevents systematic scale/offset mismatches from spamming FAILs.
    aligned_geom_bbox_xyxy, geom_align = align_geom_bbox_to_qt(
        raw_alpha_bbox,
        geom_bbox_xyxy,
        render_px=int(render_px),
        qtsvg_viewbox=(qtsvg_info.get("viewbox") if isinstance(qtsvg_info, dict) and qtsvg_info.get("has_viewbox") else None),
        svge_viewbox=geom_viewbox,
        svge_doc_size=geom_doc_size,
        tol_abs_px=float(bbox_tol),
        warn_abs_px=float(bbox_warn),
    )

    geom_compare = compare_bboxes(
        raw_alpha_bbox,
        aligned_geom_bbox_xyxy,
        tol_abs_px=float(bbox_tol),
        warn_abs_px=float(bbox_warn),
    )
    geom_compare["geom_align"] = geom_align

    # Phase 2a: clasificación más útil (sin romper compat del harness).
    # - INVISIBLE_QTSVG: Qt no pinta (alpha bbox None) pero hay geometría.
    # - WARN_SMALL vs WARN_RATIO: separa "poco error" de "aspect raro".
    # - FAIL_ALIGN: ninguna alineación bajó el error lo suficiente.
    try:
        st0 = str(geom_compare.get("status", "?"))
        qt_xyxy = geom_compare.get("qt_bbox_xyxy")
        gm_xyxy = geom_compare.get("geom_bbox_xyxy")
        max_err = geom_compare.get("max_abs_err_px")

        def _wh(xyxy):
            if not (isinstance(xyxy, (list, tuple)) and len(xyxy) == 4):
                return None
            x0,y0,x1,y1 = [float(v) for v in xyxy]
            return max(0.0, x1-x0), max(0.0, y1-y0)

        if st0 == "INVISIBLE" and gm_xyxy is not None:
            geom_compare["status"] = "INVISIBLE_QTSVG"
            geom_compare.setdefault("notes", []).append("QtSvg rendered fully transparent (alpha bbox empty)")

        elif st0 == "WARN":
            wq_hq = _wh(qt_xyxy)
            wg_hg = _wh(gm_xyxy)
            ratio_kind = "WARN_SMALL"
            if wq_hq and wg_hg:
                wq,hq = wq_hq
                wg,hg = wg_hg
                rq = (wq/hq) if (hq>0) else None
                rg = (wg/hg) if (hg>0) else None
                if rq and rg and rg>0:
                    # diferencia relativa de ratio
                    rel = abs(rq-rg)/rg
                    if rel >= 0.15:
                        ratio_kind = "WARN_RATIO"
            geom_compare["status"] = ratio_kind

        elif st0 == "FAIL":
            chosen = None
            try:
                chosen = (geom_align or {}).get("chosen")
            except Exception:
                chosen = None
            if chosen in {None, "raw"}:
                geom_compare["status"] = "FAIL_ALIGN"
            else:
                # hubo alineación pero igual falló: dejamos FAIL_ALIGN para forzar repro
                geom_compare["status"] = "FAIL_ALIGN"
    except Exception:
        pass


    shared_notes = {
        "render_px": int(render_px),
        "qtsvg": qtsvg_info,
        "svgelements": svgelements_info,
        "bbox_compare": geom_compare,
    }

    meta = {
        "raw_alpha_nonzero": int(raw_nonzero),
        "raw_alpha_bbox": raw_alpha_bbox,
        "bbox_compare": geom_compare,
        "svgelements_available": bool(isinstance(svgelements_info, dict) and svgelements_info.get("available") is True),
        "normalize": {
            "doc_w": float(nv.doc_w),
            "doc_h": float(nv.doc_h),
            "viewbox": list(nv.viewbox) if nv.viewbox else None,
            "ppi": float(nv.ppi),
            "units": str(nv.units),
            "raw": nv.raw,
        },
    }

    if "raw" in modes:
        out_png = out_dir / f"{svg_path.stem}__raw_qtsvg.png"
        _save(raw, out_png, size_px=size_px)
        results.append(
            RenderResult(
                kind="raw",
                out_png=out_png,
                size_px=size_px,
                render_scale=render_scale,
                alpha_nonzero=raw_nonzero,
                alpha_bbox=raw_alpha_bbox,
                notes={
                    **shared_notes,
                    "renderer_valid": bool(raw_nonzero > 0),
                },
            )
        )

    if "thumb" in modes:
        thumb_img = _apply_thumb_style(raw, render_scale=render_scale)
        out_png = out_dir / f"{svg_path.stem}__thumb_style.png"
        _save(thumb_img, out_png, size_px=size_px)
        nonzero, bbox = _alpha_stats(thumb_img, threshold=1)
        results.append(
            RenderResult(
                kind="thumb",
                out_png=out_png,
                size_px=size_px,
                render_scale=render_scale,
                alpha_nonzero=nonzero,
                alpha_bbox=bbox,
                notes={},
            )
        )

    
    if "thumbs" in modes:
        # Render "real" thumbs usando el mismo pipeline que la UI (ThumbCache + QtSvg).
        tc = ThumbCache()
        thumbs_img = tc.render_svg_to_image(svg_path, int(size_px))
        out_png = out_dir / f"{svg_path.stem}__thumbs_cache.png"
        _save(thumbs_img, out_png, size_px=size_px)
        nonzero, bbox = _alpha_stats(thumbs_img, threshold=1)
        results.append(
            RenderResult(
                kind="thumbs",
                out_png=out_png,
                size_px=size_px,
                render_scale=1,
                alpha_nonzero=nonzero,
                alpha_bbox=bbox,
                notes={"pipeline": "ThumbCache"},
            )
        )

    if "canvas" in modes:
        canvas_img = _apply_canvas_style(raw, theme_id=theme_id)
        out_png = out_dir / f"{svg_path.stem}__canvas_style.png"
        _save(canvas_img, out_png, size_px=size_px)
        nonzero, bbox = _alpha_stats(canvas_img, threshold=1)
        results.append(
            RenderResult(
                kind="canvas",
                out_png=out_png,
                size_px=size_px,
                render_scale=render_scale,
                alpha_nonzero=nonzero,
                alpha_bbox=bbox,
                notes={"theme_id": theme_id},
            )
        )

    return results, meta


def _iter_svg_inputs(p: Path, *, recursive: bool) -> list[Path]:
    if p.is_file():
        return [p]
    if not p.exists():
        return []

    pat = "**/*.svg" if recursive else "*.svg"
    return sorted([x for x in p.glob(pat) if x.is_file()])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rcs.svg.render_debug",
        description="RCS — Harness CLI: render SVG -> PNG (raw + stylize thumb/canvas) sin UI.",
    )
    ap.add_argument("input", help="Ruta a .svg o carpeta")
    ap.add_argument("--out", default="", help="Carpeta de salida (default: ./render_debug_out junto al input)")
    ap.add_argument("--size", type=int, default=int(os.environ.get("RCS_DBG_SIZE", "256")))
    ap.add_argument("--scale", type=int, default=int(os.environ.get("RCS_DBG_RENDER_SCALE", "2")))
    ap.add_argument("--theme", default=os.environ.get("RCS_DBG_THEME", "dark"))
    ap.add_argument(
        "--modes",
        default=os.environ.get("RCS_DBG_MODES", "raw,thumb,canvas"),
        help="raw,thumb,canvas (comma-separated)",
    )
    ap.add_argument("--recursive", action="store_true", help="Si input es carpeta, busca SVG recursivo")
    ap.add_argument(
        "--bbox-tol",
        type=float,
        default=float(os.environ.get("RCS_DBG_BBOX_TOL", "3.0")),
        help="Tolerancia PASS (px) para comparar bbox Qt vs geom (default: 3.0)",
    )
    ap.add_argument(
        "--bbox-warn",
        type=float,
        default=float(os.environ.get("RCS_DBG_BBOX_WARN", "8.0")),
        help="Umbral WARN (px) para comparar bbox Qt vs geom (default: 8.0)",
    )

    ap.add_argument(
        "--bbox-report",
        default=os.environ.get("RCS_DBG_BBOX_REPORT", ""),
        help="Ruta/nombre opcional para el reporte bbox (default: _bbox_report.json en out)",
    )

    ap.add_argument(
        "--bbox-top",
        type=int,
        default=int(os.environ.get("RCS_DBG_BBOX_TOP", "25")),
        help="Top N de casos no-PASS para ranking (default: 25; 0 = todos)",
    )
    ap.add_argument(
        "--bbox-failures",
        default=os.environ.get("RCS_DBG_BBOX_FAILURES", ""),
        help="Ruta/nombre opcional para el ranking de fallas bbox (default: _bbox_failures.json en out)",
    )
    ap.add_argument(
        "--bbox-baseline",
        default=os.environ.get("RCS_DBG_BBOX_BASELINE", ""),
        help="Reporte bbox baseline para comparar regresiones (path a un _bbox_report.json previo)",
    )
    ap.add_argument(
        "--bbox-regress",
        default=os.environ.get("RCS_DBG_BBOX_REGRESS", ""),
        help="Ruta/nombre opcional para reporte de regresiones (default: _bbox_regressions.json en out)",
    )
    ap.add_argument(
        "--bbox-baseline-update",
        action="store_true",
        help="Si se pasa --bbox-baseline, sobrescribe baseline con el reporte actual al finalizar",
    )
    ap.add_argument(
        "--bbox-include-no-geom",
        action="store_true",
        help="Incluye NO_GEOM en ranking (por defecto se excluye)",
    )

    ap.add_argument(
        "--sleep",
        type=float,
        default=float(os.environ.get("RCS_DBG_SLEEP", "0")),
        help="Delay opcional entre renders (para ver progreso)",
    )
    args = ap.parse_args(argv)

    inp = Path(args.input).expanduser()
    svg_files = _iter_svg_inputs(inp, recursive=bool(args.recursive))
    if not svg_files:
        print(f"[RCS] No se encontraron SVG en: {inp}")
        return 2

    out_dir = Path(args.out).expanduser() if args.out else (
        inp.parent / "render_debug_out" if inp.is_file() else (inp / "render_debug_out")
    )
    modes = {m.strip().lower() for m in str(args.modes).split(",") if m.strip()}
    modes = modes.intersection({"raw", "thumb", "canvas"}) or {"raw", "thumb", "canvas"}

    _ensure_qt_app()

    summary: dict[str, Any] = {
        "tool": "rcs.svg.render_debug",
        "when": datetime.datetime.now().isoformat(timespec="seconds"),
        "input": str(inp),
        "count": len(svg_files),
        "size_px": int(args.size),
        "render_scale": int(args.scale),
        "theme_id": str(args.theme),
        "modes": sorted(modes),
        "bbox_compare": {
            "tol_abs_px": float(args.bbox_tol),
            "warn_abs_px": float(args.bbox_warn),
            "report": "",
            "stats": {},
        },
        "items": [],
    }

    bbox_stats = {"PASS": 0, "WARN": 0, "FAIL": 0, "NO_GEOM": 0, "INVISIBLE": 0}
    bbox_report: list[dict[str, Any]] = []

    # Ayuda a detectar rápidamente si el usuario está ejecutando un módulo duplicado
    # (por ejemplo, si se extrajo un ZIP con raíz `RCS/` dentro de `C:\PROYECTOS\RCS`).
    try:
        from rcs.core.version import APP_VERSION
        v = APP_VERSION
    except Exception:
        v = "?"
    print(f"[RCS] render_debug.py: {Path(__file__).resolve()}  (RCS {v})")
    print(f"[RCS] Render debug: {len(svg_files)} SVG → {out_dir}")
    print(f"[RCS] BBox diff: tol={float(args.bbox_tol):g}px warn={float(args.bbox_warn):g}px")

    for i, svg in enumerate(svg_files, 1):
        print(f"  [{i:03d}/{len(svg_files):03d}] {svg.name}")
        try:
            results, meta = _render_one(
                svg,
                out_dir=out_dir,
                size_px=int(args.size),
                render_scale=int(args.scale),
                theme_id=str(args.theme),
                modes=modes,
                bbox_tol=float(args.bbox_tol),
                bbox_warn=float(args.bbox_warn),
            )

            geom_compare = meta.get("bbox_compare") or {}
            st = str(geom_compare.get("status", "?"))
            if st in bbox_stats:
                bbox_stats[st] += 1
            bbox_report.append(
                {
                    "svg": str(svg),
                    "status": st,
                    "max_abs_err_px": geom_compare.get("max_abs_err_px"),
                    "qt_bbox_xyxy": geom_compare.get("qt_bbox_xyxy"),
                    "geom_bbox_xyxy": geom_compare.get("geom_bbox_xyxy"),
                    "diff": geom_compare.get("diff"),
                    "notes": geom_compare.get("notes"),
                    "geom_align": geom_compare.get("geom_align"),
                }
            )
            align_kind = None
            try:
                align_kind = (geom_compare.get('geom_align') or {}).get('chosen')
            except Exception:
                align_kind = None
            if align_kind and align_kind != 'raw':
                print(f"    bbox: {st}  err={geom_compare.get('max_abs_err_px')}  align={align_kind}")
            else:
                print(f"    bbox: {st}  err={geom_compare.get('max_abs_err_px')}")

            item = {
                "svg": str(svg),
                "meta": meta,
                "results": [
                    {
                        "kind": r.kind,
                        "png": str(r.out_png),
                        "alpha_nonzero": r.alpha_nonzero,
                        "alpha_bbox": r.alpha_bbox,
                        "notes": r.notes,
                    }
                    for r in results
                ],
            }
            summary["items"].append(item)
        except Exception as e:
            summary["items"].append({"svg": str(svg), "error": repr(e)})
            print(f"    ! ERROR: {e!r}")
        if args.sleep > 0:
            time.sleep(float(args.sleep))

    out_dir.mkdir(parents=True, exist_ok=True)
    # Reporte bbox
    if args.bbox_report:
        rp = Path(str(args.bbox_report)).expanduser()
        bbox_report_path = (out_dir / rp) if not rp.is_absolute() else rp
    else:
        bbox_report_path = out_dir / "_bbox_report.json"
    bbox_report_path.write_text(json.dumps(bbox_report, indent=2, ensure_ascii=False), encoding="utf-8")

    summary["bbox_compare"]["report"] = str(bbox_report_path)
    summary["bbox_compare"]["stats"] = bbox_stats

    # ------------------------------------------------------------
    # Ranking de casos no-PASS + comandos de repro
    # ------------------------------------------------------------
    try:
        top_n = int(args.bbox_top)
    except Exception:
        top_n = 25
    limit = None if top_n == 0 else max(1, top_n)
    ranked = rank_items(bbox_report, include_no_geom=bool(args.bbox_include_no_geom), limit=limit)

    for it in ranked:
        try:
            it["repro"] = build_repro_cmd(
                str(it.get("svg") or ""),
                out_dir=str(out_dir),
                modes=sorted(modes),
                size_px=int(args.size),
                render_scale=float(args.scale),
                bbox_tol=float(args.bbox_tol),
                bbox_warn=float(args.bbox_warn),
                recursive=bool(args.recursive),
            )
        except Exception:
            it["repro"] = None

    if args.bbox_failures:
        fp = Path(str(args.bbox_failures)).expanduser()
        failures_path = (out_dir / fp) if not fp.is_absolute() else fp
    else:
        failures_path = out_dir / "_bbox_failures.json"
    failures_path.write_text(json.dumps(ranked, indent=2, ensure_ascii=False), encoding="utf-8")
    summary["bbox_compare"]["failures_report"] = str(failures_path)

    # ------------------------------------------------------------
    # Baseline compare (regressions)
    # ------------------------------------------------------------
    regress_path = None
    if args.bbox_baseline:
        try:
            bp = Path(str(args.bbox_baseline)).expanduser()
            baseline_path = bp
            baseline_items = load_bbox_report(baseline_path)
            reg = compare_reports(baseline_items=baseline_items, current_items=bbox_report)

            # Add repro cmd for regression entries (current svg)
            for r in reg.get("regressions", []) or []:
                try:
                    svg_path = str(r.get("svg") or "")
                    r["repro"] = build_repro_cmd(
                        svg_path,
                        out_dir=str(out_dir),
                        modes=sorted(modes),
                        size_px=int(args.size),
                        render_scale=float(args.scale),
                        bbox_tol=float(args.bbox_tol),
                        bbox_warn=float(args.bbox_warn),
                        recursive=bool(args.recursive),
                    )
                except Exception:
                    r["repro"] = None

            if args.bbox_regress:
                rp = Path(str(args.bbox_regress)).expanduser()
                regress_path = (out_dir / rp) if not rp.is_absolute() else rp
            else:
                regress_path = out_dir / "_bbox_regressions.json"

            regress_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
            summary["bbox_compare"]["baseline"] = str(baseline_path)
            summary["bbox_compare"]["regressions_report"] = str(regress_path)

            c = reg.get("counts") or {}
            print(f"[RCS] Baseline compare: regressions={c.get('regressions')} improvements={c.get('improvements')} unchanged={c.get('unchanged')} new={c.get('new')} missing={c.get('missing')}")

            if bool(args.bbox_baseline_update):
                try:
                    # Overwrite baseline with current report (explicit opt-in)
                    baseline_path.write_text(
                        bbox_report_path.read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                    print(f"[RCS] Baseline actualizado: {baseline_path}")
                except Exception as e:
                    print(f"[RCS] ! No se pudo actualizar baseline: {e!r}")
        except Exception as e:
            print(f"[RCS] ! Baseline compare falló: {e!r}")

    summary_path = out_dir / "_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[RCS] OK — bbox_report: {bbox_report_path}")
    print(f"[RCS] OK — summary: {summary_path}")
    print(f"[RCS] BBox stats: {bbox_stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())