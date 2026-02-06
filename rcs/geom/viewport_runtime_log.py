# File: rcs/geom/viewport_runtime_log.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.44
# Purpose: Telemetría mínima ("una vez por archivo") para normalización runtime.

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# Guardamos paths resueltos para evitar spameo en rustic.log
_SEEN: set[str] = set()


def log_normalize_once(svg_path: Path, meta: dict[str, Any] | None, *, where: str) -> None:
    """Loggea 1 vez por archivo el resultado de normalize_svg_viewport.

    No hace "clasificación" pesada (alpha/bbox) para no impactar performance.
    Se centra en: units/ppi/viewbox/doc size.
    """

    try:
        key = str(svg_path.resolve())
    except Exception:
        key = str(svg_path)

    if key in _SEEN:
        return
    _SEEN.add(key)

    if not meta or not isinstance(meta, dict):
        log.info("[normalize] %s: %s -> meta=None", where, key)
        return

    try:
        vb = meta.get("viewbox")
        dw = meta.get("doc_w")
        dh = meta.get("doc_h")
        units = meta.get("units")
        ppi = meta.get("ppi")
        log.info(
            "[normalize] %s: %s -> units=%s ppi=%s doc=%sx%s viewbox=%s",
            where,
            key,
            units,
            ppi,
            dw,
            dh,
            vb,
        )
    except Exception:
        # Nunca romper la UI por logging.
        log.debug("log_normalize_once fallo", exc_info=True)
