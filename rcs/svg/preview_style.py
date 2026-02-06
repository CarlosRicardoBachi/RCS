# File: rcs/svg/preview_style.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.9
# Status: stable
# Date: 2026-01-21
# Purpose: Unificar estilo de previews (canvas + thumbs) en un solo pipeline Qt6-safe.
# Notes:
# - Qt6/PySide6: QImage.bits() puede devolver memoryview (no tiene setsize).
# - NO usar QImage.alphaChannel()/setAlphaChannel() como requisito (Qt6).
from __future__ import annotations

from dataclasses import dataclass
import os

try:
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QColor, QImage, QPainter
except Exception:  # pragma: no cover
    # En tests/entornos sin Qt, el módulo igual debe importar.
    QRect = object  # type: ignore
    QColor = object  # type: ignore
    QImage = object  # type: ignore
    QPainter = object  # type: ignore


_IMPL_TAG = "pv1"


def _env_int(name: str, default: int, *, min_value: int | None = None, max_value: int | None = None) -> int:
    try:
        raw = os.environ.get(name, "")
        v = int(str(raw).strip()) if raw != "" else int(default)
    except Exception:
        v = int(default)

    if min_value is not None:
        v = max(int(min_value), int(v))
    if max_value is not None:
        v = min(int(max_value), int(v))
    return int(v)


def qimage_bits_view(img: QImage, nbytes: int) -> memoryview | None:
    """Devuelve un memoryview sobre img.bits() sin depender de setsize().

    - En PySide2, bits() suele ser un objeto con .setsize().
    - En PySide6, bits() puede ser memoryview directamente (sin .setsize()).
    """
    try:
        bits = img.bits()
        if bits is None:
            return None

        # PySide2/Qt5: ajustar tamaño si existe.
        try:
            if hasattr(bits, "setsize"):
                bits.setsize(int(nbytes))  # type: ignore[attr-defined]
        except Exception:
            pass

        try:
            mv = memoryview(bits)
            return mv
        except TypeError:
            # si bits ya es memoryview, memoryview(bits) puede fallar en algunos bindings
            if isinstance(bits, memoryview):
                return bits
            return None
    except Exception:
        return None


def extract_alpha8(img: QImage) -> QImage:
    """Extrae máscara alfa (Alpha8) Qt5/Qt6-safe."""
    if img is None or img.isNull():
        return QImage()

    # Qt5: rápido.
    try:
        if hasattr(img, "alphaChannel"):
            ach = img.alphaChannel()
            if isinstance(ach, QImage) and not ach.isNull():
                try:
                    return ach.convertToFormat(QImage.Format_Alpha8)
                except Exception:
                    return ach
    except Exception:
        pass

    # Qt6: construir manual desde ARGB/RGBA.
    src = img
    try:
        fmt = src.format()
        if fmt not in (
            QImage.Format_ARGB32,
            QImage.Format_ARGB32_Premultiplied,
            QImage.Format_RGBA8888,
            QImage.Format_RGBA8888_Premultiplied,
        ):
            src = src.convertToFormat(QImage.Format_ARGB32)
    except Exception:
        try:
            src = src.convertToFormat(QImage.Format_ARGB32)
        except Exception:
            return QImage()

    w = int(src.width())
    h = int(src.height())
    if w <= 0 or h <= 0:
        return QImage()

    alpha = QImage(w, h, QImage.Format_Alpha8)
    alpha.fill(0)

    try:
        s_bpl = int(src.bytesPerLine())
        a_bpl = int(alpha.bytesPerLine())

        sview = qimage_bits_view(src, s_bpl * h)
        aview = qimage_bits_view(alpha, a_bpl * h)
        if sview is None or aview is None:
            return QImage()

        # 4 bytes/px; alfa en byte +3 (BGRA o RGBA).
        for y in range(h):
            srow = y * s_bpl
            arow = y * a_bpl
            for x in range(w):
                aview[arow + x] = sview[srow + x * 4 + 3]
        return alpha
    except Exception:
        return QImage()


def tint_from_alpha8(alpha8: QImage, color: QColor) -> QImage:
    """Devuelve imagen ARGB con RGB fijo y alfa tomado de Alpha8."""
    if alpha8 is None or alpha8.isNull():
        return QImage()
    w = int(alpha8.width())
    h = int(alpha8.height())
    if w <= 0 or h <= 0:
        return QImage()

    out = QImage(w, h, QImage.Format_ARGB32)
    out.fill(QColor(0, 0, 0, 0))

    try:
        a_bpl = int(alpha8.bytesPerLine())
        aview = qimage_bits_view(alpha8, a_bpl * h)

        o_bpl = int(out.bytesPerLine())
        oview = qimage_bits_view(out, o_bpl * h)

        if aview is None or oview is None:
            return out.convertToFormat(QImage.Format_ARGB32_Premultiplied)

        r = int(color.red())
        g = int(color.green())
        b = int(color.blue())

        row_bytes = 4 * w
        br = bytes([b]) * w
        gr = bytes([g]) * w
        rr = bytes([r]) * w

        for y in range(h):
            arow = y * a_bpl
            orow = y * o_bpl
            row = oview[orow : orow + row_bytes]
            # set RGB
            row[0:row_bytes:4] = br
            row[1:row_bytes:4] = gr
            row[2:row_bytes:4] = rr
            # set A from mask
            row[3:row_bytes:4] = aview[arow : arow + w]
        return out.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    except Exception:
        return out.convertToFormat(QImage.Format_ARGB32_Premultiplied)


def dilate_alpha(alpha: QImage, thick: int) -> QImage:
    """Dilatación simple (vecindad 8) sobre Alpha8 usando composition Lighten."""
    if alpha is None or alpha.isNull():
        return QImage()
    thick = int(thick)
    if thick <= 0:
        return alpha

    out = alpha.copy()
    for _ in range(thick):
        src = out.copy()
        p = QPainter(out)
        p.setCompositionMode(QPainter.CompositionMode_Lighten)
        p.drawImage(-1, -1, src)
        p.drawImage(0, -1, src)
        p.drawImage(1, -1, src)
        p.drawImage(-1, 0, src)
        p.drawImage(1, 0, src)
        p.drawImage(-1, 1, src)
        p.drawImage(0, 1, src)
        p.drawImage(1, 1, src)
        p.end()
    return out


def alpha_bbox(img: QImage, *, alpha_threshold: int = 1) -> QRect | None:
    """BBox de pixeles con alfa > threshold. Retorna None si está vacío."""
    if img is None or img.isNull():
        return None

    src = img
    try:
        fmt = src.format()
        if fmt not in (
            QImage.Format_ARGB32,
            QImage.Format_ARGB32_Premultiplied,
            QImage.Format_RGBA8888,
            QImage.Format_RGBA8888_Premultiplied,
        ):
            src = src.convertToFormat(QImage.Format_ARGB32)
    except Exception:
        try:
            src = src.convertToFormat(QImage.Format_ARGB32)
        except Exception:
            return None

    w = int(src.width())
    h = int(src.height())
    if w <= 0 or h <= 0:
        return None

    bpl = int(src.bytesPerLine())
    view = qimage_bits_view(src, bpl * h)
    if view is None:
        return None

    minx = w
    miny = h
    maxx = -1
    maxy = -1

    row_bytes = 4 * w
    thr = int(alpha_threshold)

    for y in range(h):
        row = view[y * bpl : y * bpl + row_bytes]
        arow = row[3:row_bytes:4]
        # arow es bytes-like; iter es ints
        for x, a in enumerate(arow):
            if int(a) > thr:
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y

    if maxx < 0:
        return None

    return QRect(int(minx), int(miny), int(maxx - minx + 1), int(maxy - miny + 1))


def preview_colors_for_theme(theme_id: str) -> tuple[QColor, QColor]:
    """(ink, outline) según el tema del lienzo."""
    tid = (theme_id or "").strip().lower()
    if tid in ("dark", "mid"):
        ink = QColor(245, 245, 245, 255)       # blanco suave
        outline = QColor(255, 200, 0, 220)     # amarillo cálido
        return ink, outline
    ink = QColor(20, 20, 20, 255)
    outline = QColor(210, 130, 0, 210)
    return ink, outline


def _choose_thickness(kind: str) -> tuple[int, int]:
    """Decide stroke/outline con precedencia de env vars.

    Regla clave (para evitar sorpresas):
    - Si existe un override por-kind, gana (thumb/canvas).
    - Si no existe, cae al override global RCS_PREVIEW_*.
    - Si tampoco existe, usa defaults razonables.

    Esto permite ajustar miniaturas y canvas de forma independiente.
    """
    k = (kind or "").strip().lower()

    if k == "thumb":
        # Miniaturas: por defecto *sin* engorde/contorno.
        # Si querés copiar el estilo del canvas, seteá explícitamente los RCS_THUMB_*.
        st = _env_int("RCS_THUMB_STROKE_THICK", 0, min_value=0, max_value=48)
        ot = _env_int("RCS_THUMB_OUTLINE_THICK", 0, min_value=0, max_value=48)
        return st, ot

    # Canvas (y otros): defaults históricos.
    st = _env_int(
        "RCS_CANVAS_STROKE_THICK",
        _env_int("RCS_PREVIEW_STROKE_THICK", 2, min_value=0, max_value=48),
        min_value=0, max_value=48,
    )
    ot = _env_int(
        "RCS_CANVAS_OUTLINE_THICK",
        _env_int("RCS_PREVIEW_OUTLINE_THICK", 1, min_value=0, max_value=48),
        min_value=0, max_value=48,
    )
    return st, ot


def choose_thickness(kind: str) -> tuple[int, int]:
    """API pública para obtener (stroke, outline) según env vars."""
    return _choose_thickness(kind)


def preview_style_signature(*, kind: str, theme_id: str, stroke_thick: int, outline_thick: int, render_scale: int = 1) -> str:
    k = (kind or "").strip().lower() or "canvas"
    t = (theme_id or "").strip().lower() or "dark"
    return f"{_IMPL_TAG}|k={k}|t={t}|st={int(stroke_thick)}|ot={int(outline_thick)}|rs={int(render_scale)}"


def stylize_preview_image(img: QImage, *, kind: str, theme_id: str = "dark", render_scale: int = 1,
                          stroke_thick: int | None = None, outline_thick: int | None = None) -> QImage:
    """Aplica estilo de preview (ink + outline) sobre un render crudo.

    - kind: 'thumb' o 'canvas' (solo afecta defaults de env vars).
    - render_scale: factor de render interno (thumbs suelen renderizar más grande).
    """
    if img is None or img.isNull():
        return img

    if stroke_thick is None or outline_thick is None:
        st0, ot0 = _choose_thickness(kind)
        stroke_thick = st0 if stroke_thick is None else int(stroke_thick)
        outline_thick = ot0 if outline_thick is None else int(outline_thick)

    rs = max(1, int(render_scale))
    st = int(stroke_thick) * rs
    ot = int(outline_thick) * rs

    # Extraer alfa base
    base_alpha = extract_alpha8(img)
    if base_alpha.isNull() or base_alpha.width() <= 0 or base_alpha.height() <= 0:
        return img

    if alpha_bbox(img, alpha_threshold=0) is None:
        return img

    # Dilatar para grosor / contorno
    alpha_stroke = dilate_alpha(base_alpha.copy(), st)
    # Contorno = dilatación total (stroke + outline) sobre el alfa base.
    alpha_outline = dilate_alpha(base_alpha.copy(), st + ot)

    ink_color, outline_color = preview_colors_for_theme(theme_id)

    ink_img = tint_from_alpha8(alpha_stroke, ink_color)
    outline_img = tint_from_alpha8(alpha_outline, outline_color)

    out = QImage(img.size(), QImage.Format_ARGB32_Premultiplied)
    out.fill(QColor(0, 0, 0, 0))

    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.drawImage(0, 0, outline_img)
    p.drawImage(0, 0, ink_img)
    p.end()

    # Última línea de defensa: si quedara invisible, devolver original.
    if alpha_bbox(out, alpha_threshold=0) is None:
        return img
    return out
