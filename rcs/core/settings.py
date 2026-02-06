# File: rcs/core/settings.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.0
# Status: wip
# Date: 2026-01-16
# Purpose: Persistencia de preferencias de usuario (JSON): tema, preview de trazos, etc.
# Notes: No depende de Qt; guarda en ~\\.rcs\\settings.json (Windows/Linux/mac).
from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from rcs.core.tool_mode import ToolMode, coerce_tool_mode

log = logging.getLogger(__name__)


def settings_dir() -> Path:
    """Carpeta de settings del usuario.

    Elegimos una ruta simple y explícita (no Qt) para evitar sorpresas en Windows.
    """
    return Path.home() / ".rcs"


def settings_path() -> Path:
    return settings_dir() / "settings.json"


# ------------------------------
# Project settings (repo-local)
# ------------------------------
# Permite defaults reproducibles por proyecto (no por usuario) sin tocar el código.
# Archivo esperado: rcs_settings.json en la raíz del repo/proyecto (o en un padre del CWD).
PROJECT_SETTINGS_FILENAME = "rcs_settings.json"


def find_project_settings_path(start: Path | None = None) -> Path | None:
    """Busca rcs_settings.json subiendo desde start (o CWD).

    Objetivo: que funcione en Windows cuando corrés desde C:\\PROYECTOS\\RCS
    y también desde subcarpetas.
    """
    start = (start or Path.cwd()).resolve()
    for p in (start, *start.parents):
        candidate = p / PROJECT_SETTINGS_FILENAME
        if candidate.is_file():
            return candidate
    return None


# [RCS-KEEP] Helpers para leer/escribir rcs_settings.json (repo-local).
# Usado por UI para persistir defaults sin tocar settings del usuario (~/.rcs).

def load_project_settings(start: Path | None = None, *, logger: logging.Logger | None = None) -> Dict[str, Any]:
    """Carga el JSON de project settings. Devuelve {} si no existe o es inválido."""
    _log = logger or log
    p = find_project_settings_path(start)
    if not p:
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        _log.warning("No se pudo leer %s: %s", p, e)
        return {}


def save_project_settings(data: Dict[str, Any], start: Path | None = None, *, logger: logging.Logger | None = None) -> Path | None:
    """Guarda project settings en rcs_settings.json.

    - Si se encuentra un archivo existente, lo pisa.
    - Si no existe, lo crea en el CWD (útil en setups nuevos).

    Devuelve el Path guardado o None si falla.
    """
    _log = logger or log
    p = find_project_settings_path(start)
    if not p:
        p = (start or Path.cwd()).resolve() / PROJECT_SETTINGS_FILENAME
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        # Mantener un formato simple y legible (sin sort_keys para no reordenar a lo loco).
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return p
    except Exception as e:
        _log.warning("No se pudo guardar %s: %s", p, e)
        return None


def _deep_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def apply_project_settings(*, logger: logging.Logger | None = None, prefer_env: bool = True) -> Dict[str, Any]:
    """Carga rcs_settings.json (si existe) y aplica overrides vía variables de entorno.

    Motivo: mantenemos el resto del código desacoplado de este módulo.
    Los consumidores (thumbs / preview_style / render_debug / canvas) ya leen env vars.

    - Si `prefer_env=True`, una env var ya seteada NO se pisa (ganan los overrides manuales).
    - Si `prefer_env=False`, el JSON pisa la env var.

    Devuelve un dict con los valores *aplicados desde JSON* (útil para logging/debug).
    """
    _log = logger or log
    p = find_project_settings_path()
    if not p:
        return {}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning("No se pudo leer %s: %s", p, e)
        return {}

    applied: Dict[str, Any] = {}

    def _set_env(key: str, value: Any) -> None:
        if prefer_env and os.environ.get(key):
            return
        os.environ[key] = str(value)

    # Thumbnails (biblioteca)
    thumb_size = _deep_get(data, "preview.thumbs.size_px")
    if isinstance(thumb_size, int) and 16 <= thumb_size <= 512:
        applied["preview.thumbs.size_px"] = thumb_size
        _set_env("RCS_THUMB_SIZE", thumb_size)

    thumb_scale = _deep_get(data, "preview.thumbs.render_scale")
    if isinstance(thumb_scale, int) and 1 <= thumb_scale <= 8:
        applied["preview.thumbs.render_scale"] = thumb_scale
        _set_env("RCS_THUMB_RENDER_SCALE", thumb_scale)

    thumb_stroke = _deep_get(data, "preview.thumbs.stroke_thick")
    if isinstance(thumb_stroke, int) and 0 <= thumb_stroke <= 32:
        applied["preview.thumbs.stroke_thick"] = thumb_stroke
        _set_env("RCS_THUMB_STROKE_THICK", thumb_stroke)

    thumb_outline = _deep_get(data, "preview.thumbs.outline_thick")
    if isinstance(thumb_outline, int) and 0 <= thumb_outline <= 32:
        applied["preview.thumbs.outline_thick"] = thumb_outline
        _set_env("RCS_THUMB_OUTLINE_THICK", thumb_outline)

    thumb_theme = _deep_get(data, "preview.thumbs.theme")
    if isinstance(thumb_theme, str):
        thumb_theme = thumb_theme.strip().lower()
        if thumb_theme in ("dark", "light"):
            applied["preview.thumbs.theme"] = thumb_theme
            _set_env("RCS_THUMB_THEME", thumb_theme)

    # Toolbar style
    tb_style = _deep_get(data, "ui.toolbar.style")
    if isinstance(tb_style, str):
        tb_style = tb_style.strip().lower()
        if tb_style in ("icons", "text", "text_only", "icons_only", "mixed"):
            applied["ui.toolbar.style"] = tb_style
            _set_env("RCS_TOOLBAR_STYLE", tb_style)

    # Canvas - zoom after initial fit (1.0 = como siempre)
    zf = _deep_get(data, "ui.canvas.zoom_after_fit")
    if isinstance(zf, (int, float)):
        zf = float(zf)
        if 0.05 <= zf <= 20.0:
            applied["ui.canvas.zoom_after_fit"] = zf
            _set_env("RCS_CANVAS_START_ZOOM", zf)

    # Canvas - anchor inicial (para ubicar el "punto 0" al abrir)
    anchor = _deep_get(data, "ui.canvas.start_anchor")
    if isinstance(anchor, str):
        anchor = anchor.strip().lower()
        # Valores soportados: sheet_center | sheet_origin | canvas_origin | canvas_center
        if anchor in (
            "sheet_center",
            "sheet_origin",
            "canvas_origin",
            "canvas_center",
            # aliases
            "origin",
            "canvas0",
            "0",
            "center",
        ):
            applied["ui.canvas.start_anchor"] = anchor
            _set_env("RCS_CANVAS_START_ANCHOR", anchor)

    # Canvas - tamaño por defecto (mm) para proyectos nuevos (y para el diálogo F10)
    default_mm = _deep_get(data, "ui.canvas.default_canvas_mm")
    if isinstance(default_mm, (list, tuple)) and len(default_mm) == 2:
        try:
            w_mm = float(default_mm[0]); h_mm = float(default_mm[1])
        except Exception:
            w_mm = h_mm = None
        if w_mm and h_mm and 1.0 <= w_mm <= 5000.0 and 1.0 <= h_mm <= 5000.0:
            applied["ui.canvas.default_canvas_mm"] = [w_mm, h_mm]
            _set_env("RCS_CANVAS_DEFAULT_W_MM", w_mm)
            _set_env("RCS_CANVAS_DEFAULT_H_MM", h_mm)

    # Canvas - vista inicial explícita (centro + zoom). Si está, gana sobre anchor/zoom_after_fit.
    start_view = _deep_get(data, "ui.canvas.start_view")
    if isinstance(start_view, dict):
        center = start_view.get("center_canvas") or start_view.get("center_mm")
        zoom = start_view.get("zoom")
        if isinstance(center, (list, tuple)) and len(center) == 2 and isinstance(zoom, (int, float)):
            try:
                cx = float(center[0]); cy = float(center[1]); z = float(zoom)
            except Exception:
                cx = cy = z = None
            if cx is not None and cy is not None and z is not None:
                applied["ui.canvas.start_view"] = {"center_canvas": [cx, cy], "zoom": z}
                _set_env("RCS_CANVAS_START_VIEW", f"{cx},{cy},{z}")
    elif isinstance(start_view, str):
        s = start_view.strip()
        if s:
            applied["ui.canvas.start_view"] = s
            _set_env("RCS_CANVAS_START_VIEW", s)

    # Canvas - factor de rango de zoom (1.0 = default). Afecta min y max.
    zr = _deep_get(data, "ui.canvas.zoom_range")
    if isinstance(zr, (int, float)):
        zr = float(zr)
        if 0.25 <= zr <= 4.0:
            applied["ui.canvas.zoom_range"] = zr
            _set_env("RCS_CANVAS_ZOOM_RANGE", zr)

    # Canvas - scrollbars (h/v). Admitimos bool legacy (scroll_h/scroll_v)
    # y el modo nuevo por política: scroll_h_policy / scroll_v_policy en {off, needed, on}.

    def _norm_pol(v):
        if not isinstance(v, str):
            return None
        v = v.strip().lower()
        return v if v in ("off", "needed", "on") else None

    pol_h = _norm_pol(_deep_get(data, "ui.canvas.scroll_h_policy"))
    pol_v = _norm_pol(_deep_get(data, "ui.canvas.scroll_v_policy"))

    # Fallback legacy bool -> needed/off
    sh = _deep_get(data, "ui.canvas.scroll_h") if pol_h is None else None
    sv = _deep_get(data, "ui.canvas.scroll_v") if pol_v is None else None

    if pol_h is None and isinstance(sh, bool):
        pol_h = "needed" if sh else "off"
        applied["ui.canvas.scroll_h"] = sh
    if pol_v is None and isinstance(sv, bool):
        pol_v = "needed" if sv else "off"
        applied["ui.canvas.scroll_v"] = sv

    if pol_h is not None:
        applied["ui.canvas.scroll_h_policy"] = pol_h
        _set_env("RCS_CANVAS_SCROLL_H", pol_h)
    if pol_v is not None:
        applied["ui.canvas.scroll_v_policy"] = pol_v
        _set_env("RCS_CANVAS_SCROLL_V", pol_v)


    if applied:
        _log.info("Project settings aplicados desde %s: %s", p, applied)
    return applied



# Temas válidos para el lienzo (CanvasView). Mantener en sync con CanvasView.THEME_PRESETS.
VALID_CANVAS_THEMES = ("dark", "mid", "light")

VALID_TOOLBAR_STYLES = (
    "icon_only",
    "text_only",
    "text_beside_icon",
    "text_under_icon",
)


@dataclass
class AppSettings:
    """Preferencias persistentes del usuario."""

    canvas_theme: str = "dark"

    # Preview en el lienzo (solo visual). Valores en "px" antes del zoom.
    canvas_stroke_thick: int = 2
    canvas_outline_thick: int = 1

    # Miniaturas en biblioteca (solo visual).
    thumb_stroke_thick: int = 2
    thumb_outline_thick: int = 1

    # Toolbar: estilo de botones (solo UI).
    # Valores: icon_only | text_only | text_beside_icon | text_under_icon
    toolbar_style: str = 'text_only'

    # Tooling (no afecta al .RCS)
    tool_mode: ToolMode = ToolMode.SELECT

    # ------------------------------
    # UI (Qt) — persistencia de layout
    # ------------------------------
    # Se guardan como base64 (bytes->str) para evitar dependencia fuerte a Qt.
    ui_main_geometry_b64: str = ""
    ui_main_state_b64: str = ""
    ui_library_splitter_b64: str = ""

    # [RCS-KEEP] Cargar settings desde disco (tolerante a errores).
    @classmethod
    def load(cls) -> "AppSettings":
        p = settings_path()
        try:
            if not p.exists():
                return cls()
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return cls()
            out = cls()
            out.canvas_theme = _coerce_canvas_theme(data.get("canvas_theme", out.canvas_theme))

            out.canvas_stroke_thick = _coerce_int(data.get("canvas_stroke_thick", out.canvas_stroke_thick), 0, 12, out.canvas_stroke_thick)
            out.canvas_outline_thick = _coerce_int(data.get("canvas_outline_thick", out.canvas_outline_thick), 0, 12, out.canvas_outline_thick)
            out.thumb_stroke_thick = _coerce_int(data.get("thumb_stroke_thick", out.thumb_stroke_thick), 0, 12, out.thumb_stroke_thick)
            out.thumb_outline_thick = _coerce_int(data.get("thumb_outline_thick", out.thumb_outline_thick), 0, 12, out.thumb_outline_thick)

            out.toolbar_style = _coerce_toolbar_style(data.get('toolbar_style', os.environ.get('RCS_TOOLBAR_STYLE', getattr(out, 'toolbar_style', 'text_only'))))

            out.tool_mode = coerce_tool_mode(data.get("tool_mode", out.tool_mode.value))

            # UI state (opcional)
            out.ui_main_geometry_b64 = str(data.get("ui_main_geometry_b64", "") or "")
            out.ui_main_state_b64 = str(data.get("ui_main_state_b64", "") or "")
            out.ui_library_splitter_b64 = str(data.get("ui_library_splitter_b64", "") or "")
            return out
        except Exception:
            log.debug("No se pudieron cargar settings: %s", p, exc_info=True)
            return cls()

    # [RCS-KEEP] Guardar settings en disco (no debe romper la app).
    def save(self) -> None:
        try:
            d = settings_dir()
            d.mkdir(parents=True, exist_ok=True)
            payload: Dict[str, Any] = {
                "schema_version": 1,
                "canvas_theme": _coerce_canvas_theme(self.canvas_theme),

                "canvas_stroke_thick": _coerce_int(self.canvas_stroke_thick, 0, 12, 2),
                "canvas_outline_thick": _coerce_int(self.canvas_outline_thick, 0, 12, 1),
                "thumb_stroke_thick": _coerce_int(self.thumb_stroke_thick, 0, 12, 2),
                "thumb_outline_thick": _coerce_int(self.thumb_outline_thick, 0, 12, 1),

                "toolbar_style": _coerce_toolbar_style(self.toolbar_style),

                "tool_mode": str(coerce_tool_mode(self.tool_mode).value),

                # UI state (opcional)
                "ui_main_geometry_b64": str(self.ui_main_geometry_b64 or ""),
                "ui_main_state_b64": str(self.ui_main_state_b64 or ""),
                "ui_library_splitter_b64": str(self.ui_library_splitter_b64 or ""),
            }
            settings_path().write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            log.debug("No se pudieron guardar settings", exc_info=True)


def _coerce_canvas_theme(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in VALID_CANVAS_THEMES:
        return s
    return "dark"


def _coerce_toolbar_style(v: Any) -> str:
    if isinstance(v, str):
        vv = v.strip().lower()
        if vv in VALID_TOOLBAR_STYLES:
            return vv
    return "text_only"



def _coerce_int(v: Any, min_v: int, max_v: int, default: int) -> int:
    try:
        n = int(v)
        if n < min_v:
            return min_v
        if n > max_v:
            return max_v
        return n
    except Exception:
        return int(default)
