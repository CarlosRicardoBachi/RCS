# File: rcs/ui/canvas_view.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.63
# Status: stable
# Date: 2026-01-31
# Purpose: Lienzo base (QGraphicsView) con unidades en mm, grilla e inserción de SVG.
# Notes: Hotfix: previews SVG nítidos (DPR) + grilla limitada a hoja + zoom mínimo adaptativo + hit-test interior + QByteArray para QSvgRenderer(bytes).
from __future__ import annotations

import os
import re
import time
import uuid
import math

from pathlib import Path

from PySide6.QtCore import QRectF, QRect, QPointF, Signal, QSize, Qt, QTimer, QByteArray, QDateTime
from PySide6.QtGui import QPainter, QPen, QTransform, QImage, QPixmap, QColor, QFont, QFontMetrics, QCursor
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtSvg import QSvgRenderer

# Optional: hardware-accelerated viewport (only if enabled by env var).
try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
except Exception:  # pragma: no cover
    QOpenGLWidget = None  # type: ignore
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QGraphicsPixmapItem,
    QMenu,
)

from rcs.core.models import Project, SceneObject, Transform, new_object_id
from rcs.core.tool_mode import ToolMode
from rcs.svg.importer import validate_svg_supported
from rcs.svg import preview_style as pv
from rcs.utils.log import get_logger

log = get_logger(__name__)


def _env_int(name: str, default: int, *, min_value: int = 0, max_value: int = 12) -> int:
    """Lee un entero desde env (tolerante)."""
    try:
        raw = os.environ.get(name, "")
        if raw is None or str(raw).strip() == "":
            return int(default)
        v = int(str(raw).strip())
        if v < min_value:
            return min_value
        if v > max_value:
            return max_value
        return v
    except Exception:
        return int(default)


def _env_float(name: str, default: float, *, min_value: float = -1e9, max_value: float = 1e9) -> float:
    try:
        v = float(os.getenv(name, str(default)).strip())
    except Exception:
        return float(default)
    if v < float(min_value):
        return float(min_value)
    if v > float(max_value):
        return float(max_value)
    return float(v)


def _env_bool(name: str, default: bool) -> bool:
    """Lee un booleano desde env (tolerante)."""
    try:
        raw = os.getenv(name)
        if raw is None:
            return bool(default)
        s = str(raw).strip().lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off"):
            return False
        return bool(default)
    except Exception:
        return bool(default)



def _extract_alpha8(img: QImage) -> QImage:
    """Qt6-safe: delega a rcs.svg.preview_style.extract_alpha8."""
    return pv.extract_alpha8(img)
def _tint_from_alpha8(alpha8: QImage, color: QColor) -> QImage:
    """Qt6-safe: delega a rcs.svg.preview_style.tint_from_alpha8."""
    return pv.tint_from_alpha8(alpha8, color)
def _dilate_alpha(alpha: QImage, thick: int) -> QImage:
    """Dilatación vecindad-8: delega a rcs.svg.preview_style.dilate_alpha."""
    return pv.dilate_alpha(alpha, thick)
def _preview_colors_for_theme(theme_id: str) -> tuple[QColor, QColor]:
    """(ink, outline) - fuente única (rcs.svg.preview_style)."""
    return pv.preview_colors_for_theme(theme_id)
def _stylize_preview_image(img: QImage, theme_id: str, *, stroke_thick=None, outline_thick=None, render_scale: int = 1) -> QImage:
    """Stylize unificado (canvas/thumbs) - Qt6-safe.

    Soporta kwargs (stroke_thick/outline_thick) porque el canvas puede escalar por DPR.
    """
    return pv.stylize_preview_image(
        img,
        kind="canvas",
        theme_id=theme_id,
        render_scale=int(render_scale) if render_scale else 1,
        stroke_thick=stroke_thick,
        outline_thick=outline_thick,
    )
def _add_interior_hit_fill(img: QImage) -> QImage:
    """Hace clic-able el interior de figuras cerradas.

    El preview es un trazo/halo con interior transparente; por máscara alfa,
    Qt obliga a clickear "la línea". Aquí rellenamos huecos encerrados con
    un alfa mínimo (1/255) y RGB=0 (virtualmente invisible), así el interior
    también cuenta para hit-test.
    """
    if img.isNull():
        return img

    # ARGB32 premultiplied para tocar bytes.
    if img.format() != QImage.Format_ARGB32_Premultiplied:
        img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)

    alpha_img = _extract_alpha8(img)
    w = int(alpha_img.width())
    h = int(alpha_img.height())
    if w <= 2 or h <= 2:
        return img
    try:
        a_bpl = int(alpha_img.bytesPerLine())
        ptr = alpha_img.bits()
        if hasattr(ptr, 'setsize'):
            ptr.setsize(a_bpl * h)
        aview = memoryview(ptr)

        # Copiamos solo los w bytes útiles por fila (Alpha8 puede estar alineado).
        alpha = bytearray(w * h)
        for y in range(h):
            src_off = y * a_bpl
            dst_off = y * w
            alpha[dst_off : dst_off + w] = aview[src_off : src_off + w]
    except Exception:
        return img

    opaque = bytearray(1 if a > 0 else 0 for a in alpha)

    from collections import deque

    outside = bytearray(w * h)
    q = deque()

    def push(ix: int) -> None:
        if outside[ix]:
            return
        outside[ix] = 1
        q.append(ix)

    # Bordes (transparentes)
    for x in range(w):
        i1 = x
        i2 = (h - 1) * w + x
        if not opaque[i1]:
            push(i1)
        if not opaque[i2]:
            push(i2)
    for y in range(h):
        i1 = y * w
        i2 = y * w + (w - 1)
        if not opaque[i1]:
            push(i1)
        if not opaque[i2]:
            push(i2)

    while q:
        ix = q.popleft()
        y = ix // w
        x = ix - y * w
        if x > 0:
            j = ix - 1
            if not opaque[j] and not outside[j]:
                push(j)
        if x + 1 < w:
            j = ix + 1
            if not opaque[j] and not outside[j]:
                push(j)
        if y > 0:
            j = ix - w
            if not opaque[j] and not outside[j]:
                push(j)
        if y + 1 < h:
            j = ix + w
            if not opaque[j] and not outside[j]:
                push(j)
    try:
        img_bpl = int(img.bytesPerLine())
        bits = img.bits()
        if hasattr(bits, 'setsize'):
            bits.setsize(img_bpl * h)
        buf = memoryview(bits)
    except Exception:
        return img

    img_bpl = int(img.bytesPerLine())
    for y in range(h):
        row_off = y * img_bpl
        for x in range(w):
            i = y * w + x
            if opaque[i] or outside[i]:
                continue
            off = row_off + x * 4  # BGRA
            buf[off + 0] = 0
            buf[off + 1] = 0
            buf[off + 2] = 0
            buf[off + 3] = 1

    return img


def _apply_outline_effect(item: QGraphicsPixmapItem) -> None:
    """[RCS-KEEP] Compat (no-op): en v0.2.17 se removió el efecto de sombra/dup.

    Se mantiene por estabilidad de llamadas antiguas.
    """
    _ = item
    return


def _alpha_bbox(img: QImage, alpha_threshold: int = 1) -> QRect | None:
    """BBox de alfa: delega a rcs.svg.preview_style.alpha_bbox."""
    return pv.alpha_bbox(img, alpha_threshold=int(alpha_threshold))
def _crop_pixmap_to_alpha(pm: QPixmap, *, alpha_threshold: int = 1, pad_px: int = 0) -> QPixmap:
    """Recorta un QPixmap al bbox de alpha, preservando devicePixelRatio."""
    try:
        dpr = float(pm.devicePixelRatioF())
    except Exception:
        dpr = 1.0

    img = pm.toImage()
    rect = _alpha_bbox(img, alpha_threshold=alpha_threshold)
    if rect is None:
        return pm

    if pad_px:
        rect = QRect(
            max(0, rect.x() - pad_px),
            max(0, rect.y() - pad_px),
            min(img.width() - max(0, rect.x() - pad_px), rect.width() + 2 * pad_px),
            min(img.height() - max(0, rect.y() - pad_px), rect.height() + 2 * pad_px),
        )

    out = pm.copy(rect)
    try:
        out.setDevicePixelRatio(dpr)
    except Exception:
        pass
    return out



class CanvasView(QGraphicsView):
    inserted = Signal(str)  # object_id
    project_modified = Signal(str)  # reason
    zoom_changed = Signal(float)  # zoom factor 0.1..8.0
    zoom_limits_changed = Signal(float, float)  # (min_zoom, max_zoom)

    THEME_PRESETS = {
        'dark': {
            'bg': (30, 30, 30),
            'grid_minor': (45, 45, 45),
            'grid_major': (60, 60, 60),
        },
        'mid': {
            'bg': (55, 55, 55),
            'grid_minor': (72, 72, 72),
            'grid_major': (90, 90, 90),
        },
        'light': {
            'bg': (235, 235, 235),
            'grid_minor': (210, 210, 210),
            'grid_major': (190, 190, 190),
        },
    }

    # Hoja de trabajo mínima (mm). El lienzo real del proyecto (canvas_mm)
    # se dibuja como un rectángulo dentro de esta hoja.
    SHEET_MIN_MM = (500.0, 500.0)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._project: Project | None = None
        self._items: dict[str, QGraphicsItem] = {}
        # GMPR: preview base (SVG embebido) que se dibuja por debajo sin participar del modelo.
        self._gmpr_base_item: QGraphicsItem | None = None

        # Tooling (modo activo del lienzo) + clipboard interno (objetos copiados).
        self._tool_mode: ToolMode = ToolMode.SELECT
        self._clipboard: list[dict] = []
        # Clipboard de tamaño (mm): usado por el menú contextual (copiar/pegar ancho/alto).
        self._size_clipboard_mm: dict[str, float | None] = {'w': None, 'h': None}


        self._mm_per_px = 25.4 / 96.0  # asume 96 dpi para preview

        # Preview style (valores base antes de compensación por zoom).
        self._preview_stroke_thick_base = _env_int("RCS_CANVAS_STROKE_THICK", 2, min_value=0, max_value=12)
        self._preview_outline_thick_base = _env_int("RCS_CANVAS_OUTLINE_THICK", 1, min_value=0, max_value=12)

        # Zoom (solo view). Compensa el grosor del preview para que se perciba estable.
        # Nota: el mínimo se recalcula según tamaño de hoja vs viewport.
        self._zoom_max_base = 8.0
        self._zoom_range_factor = _env_float("RCS_CANVAS_ZOOM_RANGE", 1.0, min_value=0.25, max_value=4.0)
        self._zoom_max = float(self._zoom_max_base) * float(self._zoom_range_factor)
        self._zoom_min_dynamic = 0.1

        # Vista inicial explícita (centro + zoom) desde rcs_settings.json -> env.
        self._startup_view_state = self._parse_start_view_from_env()
        self._startup_view_state_applied = False
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)
        self.zoom_limits_changed.emit(self._zoom_min_dynamic, self._zoom_max)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self._preview_rerender_timer = QTimer(self)
        self._preview_rerender_timer.setSingleShot(True)
        self._preview_rerender_timer.setInterval(60)
        self._preview_rerender_timer.timeout.connect(self._rerender_svg_previews if hasattr(self, "_rerender_svg_previews") else (lambda: None))

        self._theme_id = 'dark'
        self._bg_color = QColor(*self.THEME_PRESETS['dark']['bg'])
        self._grid_minor = QColor(*self.THEME_PRESETS['dark']['grid_minor'])
        self._grid_major = QColor(*self.THEME_PRESETS['dark']['grid_major'])

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)

        self.setFocusPolicy(Qt.StrongFocus)

        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        # Preview quality (raster SVG).
        # - DPI lógico del preview: se mantiene constante con devicePixelRatio (DPR).
        # - DPR base por env: RCS_CANVAS_PREVIEW_DPR (1..4). Default 2.
        # - Tamaño lógico en px por env: RCS_CANVAS_PREVIEW_PX (96..1024). Default 240.
        self._preview_dpr_base = _env_int("RCS_CANVAS_PREVIEW_DPR", 2, min_value=1, max_value=4)
        self._preview_logical_px = _env_int("RCS_CANVAS_PREVIEW_PX", 240, min_value=96, max_value=1024)

        # Optional: OpenGL viewport (hardware acceleration).
        # Enable with env `RCS_CANVAS_OPENGL=1`.
        try:
            gl_on = (os.environ.get("RCS_CANVAS_OPENGL", "") or "").strip().lower()
            if gl_on in ("1", "true", "yes", "on") and QOpenGLWidget is not None:
                self.setViewport(QOpenGLWidget())
        except Exception:
            # No hard-fail: algunos drivers/Qt pueden rechazar el viewport.
            log.debug("OpenGL viewport no disponible", exc_info=True)

        # Scrollbars
        # - Default: OFF (evita ruido visual y "saltitos" por cambios del viewport).
        # - Override: env var RCS_CANVAS_SCROLLBARS = off|needed|on
        self._apply_scrollbar_policy_from_env()


        # Grouping v1: si seleccionás un miembro de un grupo, se selecciona el grupo completo.
        self._group_select_sync = False
        self._scene.selectionChanged.connect(self._on_scene_selection_changed_group)

        # Middle-mouse panning (always available, independent of tool mode).
        self._mmb_panning = False
        self._mmb_last_pos = None

        # ------------------------------------------------------------
        # Overlays de medición (UX)
        # - Lienzo: siempre muestra el tamaño del lienzo en mm.
        # - Objeto: se muestra temporalmente cuando se escala o al presionar V.
        # ------------------------------------------------------------
        self._overlay_obj_text: str | None = None
        self._overlay_obj_until_ms: int = 0
        # Aux overlay (e.g., rotation angle)
        self._overlay_aux_text: str | None = None
        self._overlay_aux_until_ms: int = 0

        # Move snap (drag en ToolMode.SELECT) — grilla + object-snap con guías
        # Nota: se aplica solo a raster items (QGraphicsPixmapItem) y solo con selección simple.
        self._move_snap_enabled: bool = False
        self._move_snap_grid_step_mm: float = 1.0
        self._move_snap_fine_step_mm: float = 0.1
        self._move_snap_threshold_px: float = 12.0  # distancia de enganche en pantalla
        self._move_snap_guides_scene: dict[str, float | None] = {"vx": None, "hy": None}

        # Scale handles drag state (ToolMode.SCALE)
        self._scale_drag_active: bool = False
        self._scale_drag_handle: int | None = None
        self._scale_drag_pivot_scene: QPointF | None = None
        self._scale_drag_bbox0_scene: QRectF | None = None
        self._scale_drag_corner0_scene: QPointF | None = None
        self._scale_drag_snap: dict[str, dict[str, float]] = {}
        self._scale_handle_px: int = 6
        # Rotate gizmo drag state (ToolMode.ROTATE)
        self._rotate_drag_active: bool = False
        self._rotate_drag_pivot_scene: QPointF | None = None
        self._rotate_drag_angle0_rad: float = 0.0
        # Snapshot por objeto: {oid: {"rot0": float, "center0": QPointF}}
        self._rotate_drag_snap: dict[str, dict[str, object]] = {}

        # Rotate gizmo (viewport pixels)
        self._rotate_handle_px: int = 10
        self._rotate_handle_offset_px: int = 28  # px arriba del bbox

        # ------------------------------------------------------------
        # Toolbox UX helpers
        # - Space = pan temporal (como editores clásicos)
        # - Cursor dedicado para ROTATE (flechita curva) con fallback seguro
        # ------------------------------------------------------------
        self._temp_pan_active: bool = False
        self._temp_pan_prev_mode: ToolMode | None = None
        self._rotate_cursor_cache: QCursor | None = None

    def _apply_scrollbar_policy_from_env(self) -> None:
        """Configura la política de scrollbars del view.

        Default: OFF (evita ruido visual y micro-saltos por cambios del viewport).

        Override por env vars:
        - `RCS_CANVAS_SCROLL_H` / `RCS_CANVAS_SCROLL_V`: off|needed|on (independientes)
        - fallback: `RCS_CANVAS_SCROLLBARS`: off|needed|on (aplica a ambos)
        """

        def _policy(mode: str):
            m = (mode or "").strip().lower()
            sb_on = getattr(Qt, "ScrollBarAlwaysOn", Qt.ScrollBarAlwaysOn)
            sb_off = getattr(Qt, "ScrollBarAlwaysOff", Qt.ScrollBarAlwaysOff)
            sb_need = getattr(Qt, "ScrollBarAsNeeded", Qt.ScrollBarAsNeeded)
            if m in ("1", "on", "always", "alwayson", "true", "yes"):
                return sb_on
            if m in ("needed", "asneeded", "auto"):
                return sb_need
            return sb_off

        h_mode = os.environ.get("RCS_CANVAS_SCROLL_H")
        v_mode = os.environ.get("RCS_CANVAS_SCROLL_V")
        if h_mode is None and v_mode is None:
            mode = (os.environ.get("RCS_CANVAS_SCROLLBARS", "") or "").strip().lower()
            pol_h = pol_v = _policy(mode)
        else:
            base = (os.environ.get("RCS_CANVAS_SCROLLBARS", "off") or "off").strip().lower()
            pol_h = _policy(h_mode if h_mode is not None else base)
            pol_v = _policy(v_mode if v_mode is not None else base)

        try:
            self.setHorizontalScrollBarPolicy(pol_h)
            self.setVerticalScrollBarPolicy(pol_v)
        except Exception:
            pass

    def scrollbars_enabled(self) -> tuple[bool, bool]:
        """(horizontal, vertical)"""
        try:
            off = getattr(Qt, "ScrollBarAlwaysOff", Qt.ScrollBarAlwaysOff)
            h = self.horizontalScrollBarPolicy() != off
            v = self.verticalScrollBarPolicy() != off
            return bool(h), bool(v)
        except Exception:
            return False, False

    def set_scrollbars_enabled(self, *, horizontal: bool | None = None, vertical: bool | None = None) -> None:
        """Activa/desactiva scrollbars (modo AsNeeded / Off)."""
        sb_off = getattr(Qt, "ScrollBarAlwaysOff", Qt.ScrollBarAlwaysOff)
        sb_need = getattr(Qt, "ScrollBarAsNeeded", Qt.ScrollBarAsNeeded)
        try:
            if horizontal is not None:
                self.setHorizontalScrollBarPolicy(sb_need if horizontal else sb_off)
            if vertical is not None:
                self.setVerticalScrollBarPolicy(sb_need if vertical else sb_off)
        except Exception:
            pass

    # ------------------------------ Tema

    def theme_id(self) -> str:
        return self._theme_id

    def set_theme(self, theme_id: str) -> None:
        tid = (theme_id or '').strip().lower()
        if tid not in self.THEME_PRESETS:
            tid = 'dark'

        if tid == self._theme_id:
            return

        self._theme_id = tid
        preset = self.THEME_PRESETS[tid]
        self._bg_color = QColor(*preset['bg'])
        self._grid_minor = QColor(*preset['grid_minor'])
        self._grid_major = QColor(*preset['grid_major'])

        # Re-render: cambia la tinta/outline en previews.
        if self._project is not None:
            selected = [oid for oid, it in self._items.items() if it.isSelected()]
            self._rebuild_scene_from_project()
            for oid in selected:
                it = self._items.get(oid)
                if it is not None:
                    it.setSelected(True)

        self.viewport().update()

    # ------------------------------ Preview (contraste)

    def set_preview_style(self, *, stroke_thick: int, outline_thick: int) -> None:
        """Define el estilo base del preview.

        Importante: estos valores son *base* (antes de compensación por zoom).
        """
        try:
            st = max(0, min(12, int(stroke_thick)))
            ot = max(0, min(12, int(outline_thick)))
        except Exception:
            return

        changed = (st != self._preview_stroke_thick_base) or (ot != self._preview_outline_thick_base)
        self._preview_stroke_thick_base = st
        self._preview_outline_thick_base = ot
        if changed:
            # Feedback instantáneo cuando el cambio viene del menú (evita la sensación de \"no hace nada\").
            try:
                self._preview_rerender_timer.stop()
            except Exception:
                pass
            self._rerender_svg_previews()
            self.viewport().update()

    def _effective_preview_thickness(self) -> tuple[int, int]:
        z = float(self._zoom) if self._zoom else 1.0
        if z <= 0.01:
            z = 0.01

        # NOTA (hotfix): la compensación por zoom puede hacer que el menú de grosor
        # "parezca roto" cuando el zoom está alto, porque muchos valores terminan
        # cayendo en el mismo grosor efectivo.
        #
        # Por defecto NO compensamos (denom=1). Si alguien quiere el comportamiento
        # anterior, puede activarlo con:
        #   set RCS_CANVAS_THICK_COMPENSATE_ZOOM=1
        import os
        compensate = os.getenv("RCS_CANVAS_THICK_COMPENSATE_ZOOM", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }
        denom = z if (compensate and z >= 1.0) else 1.0

        def _adj(base: int) -> int:
            if base <= 0:
                return 0
            return max(1, min(12, int(round(base / denom))))

        return _adj(self._preview_stroke_thick_base), _adj(self._preview_outline_thick_base)

    def _preview_device_pixel_ratio(self) -> int:
        """DevicePixelRatio usado para el raster del SVG preview.

        Regla: base (env) + aumenta suavemente con zoom para sostener nitidez
        cuando el usuario acerca. Clamp 1..4 para no matar la RAM.
        """
        base = int(getattr(self, '_preview_dpr_base', 2) or 2)
        try:
            z = float(self._zoom) if self._zoom else 1.0
        except Exception:
            z = 1.0
        # Empieza a subir a partir de ~2x de zoom.
        desired = int(round(base * max(1.0, z / 2.0)))
        if desired < 1:
            desired = 1
        if desired > 4:
            desired = 4
        return desired

    def _schedule_preview_rerender(self) -> None:
        if self._project is None:
            return
        # Coalesce múltiples eventos (zoom/tema/...).
        self._preview_rerender_timer.start()

    # ------------------------------ Zoom

    def zoom_factor(self) -> float:
        return float(self._zoom)

    def set_zoom_factor(self, z: float) -> None:
        """Setea el zoom del lienzo.

        Nota: el mínimo se ajusta automáticamente al tamaño de la hoja vs
        viewport para evitar zoom-out extremo.
        """
        self._set_zoom(z)

    def zoom_limits(self) -> tuple[float, float]:
        return float(self._zoom_min_dynamic), float(self._zoom_max)

    def _compute_zoom_min_fit_sheet(self) -> float:
        """Zoom mínimo recomendado para que la hoja siga siendo "usable"."""
        # Si aún no hay hoja, caemos al mínimo por defecto.
        rect = getattr(self, "_sheet_rect", None)
        # Compat: en algunas rutas del código `_sheet_rect` puede quedar como
        # referencia a función/método (callable) y no como QRectF.
        if callable(rect):
            try:
                rect = rect()
            except TypeError:
                # Si no se puede invocar, tratamos como no-disponible.
                rect = None

        if rect is None or (hasattr(rect, "isNull") and rect.isNull()):
            return 0.1

        # La hoja (scene units) están en mm; a zoom=1, 1mm ~ 1px.
        sheet_w = max(1.0, float(rect.width()))
        sheet_h = max(1.0, float(rect.height()))

        vp = self.viewport().size()
        vp_w = max(1, int(vp.width()))
        vp_h = max(1, int(vp.height()))

        pad = 48  # px de margen visual
        avail_w = max(1, vp_w - pad)
        avail_h = max(1, vp_h - pad)

        fit = min(avail_w / sheet_w, avail_h / sheet_h)
        # Si el viewport es enorme, fit puede ser >1. No bloqueamos el zoom-out
        # por encima de 1.0, para mantener comportamiento natural.
        zmin = min(1.0, fit)
        # Piso de seguridad (no menos de 5%).
        return max(0.05, float(zmin))

    def _recalc_zoom_limits(self, *, clamp_current: bool = True) -> None:
        # Min dinámico basado en fitInView, ajustado por un factor de rango (F12).
        try:
            f = float(self._zoom_range_factor) if self._zoom_range_factor else 1.0
        except Exception:
            f = 1.0
        if f < 0.25:
            f = 0.25
        if f > 4.0:
            f = 4.0

        # Max también escala con el factor (más rango => más zoom-in y más zoom-out).
        new_max = float(self._zoom_max_base) * float(f)

        new_min_base = self._compute_zoom_min_fit_sheet()
        new_min = float(new_min_base) / float(f)
        if new_min < 0.01:
            new_min = 0.01

        if abs(new_min - float(self._zoom_min_dynamic)) < 1e-6 and abs(new_max - float(self._zoom_max)) < 1e-6:
            return

        self._zoom_min_dynamic = float(new_min)
        self._zoom_max = float(new_max)
        self.zoom_limits_changed.emit(float(self._zoom_min_dynamic), float(self._zoom_max))

        if clamp_current and self._zoom < self._zoom_min_dynamic:
            # Ajuste suave: respeta clamp dinámico dentro de _set_zoom.
            self._set_zoom(self._zoom_min_dynamic)

    def zoom_reset(self) -> None:
        self._set_zoom(1.0)

    def zoom_range_factor(self) -> float:
        return float(self._zoom_range_factor)

    def set_zoom_range_factor(self, factor: float) -> None:
        """Ajusta el rango de zoom (F12).

        factor=1.0 => rango default
        factor>1.0 => más zoom-in y más zoom-out
        factor<1.0 => rango más acotado
        """
        try:
            f = float(factor)
        except Exception:
            return
        if f < 0.25:
            f = 0.25
        if f > 4.0:
            f = 4.0
        if abs(f - float(self._zoom_range_factor)) < 1e-9:
            return
        self._zoom_range_factor = f
        # Recalcula min/max (incluye max).
        self._recalc_zoom_limits(clamp_current=True)

    def zoom_in(self) -> None:
        self._set_zoom(self._zoom * 1.25)

    def zoom_out(self) -> None:
        self._set_zoom(self._zoom / 1.25)

    def _set_zoom(self, z: float) -> None:
        """Aplica zoom del view.

        Regla:
        - Por defecto, el zoom interactivo se limita a 0.1..8.0.
        - Pero si el zoom actual quedó fuera de ese rango (p.ej. por fitInView),
          usamos un clamp *dinámico* para evitar saltos bruscos:
            - no deja alejar más si ya está por debajo del mínimo
            - no deja acercar más si ya está por encima del máximo

        Esto evita el clásico bug: fitInView() deja el zoom en 0.03, pero el
        estado interno se clampa a 0.1 y el primer gesto de zoom pega un salto.
        """
        try:
            z = float(z)
        except Exception:
            return

        # Zoom actual real (puede venir de fitInView y estar fuera del rango “normal”).
        cur = float(self._zoom) if self._zoom else 1.0
        if cur <= 0.000001:
            cur = 1.0

        # Clamp dinámico: si estamos fuera del rango, el límite se “pega” al zoom actual
        # para que el primer gesto no produzca un salto.
        zmin_user, zmax_user = float(self._zoom_min_dynamic), float(self._zoom_max)
        zmin = min(zmin_user, cur)
        zmax = max(zmax_user, cur)

        if z < zmin:
            z = zmin
        elif z > zmax:
            z = zmax

        if abs(z - self._zoom) < 1e-6:
            return

        self._zoom = z
        self.resetTransform()
        self.scale(self._zoom, self._zoom)
        self.zoom_changed.emit(self._zoom)
        self._schedule_preview_rerender()

    def wheelEvent(self, event) -> None:
        dy = 0
        try:
            dy = int(event.angleDelta().y())
        except Exception:
            dy = 0

        if not dy:
            super().wheelEvent(event)
            return

        # 1) En herramientas de objeto, la rueda actúa sobre el objeto.
        if self._tool_mode in (ToolMode.ROTATE, ToolMode.SCALE):
            target = self._pick_target_item(event)
            if target is not None:
                oid = self._item_object_id(target)
                if oid:
                    if self._tool_mode == ToolMode.ROTATE:
                        self._rotate_object(oid, dy, fine=bool(event.modifiers() & Qt.ShiftModifier))
                    else:
                        self._scale_object(oid, dy, fine=bool(event.modifiers() & Qt.ShiftModifier))
                    event.accept()
                    return

        # 2) Herramienta zoom: rueda = zoom (sin Ctrl).
        if self._tool_mode == ToolMode.ZOOM:
            steps = dy / 120.0
            # Zoom más suave: reducimos la agresividad ~40% por defecto.
            # Con Shift: aún más fino (~60% respecto al comportamiento anterior).
            smooth = 0.6
            if event.modifiers() & Qt.ShiftModifier:
                smooth = 0.4
            factor = 1.25 ** (steps * smooth)
            self._set_zoom(self._zoom * factor)
            event.accept()
            return

        # 3) Compat: Ctrl+rueda = zoom (modo select).
        if event.modifiers() & Qt.ControlModifier:
            steps = dy / 120.0
            smooth = 0.6
            if event.modifiers() & Qt.ShiftModifier:
                smooth = 0.4
            factor = 1.25 ** (steps * smooth)
            self._set_zoom(self._zoom * factor)
            event.accept()
            return

        super().wheelEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Recalcular mínimo de zoom cuando cambia el viewport.
        self._recalc_zoom_limits(clamp_current=True)

    def _sync_zoom_from_view_transform(self) -> None:
        """Sincroniza self._zoom con el transform actual del view.

        Se usa después de fitInView() al abrir/proyectar un .RCS.

        Importante: fitInView() puede dejar el view en escalas fuera del rango
        de zoom interactivo (0.1..8.0). En ese caso, registramos el zoom real
        para que el indicador sea coherente y el primer gesto de zoom no pegue
        un salto.
        """
        try:
            z = float(self.transform().m11())
        except Exception:
            return
        if z <= 0.000001:
            return
        if abs(z - self._zoom) < 1e-6:
            return
        self._zoom = z
        self.zoom_changed.emit(self._zoom)
        self._schedule_preview_rerender()

    def _apply_startup_zoom_after_fit(self) -> None:
        """Aplica un multiplicador de zoom luego del fit-to-sheet inicial.

        Config:
          - Env: RCS_CANVAS_START_ZOOM
          - Proyecto: rcs_settings.json → ui.canvas.zoom_after_fit
        """
        raw = os.environ.get("RCS_CANVAS_START_ZOOM", "").strip()
        if not raw:
            return
        try:
            factor = float(raw)
        except Exception:
            return
        if abs(factor - 1.0) < 1e-6:
            return
        factor = max(0.25, min(4.0, factor))
        self._set_zoom(self._zoom * factor)



    def _apply_startup_view_anchor(self) -> None:
        """Aplica un anclaje inicial de vista (ej. centrar en el origen del canvas).

        Configuración via env var (inyectada por rcs_settings.json):
          - RCS_CANVAS_START_ANCHOR=canvas_origin | canvas_center | sheet_origin | sheet_center

        Nota: se aplica una sola vez por sesión (para no 'secuestrar' la vista del usuario).
        """
        if getattr(self, "_startup_anchor_applied", False):
            return

        raw = os.environ.get("RCS_CANVAS_START_ANCHOR", "").strip().lower()
        if not raw:
            return

        # Marcar antes por si algo falla y evitar bucles.
        self._startup_anchor_applied = True

        # Aliases tolerantes
        if raw in ("origin", "canvas0", "0"):
            raw = "canvas_origin"
        elif raw in ("center",):
            raw = "canvas_center"

        try:
            if raw == "canvas_origin":
                self.centerOn(self._canvas_origin_mm())
            elif raw == "canvas_center":
                self.centerOn(self._canvas_rect().center())
            elif raw == "sheet_origin":
                self.centerOn(QPointF(0.0, 0.0))
            elif raw == "sheet_center":
                self.centerOn(self._sheet_rect().center())
        except Exception:
            # Fallo silencioso: no bloquear inicio por un ajuste cosmético.
            return


    def _parse_start_view_from_env(self) -> tuple[float, float, float] | None:
        """Lee la vista de inicio desde env (inyectada por rcs_settings.json).

        Formato esperado: RCS_CANVAS_START_VIEW="x_mm,y_mm,zoom" (coords canvas).
        """
        raw = os.environ.get("RCS_CANVAS_START_VIEW", "").strip()
        if not raw:
            return None
        # tolerar 'x;y;z'
        raw = raw.replace(";", ",")
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) != 3:
            return None
        try:
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2])
        except Exception:
            return None
        # clamps suaves
        try:
            z = max(0.05, min(128.0, z))
        except Exception:
            pass
        return (x, y, z)

    def _apply_startup_view_state(self) -> None:
        """Aplica vista de inicio (center + zoom) si está configurada.

        Tiene prioridad sobre zoom_after_fit y start_anchor.
        """
        if getattr(self, "_startup_view_state_applied", False):
            return
        st = getattr(self, "_startup_view_state", None)
        if not st:
            return
        self._startup_view_state_applied = True
        try:
            cx, cy, z = st
            # clamp a canvas actual
            w, h = self._canvas_size_mm()
            if w and h:
                cx = max(0.0, min(float(w), float(cx)))
                cy = max(0.0, min(float(h), float(cy)))
            sx, sy = self._canvas_to_scene_xy(float(cx), float(cy))
            self.centerOn(QPointF(sx, sy))
            self._set_zoom(float(z))
        except Exception:
            return


    # ------------------------------ Vista / encuadre

    def _scene_rect_of_object_items(self, items: list[QGraphicsItem]) -> QRectF | None:
        """Devuelve el QRectF unión de items *de objeto* en coordenadas de escena.

        Nota: filtra items sin object_id (evita encuadrar overlays internos).
        """
        rect: QRectF | None = None
        for it in items:
            try:
                if not self._item_object_id(it):
                    continue
                r = it.sceneBoundingRect()
                if r.isNull() or r.width() <= 0.0 or r.height() <= 0.0:
                    continue
                rect = r if rect is None else rect.united(r)
            except Exception:
                continue
        return rect

    def _expand_scene_rect(self, r: QRectF, *, pad_mm: float = 12.0) -> QRectF:
        """Expande un rect en mm para darle aire al encuadre (margen visual)."""
        try:
            w = float(r.width())
            h = float(r.height())
            base = max(w, h)
            pad = max(float(pad_mm), base * 0.06)  # 6% o mínimo
            pad = min(pad, 80.0)  # clamp anti-rects enormes
            return QRectF(float(r.x()) - pad, float(r.y()) - pad, w + 2.0 * pad, h + 2.0 * pad)
        except Exception:
            return r

    def frame_selection(self) -> bool:
        """Encuadra la selección actual en el viewport.

        Retorna True si había al menos 1 objeto seleccionado.
        """
        r = self._scene_rect_of_object_items(list(self._scene.selectedItems()))
        if r is None:
            return False
        self.fitInView(self._expand_scene_rect(r, pad_mm=12.0), Qt.KeepAspectRatio)
        self._sync_zoom_from_view_transform()
        return True

    def frame_all_objects(self) -> bool:
        """Encuadra todos los objetos del proyecto (no la hoja)."""
        r = self._scene_rect_of_object_items(list(self._items.values()))
        if r is None:
            return False
        self.fitInView(self._expand_scene_rect(r, pad_mm=20.0), Qt.KeepAspectRatio)
        self._sync_zoom_from_view_transform()
        return True

    def view_reset_to_sheet(self) -> None:
        """Reset de vista: encuadra la hoja (sheet_rect) como al abrir un proyecto."""
        self.fitInView(self._sheet_rect(), Qt.KeepAspectRatio)
        self._sync_zoom_from_view_transform()

    def get_view_state_canvas(self) -> dict:
        """Devuelve el estado actual de vista para persistirlo.

        Retorna un dict con center_canvas=[x_mm,y_mm] y zoom.

        Nota: center_canvas está en coordenadas de lienzo (mm) para que
        sobreviva cambios de origen de scene/sheet.
        """
        c = self.mapToScene(self.viewport().rect().center())
        cx, cy = self._scene_to_canvas_xy(float(c.x()), float(c.y()))
        return {"center_canvas": [float(cx), float(cy)], "zoom": float(self._zoom)}

    def set_startup_view_state(self, center_canvas: tuple[float, float], zoom: float) -> None:
        """Define la vista de inicio para futuros `set_project()`.

        Se guarda internamente y se marcará como pendiente para aplicar
        en la próxima reconstrucción (por ejemplo al crear/abrir proyecto).
        """
        cx, cy = float(center_canvas[0]), float(center_canvas[1])
        z = float(zoom)
        self._startup_view_state = (cx, cy, z)
        self._startup_view_state_applied = False

    def clear_startup_view_state(self) -> None:
        """Quita la vista de inicio persistida (vuelve al comportamiento default)."""
        self._startup_view_state = None
        self._startup_view_state_applied = False

    def apply_view_state_canvas(self, center_canvas: tuple[float, float], zoom: float) -> None:
        """Aplica center/zoom guardados (ej. vista de inicio)."""
        cx, cy = center_canvas
        # clamp al lienzo actual
        try:
            w, h = self._project.canvas_mm
            cx = max(0.0, min(float(w), float(cx)))
            cy = max(0.0, min(float(h), float(cy)))
        except Exception:
            cx, cy = float(cx), float(cy)
        sx, sy = self._canvas_to_scene_xy(float(cx), float(cy))
        self.centerOn(QPointF(sx, sy))
        self._set_zoom(float(zoom), clamp=True, emit=True)

    def scrollbars_policy(self) -> tuple[str, str]:
        """(horizontal, vertical) policy: off | needed | on."""

        def _from_qt(pol) -> str:
            if pol == Qt.ScrollBarAlwaysOff:
                return "off"
            if pol == Qt.ScrollBarAlwaysOn:
                return "on"
            return "needed"

        return (_from_qt(self.horizontalScrollBarPolicy()), _from_qt(self.verticalScrollBarPolicy()))

    def scrollbars_enabled(self) -> tuple[bool, bool]:
        """(horizontal, vertical) habilitados (policy != off)."""
        h, v = self.scrollbars_policy()
        return (h != "off", v != "off")

    def set_scrollbars_policy(self, *, horizontal: str | None = None, vertical: str | None = None) -> None:
        """Configura scrollbars en runtime.

        Valores admitidos: off | needed | on.
        """

        def _to_qt(v: str):
            vv = str(v or "").strip().lower()
            if vv == "off":
                return Qt.ScrollBarAlwaysOff
            if vv == "on":
                return Qt.ScrollBarAlwaysOn
            return Qt.ScrollBarAsNeeded

        if horizontal is not None:
            self.setHorizontalScrollBarPolicy(_to_qt(horizontal))
        if vertical is not None:
            self.setVerticalScrollBarPolicy(_to_qt(vertical))
        try:
            self.viewport().update()
        except Exception:
            pass

    def set_scrollbars_enabled(self, *, horizontal: bool | None = None, vertical: bool | None = None) -> None:
        """Compat legacy: True=>needed, False=>off."""
        if horizontal is not None:
            self.set_scrollbars_policy(horizontal=("needed" if bool(horizontal) else "off"))
        if vertical is not None:
            self.set_scrollbars_policy(vertical=("needed" if bool(vertical) else "off"))

    # ------------------------------ Tooling / edición

    def tool_mode(self) -> ToolMode:
        return self._tool_mode

    def set_tool_mode(self, mode: ToolMode | str | None) -> None:
        try:
            if isinstance(mode, ToolMode):
                m = mode
            else:
                m = ToolMode(str(mode or '').strip().lower())
        except Exception:
            m = ToolMode.SELECT

        if m == self._tool_mode:
            return
        self._tool_mode = m

        pan_mode = getattr(ToolMode, "PAN", None)

        # UX:
        # - zoom: rueda = zoom, sin rubberband.
        # - pan : drag = mover vista (mano).
        # - resto: rubberband.
        try:
            self.unsetCursor()
        except Exception:
            pass

        if self._tool_mode == ToolMode.ZOOM:
            self.setDragMode(QGraphicsView.NoDrag)

            # Cursor tipo "lupita" cuando está disponible (Qt puede exponer ZoomInCursor).
            zoom_cursor = None
            try:
                if hasattr(Qt, "CursorShape") and hasattr(Qt.CursorShape, "ZoomInCursor"):
                    zoom_cursor = Qt.CursorShape.ZoomInCursor
                elif hasattr(Qt, "ZoomInCursor"):
                    zoom_cursor = Qt.ZoomInCursor
            except Exception:
                zoom_cursor = None

            if zoom_cursor is None:
                zoom_cursor = Qt.CrossCursor

            self.setCursor(zoom_cursor)
            self.viewport().setCursor(zoom_cursor)

        elif pan_mode is not None and self._tool_mode == pan_mode:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            try:
                self.setCursor(Qt.OpenHandCursor)
            except Exception:
                pass

            # Mantener consistente el cursor también en el viewport.
            try:
                self.viewport().setCursor(Qt.OpenHandCursor)
            except Exception:
                pass

        elif self._tool_mode == ToolMode.ROTATE:
            # En rotación no usamos drag mode; el gizmo + drag rotan.
            self.setDragMode(QGraphicsView.RubberBandDrag)
            cur = None
            try:
                cur = self._get_rotate_cursor()
            except Exception:
                cur = None
            if cur is None:
                cur = Qt.CrossCursor
            try:
                self.setCursor(cur)
                self.viewport().setCursor(cur)
            except Exception:
                pass

        elif self._tool_mode == ToolMode.SCALE:
            # Cursor de escala (laser/CNC friendly: deja claro que estamos "deformando" bbox)
            self.setDragMode(QGraphicsView.RubberBandDrag)
            try:
                self.setCursor(Qt.SizeAllCursor)
                self.viewport().setCursor(Qt.SizeAllCursor)
            except Exception:
                pass
        else:
            self.setDragMode(QGraphicsView.RubberBandDrag)

        # En modo PICK (solo seleccionar) deshabilitamos el drag-move.
        self._apply_items_movable_flags()

    def _apply_items_movable_flags(self) -> None:
        """Activa/desactiva ItemIsMovable según herramienta.

        - SELECT: selecciona + mueve con drag.
        - PICK  : solo selección (evita arrastres accidentales).

        Nota: no toca items que no correspondan a objetos del modelo.
        """
        # Mantener comportamiento: PICK deshabilita mover. Además, en ZOOM/PAN
        # no queremos arrastrar objetos por accidente.
        pick = getattr(ToolMode, "PICK", ToolMode.SELECT)
        pan = getattr(ToolMode, "PAN", None)
        movable = self._tool_mode not in {pick, ToolMode.ZOOM, pan}
        for it in self._items.values():
            try:
                if not self._item_object_id(it):
                    continue
                it.setFlag(QGraphicsItem.ItemIsMovable, bool(movable))
            except Exception:
                continue

    def _get_rotate_cursor(self) -> QCursor:
        """Cursor de rotación (flechita curva).

        - Se genera en runtime (sin assets externos).
        - Si algo falla, cae a CrossCursor.
        """
        if self._rotate_cursor is not None:
            return self._rotate_cursor

        try:
            pm = QPixmap(32, 32)
            pm.fill(Qt.transparent)

            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing, True)
            pen = QPen(QColor(255, 255, 0))
            pen.setWidth(2)
            p.setPen(pen)

            # Arco principal
            arc_rect = QRect(6, 6, 20, 20)
            p.drawArc(arc_rect, 45 * 16, 270 * 16)

            # Flecha (punta) al final del arco
            import math

            cx, cy = 16, 16
            r = 10
            ang = math.radians(-45)  # 315°
            ex = cx + r * math.cos(ang)
            ey = cy + r * math.sin(ang)

            def pt(a_deg: float, rr: float = 6.0):
                a = math.radians(a_deg)
                return (ex - rr * math.cos(a), ey - rr * math.sin(a))

            a1 = pt(-45 - 25)
            a2 = pt(-45 + 25)
            p.drawLine(QPointF(ex, ey), QPointF(a1[0], a1[1]))
            p.drawLine(QPointF(ex, ey), QPointF(a2[0], a2[1]))

            p.end()

            self._rotate_cursor = QCursor(pm, 16, 16)
            return self._rotate_cursor
        except Exception:
            self._rotate_cursor = QCursor(Qt.CrossCursor)
            return self._rotate_cursor

    def selected_object_ids(self) -> list[str]:
        out: list[str] = []
        for it in self._scene.selectedItems():
            oid = self._item_object_id(it)
            if oid:
                out.append(oid)
        return out


    # ------------------------------ Grouping (v1) ------------------------------

    def _on_scene_selection_changed_group(self) -> None:
        """Expande la selección a grupo completo.

        Regla: si algún item seleccionado tiene `group_id`, se seleccionan
        todos los items con ese mismo `group_id`.
        """
        if self._group_select_sync:
            return
        if not self._project:
            return

        # GMPR base: selección exclusiva (si hay otros items seleccionados, se deselecciona el fondo)
        if self._gmpr_base_item is not None and self._gmpr_base_item.isSelected():
            for it in self._scene.selectedItems():
                if it is not self._gmpr_base_item:
                    self._group_select_sync = True
                    try:
                        self._gmpr_base_item.setSelected(False)
                    finally:
                        self._group_select_sync = False
                    break


        ids = self.selected_object_ids()
        if not ids:
            return

        group_ids = self._project.groups_of_ids(ids)
        if not group_ids:
            return

        self._group_select_sync = True
        try:
            for gid in group_ids:
                for mid in self._project.group_member_ids(gid):
                    it = self._items.get(mid)
                    if it is not None and (not it.isSelected()):
                        it.setSelected(True)
        finally:
            self._group_select_sync = False

    def can_group_selection(self) -> bool:
        if not self._project:
            return False
        ids = self.selected_object_ids()
        if len(ids) < 2:
            return False
        # Solo objetos sin grupo.
        for oid in ids:
            o = self._project.get_object(oid)
            if not o or o.group_id:
                return False
        return True

    def can_ungroup_selection(self) -> bool:
        if not self._project:
            return False
        ids = self.selected_object_ids()
        if not ids:
            return False
        gids = self._project.groups_of_ids(ids)
        return len(gids) == 1

    def can_reset_scale_selection(self) -> bool:
        """True si la selección contiene algún item con escala != 1.0."""
        if not self._project:
            return False
        ids = self.selected_object_ids()
        if not ids:
            return False
        for oid in ids:
            o = self._project.get_object(oid)
            if not o:
                continue
            try:
                sx = float(getattr(o.transform, 'scale_x', 1.0) or 1.0)
                sy = float(getattr(o.transform, 'scale_y', 1.0) or 1.0)
            except Exception:
                continue
            if abs(sx - 1.0) > 1e-6 or abs(sy - 1.0) > 1e-6:
                return True
        return False

    def reset_selected_scale(self) -> None:
        """Restaura escala (1.0, 1.0) sin mover el centro visual."""
        if not self._project:
            return
        ids = self.selected_object_ids()
        if not ids:
            return

        changed = False
        for oid in ids:
            obj = self._project.get_object(oid)
            it = self._items.get(oid)
            if not obj or not it:
                continue
            try:
                sx = float(getattr(obj.transform, 'scale_x', 1.0) or 1.0)
                sy = float(getattr(obj.transform, 'scale_y', 1.0) or 1.0)
            except Exception:
                sx = 1.0
                sy = 1.0

            if abs(sx - 1.0) <= 1e-6 and abs(sy - 1.0) <= 1e-6:
                continue

            old_center = self._item_scene_center(it)
            obj.transform.scale_x = 1.0
            obj.transform.scale_y = 1.0
            self._apply_object_transform_to_item(obj, it)
            self._lock_item_center(obj, it, old_center)
            self._rerender_svg_preview_for_object(oid)
            changed = True

        if changed:
            self._project.mark_dirty('scale')
            self.project_modified.emit('scale')


    def _pack_selection_contiguous_keep_top(self, ids: list[str]) -> None:
        """Reordena Z localmente para que `ids` queden contiguos (bloque).

        No toca objetos fuera del rango [min_idx, max_idx] del conjunto en el
        orden por Z. Mantiene el multiset de z dentro del rango, reasignando
        z a los objetos para lograr un bloque estable.
        """
        if not self._project or len(ids) < 2:
            return
        sel = set(ids)
        objs = self._objects_in_z_order()
        idx_map = {o.id: i for i, o in enumerate(objs)}
        sel_idx = [idx_map.get(oid) for oid in ids if oid in idx_map]
        if not sel_idx:
            return
        min_i, max_i = min(sel_idx), max(sel_idx)
        if max_i - min_i + 1 == len(sel):
            return  # ya contiguo

        segment = objs[min_i : max_i + 1]
        z_list = [int(o.z) for o in segment]

        non_sel = [o for o in segment if o.id not in sel]
        sel_objs = [o for o in segment if o.id in sel]

        new_segment = non_sel + sel_objs  # ids al final => bloque arriba (frente)
        for j, o in enumerate(new_segment):
            self._set_object_z(o, int(z_list[j]))

    def group_selected(self) -> None:
        if not self._project:
            return
        ids = self.selected_object_ids()
        if len(ids) < 2:
            return
        if not self.can_group_selection():
            self.project_modified.emit("Agrupar: selección inválida")
            return

        # Normalizar Z localmente para que el grupo sea un bloque.
        self._pack_selection_contiguous_keep_top(ids)

        gid = uuid.uuid4().hex[:10]
        for oid in ids:
            o = self._project.get_object(oid)
            if o:
                o.group_id = gid

        self._project.mark_dirty("group")
        self.project_modified.emit(f"Agrupado: {len(ids)}")

    def ungroup_selected(self) -> None:
        if not self._project:
            return
        ids = self.selected_object_ids()
        if not ids:
            return
        if not self.can_ungroup_selection():
            self.project_modified.emit("Desagrupar: selección inválida")
            return

        gids = list(self._project.groups_of_ids(ids))
        gid = gids[0] if gids else None
        if not gid:
            return

        members = self._project.group_member_ids(gid)
        for oid in members:
            o = self._project.get_object(oid)
            if o:
                o.group_id = None

        self._project.mark_dirty("ungroup")
        self.project_modified.emit(f"Desagrupado: {len(members)}")


    def delete_selected(self) -> None:
        if not self._project:
            return
        ids = self.selected_object_ids()
        if not ids:
            return

        # Scene
        for oid in ids:
            it = self._items.get(oid)
            if it:
                self._scene.removeItem(it)
                self._items.pop(oid, None)

        # Model
        self._project.objects = [o for o in self._project.objects if o.id not in set(ids)]
        self._project.mark_dirty("delete")
        self.project_modified.emit("delete")

    def copy_selected(self) -> None:
        if not self._project:
            return
        ids = self.selected_object_ids()
        if not ids:
            return
        copied: list[dict] = []
        for oid in ids:
            obj = self._project.get_object(oid)
            if obj:
                d = obj.to_dict()
                d.pop('id', None)
                copied.append(d)
        self._clipboard = copied

    def paste_clipboard(self) -> None:
        if not self._project:
            return
        if not self._clipboard:
            return

        # Preserva el orden relativo por Z.
        ordered = sorted(self._clipboard, key=lambda d: int(d.get('z', 0)))
        base_z = self._project.next_z()
        # Grouping v1: remap group_id (no enlazar con el original)
        gid_map: dict[str, str] = {}

        dx_mm, dy_mm = 2.0, 2.0

        new_ids: list[str] = []
        for idx, d in enumerate(ordered):
            try:
                dd = dict(d)
                g0 = dd.get('group_id')
                if g0:
                    g0s = str(g0)
                    if g0s not in gid_map:
                        gid_map[g0s] = uuid.uuid4().hex[:10]
                    dd['group_id'] = gid_map[g0s]
                obj = SceneObject.from_dict({**dd, 'id': new_object_id('obj')})
            except Exception:
                continue
            obj.z = base_z + idx
            obj.transform.x = float(obj.transform.x) + dx_mm
            obj.transform.y = float(obj.transform.y) + dy_mm
            self._project.objects.append(obj)

            if obj.type == 'svg':
                self._add_svg_item(obj)
            elif obj.type == 'text':
                self._add_text_item(obj)

            new_ids.append(obj.id)

        # Seleccionar los nuevos
        self._scene.clearSelection()
        for oid in new_ids:
            it = self._items.get(oid)
            if it:
                it.setSelected(True)

        self._project.mark_dirty("paste")
        self.project_modified.emit("paste")

    # Compat API: versiones anteriores llamaban paste_copied()
    def paste_copied(self) -> None:
        self.paste_clipboard()

    # ------------------------------ Z-Order
    def _objects_in_z_order(self) -> list[SceneObject]:
        """Devuelve los objetos ordenados por z (y estable por orden interno).

        Nota: se usa para operaciones de apilado (Z-order).
        """
        if not self._project:
            return []
        idx = {o.id: i for i, o in enumerate(self._project.objects)}
        objs = list(self._project.objects)
        objs.sort(key=lambda o: (int(o.z), idx.get(o.id, 0)))
        return objs

    def _set_object_z(self, oid: str, z: int) -> None:
        if not self._project:
            return
        obj = self._project.get_object(oid)
        if not obj:
            return
        obj.z = int(z)
        it = self._items.get(oid)
        if it:
            try:
                it.setZValue(float(obj.z))
            except Exception:
                pass

    def z_bring_to_front(self) -> None:
        if not self._project:
            return
        sel_ids = self.selected_object_ids()
        if not sel_ids:
            return

        sel_set = set(sel_ids)
        objs = self._objects_in_z_order()
        if not objs:
            return

        max_z = max(int(o.z) for o in objs)
        picked = [o for o in objs if o.id in sel_set]
        if not picked:
            return

        start = int(max_z) + 1
        old_first = int(picked[0].z)
        for i, o in enumerate(picked):
            self._set_object_z(o.id, start + i)

        self._project.mark_dirty("z_front")
        if len(picked) == 1:
            self.project_modified.emit(f"Z: {old_first} → {start}")
        else:
            self.project_modified.emit(
                f"Z: {len(picked)} al frente (max {max_z} → {start + len(picked) - 1})"
            )

    def z_send_to_back(self) -> None:
        if not self._project:
            return
        sel_ids = self.selected_object_ids()
        if not sel_ids:
            return

        sel_set = set(sel_ids)
        objs = self._objects_in_z_order()
        if not objs:
            return

        min_z = min(int(o.z) for o in objs)
        picked = [o for o in objs if o.id in sel_set]
        if not picked:
            return

        start = int(min_z) - len(picked)
        old_first = int(picked[0].z)
        for i, o in enumerate(picked):
            self._set_object_z(o.id, start + i)

        self._project.mark_dirty("z_back")
        if len(picked) == 1:
            self.project_modified.emit(f"Z: {old_first} → {start}")
        else:
            self.project_modified.emit(
                f"Z: {len(picked)} al fondo (min {min_z} → {start})"
            )

    def z_raise_one(self) -> None:
        """Sube la selección 1 nivel (swap mínimo con el vecino superior).

        - No reordena toda la escena.
        - Para multiselección, se procesa de arriba hacia abajo para mover el bloque.
        """
        if not self._project:
            return
        sel_ids = self.selected_object_ids()
        if not sel_ids:
            return

        sel_set = set(sel_ids)
        objs = self._objects_in_z_order()
        if len(objs) < 2:
            return

        before = None
        if len(sel_set) == 1:
            oid = next(iter(sel_set))
            o = self._project.get_object(oid)
            before = int(o.z) if o else None

        swaps = 0
        # Iterar de arriba hacia abajo para mover el bloque sin invertirlo.
        for i in range(len(objs) - 2, -1, -1):
            a = objs[i]
            b = objs[i + 1]
            if (a.id in sel_set) and (b.id not in sel_set):
                za, zb = int(a.z), int(b.z)
                self._set_object_z(a.id, zb)
                self._set_object_z(b.id, za)
                objs[i], objs[i + 1] = b, a
                swaps += 1

        if swaps:
            self._project.mark_dirty("z_raise")

        if before is not None:
            after = int(self._project.get_object(next(iter(sel_set))).z)
            if after != before:
                self.project_modified.emit(f"Z: {before} → {after}")
            else:
                self.project_modified.emit("Z: sin cambio")
        else:
            self.project_modified.emit(f"Z: subir 1 (swaps={swaps})")

    def z_lower_one(self) -> None:
        """Baja la selección 1 nivel (swap mínimo con el vecino inferior).

        - No reordena toda la escena.
        - Para multiselección, se procesa de abajo hacia arriba para mover el bloque.
        """
        if not self._project:
            return
        sel_ids = self.selected_object_ids()
        if not sel_ids:
            return

        sel_set = set(sel_ids)
        objs = self._objects_in_z_order()
        if len(objs) < 2:
            return

        before = None
        if len(sel_set) == 1:
            oid = next(iter(sel_set))
            o = self._project.get_object(oid)
            before = int(o.z) if o else None

        swaps = 0
        for i in range(1, len(objs)):
            b = objs[i]
            a = objs[i - 1]
            if (b.id in sel_set) and (a.id not in sel_set):
                za, zb = int(a.z), int(b.z)
                self._set_object_z(b.id, za)
                self._set_object_z(a.id, zb)
                objs[i - 1], objs[i] = b, a
                swaps += 1

        if swaps:
            self._project.mark_dirty("z_lower")

        if before is not None:
            after = int(self._project.get_object(next(iter(sel_set))).z)
            if after != before:
                self.project_modified.emit(f"Z: {before} → {after}")
            else:
                self.project_modified.emit("Z: sin cambio")
        else:
            self.project_modified.emit(f"Z: bajar 1 (swaps={swaps})")

    def duplicate_selected(self) -> None:
        """Duplica la selección actual (equivalente a copiar+pegar)."""
        self.copy_selected()
        self.paste_clipboard()

    def fit_selected_to_content(self) -> int:
        """Ajusta el marco de los SVGs seleccionados al contenido visible.

        Caso típico: SVG con viewBox grande / márgenes blancos internos.
        Implementación: recorta el pixmap preview por canal alfa y compensa
        la posición para que el contenido no "salte".

        Persistencia: marca `obj.svg_fit_content = True` para que en re-render
        (cambio de tema) y en load se vuelva a recortar.

        Devuelve: cantidad de objetos ajustados.
        """
        if not self._project:
            return 0
        sel = list(self._scene.selectedItems())
        if not sel:
            return 0

        adjusted = 0
        for it in sel:
            oid = self._item_object_id(it)
            if not oid:
                continue
            obj = self._project.get_object(oid)
            if not obj or obj.type != 'svg':
                continue
            if not isinstance(it, QGraphicsPixmapItem):
                continue

            pm = it.pixmap()
            if pm.isNull():
                continue

            img = pm.toImage()
            rect = _alpha_bbox(img, alpha_threshold=1)
            if rect is None:
                continue
            if rect.x() == 0 and rect.y() == 0 and rect.width() == img.width() and rect.height() == img.height():
                # Ya está ajustado.
                obj.svg_fit_content = True
                continue

            # Centro del contenido (antes) en escena.
            old_center_scene = it.mapToScene(
                QPointF(float(rect.x()) + float(rect.width()) / 2.0, float(rect.y()) + float(rect.height()) / 2.0)
            )

            cropped_img = img.copy(rect)
            new_pm = QPixmap.fromImage(cropped_img)
            if new_pm.isNull():
                continue

            # Aplicar recorte y re-aplicar transform con pivot al centro nuevo.
            it.setPixmap(new_pm)
            it.setScale(self._mm_per_px)
            _apply_outline_effect(it)

            obj.svg_fit_content = True
            self._apply_object_transform_to_item(obj, it)

            # Compensar posición para mantener el contenido en el mismo lugar.
            new_center_scene = it.mapToScene(QPointF(float(new_pm.width()) / 2.0, float(new_pm.height()) / 2.0))
            delta = old_center_scene - new_center_scene
            it.setPos(it.pos() + delta)

            # Persistir nueva pos al modelo.
            p = it.pos()
            nx, ny = self._scene_to_canvas_xy(float(p.x()), float(p.y()))
            obj.transform.x = float(nx)
            obj.transform.y = float(ny)

            adjusted += 1

        if adjusted:
            self._project.mark_dirty("fit_content")
            self.project_modified.emit("fit_content")
        return adjusted

    def auto_canvas_to_content(self, padding_mm: float = 0.0) -> bool:
        """Ajusta el tamaño del lienzo al contenido actual (sin márgenes).

        - Calcula el bounding box (bbox) de todos los objetos visibles.
        - Traslada TODOS los objetos para que el bbox quede desde (padding_mm, padding_mm).
        - Ajusta el canvas a (bbox + padding).

        Nota: esto NO modifica el SVG (stroke-width real). Solo mueve objetos y cambia el tamaño del lienzo,
        útil para exportar con tamaño justo.
        """
        if not self._project:
            return False
        if not self._items:
            return False

        # --- bbox en coordenadas de escena (mm)
        bbox = None
        for it in self._items.values():
            try:
                r = it.sceneBoundingRect()
            except Exception:
                continue
            bbox = r if bbox is None else bbox.united(r)

        if bbox is None or bbox.isNull():
            return False

        pad = float(padding_mm or 0.0)

        # bbox en coordenadas de canvas (mm): scene - origin
        origin = self._canvas_origin_mm()
        bbox_canvas = bbox.translated(-origin.x(), -origin.y())

        # Shift para que el contenido arranque en (pad, pad)
        shift_x = float(bbox_canvas.left() - pad)
        shift_y = float(bbox_canvas.top() - pad)

        # Nuevo tamaño de canvas (mínimo 1mm para evitar degenerados)
        new_w = max(1.0, float(bbox_canvas.width() + 2.0 * pad))
        new_h = max(1.0, float(bbox_canvas.height() + 2.0 * pad))

        changed = False

        # --- mover objetos (modelo + escena)
        if abs(shift_x) > 1e-6 or abs(shift_y) > 1e-6:
            for obj in self._project.objects:
                obj.transform.x = float(obj.transform.x) - shift_x
                obj.transform.y = float(obj.transform.y) - shift_y
            for it in self._items.values():
                it.moveBy(-shift_x, -shift_y)
            self._project.mark_dirty('canvas_autofit_translate')
            changed = True

        # --- ajustar canvas
        cur_w, cur_h = self._project.canvas_mm
        if abs(cur_w - new_w) > 1e-6 or abs(cur_h - new_h) > 1e-6:
            # set_canvas_mm ya marca dirty + emite project_modified
            self.set_canvas_mm(new_w, new_h)
            changed = True
        else:
            # Si solo translacionamos, avisar igual
            if changed:
                self.project_modified.emit()

        return changed

    def nudge_selected(self, dx_mm: float, dy_mm: float) -> None:
        """Mueve los items seleccionados (en mm) y sincroniza al modelo."""
        if not self._project:
            return
        sel = self._scene.selectedItems()
        if not sel:
            return
        for it in sel:
            if not self._item_object_id(it):
                continue
            try:
                it.moveBy(float(dx_mm), float(dy_mm))
            except Exception:
                continue
        self._sync_selected_geometry_to_model()

    def keyPressEvent(self, event) -> None:
        try:
            # Space = PAN temporal (mantener presionado)
            if (
                event.key() == Qt.Key_Space
                and not event.isAutoRepeat()
                and not self._temp_pan_active
                and not self._rotate_drag_active
                and not self._scale_drag_active
            ):
                self._temp_pan_prev_mode = self._tool_mode
                # No tiene sentido si ya estamos en PAN
                if self._temp_pan_prev_mode != ToolMode.PAN:
                    self.set_tool_mode(ToolMode.PAN)
                    self._temp_pan_active = True
                    event.accept()
                    return

            # V: mostrar medidas del objeto seleccionado (3s)
            if event.key() == Qt.Key_V and not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
                self._show_selected_size_overlay(seconds=3)
                event.accept()
                return

            # S: toggle snap de movimiento (drag raster) ON/OFF
            if event.key() == Qt.Key_S and not event.isAutoRepeat():
                self._move_snap_enabled = not getattr(self, "_move_snap_enabled", False)
                self._overlay_aux_text = "SNAP ON" if self._move_snap_enabled else "SNAP OFF"
                self._overlay_aux_until_ms = int(time.time() * 1000) + 900
                if not self._move_snap_enabled:
                    self._clear_move_snap_guides()
                self.viewport().update()
                event.accept()
                return


            # Flechas: mover selección por pasos (mm)
            if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                step = 1.0
                if event.modifiers() & Qt.ShiftModifier:
                    step = 10.0
                elif event.modifiers() & Qt.AltModifier:
                    step = 0.1

                dx = 0.0
                dy = 0.0
                if event.key() == Qt.Key_Left:
                    dx = -step
                elif event.key() == Qt.Key_Right:
                    dx = step
                elif event.key() == Qt.Key_Up:
                    dy = -step
                elif event.key() == Qt.Key_Down:
                    dy = step

                self.nudge_selected(dx, dy)
                event.accept()
                return

            if event.key() == Qt.Key_Delete:
                self.delete_selected()
                event.accept()
                return

            if event.matches(event.StandardKey.Copy):
                self.copy_selected()
                event.accept()
                return

            if event.matches(event.StandardKey.Paste):
                self.paste_clipboard()
                event.accept()
                return
        except Exception:
            pass
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        # Fin del PAN temporal
        try:
            if (
                event.key() == Qt.Key_Space
                and not event.isAutoRepeat()
                and self._temp_pan_active
            ):
                prev = self._temp_pan_prev_mode
                self._temp_pan_prev_mode = None
                self._temp_pan_active = False
                if prev is not None:
                    self.set_tool_mode(prev)
                event.accept()
                return
        except Exception:
            pass
        super().keyReleaseEvent(event)


    def mousePressEvent(self, event) -> None:
        # Middle button: pan view by scrolling.
        try:
            btn = event.button()
        except Exception:
            btn = None
                # ToolMode.ROTATE: click+drag del gizmo para rotación de grupo.
        if btn == Qt.LeftButton and self._tool_mode == ToolMode.ROTATE and (not self._rotate_drag_active):
            try:
                vp = event.position().toPoint()  # Qt6
            except Exception:
                vp = event.pos()                 # Qt5 fallback
            if self._hit_test_rotate_handle(vp):
                self._begin_rotate_handle_drag(vp)
                event.accept()
                return

# ToolMode.SCALE: click en los 4 handles (esquinas) para escalar arrastrando.
        if btn == Qt.LeftButton and self._tool_mode == ToolMode.SCALE and (not self._scale_drag_active):
            try:
                vp = event.position().toPoint()  # Qt6
            except Exception:
                vp = event.pos()                 # Qt5 fallback
            hid = self._hit_test_scale_handle(vp)
            if hid is not None:
                self._begin_scale_handle_drag(int(hid))
                event.accept()
                return

        if btn == Qt.MiddleButton:
            self._mmb_panning = True
            try:
                self._mmb_last_pos = event.position().toPoint()
            except Exception:
                self._mmb_last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        # Menú contextual: forzamos apertura en RightButton (QGraphicsView a veces no dispara contextMenuEvent).
        if btn == Qt.RightButton:
            try:
                vp = event.position().toPoint()  # Qt6
            except Exception:
                vp = event.pos()                 # Qt5 fallback
            try:
                global_pos = event.globalPosition().toPoint()  # Qt6
            except Exception:
                global_pos = event.globalPos()                 # Qt5 fallback
            scene_pos = self.mapToScene(vp)
            self._open_context_menu(scene_pos, global_pos)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        # Drag del gizmo (ToolMode.ROTATE)
        if getattr(self, "_rotate_drag_active", False):
            try:
                vp = event.position().toPoint()
            except Exception:
                vp = event.pos()
            try:
                fine = bool(event.modifiers() & Qt.ShiftModifier)
            except Exception:
                fine = False
            self._update_rotate_handle_drag(vp, fine=fine)
            event.accept()
            return

        # Drag de handles (ToolMode.SCALE)
        if getattr(self, "_scale_drag_active", False):
            try:
                vp = event.position().toPoint()
            except Exception:
                vp = event.pos()
            try:
                fine = bool(event.modifiers() & Qt.ShiftModifier)
            except Exception:
                fine = False
            self._update_scale_handle_drag(vp, fine=fine)
            event.accept()
            return

        if getattr(self, "_mmb_panning", False):
            try:
                p = event.position().toPoint()
            except Exception:
                p = event.pos()
            last = getattr(self, "_mmb_last_pos", None)
            if last is not None:
                dx = p.x() - last.x()
                dy = p.y() - last.y()
                h = self.horizontalScrollBar()
                v = self.verticalScrollBar()
                h.setValue(h.value() - dx)
                v.setValue(v.value() - dy)
            self._mmb_last_pos = p
            event.accept()
            return
        super().mouseMoveEvent(event)
        # Post-drag snap (MOVE): object-snap > grid-snap (ToolMode.SELECT)
        try:
            self._maybe_apply_move_snap_after_drag(event)
        except Exception:
            pass

    def mouseReleaseEvent(self, event) -> None:
        # Finish MMB pan.
        try:
            btn = event.button()
        except Exception:
            btn = None
                # Fin de drag del gizmo (ToolMode.ROTATE)
        if getattr(self, "_rotate_drag_active", False) and btn == Qt.LeftButton:
            self._end_rotate_handle_drag()
            event.accept()
            return

# Fin de drag de handles (ToolMode.SCALE)
        if getattr(self, "_scale_drag_active", False) and btn == Qt.LeftButton:
            self._end_scale_handle_drag()
            event.accept()
            return

        if getattr(self, "_mmb_panning", False) and btn == Qt.MiddleButton:
            self._mmb_panning = False
            self._mmb_last_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self._sync_selected_geometry_to_model()
        # Limpieza de guías de move-snap
        self._clear_move_snap_guides()

    def contextMenuEvent(self, event) -> None:
        # Qt a veces envía el evento al viewport. Igual dejamos el override por si llega.
        try:
            scene_pos = self.mapToScene(event.pos())
        except Exception:
            try:
                scene_pos = self.mapToScene(event.position().toPoint())  # Qt6
            except Exception:
                scene_pos = self.mapToScene(QPoint(0, 0))
        try:
            global_pos = event.globalPos()
        except Exception:
            try:
                global_pos = event.globalPosition().toPoint()  # Qt6
            except Exception:
                global_pos = QPoint(0, 0)

        self._open_context_menu(scene_pos, global_pos)
        try:
            event.accept()
        except Exception:
            pass

    def _open_context_menu(self, scene_pos, global_pos) -> None:
        """Menú contextual unificado (se puede llamar desde mousePressEvent)."""
        try:
            selected = self._scene.selectedItems()
            has_sel = bool(selected)

            self._ensure_size_clipboard_mm()
            can_paste_w = has_sel and self._size_clipboard_has('w')
            can_paste_h = has_sel and self._size_clipboard_has('h')
            can_paste_wh = has_sel and self._size_clipboard_has('wh')

            menu = QMenu(self)

            # ----- Tamaño -----
            m_size = menu.addMenu("Tamaño")
            m_size_copy = m_size.addMenu("Copiar")
            m_size_paste = m_size.addMenu("Pegar")

            act_cw = m_size_copy.addAction("Ancho (W)")
            act_cw.setEnabled(has_sel)
            act_cw.triggered.connect(lambda checked=False: self._copy_selected_size_to_clipboard('w'))

            act_ch = m_size_copy.addAction("Alto (H)")
            act_ch.setEnabled(has_sel)
            act_ch.triggered.connect(lambda checked=False: self._copy_selected_size_to_clipboard('h'))

            act_cwh = m_size_copy.addAction("Ancho + Alto (W×H)")
            act_cwh.setEnabled(has_sel)
            act_cwh.triggered.connect(lambda checked=False: self._copy_selected_size_to_clipboard('wh'))

            act_pw = m_size_paste.addAction("Ancho (W)")
            act_pw.setEnabled(can_paste_w)
            act_pw.triggered.connect(lambda checked=False: self._paste_size_from_clipboard('w'))

            act_ph = m_size_paste.addAction("Alto (H)")
            act_ph.setEnabled(can_paste_h)
            act_ph.triggered.connect(lambda checked=False: self._paste_size_from_clipboard('h'))

            act_pwh = m_size_paste.addAction("Ancho + Alto (W×H)")
            act_pwh.setEnabled(can_paste_wh)
            act_pwh.triggered.connect(lambda checked=False: self._paste_size_from_clipboard('wh'))

            # Info de clipboard (solo visual)
            w_cb = self._size_clipboard_mm.get('w')
            h_cb = self._size_clipboard_mm.get('h')
            info = f"Clipboard: {self._fmt_mm(w_cb)} × {self._fmt_mm(h_cb)} mm"
            act_info = m_size.addAction(info)
            act_info.setEnabled(False)

            m_size.addSeparator()
            act_set = m_size.addAction("Definir tamaño…")
            act_set.setEnabled(has_sel)
            act_set.triggered.connect(self.set_selected_size_mm)

            # ----- Agrupar / Z-order / Reset -----
            if has_sel:
                menu.addSeparator()
                act_group = menu.addAction("Agrupar selección")
                act_group.setEnabled(self.can_group_selection())
                act_group.triggered.connect(self.group_selected)

                act_ungroup = menu.addAction("Desagrupar selección")
                act_ungroup.setEnabled(self.can_ungroup_selection())
                act_ungroup.triggered.connect(self.ungroup_selected)

                menu.addSeparator()
                act_front = menu.addAction("Traer al frente")
                act_front.triggered.connect(self.z_bring_to_front)
                act_back = menu.addAction("Enviar al fondo")
                act_back.triggered.connect(self.z_send_to_back)
                act_up = menu.addAction("Subir un nivel")
                act_up.triggered.connect(self.z_raise_one)
                act_down = menu.addAction("Bajar un nivel")
                act_down.triggered.connect(self.z_lower_one)

                menu.addSeparator()
                act_reset = menu.addAction("Resetear escala")
                act_reset.setEnabled(self.can_reset_scale_selection())
                act_reset.triggered.connect(self.reset_selected_scale)

            menu.exec(global_pos)

        except Exception:
            import traceback
            traceback.print_exc()
    def _item_object_id(self, it: QGraphicsItem | None) -> str | None:
        if it is None:
            return None
        try:
            v = it.data(1)
        except Exception:
            v = None
        if not v:
            return None
        return str(v)

    def _pick_target_item(self, event) -> QGraphicsItem | None:
        """Devuelve un item target para herramientas de objeto.

        Prioridad: selección actual; si no hay selección, item bajo cursor.
        """
        sel = self._scene.selectedItems()
        if sel:
            return sel[0]

        try:
            p = event.position().toPoint()
        except Exception:
            # Qt5 compat
            try:
                p = event.pos()
            except Exception:
                return None

        it = self.itemAt(p)
        if it is None:
            return None
        if not self._item_object_id(it):
            return None
        # UX: seleccionar automáticamente el item bajo cursor.
        self._scene.clearSelection()
        it.setSelected(True)
        return it

    def _apply_object_transform_to_item(self, obj: SceneObject, it: QGraphicsItem) -> None:
        """Aplica transform del modelo al item (sin tocar el scale base mm_per_px)."""
        # Posicion en escena (mm): modelo guarda coordenadas relativas al canvas.
        sx, sy = self._canvas_to_scene_xy(float(obj.transform.x), float(obj.transform.y))
        it.setPos(float(sx), float(sy))

        # QTransform centrado (rota/escala alrededor del centro del bounding box local).
        try:
            br = it.boundingRect()
            c = br.center()
        except Exception:
            c = QPointF(0, 0)

        sxm = float(obj.transform.scale_x)
        sym = float(obj.transform.scale_y)
        if obj.transform.flip_h:
            sxm *= -1.0
        if obj.transform.flip_v:
            sym *= -1.0

        t = QTransform()
        t.translate(c.x(), c.y())
        t.rotate(float(obj.transform.rotation_deg))
        t.scale(sxm, sym)
        t.translate(-c.x(), -c.y())
        it.setTransform(t)
        it.setZValue(float(obj.z))

    def _rotate_object(self, oid: str, dy: int, *, fine: bool = False) -> None:
        if not self._project:
            return
        obj = self._project.get_object(oid)
        it = self._items.get(oid)
        if not obj or not it:
            return
        old_center = self._item_scene_center(it)

        # Shift = fino (más precisión)
        step = 0.5 if fine else 5.0
        delta = (dy / 120.0) * step
        obj.transform.rotation_deg = float(obj.transform.rotation_deg) + float(delta)

        self._apply_object_transform_to_item(obj, it)
        self._lock_item_center(obj, it, old_center)

        self._project.mark_dirty("rotate")
        self.project_modified.emit("rotate")

        # UX: overlay de ángulo.
        self._show_selected_angle_overlay(float(obj.transform.rotation_deg), fine=fine)

    def _scale_object(self, oid: str, dy: int, *, fine: bool = False) -> None:
        if not self._project:
            return
        obj = self._project.get_object(oid)
        it = self._items.get(oid)
        if not obj or not it:
            return
        old_center = self._item_scene_center(it)
        steps = dy / 120.0
        base = 1.01 if fine else 1.05
        factor = float(base ** steps)
        new_sx = max(0.05, min(50.0, float(obj.transform.scale_x) * factor))
        new_sy = max(0.05, min(50.0, float(obj.transform.scale_y) * factor))
        obj.transform.scale_x = new_sx
        obj.transform.scale_y = new_sy
        self._apply_object_transform_to_item(obj, it)
        self._lock_item_center(obj, it, old_center)
        # Re-render SVG preview con compensación de grosor por escala (stroke fijo visualmente).
        self._rerender_svg_preview_for_object(oid)
        self._project.mark_dirty("scale")
        self.project_modified.emit("scale")

        # UX: mostrar medidas actuales del objeto durante un instante.
        self._show_selected_size_overlay(seconds=3)

    def _sync_selected_geometry_to_model(self) -> None:
        """Sincroniza posicion (x,y) de los items seleccionados al modelo.

        Se dispara al soltar el mouse para que el .RCS preserve lo que el usuario movio.
        """
        if not self._project:
            return

        changed = False
        for it in self._scene.selectedItems():
            oid = self._item_object_id(it)
            if not oid:
                continue
            obj = self._project.get_object(oid)
            if not obj:
                continue
            p = it.pos()
            nx, ny = self._scene_to_canvas_xy(float(p.x()), float(p.y()))
            if abs(nx - float(obj.transform.x)) > 1e-6 or abs(ny - float(obj.transform.y)) > 1e-6:
                obj.transform.x = float(nx)
                obj.transform.y = float(ny)
                changed = True

        if changed:
            self._project.mark_dirty("move")
            self.project_modified.emit("move")

    def _rerender_svg_previews(self) -> None:
        if self._project is None:
            return

        # Re-render solo pixmaps SVG (los que tienen data(0) = svg_abs_path).
        for oid, it in list(self._items.items()):
            try:
                if not isinstance(it, QGraphicsPixmapItem):
                    continue
                if not it.data(0):
                    continue
                self._rerender_svg_preview_for_object(str(oid))
            except Exception:
                continue

    def _object_effective_scale(self, obj: SceneObject) -> float:
        """Escala escalar para compensaciones de preview.

        Usamos media geométrica para soportar escalas no-uniformes sin
        sobrecompensar.
        """
        try:
            sx = float(getattr(obj.transform, 'scale_x', 1.0) or 1.0)
            sy = float(getattr(obj.transform, 'scale_y', 1.0) or 1.0)
        except Exception:
            return 1.0

        s = (abs(sx * sy) ** 0.5)
        if s <= 0:
            s = 1.0
        return max(1e-3, float(s))

    def _crop_pixmap_to_alpha_bbox(self, pm: QPixmap) -> QPixmap:
        """Recorta un QPixmap al bbox alfa (para svg_fit_content).

        Nota: el bbox puede variar 1px según rasterización (DPR/tema).
        """
        try:
            img0 = pm.toImage()
            rect = _alpha_bbox(img0, alpha_threshold=1)
            if rect is None:
                return pm
            if rect.x() == 0 and rect.y() == 0 and rect.width() == pm.width() and rect.height() == pm.height():
                return pm
            return pm.copy(rect)
        except Exception:
            return pm

    def _rerender_svg_preview_for_object(self, oid: str) -> None:
        if not self._project:
            return
        obj = self._project.get_object(oid)
        it = self._items.get(oid)
        if not obj or not it:
            return
        if obj.type != 'svg':
            return
        if not isinstance(it, QGraphicsPixmapItem):
            return

        svg_abs = it.data(0)
        svg_path = Path(str(svg_abs)) if svg_abs else None
        if (not svg_path) or (not svg_path.exists()):
            # Fallback: resolver desde el proyecto si se movió el root.
            try:
                root = self._project.components_root_path(cwd=Path.cwd())  # type: ignore[attr-defined]
            except Exception:
                root = Path(getattr(self._project, 'components_root', 'componentes')).resolve()
            if obj.source:
                svg_path = (root / str(obj.source)).resolve()

        if not svg_path or not svg_path.exists():
            return

        old_center = self._item_scene_center(it)
        stroke_thick, outline_thick = self._effective_preview_thickness()
        pm = self._render_svg_preview_pixmap(
            svg_path,
            stroke_thick=stroke_thick,
            outline_thick=outline_thick,
            obj_scale=self._object_effective_scale(obj),
        )

        if getattr(obj, 'svg_fit_content', False):
            pm = self._crop_pixmap_to_alpha_bbox(pm)

        if not pm.isNull():
            it.setPixmap(pm)
            try:
                it.setScale(self._mm_per_px)
            except Exception:
                pass
            _apply_outline_effect(it)

        # Mantener centro visual estable (evita 'salto' si cambia el bbox 1px).
        self._lock_item_center(obj, it, old_center)

    # ------------------------------ Proyecto

    def _sheet_size_mm(self) -> tuple[float, float]:
        """Devuelve el tamaño (mm) de la hoja de trabajo visible.

        La hoja es al menos SHEET_MIN_MM, pero crece si el canvas_mm del
        proyecto es mayor.
        """
        if not self._project:
            return float(self.SHEET_MIN_MM[0]), float(self.SHEET_MIN_MM[1])
        cw, ch = self._project.canvas_mm
        sw = max(float(self.SHEET_MIN_MM[0]), float(cw))
        sh = max(float(self.SHEET_MIN_MM[1]), float(ch))
        return sw, sh

    def _sheet_rect(self) -> QRectF:
        sw, sh = self._sheet_size_mm()
        return QRectF(0.0, 0.0, float(sw), float(sh))

    def _canvas_rect(self) -> QRectF:
        if not self._project:
            return QRectF(0.0, 0.0, 0.0, 0.0)
        sw, sh = self._sheet_size_mm()
        cw, ch = self._project.canvas_mm
        cw = float(max(1.0, cw))
        ch = float(max(1.0, ch))
        # Center canvas inside the visible sheet (SHEET_MIN_MM).
        x0 = (float(sw) - cw) / 2.0
        y0 = (float(sh) - ch) / 2.0
        if x0 < 0.0:
            x0 = 0.0
        if y0 < 0.0:
            y0 = 0.0
        return QRectF(x0, y0, cw, ch)

    def _canvas_origin_mm(self) -> QPointF:
        """Top-left del canvas (mm) en coordenadas de escena."""
        try:
            r = self._canvas_rect()
            return r.topLeft()
        except Exception:
            return QPointF(0.0, 0.0)

    def _scene_to_canvas_xy(self, x_scene: float, y_scene: float) -> tuple[float, float]:
        o = self._canvas_origin_mm()
        return float(x_scene - o.x()), float(y_scene - o.y())

    def _canvas_to_scene_xy(self, x_canvas: float, y_canvas: float) -> tuple[float, float]:
        o = self._canvas_origin_mm()
        return float(x_canvas + o.x()), float(y_canvas + o.y())

    def _item_scene_center(self, it: QGraphicsItem) -> QPointF:
        try:
            br = it.boundingRect()
            return it.mapToScene(br.center())
        except Exception:
            return it.scenePos()

    def _lock_item_center(self, obj: SceneObject, it: QGraphicsItem, old_center: QPointF) -> None:
        """Mantiene el centro del item fijo en escena tras rotar/escalar."""
        try:
            new_center = self._item_scene_center(it)
            dx = float(old_center.x() - new_center.x())
            dy = float(old_center.y() - new_center.y())
            if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                it.moveBy(dx, dy)
            # Sync model pos (canvas coords)
            p = it.pos()
            nx, ny = self._scene_to_canvas_xy(float(p.x()), float(p.y()))
            obj.transform.x = float(nx)
            obj.transform.y = float(ny)
        except Exception:
            pass

    def set_project(self, project: Project) -> None:
        self._project = project
        # Los ajustes de arranque deben aplicarse por proyecto (no por rebuild).
        self._startup_anchor_applied = False
        self._startup_zoom_after_fit_applied = False
        self._startup_view_state_applied = False
        self._rebuild_scene_from_project()

    def set_canvas_mm(self, w_mm: float, h_mm: float) -> None:
        """Ajusta el tamano del lienzo en mm."""
        if not self._project:
            return
        old_origin = self._canvas_origin_mm()
        self._project.set_canvas_mm(w_mm, h_mm)
        # La hoja visible tiene un minimo y muestra el canvas como un rectangulo.
        self._scene.setSceneRect(self._sheet_rect())
        new_origin = self._canvas_origin_mm()
        dx = float(new_origin.x() - old_origin.x())
        dy = float(new_origin.y() - old_origin.y())
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            # Mover items visuales: el modelo queda en coords relativas al canvas.
            for it in list(self._items.values()):
                try:
                    it.moveBy(dx, dy)
                except Exception:
                    pass
        # no re-fit automatico: el usuario controla el zoom
        self._recalc_zoom_limits(clamp_current=True)
        self.viewport().update()
        self.project_modified.emit("canvas_size")

    def _rebuild_scene_from_project(self) -> None:
        self._scene.clear()
        self._items.clear()

        if not self._project:
            return

        # La escena siempre muestra una "hoja" mínima y dentro de ella se
        # dibuja el rectángulo del lienzo real (canvas_mm).
        sheet_rect = self._sheet_rect()
        canvas_rect = self._canvas_rect()
        self._scene.setSceneRect(sheet_rect)

        # Grilla (solo dibujada en drawBackground)

        # GMPR base preview (SVG embebido): se dibuja por debajo y no participa
        # de selección / snap / modelo.
        self._gmpr_base_item = None
        self._add_gmpr_base_preview_if_needed()

        # Items
        for obj in self._project.objects:
            if obj.type == 'svg':
                self._add_svg_item(obj)
            elif obj.type == 'text':
                self._add_text_item(obj)
            elif obj.type == 'raster':
                self._add_raster_item(obj)

        # Fit a la hoja (no al canvas), así el usuario ve el área disponible.
        self.fitInView(sheet_rect, Qt.KeepAspectRatio)
        self._sync_zoom_from_view_transform()
        self._apply_startup_zoom_after_fit()
        self._apply_startup_view_anchor()
        self._apply_startup_view_state()
        # Respeta el modo activo (PICK = no drag-move)
        self._apply_items_movable_flags()

    # ------------------------------ Dibujo
    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.fillRect(rect, self._bg_color)

        if not self._project:
            painter.restore()
            return

        grid = float(self._project.grid.size_mm)
        if grid <= 0.1:
            painter.restore()
            return

        # Limitamos la grilla al área de hoja para evitar el efecto “infinito”
        # cuando el usuario se aleja mucho.
        sheet_rect = self._sheet_rect()
        clip = rect.intersected(sheet_rect.adjusted(-grid, -grid, grid, grid))
        if clip.isNull() or clip.width() <= 0.0 or clip.height() <= 0.0:
            painter.restore()
            return

        # Grilla nítida: sin antialias + líneas cosméticas (1px en pantalla).
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        try:
            painter.setClipRect(clip)
        except Exception:
            pass

        left = int(clip.left() // grid) * grid
        top = int(clip.top() // grid) * grid

        # minor
        pen_minor = QPen(self._grid_minor)
        pen_minor.setCosmetic(True)
        pen_minor.setWidthF(0.0)
        painter.setPen(pen_minor)

        x = left
        while x < clip.right():
            painter.drawLine(x, clip.top(), x, clip.bottom())
            x += grid

        y = top
        while y < clip.bottom():
            painter.drawLine(clip.left(), y, clip.right(), y)
            y += grid

        # major (cada 5)
        pen_major = QPen(self._grid_major)
        pen_major.setCosmetic(True)
        pen_major.setWidthF(0.0)
        painter.setPen(pen_major)

        major = grid * 5
        x = int(clip.left() // major) * major
        while x < clip.right():
            painter.drawLine(x, clip.top(), x, clip.bottom())
            x += major

        y = int(clip.top() // major) * major
        while y < clip.bottom():
            painter.drawLine(clip.left(), y, clip.right(), y)
            y += major

        painter.restore()



    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja guías encima de la grilla: hoja y área de lienzo.

        - Hoja: escena (mínimo 500x500mm por defecto)
        - Lienzo: project.canvas_mm (área de trabajo real)
        """
        _ = rect
        if not self._project:
            return

        sheet_rect = self._sheet_rect()
        canvas_rect = self._canvas_rect()

        # Colores sutiles según tema.
        if (self._theme_id or '').lower() == 'light':
            col_sheet = QColor(120, 120, 120)
            col_canvas = QColor(40, 40, 40)
        else:
            col_sheet = QColor(110, 110, 110)
            col_canvas = QColor(190, 190, 190)

        painter.save()

        pen_sheet = QPen(col_sheet)
        pen_sheet.setCosmetic(True)
        pen_sheet.setWidthF(0.0)
        painter.setPen(pen_sheet)
        painter.drawRect(sheet_rect)

        pen_canvas = QPen(col_canvas)
        pen_canvas.setCosmetic(True)
        pen_canvas.setWidthF(0.0)
        painter.setPen(pen_canvas)
        painter.drawRect(canvas_rect)

        painter.restore()

        # ------------------------------ Move-snap guides (scene coords, cosmetic pen)
        self._draw_move_snap_guides(painter, canvas_rect)

        # ------------------------------ Overlay de medición (en viewport)
        # Never let overlay rendering kill the whole foreground pass.
        try:
            self._draw_measure_overlays(painter)
        except Exception:
            import traceback
            traceback.print_exc()


    def _draw_measure_overlays(self, painter: QPainter) -> None:
        """Dibuja overlays de medición en coordenadas de viewport (no escalan con zoom)."""
        if not self._project:
            return

        lines: list[str] = []

        # Hoja (scene) + Lienzo (área de trabajo real)
        try:
            sr = self._sheet_rect()
            lines.append(f"Hoja: {float(sr.width()):.2f} x {float(sr.height()):.2f} mm")
        except Exception:
            pass

        try:
            cw, ch = self._project.canvas_mm
            lines.append(f"Lienzo: {float(cw):.2f} x {float(ch):.2f} mm")
        except Exception:
            pass

        # Zoom actual del view (no depende del project)
        try:
            z = float(getattr(self, "_zoom", 1.0) or 1.0)
            lines.append(f"Zoom: {z * 100.0:.0f}%")
        except Exception:
            pass


        # Indicador persistente (solo cuando está activo)
        if getattr(self, "_move_snap_enabled", False):
            lines.append("SNAP ON")

        now_ms = int(QDateTime.currentMSecsSinceEpoch())

        obj_until = int(getattr(self, "_overlay_obj_until_ms", 0) or 0)
        obj_text = getattr(self, "_overlay_obj_text", None)
        if obj_until and now_ms < obj_until and obj_text:
            lines.append(str(obj_text))

        aux_until = int(getattr(self, "_overlay_aux_until_ms", 0) or 0)
        aux_text = getattr(self, "_overlay_aux_text", None)
        if aux_until and now_ms < aux_until and aux_text:
            lines.append(str(aux_text))

        if not lines:
            # Aún así, en modo escala, dibujamos handles si corresponde.
            try:
                painter.save()
                painter.resetTransform()
                self._draw_scale_handles_overlay(painter)
            finally:
                painter.restore()
            return

        painter.save()
        painter.resetTransform()
        try:
            # Caja de fondo
            font = painter.font()
            font.setPointSize(max(8, font.pointSize()))
            painter.setFont(font)

            padding = 6
            x0, y0 = 10, 10
            fm = QFontMetrics(font)
            w = max(fm.horizontalAdvance(s) for s in lines) + padding * 2
            h = (fm.height() * len(lines)) + padding * 2

            bg = QColor(0, 0, 0, 140)
            fg = QColor(255, 230, 0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(QRectF(x0, y0, w, h), 4.0, 4.0)

            painter.setPen(fg)
            ty = y0 + padding + fm.ascent()
            for s in lines:
                painter.drawText(x0 + padding, ty, s)
                ty += fm.height()

            # Gizmo de rotación (cuando ROTATE está activo).
            self._draw_rotate_handle_overlay(painter)

            # Handles de escala (8: esquinas + medios) cuando la herramienta SCALE está activa.
            self._draw_scale_handles_overlay(painter)
        finally:
            painter.restore()


    # ---------------------------------------------------------------------
    # Move-snap (drag raster items) — Hotfix 0.3.10.2.63
    # ---------------------------------------------------------------------

    def _move_snap_threshold_scene(self) -> float:
        """Umbral de enganche en unidades de escena (mm aprox), derivado de px en viewport."""
        try:
            px = float(getattr(self, "_move_snap_threshold_px", 12.0) or 12.0)
        except Exception:
            px = 12.0
        try:
            s = float(self.transform().m11() or 1.0)
        except Exception:
            s = 1.0
        if s <= 1e-6:
            return px
        return px / s

    def _set_move_snap_guides(self, vx: float | None, hy: float | None) -> None:
        """Actualiza guías cosméticas (scene coords) y repinta si cambian."""
        try:
            g = self._move_snap_guides_scene
        except Exception:
            self._move_snap_guides_scene = {"vx": None, "hy": None}
            g = self._move_snap_guides_scene
        changed = (g.get("vx") != vx) or (g.get("hy") != hy)
        if changed:
            g["vx"] = vx
            g["hy"] = hy
            try:
                self.viewport().update()
            except Exception:
                pass

    def _clear_move_snap_guides(self) -> None:
        self._set_move_snap_guides(None, None)

    def _draw_move_snap_guides(self, painter: QPainter, canvas_rect: QRectF) -> None:
        """Dibuja guías amarillas cuando hay object-snap (no escalan con zoom)."""
        try:
            g = self._move_snap_guides_scene
        except Exception:
            return
        vx = g.get("vx")
        hy = g.get("hy")
        if vx is None and hy is None:
            return

        painter.save()
        pen = QPen(QColor(255, 230, 0))
        pen.setCosmetic(True)
        pen.setWidthF(0.0)
        painter.setPen(pen)

        if vx is not None:
            x = float(vx)
            painter.drawLine(QPointF(x, float(canvas_rect.top())), QPointF(x, float(canvas_rect.bottom())))
        if hy is not None:
            y = float(hy)
            painter.drawLine(QPointF(float(canvas_rect.left()), y), QPointF(float(canvas_rect.right()), y))

        painter.restore()

    def _maybe_apply_move_snap_after_drag(self, event: QMouseEvent) -> None:
        """Snap de movimiento post-Qt-drag: Object-snap (edge/center) > Grid-snap.

        - Solo ToolMode.SELECT
        - Solo raster items (QGraphicsPixmapItem con object_id)
        - Si hay selección múltiple de raster → NO snap (evita desync de deltas)
        - Shift: step fino (0.1mm)
        - Alt: snap temporal OFF mientras arrastra
        """
        if not self._project:
            return
        if getattr(self, "_tool_mode", None) != ToolMode.SELECT:
            self._clear_move_snap_guides()
            return
        if not getattr(self, "_move_snap_enabled", False):
            self._clear_move_snap_guides()
            return

        # Sólo durante drag con botón izquierdo
        if not (event.buttons() & Qt.LeftButton):
            self._clear_move_snap_guides()
            return

        # Override temporal: Alt
        if event.modifiers() & Qt.AltModifier:
            self._clear_move_snap_guides()
            return

        # No interferir con otros drags especiales
        if getattr(self, "_scale_drag_active", False) or getattr(self, "_rotate_drag_active", False) or getattr(self, "_is_panning_mmb", False):
            self._clear_move_snap_guides()
            return

        grabber = None
        try:
            grabber = self._scene.mouseGrabberItem()
        except Exception:
            grabber = None

        if grabber is None:
            self._clear_move_snap_guides()
            return

        # Solo raster items "reales" (pixmap) con object_id
        try:
            is_raster = isinstance(grabber, QGraphicsPixmapItem)
        except Exception:
            is_raster = False
        if not is_raster:
            self._clear_move_snap_guides()
            return

        oid = self._item_object_id(grabber)
        if not oid:
            self._clear_move_snap_guides()
            return

        # Selección simple de raster (riesgo controlado)
        sel_rasters = [
            it for it in self._scene.selectedItems()
            if isinstance(it, QGraphicsPixmapItem) and self._item_object_id(it)
        ]
        if len(sel_rasters) != 1 or sel_rasters[0] is not grabber:
            self._clear_move_snap_guides()
            return

        fine = bool(event.modifiers() & Qt.ShiftModifier)
        step_mm = float(self._move_snap_fine_step_mm if fine else self._move_snap_grid_step_mm)
        step_mm = max(step_mm, 1e-6)

        # -------------------- Object-snap (prioridad)
        thr = float(self._move_snap_threshold_scene())
        mr = grabber.sceneBoundingRect()

        mx = (float(mr.left()), float(mr.center().x()), float(mr.right()))
        my = (float(mr.top()), float(mr.center().y()), float(mr.bottom()))

        best_dx: float | None = None
        best_dy: float | None = None
        best_vx: float | None = None
        best_hy: float | None = None

        # Candidatos: otros raster (no seleccionados) con bbox en escena.
        # Nota: usamos bbox axis-aligned (sceneBoundingRect) por estabilidad.
        for it in self._items.values():
            if it is grabber:
                continue
            if not isinstance(it, QGraphicsPixmapItem):
                continue
            if self._item_object_id(it) is None:
                continue
            if it.isSelected():
                continue

            tr = it.sceneBoundingRect()
            tx = (float(tr.left()), float(tr.center().x()), float(tr.right()))
            ty = (float(tr.top()), float(tr.center().y()), float(tr.bottom()))

            # X axis (edge/center)
            for mval in mx:
                for tval in tx:
                    d = tval - mval
                    if abs(d) <= thr and (best_dx is None or abs(d) < abs(best_dx)):
                        best_dx = d
                        best_vx = tval

            # Y axis (edge/center)
            for mval in my:
                for tval in ty:
                    d = tval - mval
                    if abs(d) <= thr and (best_dy is None or abs(d) < abs(best_dy)):
                        best_dy = d
                        best_hy = tval

        # Aplicar object-snap (si corresponde)
        pos = grabber.pos()
        x = float(pos.x()) + (float(best_dx) if best_dx is not None else 0.0)
        y = float(pos.y()) + (float(best_dy) if best_dy is not None else 0.0)
        grabber.setPos(QPointF(x, y))

        # Guías solo si hubo object-snap (no para grilla)
        self._set_move_snap_guides(best_vx, best_hy)

        # -------------------- Grid-snap (si no hubo object-snap en ese eje)
        # Nota: snap en coords de canvas (mm) para mantener consistencia con transform.x/y.
        if best_dx is None or best_dy is None:
            canvas_rect = self._canvas_rect()
            origin = canvas_rect.topLeft()
            pos2 = grabber.pos()
            cx = float(pos2.x()) - float(origin.x())
            cy = float(pos2.y()) - float(origin.y())

            if best_dx is None:
                cx_s = round(cx / step_mm) * step_mm
                x = float(origin.x()) + cx_s
            else:
                x = float(pos2.x())

            if best_dy is None:
                cy_s = round(cy / step_mm) * step_mm
                y = float(origin.y()) + cy_s
            else:
                y = float(pos2.y())

            grabber.setPos(QPointF(x, y))

    def _selected_bbox_scene_rect(self) -> QRectF | None:
        """BBox unido de la selección en coordenadas de escena (mm)."""
        try:
            items = list(self.scene().selectedItems()) if self.scene() else []
        except Exception:
            items = []
        if not items:
            return None
        bbox: QRectF | None = None
        for it in items:
            try:
                r = it.sceneBoundingRect()
            except Exception:
                continue
            if bbox is None:
                bbox = QRectF(r)
            else:
                bbox = bbox.united(r)
        return bbox

    def _scale_handle_rects_viewport(self) -> dict[int, QRect]:
        """Rectángulos (viewport px) de los 8 handles de escala de la selección (4 esquinas + 4 medios)."""
        if self._tool_mode != ToolMode.SCALE:
            return {}
        bbox = self._selected_bbox_scene_rect()
        if bbox is None:
            return {}
        try:
            if bbox.width() <= 0 or bbox.height() <= 0:
                return {}
        except Exception:
            return {}
        hs = int(getattr(self, "_scale_handle_px", 6) or 6)
        handles = {
            0: bbox.topLeft(),
            1: bbox.topRight(),
            2: bbox.bottomRight(),
            3: bbox.bottomLeft(),
            4: QPointF((bbox.left() + bbox.right()) * 0.5, bbox.top()),      # top mid
            5: QPointF(bbox.right(), (bbox.top() + bbox.bottom()) * 0.5),    # right mid
            6: QPointF((bbox.left() + bbox.right()) * 0.5, bbox.bottom()),   # bottom mid
            7: QPointF(bbox.left(), (bbox.top() + bbox.bottom()) * 0.5),     # left mid
        }
        out: dict[int, QRect] = {}
        for hid, pt_scene in handles.items():
            try:
                vp = self.mapFromScene(pt_scene)
                out[int(hid)] = QRect(int(vp.x()) - hs, int(vp.y()) - hs, hs * 2, hs * 2)
            except Exception:
                continue
        return out

    def _draw_scale_handles_overlay(self, painter: QPainter) -> None:
        """Dibuja 8 "puntitos" (handles) para escalar en ToolMode.SCALE."""
        if self._tool_mode != ToolMode.SCALE:
            return
        rects = self._scale_handle_rects_viewport()
        if not rects:
            return
        painter.save()
        try:
            fg = QColor(255, 230, 0)
            painter.setPen(fg)
            painter.setBrush(fg)
            for r in rects.values():
                painter.drawRect(QRectF(r))
        finally:
            painter.restore()


    # -------------------------------
    # Rotate gizmo (ToolMode.ROTATE)
    # -------------------------------
    def _rotate_handle_rect_viewport(self) -> QRect | None:
        if self._tool_mode != ToolMode.ROTATE:
            return None
        bbox = self._selected_bbox_scene_rect()
        if bbox is None:
            return None
        try:
            if bbox.width() <= 0 or bbox.height() <= 0:
                return None
        except Exception:
            return None

        try:
            top_center_scene = QPointF((bbox.left() + bbox.right()) * 0.5, bbox.top())
            vp = self.mapFromScene(top_center_scene)
        except Exception:
            return None

        hs = int(getattr(self, "_rotate_handle_px", 10) or 10)
        off = int(getattr(self, "_rotate_handle_offset_px", 28) or 28)
        cx = int(vp.x())
        cy = int(vp.y()) - off
        return QRect(cx - hs, cy - hs, hs * 2, hs * 2)

    def _hit_test_rotate_handle(self, vp_pos) -> bool:
        r = self._rotate_handle_rect_viewport()
        if r is None:
            return False
        try:
            return bool(r.contains(int(vp_pos.x()), int(vp_pos.y())))
        except Exception:
            return False

    def _draw_rotate_handle_overlay(self, painter: QPainter) -> None:
        if self._tool_mode != ToolMode.ROTATE:
            return
        r = self._rotate_handle_rect_viewport()
        if r is None:
            return

        painter.save()
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)

            pen = QPen(QColor(255, 230, 0), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            # línea hacia el bbox
            bbox = self._selected_bbox_scene_rect()
            if bbox is not None:
                try:
                    top_center_scene = QPointF((bbox.left() + bbox.right()) * 0.5, bbox.top())
                    vp_tc = self.mapFromScene(top_center_scene)
                    painter.drawLine(int(vp_tc.x()), int(vp_tc.y()), int(r.center().x()), int(r.center().y()))
                except Exception:
                    pass

            painter.drawEllipse(r)

            # símbolo (si la fuente lo soporta, queda lindo; si no, igual es clickable)
            painter.setPen(QPen(QColor(255, 230, 0), 1))
            f = QFont(painter.font())
            f.setBold(True)
            f.setPointSize(max(8, int(f.pointSize() * 1.1)))
            painter.setFont(f)
            painter.drawText(r, Qt.AlignCenter, "⟲")
        finally:
            painter.restore()

    def _begin_rotate_handle_drag(self, vp_pos) -> None:
        if self._project is None:
            return
        bbox = self._selected_bbox_scene_rect()
        if bbox is None:
            return

        pivot = bbox.center()
        sp = self.mapToScene(vp_pos)
        try:
            a0 = math.atan2(float(sp.y()) - float(pivot.y()), float(sp.x()) - float(pivot.x()))
        except Exception:
            a0 = 0.0

        snap: dict[str, dict[str, object]] = {}
        for it in self.scene().selectedItems():
            oid = self._item_object_id(it)
            if not oid:
                continue
            obj = self._project.get_object(str(oid))
            if not obj:
                continue
            try:
                center0 = self._item_scene_center(it)
                rot0 = float(getattr(obj.transform, "rotation_deg", 0.0) or 0.0)
                snap[str(oid)] = {"rot0": rot0, "center0": QPointF(float(center0.x()), float(center0.y()))}
            except Exception:
                continue

        if not snap:
            return

        self._rotate_drag_active = True
        self._rotate_drag_pivot_scene = QPointF(float(pivot.x()), float(pivot.y()))
        self._rotate_drag_angle0_rad = float(a0)
        self._rotate_drag_snap = snap

        self._overlay_aux_text = "ΔÁngulo: 0° (snap 5° | Shift fino 1°)"
        self._overlay_aux_until_ms = int(time.time() * 1000) + 800
        self.viewport().update()

    def _update_rotate_handle_drag(self, vp_pos, *, fine: bool = False) -> None:
        if not self._rotate_drag_active:
            return
        if self._project is None:
            return
        pivot = self._rotate_drag_pivot_scene
        if pivot is None:
            return

        sp = self.mapToScene(vp_pos)
        try:
            a1 = math.atan2(float(sp.y()) - float(pivot.y()), float(sp.x()) - float(pivot.x()))
        except Exception:
            return

        delta_deg = math.degrees(float(a1) - float(self._rotate_drag_angle0_rad))

        # normalizar a [-180, +180] para estabilidad visual
        try:
            delta_deg = (delta_deg + 180.0) % 360.0 - 180.0
        except Exception:
            pass

        # CNC-friendly: snap por defecto a 5°; Shift => fino 1°
        step = 1.0 if fine else 5.0
        try:
            delta_deg = round(delta_deg / step) * step
        except Exception:
            pass

        rad = math.radians(delta_deg)
        c = math.cos(rad)
        s = math.sin(rad)

        for oid, d in self._rotate_drag_snap.items():
            it = self._items.get(str(oid))
            if it is None:
                continue
            obj = self._project.get_object(str(oid))
            if not obj:
                continue
            try:
                rot0 = float(d.get("rot0", 0.0))
                center0 = d.get("center0")
                if not isinstance(center0, QPointF):
                    continue

                # 1) actualizar rotación
                obj.transform.rotation_deg = rot0 + float(delta_deg)
                self._apply_object_transform_to_item(obj, it)

                # 2) rotar centro alrededor del pivot (grupo real)
                dx = float(center0.x()) - float(pivot.x())
                dy = float(center0.y()) - float(pivot.y())
                nx = float(pivot.x()) + dx * c - dy * s
                ny = float(pivot.y()) + dx * s + dy * c
                self._set_item_center(obj, it, QPointF(nx, ny))

                if obj.type == "svg":
                    self._rerender_svg_preview_for_object(str(oid))
            except Exception:
                continue

        try:
            tag = "Shift fino 1°" if fine else "snap 5°"
            self._overlay_aux_text = f"ΔÁngulo: {delta_deg:+.0f}° ({tag})"
            self._overlay_aux_until_ms = int(time.time() * 1000) + 800
        except Exception:
            pass
        self.viewport().update()

    def _end_rotate_handle_drag(self) -> None:
        if not self._rotate_drag_active:
            return
        self._rotate_drag_active = False
        self._rotate_drag_pivot_scene = None
        self._rotate_drag_angle0_rad = 0.0
        self._rotate_drag_snap = {}

        if self._project is not None:
            self._project.mark_dirty("rotate_handle")
        self.project_modified.emit("rotate_handle")
        self.viewport().update()

    def _hit_test_scale_handle(self, vp_pos) -> int | None:
        """Devuelve el id del handle (0..3) si el click cae dentro; si no, None."""
        rects = self._scale_handle_rects_viewport()
        if not rects:
            return None
        try:
            x = int(vp_pos.x())
            y = int(vp_pos.y())
        except Exception:
            return None
        for hid, r in rects.items():
            try:
                if r.contains(x, y):
                    return int(hid)
            except Exception:
                continue
        return None

    def _begin_scale_handle_drag(self, hid: int) -> None:
        bbox0 = self._selected_bbox_scene_rect()
        if bbox0 is None:
            return
        try:
            w0 = float(bbox0.width())
            h0 = float(bbox0.height())
        except Exception:
            return
        if (w0 <= 0) or (h0 <= 0):
            return

        handles = {
            0: bbox0.topLeft(),
            1: bbox0.topRight(),
            2: bbox0.bottomRight(),
            3: bbox0.bottomLeft(),
            4: QPointF((bbox0.left() + bbox0.right()) * 0.5, bbox0.top()),
            5: QPointF(bbox0.right(), (bbox0.top() + bbox0.bottom()) * 0.5),
            6: QPointF((bbox0.left() + bbox0.right()) * 0.5, bbox0.bottom()),
            7: QPointF(bbox0.left(), (bbox0.top() + bbox0.bottom()) * 0.5),
        }
        pivots = {
            0: bbox0.bottomRight(),
            1: bbox0.bottomLeft(),
            2: bbox0.topLeft(),
            3: bbox0.topRight(),
            4: QPointF((bbox0.left() + bbox0.right()) * 0.5, bbox0.bottom()),
            5: QPointF(bbox0.left(), (bbox0.top() + bbox0.bottom()) * 0.5),
            6: QPointF((bbox0.left() + bbox0.right()) * 0.5, bbox0.top()),
            7: QPointF(bbox0.right(), (bbox0.top() + bbox0.bottom()) * 0.5),
        }

        pivot = pivots.get(int(hid))
        c0 = handles.get(int(hid))
        if pivot is None or c0 is None:
            return

        snap: dict[str, dict[str, float]] = {}

        try:
            items = list(self.scene().selectedItems()) if self.scene() else []
        except Exception:
            items = []
        if not items:
            return

        for it in items:
            oid = self._item_object_id(it)
            if not oid:
                continue
            obj = self._project.get_object(str(oid)) if self._project else None
            if not obj:
                continue
            try:
                base_sx = float(getattr(obj.transform, "scale_x", 1.0) or 1.0)
                base_sy = float(getattr(obj.transform, "scale_y", 1.0) or 1.0)
                ctr = self._item_scene_center(it)
                rel = ctr - pivot
                snap[str(oid)] = {
                    "base_sx": base_sx,
                    "base_sy": base_sy,
                    "rel_x": float(rel.x()),
                    "rel_y": float(rel.y()),
                }
            except Exception:
                continue

        if not snap:
            return

        self._scale_drag_active = True
        self._scale_drag_handle = int(hid)
        self._scale_drag_pivot_scene = QPointF(pivot)
        self._scale_drag_bbox0_scene = QRectF(bbox0)
        self._scale_drag_corner0_scene = QPointF(c0)
        self._scale_drag_snap = snap

    def _update_scale_handle_drag(self, vp_pos, *, fine: bool = False) -> None:
        if not self._scale_drag_active:
            return
        if self._project is None:
            return
        bbox0 = self._scale_drag_bbox0_scene
        pivot = self._scale_drag_pivot_scene
        c0 = self._scale_drag_corner0_scene
        hid = self._scale_drag_handle
        if bbox0 is None or pivot is None or c0 is None or hid is None:
            return

        try:
            sp = self.mapToScene(vp_pos)
            mx = float(sp.x())
            my = float(sp.y())
        except Exception:
            return

        w0 = float(max(1e-9, bbox0.width()))
        h0 = float(max(1e-9, bbox0.height()))

        # ancho/alto nuevos según el handle arrastrado (pivot fijo en el opuesto)
        if hid == 0:  # TL, pivot BR
            nw = float(pivot.x() - mx)
            nh = float(pivot.y() - my)
        elif hid == 1:  # TR, pivot BL
            nw = float(mx - pivot.x())
            nh = float(pivot.y() - my)
        elif hid == 2:  # BR, pivot TL
            nw = float(mx - pivot.x())
            nh = float(my - pivot.y())
        elif hid == 3:  # BL, pivot TR
            nw = float(pivot.x() - mx)
            nh = float(my - pivot.y())
        elif hid == 4:  # TOP mid, pivot BOTTOM mid (solo Y)
            nw = float(w0)
            nh = float(pivot.y() - my)
        elif hid == 5:  # RIGHT mid, pivot LEFT mid (solo X)
            nw = float(mx - pivot.x())
            nh = float(h0)
        elif hid == 6:  # BOTTOM mid, pivot TOP mid (solo Y)
            nw = float(w0)
            nh = float(my - pivot.y())
        elif hid == 7:  # LEFT mid, pivot RIGHT mid (solo X)
            nw = float(pivot.x() - mx)
            nh = float(h0)
        else:
            return

        if (nw <= 0) or (nh <= 0):
            return

        sx = nw / w0
        sy = nh / h0

        # Shift (fino) -> escala uniforme (mantener aspecto).
        if fine:
            try:
                # Handles laterales: usar el eje dominante como escala uniforme.
                if hid in (4, 6):  # top/bottom => domina Y
                    s = float(sy)
                    if math.isfinite(s) and s > 0:
                        sx = s
                        sy = s
                elif hid in (5, 7):  # left/right => domina X
                    s = float(sx)
                    if math.isfinite(s) and s > 0:
                        sx = s
                        sy = s
                else:
                    # Esquinas: escala por diagonal (cursor proyectado).
                    d0 = math.hypot(float(c0.x() - pivot.x()), float(c0.y() - pivot.y()))
                    d1 = math.hypot(float(mx - pivot.x()), float(my - pivot.y()))
                    if d0 > 1e-9:
                        s = float(d1 / d0)
                        if math.isfinite(s) and s > 0:
                            sx = s
                            sy = s
            except Exception:
                pass

        if (not math.isfinite(sx)) or (not math.isfinite(sy)) or (sx <= 0) or (sy <= 0):
            return

        # Aplicar a cada objeto desde snapshot (sin acumular error)
        for oid, d in self._scale_drag_snap.items():
            it = self._items.get(str(oid))
            if it is None:
                continue
            obj = self._project.get_object(str(oid))
            if not obj:
                continue
            try:
                base_sx = float(d.get("base_sx", 1.0))
                base_sy = float(d.get("base_sy", 1.0))
                rel_x = float(d.get("rel_x", 0.0))
                rel_y = float(d.get("rel_y", 0.0))

                obj.transform.scale_x = base_sx * float(sx)
                obj.transform.scale_y = base_sy * float(sy)

                self._apply_object_transform_to_item(obj, it)

                new_center = QPointF(float(pivot.x()) + rel_x * float(sx), float(pivot.y()) + rel_y * float(sy))
                self._set_item_center(obj, it, new_center)

                if obj.type == "svg":
                    self._rerender_svg_preview_for_object(str(oid))
            except Exception:
                continue

        # HUD tamaño en vivo
        try:
            self._show_selected_size_overlay(seconds=1)
        except Exception:
            pass
        self.viewport().update()

    def _end_scale_handle_drag(self) -> None:
        if not self._scale_drag_active:
            return
        self._scale_drag_active = False
        self._scale_drag_handle = None
        self._scale_drag_pivot_scene = None
        self._scale_drag_bbox0_scene = None
        self._scale_drag_corner0_scene = None
        self._scale_drag_snap = {}

        if self._project is not None:
            self._project.mark_dirty("scale_handle")
        self.project_modified.emit("scale_handle")
        self.viewport().update()

    def _selected_bbox_mm(self) -> tuple[float, float] | None:
        """Devuelve (ancho_mm, alto_mm) de la selección en coordenadas de escena.

        Nota: en RCS las unidades de la escena son mm, por lo que el bbox ya está en mm.
        """
        items = list(self.scene().selectedItems()) if self.scene() else []
        if not items:
            return None
        r = items[0].sceneBoundingRect()
        for it in items[1:]:
            r = r.united(it.sceneBoundingRect())
        w = float(max(0.0, r.width()))
        h = float(max(0.0, r.height()))
        return w, h


    def _show_selected_size_overlay(self, seconds: int = 3) -> None:
        dims = self._selected_bbox_mm()
        if not dims:
            return
        w, h = dims
        self._overlay_obj_text = f"Objeto: {w:.2f} x {h:.2f} mm"
        self._overlay_obj_until_ms = int(time.time() * 1000) + int(seconds * 1000)
        self.viewport().update()



    def _show_selected_angle_overlay(self, angle_deg: float, *, fine: bool = False, seconds: float = 1.2) -> None:
        """UX: muestra el ángulo actual (similar al overlay de tamaño)."""
        try:
            a = float(angle_deg)
        except Exception:
            return
        if not math.isfinite(a):
            return
        # Normalizar a [-180, 180] para legibilidad
        a = a % 360.0
        if a > 180.0:
            a -= 360.0
        suf = " (fino)" if fine else ""
        self._overlay_aux_text = f"Ángulo: {a:.1f}°{suf}"
        self._overlay_aux_until_ms = int(time.time() * 1000) + int(seconds * 1000)
        self.viewport().update()

    def set_selected_size_mm(self, w_mm: float | None, h_mm: float | None, keep_aspect: bool = True) -> bool:
        """Ajusta el tamaño del objeto o selección en mm.

        Devuelve True si aplicó el cambio.
        """
        return self.apply_size_to_selection_mm(w_mm, h_mm, keep_aspect=keep_aspect)


    def apply_size_to_selection_mm(self, target_w_mm: float | None, target_h_mm: float | None, keep_aspect: bool) -> None:
        """Aplica tamaño a la selección (mm).

        Reglas:
        - Rotados: el bbox se mide por sceneBoundingRect() (visible real).
        - Multi selección: escalado de grupo real (pivot centro + posiciones relativas).
        - Validación dura: rechaza bool/None/NaN/Inf/<=0.
        """
        if self._project is None:
            return

        # Validar input
        tw = self._valid_mm_value(target_w_mm) if target_w_mm is not None else None
        th = self._valid_mm_value(target_h_mm) if target_h_mm is not None else None
        if tw is None and th is None:
            return

        # BBox actual (mm) y bbox en escena (para pivot/centros)
        rect_mm = self._selected_bbox_mm()
        if rect_mm is None:
            return
        cur_w, cur_h = rect_mm
        cur_w = float(cur_w)
        cur_h = float(cur_h)
        if (cur_w <= 0) or (cur_h <= 0):
            return

        items = [it for it in self.scene().selectedItems() if it is not None]
        if not items:
            return

        bbox_scene: QRectF | None = None
        for it in items:
            try:
                r = it.sceneBoundingRect()
            except Exception:
                continue
            if bbox_scene is None:
                bbox_scene = QRectF(r)
            else:
                bbox_scene = bbox_scene.united(r)
        if bbox_scene is None:
            return

        sx = (tw / cur_w) if tw is not None else (th / cur_h)
        sy = (th / cur_h) if th is not None else (tw / cur_w)

        if keep_aspect:
            s = sx if tw is not None else sy
            sx = s
            sy = s

        # Guard-rails
        if (not math.isfinite(sx)) or (not math.isfinite(sy)) or (sx <= 0) or (sy <= 0):
            return

        pivot = bbox_scene.center()

        changed_any = False
        for it in items:
            oid = self._item_object_id(it)
            if not oid:
                continue
            obj = self._project.get_object(str(oid))
            if not obj:
                continue

            try:
                old_center = self._item_scene_center(it)
                rel = old_center - pivot
                new_center = QPointF(pivot.x() + rel.x() * sx, pivot.y() + rel.y() * sy)

                # Escala en el modelo (no encadenar QTransform().scale en llamadas).
                obj.transform.scale_x = float(getattr(obj.transform, 'scale_x', 1.0) or 1.0) * float(sx)
                obj.transform.scale_y = float(getattr(obj.transform, 'scale_y', 1.0) or 1.0) * float(sy)

                self._apply_object_transform_to_item(obj, it)
                self._set_item_center(obj, it, new_center)

                if obj.type == 'svg':
                    self._rerender_svg_preview_for_object(str(oid))

                changed_any = True
            except Exception:
                continue

        if not changed_any:
            return

        self._project.mark_dirty("scale")
        self.project_modified.emit("scale")
        self._show_selected_size_overlay()
        self.viewport().update()

    def _valid_mm_value(self, v) -> float | None:
        """Validación dura de un valor mm (clipboard / UI).

        Rechaza: None, bool, NaN/Inf, <= 0, no-numérico.
        """
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        try:
            f = float(v)
        except Exception:
            return None
        if (not math.isfinite(f)) or (f <= 0):
            return None
        return float(f)

    def _sanitize_size_clipboard_mm(self) -> None:
        """Normaliza el clipboard interno de tamaño.

        - Convierte a float cuando es válido.
        - Si es inválido: lo borra (None) y loggea 1 línea.
        """
        self._ensure_size_clipboard_mm()
        for k in ('w', 'h'):
            raw = self._size_clipboard_mm.get(k)
            ok = self._valid_mm_value(raw)
            if ok is None and raw is not None:
                log.info("Size clipboard ignorado: %s=%r", k, raw)
                self._size_clipboard_mm[k] = None
            elif ok is not None:
                self._size_clipboard_mm[k] = ok

    def _set_item_center(self, obj: SceneObject, it: QGraphicsItem, desired_scene_center: QPointF) -> None:
        """Mueve el item para que su centro en escena coincida con `desired_scene_center`,
        y sincroniza obj.transform.x/y.
        """
        try:
            cur = self._item_scene_center(it)
            dx = float(desired_scene_center.x() - cur.x())
            dy = float(desired_scene_center.y() - cur.y())
            if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                return
            it.setPos(it.pos() + QPointF(dx, dy))
            # sync model (canvas coords)
            p = it.pos()
            nx, ny = self._scene_to_canvas_xy(float(p.x()), float(p.y()))
            obj.transform.x = float(nx)
            obj.transform.y = float(ny)
        except Exception:
            return

    def _ensure_size_clipboard_mm(self) -> None:
        if not hasattr(self, "_size_clipboard_mm") or not isinstance(self._size_clipboard_mm, dict):
            self._size_clipboard_mm = {'w': None, 'h': None}
        else:
            self._size_clipboard_mm.setdefault('w', None)
            self._size_clipboard_mm.setdefault('h', None)

    def _size_clipboard_has(self, mode: str) -> bool:
        self._sanitize_size_clipboard_mm()
        w = self._valid_mm_value(self._size_clipboard_mm.get('w'))
        h = self._valid_mm_value(self._size_clipboard_mm.get('h'))
        if mode == 'w':
            return w is not None
        if mode == 'h':
            return h is not None
        if mode in ('wh', 'hw'):
            return (w is not None) and (h is not None)
        return False

    @staticmethod
    def _fmt_mm(v) -> str:
        if isinstance(v, (int, float)):
            try:
                return f"{float(v):.2f}"
            except Exception:
                pass
        return "—"

    def _copy_selected_size_to_clipboard(self, mode: str, checked: bool = False) -> None:
        """Copia W/H/WxH desde el bbox seleccionado (en mm).

        Nota: el bbox se mide por sceneBoundingRect() (incluye rotación).
        """
        self._ensure_size_clipboard_mm()
        rect = self._selected_bbox_mm()
        if rect is None:
            return
        w0, h0 = rect
        wv = self._valid_mm_value(w0)
        hv = self._valid_mm_value(h0)
        if mode in ('w', 'wh', 'hw') and wv is not None:
            self._size_clipboard_mm['w'] = float(wv)
        if mode in ('h', 'wh', 'hw') and hv is not None:
            self._size_clipboard_mm['h'] = float(hv)
    def _paste_size_from_clipboard(self, mode: str, checked: bool = False) -> None:
        """Pega W/H/WxH al bbox seleccionado (en mm).

        - Validación dura del clipboard: rechaza bool/None/NaN/Inf/<=0.
        - Multi selección: aplica escalado de grupo (bbox unido + pivot centro).
        - Pegar solo ancho/alto mantiene relación de aspecto.
        """
        self._sanitize_size_clipboard_mm()
        rect = self._selected_bbox_mm()
        if rect is None:
            return

        w_clip = self._valid_mm_value(self._size_clipboard_mm.get('w'))
        h_clip = self._valid_mm_value(self._size_clipboard_mm.get('h'))

        if mode == 'w':
            if w_clip is None:
                return
            self.apply_size_to_selection_mm(float(w_clip), None, keep_aspect=True)
            return

        if mode == 'h':
            if h_clip is None:
                return
            self.apply_size_to_selection_mm(None, float(h_clip), keep_aspect=True)
            return

        if mode in ('wh', 'hw'):
            if (w_clip is None) or (h_clip is None):
                return
            self.apply_size_to_selection_mm(float(w_clip), float(h_clip), keep_aspect=False)
            return

    def insert_svg_from_library(self, svg_path: str) -> str | None:
        """Inserta un SVG desde la biblioteca.

        **Contrato compatible**: recibe *ruta relativa* (relativa a components_root)
        desde el LibraryPanel, pero también acepta una ruta absoluta.
        """
        if not self._project:
            return None

        p_in = Path(svg_path)

        # Resolver root de componentes (relativo al .RCS si aplica).
        try:
            root = self._project.components_root_path(cwd=Path.cwd())  # type: ignore[attr-defined]
        except Exception:
            root = Path(getattr(self._project, 'components_root', 'componentes')).resolve()

        if p_in.is_absolute():
            abs_p = p_in
            # Intentar guardar source relativo si está dentro de root.
            try:
                rel_p = abs_p.relative_to(root)
            except Exception:
                rel_p = abs_p.name
        else:
            abs_p = (root / p_in).resolve()
            rel_p = p_in

        if not abs_p.exists():
            log.warning("SVG no existe: %s (root=%s)", str(abs_p), str(root))
            self.project_modified.emit("insert_missing")
            return None

        # Validación tolerante: algunas versiones retornan None o lanzan excepción.
        ok = True
        msg = ""
        try:
            res = validate_svg_supported(abs_p)
            if isinstance(res, tuple) and len(res) == 2:
                ok, msg = bool(res[0]), str(res[1])
        except Exception as e:
            ok = False
            msg = str(e)

        if not ok:
            log.warning("SVG no soportado: %s (%s)", str(abs_p), msg)
            self.project_modified.emit(f"svg_rejected:{msg}")
            return None

        # Normalizamos separadores para portabilidad (se guarda en .RCS).
        rel = str(rel_p).replace('\\', '/')

        # Insercion: por defecto cerca del centro visible.
        x_mm, y_mm = 10.0, 10.0
        try:
            vr = self.mapToScene(self.viewport().rect()).boundingRect()
            c_scene = vr.center()
            canvas_scene = self._canvas_rect()
            if not canvas_scene.contains(c_scene):
                c_scene = canvas_scene.center()
            x_mm, y_mm = self._scene_to_canvas_xy(float(c_scene.x()), float(c_scene.y()))
        except Exception:
            pass

        obj = SceneObject(
            id=new_object_id(),
            type="svg",
            source=str(rel),
            transform=Transform(x=float(x_mm), y=float(y_mm), scale_x=1.0, scale_y=1.0, rotation_deg=0.0),
            z=self._project.next_z(),
        )
        self._project.objects.append(obj)
        it = self._add_svg_item(obj)

        if it is not None:
            try:
                self._scene.clearSelection()
                it.setSelected(True)
                # Asegura que el item quede dentro del viewport.
                self.ensureVisible(it, 40, 40)
                self.centerOn(it)
            except Exception:
                pass

        # Fuerza repaint/invalidate: algunos drivers/Qt no dibujan hasta un evento grande.
        try:
            self._scene.invalidate(self._scene.sceneRect(), QGraphicsScene.AllLayers)
            self._scene.update()
            self.viewport().update()
            self.viewport().repaint()
        except Exception:
            pass

        self._project.mark_dirty("insert")
        self.inserted.emit(obj.id)
        self.project_modified.emit("insert")
        return obj.id

    def _add_svg_item(self, obj: SceneObject) -> QGraphicsItem | None:
        assert self._project is not None
        assert obj.source is not None

        # Resolver components_root de forma robusta (puede ser relativo al CWD o absoluto).
        try:
            root = self._project.components_root_path(cwd=Path.cwd())  # type: ignore[attr-defined]
        except Exception:
            root = Path(getattr(self._project, 'components_root', 'componentes')).resolve()
        abs_path = (root / str(obj.source)).resolve()

        # v0.2.24 HOTFIX: `validate_svg_supported` puede ser una validación que
        # levanta excepción (retorna None). En versiones anteriores podía
        # retornar (ok, msg). Mantenemos compatibilidad y evitamos crash.
        ok = True
        msg = ""
        try:
            res = validate_svg_supported(abs_path)
            if isinstance(res, tuple) and len(res) == 2:
                ok, msg = bool(res[0]), str(res[1])
        except Exception as e:
            ok = False
            msg = str(e)

        if not ok:
            log.warning("SVG no soportado: %s (%s)", abs_path, msg)
            # placeholder visual mínimo
            it = QGraphicsRectItem(0, 0, 20, 20)
            it.setPen(QPen(QColor(255, 0, 0)))
            it.setToolTip(f"No soportado: {obj.source}\n{msg}")
            it.setData(1, obj.id)
            self._apply_object_transform_to_item(obj, it)
            it.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
            # Respeta modo PICK (solo selección)
            if self._tool_mode == getattr(ToolMode, "PICK", ToolMode.SELECT):
                it.setFlag(QGraphicsItem.ItemIsMovable, False)
            self._scene.addItem(it)
            self._items[obj.id] = it
            return it

        item = self._create_raster_item(abs_path)
        # Si el objeto ya viene marcado para "fit to content" (persistido en .RCS),
        # recortamos el pixmap antes de aplicar transforms para que el pivot quede centrado.
        if getattr(obj, "svg_fit_content", False):
            try:
                img0 = item.pixmap().toImage()
                r0 = _alpha_bbox(img0, alpha_threshold=1)
                if r0 is not None:
                    pm0 = item.pixmap()
                    pm2 = pm0.copy(r0)
                    item.setPixmap(pm2)
                    item.setScale(self._mm_per_px)
                    _apply_outline_effect(item)
            except Exception:
                pass
        item.setData(1, obj.id)
        self._apply_object_transform_to_item(obj, item)

        item.setToolTip(obj.source)
        item.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        if self._tool_mode == getattr(ToolMode, "PICK", ToolMode.SELECT):
            item.setFlag(QGraphicsItem.ItemIsMovable, False)

        self._scene.addItem(item)
        self._items[obj.id] = item
        return item

    def _add_gmpr_base_preview_if_needed(self) -> None:
        """Dibuja el SVG embebido del GMPR como fondo *a escala real*.

        Nota: sigue siendo un "preview" (QGraphicsPixmapItem) fuera del modelo.
        Se permite seleccionar SOLO cuando no hay otros objetos seleccionados (selección exclusiva),
        para poder inspeccionar tamaño/pos sin contaminar herramientas (scale/rotate).
        """
        if not self._project:
            return
        tmp = getattr(self._project, "gmpr_svg_tmp_path", None)
        if not tmp:
            return

        try:
            svg_path = Path(str(tmp))
        except Exception:
            return
        if not svg_path.exists():
            return

        try:
            pm, mm_per_px = self._render_gmpr_base_svg_pixmap(svg_path)
        except Exception:
            return
        if pm.isNull():
            return

        item = QGraphicsPixmapItem(pm)

        # Fondo, detrás de todo.
        item.setZValue(-1e9)
        item.setOpacity(0.22)

        # Posición: siempre al origen del canvas (top-left).
        item.setPos(self._canvas_origin_mm())

        # Escala: 1px -> mm_per_px_rendered
        try:
            item.setScale(float(mm_per_px))
        except Exception:
            pass

        # Selección (exclusiva): permite click para inspección, pero nunca junto con otros objetos.
        item.setFlag(QGraphicsItem.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.ItemIsMovable, False)
        item.setAcceptedMouseButtons(Qt.LeftButton)
        item.setToolTip("GMPR base SVG (preview a escala; selección exclusiva)")

        self._scene.addItem(item)
        self._gmpr_base_item = item


    def _add_raster_item(self, obj: SceneObject) -> QGraphicsItem | None:
        """Agrega un raster (PNG embebido en GMPR) como item movible/seleccionable."""
        assert self._project is not None

        png_map = getattr(self._project, "gmpr_raster_png_by_uid", None)
        if not isinstance(png_map, dict):
            return None
        png_bytes = png_map.get(obj.id)
        if not png_bytes:
            return None

        pm = QPixmap()
        ok = False
        try:
            ok = pm.loadFromData(png_bytes, "PNG")
        except Exception:
            ok = False
        if not ok:
            try:
                ok = pm.loadFromData(png_bytes)
            except Exception:
                ok = False
        if not ok:
            # placeholder visual mínimo
            it = QGraphicsRectItem(0, 0, 40, 40)
            it.setPen(QPen(QColor(255, 170, 0)))
            it.setToolTip(f"Raster inválido: {obj.id}")
            it.setData(1, obj.id)
            self._apply_object_transform_to_item(obj, it)
            it.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
            if self._tool_mode == getattr(ToolMode, "PICK", ToolMode.SELECT):
                it.setFlag(QGraphicsItem.ItemIsMovable, False)
            self._scene.addItem(it)
            self._items[obj.id] = it
            return it

        item = QGraphicsPixmapItem(pm)
        item.setData(1, obj.id)
        item.setZValue(float(obj.z))
        try:
            item.setShapeMode(QGraphicsPixmapItem.ShapeMode.BoundingRectShape)
        except Exception:
            pass
        item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        try:
            item.setTransformationMode(Qt.SmoothTransformation)
        except Exception:
            pass

        # 1px -> mm (consistente con SVG rasterizado)
        item.setScale(self._mm_per_px)
        _apply_outline_effect(item)

        self._apply_object_transform_to_item(obj, item)

        item.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        if self._tool_mode == getattr(ToolMode, "PICK", ToolMode.SELECT):
            item.setFlag(QGraphicsItem.ItemIsMovable, False)

        self._scene.addItem(item)
        self._items[obj.id] = item
        return item

    def _render_svg_preview_pixmap(self, svg_path: Path, *, stroke_thick: int, outline_thick: int, obj_scale: float = 1.0) -> QPixmap:
        """Renderiza SVG -> pixmap estilizado.

        Importante:
        - `stroke_thick` / `outline_thick` están en *pixeles lógicos* (preview).
        - La rasterización se hace a mayor resolución y se publica con
          `devicePixelRatio`, manteniendo el tamaño lógico constante y mejorando
          la nitidez.
        - `obj_scale` es la escala del objeto en el canvas (modelo). Se usa para
          compensar grosor: el stroke/halo se mantiene visualmente estable aunque
          el usuario escale el objeto.
        """
        logical_px = int(getattr(self, '_preview_logical_px', 240) or 240)

        base_dpr = int(self._preview_device_pixel_ratio())
        if base_dpr < 1:
            base_dpr = 1

        # `stroke_thick` / `outline_thick` llegan en px lógicos (menu "Ver").
        # Los convertimos a px físicos (DPR) y compensamos por escala del objeto
        # para que el grosor quede visualmente estable al escalar.
        st_v = float(stroke_thick or 0)
        ot_v = float(outline_thick or 0)


        # Escala global de 'niveles' de grosor (menú 1..6) a px lógicos.
        # Default: 0.5 = toda la escala a la mitad (nivel 1 más fino).
        level_scale = _env_float("RCS_CANVAS_PREVIEW_THICK_SCALE", 0.5, min_value=0.1, max_value=4.0)
        st_v *= level_scale
        ot_v *= level_scale
        try:
            s = float(obj_scale or 1.0)
        except Exception:
            s = 1.0
        if s <= 0:
            s = 1.0
        s = max(1e-3, abs(s))

        # --- Adaptive DPR: evita el "clamp a 1px" cuando el objeto se escala mucho.
        # Mantiene el grosor visual constante permitiendo subpixel + más resolución interna
        # en buckets (reduce thrash de re-render).
        max_dpr = _env_int("RCS_CANVAS_PREVIEW_DPR_MAX", 16, min_value=1, max_value=64)
        min_phys = _env_float("RCS_CANVAS_PREVIEW_MIN_THICK_PX", 0.85, min_value=0.10, max_value=4.00)

        req_mult = 1.0
        if st_v > 0:
            req_mult = max(req_mult, (min_phys * s) / float(max(1e-6, st_v * base_dpr)))
        if ot_v > 0:
            req_mult = max(req_mult, (min_phys * s) / float(max(1e-6, ot_v * base_dpr)))

        max_mult = float(max_dpr) / float(max(1, base_dpr))
        req_mult = max(1.0, min(req_mult, max_mult))

        buckets = [1, 2, 3, 4, 6, 8, 12, 16]
        # Override opcional por env: "1,2,4,8,16"
        try:
            raw_b = os.getenv("RCS_CANVAS_PREVIEW_DPR_BUCKETS", "").strip()
            if raw_b:
                tmp = []
                for part in raw_b.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    v = int(float(part))
                    if v >= 1:
                        tmp.append(v)
                if tmp:
                    buckets = sorted(set(tmp))
        except Exception:
            pass

        mult = buckets[-1]
        for b in buckets:
            if float(b) >= float(req_mult):
                mult = b
                break

        dpr = int(max(1, min(max_dpr, base_dpr * int(mult))))
        internal_px = max(96, int(logical_px) * dpr)

        # Subpixel stroke: NO clamps a int>=1.
        stroke_px = 0.0 if st_v <= 0 else (float(st_v) * float(dpr) / s)

        # Outline (dilate) requiere int: usamos DPR adaptivo para no caer a 0/1.
        outline_f = 0.0 if ot_v <= 0 else (float(ot_v) * float(dpr) / s)
        outline_px = 0 if outline_f <= 0.0 else int(round(outline_f))
        if ot_v > 0 and outline_px < 1:
            outline_px = 1

        # Render Qt al tamaño físico (internal_px). Para el CANVAS preview, el grosor real
        # se controla en el render SVG (stroke-width forzado). El halo (outline) queda
        # como post-proceso.
        img = self._render_svg_qt(svg_path, internal_px, stroke_px=stroke_px)

        st = 0
        ot = outline_px
        img = _stylize_preview_image(
            img,
            theme_id=self._theme_id,
            stroke_thick=st,
            outline_thick=ot,
        )

        # UX: selección fácil. Si el preview es "outline" (interior transparente),
        # rellenamos el interior con alfa casi-cero para que el hit-test funcione.
        if _env_bool("RCS_CANVAS_HIT_FILL", True):
            img = _add_interior_hit_fill(img)

        pm = QPixmap.fromImage(img)
        try:
            pm.setDevicePixelRatio(float(max(1, dpr)))
        except Exception:
            pass
        return pm

    def _create_raster_item(self, svg_path: Path) -> QGraphicsPixmapItem:
        stroke_thick, outline_thick = self._effective_preview_thickness()
        px = self._render_svg_preview_pixmap(svg_path, stroke_thick=stroke_thick, outline_thick=outline_thick, obj_scale=1.0)

        item = QGraphicsPixmapItem(px)

        # UX: selección/movimiento más fácil: el hit-test usa el boundingRect
        # en vez de forzar click justo sobre el trazo.
        try:
            item.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        except Exception:
            pass

        # Marca el item como SVG para re-render por zoom/tema.
        item.setData(0, str(svg_path))
        # Ajuste de escala a mm: el pixmap está en px.
        # 1px = mm_per_px
        item.setScale(self._mm_per_px)

        _apply_outline_effect(item)

        return item

    def _render_gmpr_base_svg_pixmap(self, svg_path: Path) -> tuple[QPixmap, float]:
        """Render del SVG embebido del GMPR a escala real del lienzo.

        Objetivo:
        - Que el SVG base quede *en escala* con el canvas (mm), para que los rasters importados
          queden alineados correctamente.
        - Evitar el render "preview" (240px) que se usa para librería/miniaturas.

        Retorna: (pixmap, mm_por_px_rendered) para que el caller setee `item.setScale(mm_por_px_rendered)`.
        """
        if not self._project:
            return (QPixmap(), float(self._mm_per_px))

        try:
            cw = float(self._project.canvas_mm[0])
            ch = float(self._project.canvas_mm[1])
        except Exception:
            cw, ch = 500.0, 300.0

        cw = max(1.0, cw)
        ch = max(1.0, ch)

        # Tamaño "ideal" en px a 96 PPI (mm_per_px).
        px_w0 = max(1, int(round(cw / float(self._mm_per_px))))
        px_h0 = max(1, int(round(ch / float(self._mm_per_px))))

        # Clamp de resolución para no explotar memoria en canvases enormes.
        max_px = _env_int("RCS_GMPR_BASE_MAX_PX", 4096, min_value=512, max_value=16384)
        m = max(px_w0, px_h0, 1)
        scale = 1.0 if m <= max_px else (float(max_px) / float(m))

        px_w = max(1, int(round(px_w0 * scale)))
        px_h = max(1, int(round(px_h0 * scale)))

        try:
            svg_bytes = svg_path.read_bytes()
        except Exception:
            svg_bytes = b""

        renderer = QSvgRenderer(QByteArray(svg_bytes)) if svg_bytes else QSvgRenderer(str(svg_path))
        if not renderer.isValid():
            svg_bytes = Path(svg_path).read_bytes()
            svg_bytes = self._inject_rcs_gmpr_base_css(svg_bytes, stroke_user=0.20)
            renderer = QSvgRenderer(QByteArray(svg_bytes))

        img = QImage(px_w, px_h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)

        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        renderer.render(p, QRectF(0, 0, px_w, px_h))
        p.end()

        pm = QPixmap.fromImage(img)

        # mm representados por 1 px (del pixmap renderizado).
        mm_per_px_rendered = cw / float(px_w) if px_w > 0 else float(self._mm_per_px)
        return pm, float(mm_per_px_rendered)


    def _inject_rcs_gmpr_base_css(
        self,
        svg_bytes: bytes,
        stroke_user: float = 0.20,
        stroke_color: str = "#D0D0D0",
        fill: str = "none",
    ) -> bytes:
        """Inyectar CSS para que el SVG base de GMPR sea visible en fondo oscuro.

        Forzamos stroke claro, fill controlado y un stroke-width mínimo.
        """
        try:
            s = svg_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return svg_bytes

        if "<svg" not in s:
            return svg_bytes

        style = (
            "<style id=\"rcs-gmpr-base-style\">"
            "path, line, polyline, polygon, rect, circle, ellipse {"
            f" stroke: {stroke_color} !important;"
            f" fill: {fill} !important;"
            f" stroke-width: {stroke_user} !important;"
            "}"
            "</style>"
        )

        # Insertar el <style> apenas después del tag <svg ...>
        try:
            m = re.search(r"<svg[^>]*>", s, flags=re.IGNORECASE)
            if not m:
                return svg_bytes
            insert_at = m.end()
            s2 = s[:insert_at] + style + s[insert_at:]
            return s2.encode("utf-8")
        except Exception:
            return svg_bytes

    def _inject_rcs_preview_css(self, svg_bytes: bytes, *, stroke_user: float) -> bytes:
        """Inyecta/reemplaza un <style id=\"rcs-preview-style\"> para forzar stroke-width en previews.

        Nota: esto SOLO se usa para el render de PREVIEW del canvas. No modifica archivos en disco.
        """
        try:
            text = svg_bytes.decode("utf-8", errors="ignore")
            if "<svg" not in text.lower():
                return svg_bytes
            # Compatibilidad QtSvg: además de inyectar CSS, normalizamos stroke-width en el SVG.
            sw = f"{stroke_user:.6g}"

            # 1) Atributos: stroke-width="..."
            text = re.sub(
                r'(?i)(stroke-width\s*=\s*["\'])([^"\']*)(["\'])',
                lambda mm: mm.group(1) + sw + mm.group(3),
                text,
            )
            # 2) Style inline: stroke-width: ...;
            text = re.sub(
                r'(?i)(stroke-width\s*:\s*)([^;\"\']+)',
                lambda mm: mm.group(1) + sw,
                text,
            )

            # CSS: forzamos stroke-width (en unidades de usuario del SVG) para que el grosor final sea consistente.
            # Nota: QtSvg es medio picky; selectors explícitos suelen funcionar mejor que "*".
            selectors = "path, line, polyline, polygon, rect, circle, ellipse, use"
            css = f"{selectors}{{stroke-width:{sw} !important;}}"
            style_block = f"<style id=\"rcs-preview-style\">{css}</style>"

            # Si ya existe nuestro bloque, lo reemplazamos.
            if "rcs-preview-style" in text:
                text2 = re.sub(
                    r"(<style\b[^>]*id=[\"']rcs-preview-style[\"'][^>]*>)(.*?)(</style>)",
                    lambda m: m.group(1) + css + m.group(3),
                    text,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                return text2.encode("utf-8")

            # Insertar inmediatamente después del tag <svg ...>
            m0 = re.search(r"<svg\b[^>]*>", text, flags=re.IGNORECASE)
            if not m0:
                return svg_bytes
            pos = m0.end()
            text = text[:pos] + style_block + text[pos:]
            return text.encode("utf-8")
        except Exception:
            return svg_bytes



    def _render_svg_qt(self, svg_path: Path, target_px: int, *, stroke_px=None) -> QImage:
        # Render SVG -> QImage usando QSvgRenderer. Para PREVIEW en canvas podemos forzar stroke-width (menu "Grosor de línea").
        # Importante: esto NO altera el SVG en disco; se inyecta CSS en memoria para el renderer.
        try:
            svg_bytes = svg_path.read_bytes()
        except Exception:
            svg_bytes = b""

        renderer = QSvgRenderer(QByteArray(svg_bytes)) if svg_bytes else QSvgRenderer(str(svg_path))
        if not renderer.isValid():
            # fallback: intentar por ruta
            renderer = QSvgRenderer(str(svg_path))

        size = renderer.defaultSize()
        if size.isEmpty():
            size = QSize(512, 512)

        # Escalamos al lado más grande = target_px
        denom = max(size.width(), size.height(), 1)
        scale = target_px / denom
        w = max(1, int(round(size.width() * scale)))
        h = max(1, int(round(size.height() * scale)))

        # Forzar stroke-width (en unidades del SVG) para que el grosor final sea aprox. stroke_px en píxeles del render final.
        if stroke_px is not None and stroke_px >= 0 and svg_bytes:
            try:
                # stroke_user * scale ~= stroke_px  => stroke_user ~= stroke_px/scale
                stroke_user = float(stroke_px) / max(scale, 1e-6)
                patched = self._inject_rcs_preview_css(svg_bytes, stroke_user=stroke_user)
                r2 = QSvgRenderer(QByteArray(patched))
                if r2.isValid():
                    renderer = r2
            except Exception:
                pass

        img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)

        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(p, QRectF(0, 0, w, h))
        p.end()
        return img

        size = renderer.defaultSize()
        if size.width() <= 0 or size.height() <= 0:
            size = QSize(target_px, target_px)

        scale = min(target_px / size.width(), target_px / size.height())
        w = max(1, int(size.width() * scale))
        h = max(1, int(size.height() * scale))

        img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)

        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        renderer.render(p, QRectF(0, 0, w, h))
        p.end()

        return img

    def _add_text_item(self, obj: SceneObject) -> None:
        # Placeholder v0.2.x: mostrar un label; Bloque 5 hará texto real.
        txt = QGraphicsSimpleTextItem("[text]")
        txt.setBrush(QColor(220, 220, 220))
        txt.setData(1, obj.id)
        self._apply_object_transform_to_item(obj, txt)
        txt.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        if self._tool_mode == getattr(ToolMode, "PICK", ToolMode.SELECT):
            txt.setFlag(QGraphicsItem.ItemIsMovable, False)
        self._scene.addItem(txt)
        self._items[obj.id] = txt
