# File: rcs/utils/log.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.2.0
# Status: stable
# Date: 2026-01-15
# Purpose: Logging centralizado (con archivo) y helpers.
# Notes: Cambios incrementales, no romper funcionalidades probadas.
from __future__ import annotations

import logging
import os
from pathlib import Path

_LOGGER_CONFIGURED = False


def setup_logging(log_dir: str | os.PathLike = "logs", level: int = logging.INFO) -> None:
    """Configura logging en consola + archivo.

    Nota:
        - No lanza excepción si no puede escribir el archivo; cae a consola.
    """
    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return

    logger = logging.getLogger()
    logger.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Consola
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Archivo
    try:
        d = Path(log_dir)
        d.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(d / "rcs.log", encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as e:
        logging.getLogger(__name__).warning("No se pudo inicializar FileHandler: %s", e)

    _LOGGER_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
