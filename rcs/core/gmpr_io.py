# File: rcs/core/gmpr_io.py
# Project: RusticCreadorSvg (RCS)
# Purpose: I/O para proyectos GMPR (bundle slicer: SVG base embebido + rasters embebidos).
# Notes:
# - Mantiene la estructura intacta (GMPR puede contener datos extra para el slicer).
# - Se limita a:
#   - Decodificar SVG base embebido (para preview base en CanvasView)
#   - Decodificar PNGs base64 de rasters (para instanciar items)
#   - Actualizar transforms de rasters al guardar

from __future__ import annotations

import base64
import gzip
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from rcs.core.models import Project, SceneObject, Transform
from rcs.geom.svg_viewport_normalize import CSS_PPI, normalize_svg_viewport



# Base scaling usado por CanvasView para rasters (mm por pixel a 96dpi).
RCS_MM_PER_PX = 25.4 / 96.0


def _infer_canvas_mm_from_gmpr(bundle: dict[str, Any], svg_path: Path | None) -> tuple[float, float] | None:
    """Infere tamaño del canvas (mm) al importar GMPR.

    Motivación: en GMPR los transforms (x,y) suelen estar en mm respecto al SVG base. Si el
    Project queda con un canvas_mm default, el origen del canvas en escena cambia y el raster
    aparece "en cualquier lado".

    Prioridad:
      1) Campos explícitos en el bundle (si existen).
      2) Fallback: derivar desde el SVG embebido (ancho/alto) usando el contrato canonical
         `normalize_svg_viewport()`.
    """
    # 1) Campos explícitos (si Rustic los incluye en tu build).
    candidates: list[tuple[Any, Any]] = []
    try:
        cm = bundle.get("canvas_mm")
        if isinstance(cm, (list, tuple)) and len(cm) >= 2:
            candidates.append((cm[0], cm[1]))
    except Exception:
        pass

    for key in ("project", "doc", "meta", "settings"):
        d = bundle.get(key)
        if not isinstance(d, dict):
            continue
        cm = d.get("canvas_mm")
        if isinstance(cm, (list, tuple)) and len(cm) >= 2:
            candidates.append((cm[0], cm[1]))
        # variantes comunes
        if "w_mm" in d and "h_mm" in d:
            candidates.append((d.get("w_mm"), d.get("h_mm")))
        if "width_mm" in d and "height_mm" in d:
            candidates.append((d.get("width_mm"), d.get("height_mm")))

    for w_raw, h_raw in candidates:
        w = _f(w_raw, 0.0)
        h = _f(h_raw, 0.0)
        if w > 1e-6 and h > 1e-6:
            return float(w), float(h)

    # 2) Fallback: SVG embebido.
    if svg_path and svg_path.exists():
        try:
            nv = normalize_svg_viewport(svg_path)
            if nv.doc_w > 0 and nv.doc_h > 0:
                # doc_w/doc_h están en px CSS (96dpi). Convertimos a mm con el mismo baseline.
                w_mm = float(nv.doc_w) * 25.4 / float(CSS_PPI)
                h_mm = float(nv.doc_h) * 25.4 / float(CSS_PPI)
                if w_mm > 1e-6 and h_mm > 1e-6:
                    return float(w_mm), float(h_mm)
        except Exception:
            pass

    return None


def _f(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _gmpr_rot_deg(t: Dict[str, Any]) -> float:
    if "rot" in t:
        return _f(t.get("rot"), 0.0)
    return _f(t.get("rot_deg"), 0.0)


def _gmpr_raster_transform_to_rcs_transform(
    t: dict[str, Any],
    vb_x: float = 0.0,
    vb_y: float = 0.0,
    mm_per_u_x: float = 1.0,
    mm_per_u_y: float = 1.0,
    abs_mm_per_px_x: float | None = None,
    abs_mm_per_px_y: float | None = None,
) -> Transform:
    """Convertir transform de GMPR (raster) a Transform de RCS.

    Observación clave (por archivos reales de GMPR):
    - x/y ya vienen en **mm** del canvas (no en unidades de viewBox).
    - sx/sy son **factores de escala adimensionales** (multiplican el scale base
      mm_per_px que usa RCS para mostrar rasters). Campo legacy: s (uniforme).

    Por compatibilidad, esta función conserva parámetros legacy (vb/mm_per_u/abs_mm_per_px),
    pero la conversión efectiva prioriza la convención anterior.
    """
    # Posición (mm en canvas)
    try:
        x_mm = float(t.get("x", 0.0) or 0.0)
    except Exception:
        x_mm = 0.0
    try:
        y_mm = float(t.get("y", 0.0) or 0.0)
    except Exception:
        y_mm = 0.0

    # Escala (factor adimensional sobre el scale base mm_per_px)
    try:
        s = float(t.get("s", 1.0) or 1.0)
    except Exception:
        s = 1.0
    try:
        sx = float(t.get("sx", 1.0) or 1.0)
    except Exception:
        sx = 1.0
    try:
        sy = float(t.get("sy", 1.0) or 1.0)
    except Exception:
        sy = 1.0

    scale_x = sx * s
    scale_y = sy * s

    # Rotación (grados)
    try:
        rot_deg = float(t.get("rot_deg", t.get("rot", 0.0)) or 0.0)
    except Exception:
        rot_deg = 0.0

    flip_x = bool(t.get("flip_h", False))
    flip_y = bool(t.get("flip_v", False))

    try:
        opacity = float(t.get("opacity", 1.0) or 1.0)
    except Exception:
        opacity = 1.0
    opacity = max(0.0, min(1.0, opacity))

    lock_aspect = bool(t.get("lock_aspect", True))

    return Transform(
        x=x_mm,
        y=y_mm,
        scale_x=scale_x,
        scale_y=scale_y,
        rotation_deg=rot_deg,
        flip_x=flip_x,
        flip_y=flip_y,
        opacity=opacity,
        lock_aspect=lock_aspect,
    )

def _update_gmpr_raster_transform_dict(dst: dict[str, Any], tr: Transform) -> None:
    """Actualizar in-place el dict de transform (GMPR) con valores desde Transform (RCS).

    Convención:
    - Guardamos x/y en mm.
    - Guardamos sx/sy como factores adimensionales (o s si el dict original no tenía sx/sy).
    """
    dst["x"] = float(tr.x)
    dst["y"] = float(tr.y)

    # Mantener el "formato" original si es posible
    has_sx_sy = ("sx" in dst) or ("sy" in dst)
    has_s = ("s" in dst)

    sx = float(tr.scale_x)
    sy = float(tr.scale_y)

    if has_sx_sy or not has_s:
        # Preferimos sx/sy (y neutralizamos s si existía)
        dst["sx"] = sx
        dst["sy"] = sy
        if has_s:
            dst["s"] = 1.0
    else:
        # Solo 's' legacy (uniforme)
        if tr.lock_aspect:
            dst["s"] = sx
        else:
            dst["s"] = (sx + sy) * 0.5

    dst["rot_deg"] = float(tr.rotation_deg)
    dst["flip_h"] = bool(tr.flip_x)
    dst["flip_v"] = bool(tr.flip_y)
    dst["opacity"] = max(0.0, min(1.0, float(tr.opacity)))

    if "lock_aspect" in dst:
        dst["lock_aspect"] = bool(tr.lock_aspect)

def load_gmpr_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("GMPR inválido: raíz no es objeto JSON")
    return data


def _maybe_gzip_decompress(b: bytes) -> bytes:
    try:
        return gzip.decompress(b)
    except Exception:
        return b


def extract_svg_bytes(bundle: dict[str, Any]) -> bytes | None:
    """Extrae el SVG base desde un bundle GMPR.

    Soporta (al menos):
    - bundle["svg_embedded"] = {"encoding": "gzip+base64"|"base64", "data": "..."}
    - bundle["svg"] = {"svg_base64": "...", "embedded": true, "encoding": ...}

    Devuelve bytes (UTF-8) o None si no está embebido.
    """
    svg_emb = bundle.get("svg_embedded")
    if isinstance(svg_emb, dict):
        enc = str(svg_emb.get("encoding") or "").lower()
        b64 = svg_emb.get("data")
        if isinstance(b64, str) and b64.strip():
            raw = base64.b64decode(b64)
            if "gzip" in enc:
                raw = _maybe_gzip_decompress(raw)
            return raw

    svg = bundle.get("svg")
    if isinstance(svg, dict):
        b64 = svg.get("svg_base64") or svg.get("data")
        if isinstance(b64, str) and b64.strip():
            raw = base64.b64decode(b64)
            enc = str(svg.get("encoding") or "").lower()
            if "gzip" in enc:
                raw = _maybe_gzip_decompress(raw)
            else:
                # heurística: algunos guardan gzip sin declarar
                raw = _maybe_gzip_decompress(raw)
            return raw

    # referencia externa (no embebido)
    return None


def materialize_svg_to_temp(svg_bytes: bytes, *, prefix: str = "rcs_gmpr_") -> Path:
    """Escribe el SVG embebido a un archivo temporal y devuelve la ruta.

    Nota: se usa para el preview base (QSvgRenderer suele necesitar path).
    """
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=".svg")
    p = Path(path)
    try:
        p.write_bytes(svg_bytes)
    finally:
        try:
            # cerramos el fd (en Windows es crítico)
            import os

            os.close(fd)
        except Exception:
            pass
    return p


def _decode_png_b64(b64: str) -> bytes:
    return base64.b64decode(b64)


def _gmpr_uid(obj: dict[str, Any]) -> str | None:
    for k in ("uid", "id", "object_id"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _iter_gmpr_raster_objects(bundle: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Itera rasters declarados directamente en objects[].

    Yields: (uid, raster_meta, obj_dict)
    """
    objs = bundle.get("objects")
    if not isinstance(objs, list):
        return
    for o in objs:
        if not isinstance(o, dict):
            continue
        if str(o.get("custom_kind") or "").lower() == "raster":
            uid = _gmpr_uid(o)
            if not uid:
                continue
            rm = o.get("raster_meta")
            if isinstance(rm, dict):
                yield uid, rm, o


def _iter_custom_by_uid_rasters(bundle: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    """Itera rasters en custom_by_uid{uid: payload} (variante alternativa)."""
    cb = bundle.get("custom_by_uid")
    if not isinstance(cb, dict):
        return
    for uid, payload in cb.items():
        if not (isinstance(uid, str) and uid.strip()):
            continue
        if not isinstance(payload, dict):
            continue
        ck = str(payload.get("custom_kind") or "").lower()
        if ck != "raster":
            continue
        # El raster meta puede venir con varios nombres.
        rm = payload.get("raster_meta")
        if isinstance(rm, dict):
            yield uid, rm


def gmpr_to_project(bundle: dict[str, Any], *, gmpr_path: str | Path) -> Project:
    """Convierte un bundle GMPR a Project (runtime) + caches necesarios."""
    prj = Project()
    prj.set_file_path(gmpr_path)
    prj.gmpr_bundle = bundle

    # SVG base (si está embebido)
    svg_bytes = extract_svg_bytes(bundle)
    if svg_bytes:
        prj.gmpr_svg_tmp_path = materialize_svg_to_temp(svg_bytes)

        tmp_svg = prj.gmpr_svg_tmp_path

        # Métricas SVG -> mm (para convertir coordenadas del viewBox a mm).
        vb_x = 0.0
        vb_y = 0.0
        mm_per_u_x: float | None = None
        mm_per_u_y: float | None = None
        try:
            vp = normalize_svg_viewport(Path(tmp_svg)) if tmp_svg else None
            if vp and vp.doc_w > 0 and vp.doc_h > 0:
                svg_w_mm = float(vp.doc_w) * 25.4 / float(vp.ppi or CSS_PPI)
                svg_h_mm = float(vp.doc_h) * 25.4 / float(vp.ppi or CSS_PPI)
                if vp.viewbox is not None:
                    vb_x, vb_y, vb_w, vb_h = vp.viewbox
                else:
                    vb_x, vb_y, vb_w, vb_h = 0.0, 0.0, float(vp.doc_w), float(vp.doc_h)
                if vb_w and vb_h:
                    mm_per_u_x = svg_w_mm / float(vb_w)
                    mm_per_u_y = svg_h_mm / float(vb_h)
        except Exception:
            pass

    # Canvas sizing (crítico para que x/y en mm caigan donde corresponden)
    canvas_mm = _infer_canvas_mm_from_gmpr(bundle, getattr(prj, "gmpr_svg_tmp_path", None))
    if canvas_mm:
        try:
            prj.set_canvas_mm(float(canvas_mm[0]), float(canvas_mm[1]))
        except Exception:
            pass

    # Rasters
    raster_png_by_uid: dict[str, bytes] = {}
    objects: list[SceneObject] = []

    # Variante A: raster definido dentro de objects[] (como en Rustic Creator actual)
    #   objects[].custom_kind="raster" y objects[].raster_meta.png_base64
    idx = 0
    for uid, raster_meta, o in _iter_gmpr_raster_objects(bundle):
        idx += 1
        png_b64 = raster_meta.get("png_base64") or o.get("png_base64")
        if isinstance(png_b64, str) and png_b64.strip():
            try:
                raster_png_by_uid[uid] = _decode_png_b64(png_b64)
            except Exception:
                # Si el PNG está corrupto no tiramos abajo el proyecto.
                raster_png_by_uid[uid] = b""

        t = raster_meta.get("transform")
        if not isinstance(t, dict):
            t = {}
        tr = _gmpr_raster_transform_to_rcs_transform(t)

        z = int(o.get("z", idx))

        objects.append(
            SceneObject(
                id=uid,
                type="raster",  # type: ignore[arg-type]
                source=None,
                transform=tr,
                z=z,
            )
        )

    # Variante B: custom_by_uid (si existe). Solo crea objetos para los uid que
    # estén declarados en objects[] o (fallback) si no hay objects[] o están vacíos.
    # NOTA: No intentamos reconstruir vectores acá.
    declared_uids = {o.id for o in objects}
    for uid, raster_meta in _iter_custom_by_uid_rasters(bundle):
        if uid in declared_uids:
            continue
        png_b64 = raster_meta.get("png_base64")
        if isinstance(png_b64, str) and png_b64.strip():
            try:
                raster_png_by_uid[uid] = _decode_png_b64(png_b64)
            except Exception:
                raster_png_by_uid[uid] = b""

        t = raster_meta.get("transform")
        if not isinstance(t, dict):
            t = {}
        tr = _gmpr_raster_transform_to_rcs_transform(t)

        objects.append(
            SceneObject(
                id=uid,
                type="raster",  # type: ignore[arg-type]
                source=None,
                transform=tr,
                z=prj.next_z(),
            )
        )

    prj.objects = objects
    prj.gmpr_raster_png_by_uid = raster_png_by_uid
    prj.clear_dirty()
    return prj


def _now_iso() -> str:
    # sin timezone para mantener compat simple
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _backup_file(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak_{ts}")
    shutil.copy2(path, bak)


def _gmpr_raster_transform_dict(container: dict[str, Any]) -> dict[str, Any] | None:
    """Devuelve (y crea si falta) el dict `raster_meta.transform` para un raster GMPR.

    Punto único para acceder al dict de transform. La conversión RCS<->GMPR vive en:
      - _gmpr_raster_transform_to_rcs_transform()
      - _update_gmpr_raster_transform_dict()
    """
    rm = container.get("raster_meta")
    if not isinstance(rm, dict):
        return None
    tr = rm.get("transform")
    if not isinstance(tr, dict):
        tr = {}
        rm["transform"] = tr
    return tr


def update_gmpr_bundle_from_project(bundle: dict[str, Any], project: Project) -> dict[str, Any]:
    """Actualiza (IN PLACE) transforms de rasters y metadata simple.

    IMPORTANTE: no reordena ni borra claves. Solo actualiza campos de transform.
    """
    # timestamp
    if "saved_at" in bundle:
        bundle["saved_at"] = _now_iso()
    elif "project" in bundle and isinstance(bundle.get("project"), dict):
        pr = bundle["project"]
        if "modified" in pr:
            pr["modified"] = _now_iso()

    # objects[] direct
    objs = bundle.get("objects")
    if isinstance(objs, list):
        by_uid: dict[str, dict[str, Any]] = {}
        for o in objs:
            if isinstance(o, dict):
                uid = _gmpr_uid(o)
                if uid:
                    by_uid[uid] = o

        for so in project.objects:
            if so.type != "raster":
                continue
            o = by_uid.get(so.id)
            if o and str(o.get("custom_kind") or "").lower() == "raster":
                trd = _gmpr_raster_transform_dict(o)
                if trd is not None:
                    _update_gmpr_raster_transform_dict(trd, so.transform)

    # custom_by_uid variant
    cb = bundle.get("custom_by_uid")
    if isinstance(cb, dict):
        for so in project.objects:
            if so.type != "raster":
                continue
            payload = cb.get(so.id)
            if isinstance(payload, dict) and str(payload.get("custom_kind") or "").lower() == "raster":
                trd = _gmpr_raster_transform_dict(payload)
                if trd is not None:
                    _update_gmpr_raster_transform_dict(trd, so.transform)

    return bundle


def save_gmpr_project(project: Project, path: str | Path, *, make_backup: bool = True) -> Path:
    """Guarda el Project actual en GMPR.

    Requiere que project.gmpr_bundle exista (bundle original cargado).
    """
    if not isinstance(project.gmpr_bundle, dict):
        raise ValueError("Proyecto no tiene gmpr_bundle cargado (no se puede guardar)")

    p = Path(path)
    if make_backup:
        _backup_file(p)

    bundle = project.gmpr_bundle
    update_gmpr_bundle_from_project(bundle, project)

    # Escribimos JSON con indent legible, sin modificar más.
    txt = json.dumps(bundle, ensure_ascii=False, indent=2)
    p.write_text(txt, encoding="utf-8")

    project.set_file_path(p)
    project.clear_dirty()
    return p


def cleanup_gmpr_temp(project: Project) -> None:
    """Borra el SVG temporal si existe."""
    p = project.gmpr_svg_tmp_path
    if p and isinstance(p, Path) and p.exists():
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
    project.gmpr_svg_tmp_path = None
