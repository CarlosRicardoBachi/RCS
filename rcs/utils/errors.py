# File: rcs/utils/errors.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.2.0
# Status: stable
# Date: 2026-01-15
# Purpose: Errores tipados del proyecto.
# Notes: Cambios incrementales, no romper funcionalidades probadas.
from __future__ import annotations


class RcsError(Exception):
    """Error base del proyecto."""


class RcsValidationError(RcsError):
    """Error de validación (input/archivo/estructura)."""


class RcsIOError(RcsError):
    """Error de E/S (lectura/escritura)."""


class RcsSchemaError(RcsValidationError):
    """Error de esquema (.RCS) o incompatibilidad de versión."""


class RcsUserCancelled(RcsError):
    """Acción cancelada por el usuario (no es un fallo)."""
