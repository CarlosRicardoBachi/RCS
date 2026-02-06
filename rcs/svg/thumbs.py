# File: rcs/svg/thumbs.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.9
# Status: stable
# Date: 2026-01-21
# Purpose: Cache + render de miniaturas SVG para UI (QtSvg).
# Notes:
# - Render en hilo UI (se usa desde widgets). Si falla, devuelve placeholder.
# - Mejora de contraste: tinta + contorno y grosor por env vars.
# - Qt6/PySide6: NO usar QImage.alphaChannel()/setAlphaChannel().
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap, QColor, QPen

from rcs.svg import preview_style as pv

from rcs.geom.viewport_runtime_log import log_normalize_once

# Normalización de viewport (contrato compartido con canvas).
try:
    from rcs.geom.svg_viewport_normalize import normalize_svg_viewport
except Exception:  # pragma: no cover
    normalize_svg_viewport = None  # type: ignore


try:
    from PySide6.QtSvg import QSvgRenderer

except Exception:  # pragma: no cover
    QSvgRenderer = None  # type: ignore

log = logging.getLogger(__name__)

CACHE_IMPL_TAG = "thumbs-impl-v3"


def _qimage_bits_view(img: QImage, nbytes: int) -> memoryview | None:
    """Devuelve una vista a los bytes de un QImage de forma compatible Qt6/PySide6.

    - En PySide6/Qt6, `bits()` puede no soportar `setsize`.
    - `memoryview(bits)` puede fallar si el buffer no es "bytes-like".
    """
    try:
        b = img.bits()
    except Exception:
        return None
    try:
        if hasattr(b, "setsize"):
            b.setsize(nbytes)  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        v = b if isinstance(b, memoryview) else memoryview(b)
    except Exception:
        return None
    if len(v) < nbytes:
        return None
    return v


def _extract_alpha8(src: QImage) -> QImage:
    """Extrae el canal alfa como Alpha8 sin usar alphaChannel()."""
    if src.isNull():
        return src

    # Garantizar ARGB32 para leer byte alfa (offset 3 en BGRA little-endian)
    s = src.convertToFormat(QImage.Format_ARGB32)
    w, h = s.width(), s.height()

    a = QImage(w, h, QImage.Format_Alpha8)
    a.fill(0)

    s_bpl = s.bytesPerLine()
    a_bpl = a.bytesPerLine()

    sview = _qimage_bits_view(s, s_bpl * h)
    aview = _qimage_bits_view(a, a_bpl * h)
    if sview is None or aview is None:
        return a

    # Copiamos un byte por pixel: alpha = srow[3:4*w:4]
    row_bytes = 4 * w
    for y in range(h):
        srow = sview[y * s_bpl : y * s_bpl + row_bytes]
        arow = aview[y * a_bpl : y * a_bpl + w]
        try:
            arow[:] = srow[3:row_bytes:4]
        except Exception:
            # fallback lento
            for x in range(w):
                arow[x] = srow[x * 4 + 3]
    return a


def _tint_from_alpha8(alpha: QImage, color: QColor) -> QImage:
    """Crea una imagen ARGB32_Premultiplied con color + alpha dado."""
    if alpha.isNull():
        return alpha

    a = alpha
    if a.format() != QImage.Format_Alpha8:
        a = a.convertToFormat(QImage.Format_Alpha8)

    w, h = a.width(), a.height()
    out = QImage(w, h, QImage.Format_ARGB32)
    out.fill(QColor(color.red(), color.green(), color.blue(), 255))

    a_bpl = a.bytesPerLine()
    o_bpl = out.bytesPerLine()

    aview = _qimage_bits_view(a, a_bpl * h)
    oview = _qimage_bits_view(out, o_bpl * h)
    if aview is None or oview is None:
        return out.convertToFormat(QImage.Format_ARGB32_Premultiplied)

    row_bytes = 4 * w
    for y in range(h):
        arow = aview[y * a_bpl : y * a_bpl + w]
        orow = oview[y * o_bpl : y * o_bpl + row_bytes]
        try:
            orow[3:row_bytes:4] = arow[:]
        except Exception:
            for x in range(w):
                orow[x * 4 + 3] = arow[x]

    return out.convertToFormat(QImage.Format_ARGB32_Premultiplied)


def _env_int(name: str, default: int, *, min_value: int = 0, max_value: int = 12) -> int:
    try:
        v = int(os.environ.get(name, str(default)))
    except Exception:
        v = default
    return max(min_value, min(v, max_value))


def default_cache_dir() -> Path:
    return Path.home() / ".rcs_cache" / "thumbs"


# Convenience: expuesto para debugging (ver comandos de Cai).
THUMB_CACHE_DIR: Path = default_cache_dir()
THUMBS_CACHE_DIR: Path = THUMB_CACHE_DIR
CACHE_DIR: Path = THUMB_CACHE_DIR


@dataclass(frozen=True)
class ThumbRequest:
    svg_path: Path
    size_px: int


class ThumbCache:
    """Cache simple en disco para miniaturas.

    - Clave = hash(path absoluto + mtime + tamaño + estilo).
    - Salida = PNG en ~/.rcs_cache/thumbs
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self.cache_dir = (cache_dir or default_cache_dir()).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def key_for(self, svg_path: Path, size_px: int) -> str:
        p = svg_path.resolve()
        try:
            mt = p.stat().st_mtime_ns
        except Exception:
            mt = 0

        svg_hash = f"{p.as_posix()}|{mt}"
        rs = _env_int("RCS_THUMB_RENDER_SCALE", 2, min_value=1, max_value=8)

        # Unificar estilo con el canvas (ver rcs.svg.preview_style).
        theme_id = os.environ.get("RCS_THUMB_THEME", os.environ.get("RCS_PREVIEW_THEME", "dark"))
        st, ot = pv.choose_thickness("thumb")
        style_sig = pv.preview_style_signature(kind="thumb", theme_id=theme_id, stroke_thick=st, outline_thick=ot, render_scale=rs)
        return f"{CACHE_IMPL_TAG}|{svg_hash}|{size_px}|{style_sig}"
    def icon_for(self, svg_path: Path, size_px: int) -> QIcon:
        pm = self.pixmap_for(svg_path, size_px)
        return QIcon(pm)

    def pixmap_for(self, svg_path: Path, size_px: int) -> QPixmap:
        key = self.key_for(svg_path, size_px)
        digest = hashlib.sha1(key.encode('utf-8', 'ignore')).hexdigest()[:20]
        png = self.cache_dir / f"{digest}_{size_px}px.png"

        if png.exists():
            pm = QPixmap(str(png))
            if not pm.isNull():
                return pm

        img = self.render_svg_to_image(svg_path, size_px)
        try:
            img.save(str(png))
        except Exception:
            log.debug("No se pudo guardar thumb: %s", png, exc_info=True)

        return QPixmap.fromImage(img)

    def render_svg_to_image(self, svg_path: Path, size_px: int) -> QImage:
        size_px = int(size_px)
        render_scale = _env_int("RCS_THUMB_RENDER_SCALE", 2, min_value=1, max_value=8)
        render_px = max(32, min(size_px * render_scale, 512))

        img = QImage(render_px, render_px, QImage.Format_ARGB32_Premultiplied)
        img.fill(QColor(0, 0, 0, 0))

        if QSvgRenderer is None:
            return self._draw_placeholder(img, "QtSvg?")

        try:
            r = QSvgRenderer(str(svg_path.resolve()))
            if not r.isValid():
                return self._draw_placeholder(img, "SVG!")
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing, True)

            # Render aspect-safe: preservamos relación de aspecto dentro de un cuadrado.
            vb = r.viewBoxF()

            # Intentar normalizar viewport (misma lógica que canvas) para evitar divergencias.
            if normalize_svg_viewport is not None:
                try:
                    meta = normalize_svg_viewport(svg_path)
                    # Telemetría "una vez" por archivo.
                    log_normalize_once(svg_path, meta, where="thumbs")
                    vb_list = meta.get("viewbox") if isinstance(meta, dict) else None
                    if vb_list and len(vb_list) == 4:
                        nx, ny, nw, nh = [float(x) for x in vb_list]
                        if nw > 0 and nh > 0:
                            nrect = QRectF(nx, ny, nw, nh)
                            try:
                                r.setViewBox(nrect)
                                vb = nrect
                            except Exception:
                                pass
                except Exception:
                    pass

            if vb.isNull() or vb.width() <= 0 or vb.height() <= 0:
                ds = r.defaultSize()
                svg_w = float(ds.width() if ds.width() > 0 else render_px)
                svg_h = float(ds.height() if ds.height() > 0 else render_px)
            else:
                svg_w = float(vb.width())
                svg_h = float(vb.height())

            scale = min(render_px / svg_w, render_px / svg_h) if (svg_w > 0 and svg_h > 0) else 1.0
            tw = svg_w * scale
            th = svg_h * scale
            tx = (render_px - tw) / 2.0
            ty = (render_px - th) / 2.0

            target = QRectF(tx, ty, tw, th)
            r.render(p, target)
            p.end()

            img = self._stylize_preview_image(img, render_scale=render_scale)

            if render_px != size_px:
                img = img.scaled(size_px, size_px, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return img
        except Exception:
            log.debug("Render SVG falló: %s", svg_path, exc_info=True)
            return self._draw_placeholder(img, "ERR")

    def _dilate_alpha(self, alpha: QImage, thick: int) -> QImage:
        if thick <= 0:
            return alpha
        out = alpha.copy()
        for _ in range(thick):
            tmp = out.copy()
            p = QPainter(out)
            p.setCompositionMode(QPainter.CompositionMode_Lighten)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    p.drawImage(dx, dy, tmp)
            p.end()
        return out

    def _stylize_preview_image(self, img: QImage, *, render_scale: int = 1) -> QImage:
        """Stylize unificado (thumbs/canvas) - Qt6-safe."""
        theme_id = os.environ.get("RCS_THUMB_THEME", os.environ.get("RCS_PREVIEW_THEME", "dark"))
        return pv.stylize_preview_image(img, kind="thumb", theme_id=theme_id, render_scale=render_scale)
    def placeholder_icon(self, size_px: int) -> QIcon:
        img = QImage(int(size_px), int(size_px), QImage.Format_ARGB32_Premultiplied)
        img.fill(QColor(40, 40, 40, 255))
        self._draw_placeholder(img, "")
        return QIcon(QPixmap.fromImage(img))

    def _draw_placeholder(self, img: QImage, text: str) -> QImage:
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = img.width()
        h = img.height()

        # fondo suave
        p.fillRect(0, 0, w, h, QColor(50, 50, 50, 255))

        # borde
        pen = QPen(QColor(110, 110, 110, 255))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawRect(1, 1, w - 2, h - 2)

        # X sutil si falla
        if text in ("SVG!", "ERR", "QtSvg?"):
            pen2 = QPen(QColor(180, 80, 80, 255))
            pen2.setWidth(3)
            p.setPen(pen2)
            p.drawLine(8, 8, w - 8, h - 8)
            p.drawLine(8, h - 8, w - 8, 8)

        if text:
            p.setPen(QColor(220, 220, 220, 255))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, text)

        p.end()
        return img
