# File: rcs/core/serialization.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.2.0
# Status: stable
# Date: 2026-01-15
# Purpose: Carga/guardado del formato .RCS (JSON legible).
# Notes: Cambios incrementales, no romper funcionalidades probadas.
from __future__ import annotations

import json
from pathlib import Path

from rcs.core.models import Project
from rcs.utils.errors import RcsIOError, RcsValidationError


def save_rcs(project: Project, path: str | Path | None = None) -> Path:
    """Guarda un Project en JSON con extensión .RCS.

    - Si `path` es None, usa project.file_path (si existe).
    - Escribe de forma atómica (tmp + replace) para evitar archivos corruptos.
    """
    p = Path(path) if path else (project.file_path if project.file_path else None)
    if p is None:
        raise RcsValidationError("No hay path de guardado. Usá Guardar como…")

    p = Path(p)
    if p.suffix.lower() != ".rcs":
        # [RCS-KEEP] Se fuerza extensión consistente. Cambiar solo con razón fuerte.
        p = p.with_suffix(".RCS")

    try:
        p.parent.mkdir(parents=True, exist_ok=True)

        data = project.to_dict()
        data["components_root"] = _normalize_components_root_for_save(
            data.get("components_root", "componentes"), project_path=p
        )

        txt = json.dumps(data, ensure_ascii=False, indent=2)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(txt, encoding="utf-8")
        tmp.replace(p)

        project.set_file_path(p)
        project.clear_dirty()
        return p
    except RcsValidationError:
        raise
    except Exception as e:
        raise RcsIOError("No se pudo guardar .RCS: {}".format(p)) from e


def load_rcs(path: str | Path) -> Project:
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except Exception as e:
        raise RcsIOError("No se pudo leer .RCS: {}".format(p)) from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RcsValidationError(
            ".RCS inválido (JSON malformado): {} (línea {}, columna {})".format(p, e.lineno, e.colno)
        ) from e
    except Exception as e:
        raise RcsValidationError(".RCS inválido (JSON malformado): {}".format(p)) from e

    if not isinstance(data, dict):
        raise RcsValidationError("Estructura .RCS inválida: raíz no es objeto JSON")

    prj = Project.from_dict(data)
    prj.set_file_path(p)
    prj.clear_dirty()
    return prj


def _normalize_components_root_for_save(components_root: str, *, project_path: Path) -> str:
    """Normaliza components_root para que el .RCS sea portable cuando sea posible."""
    try:
        cr = Path(str(components_root))
        if cr.is_absolute():
            try:
                rel = cr.resolve().relative_to(project_path.parent.resolve())
                return rel.as_posix()
            except Exception:
                return cr.as_posix()
        return cr.as_posix()
    except Exception:
        return str(components_root)
