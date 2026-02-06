# File: rcs/core/models.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.8
# Status: stable
# Date: 2026-01-16
# Purpose: Modelos de datos del proyecto (.RCS).
# Notes: Cambios incrementales, no romper funcionalidades probadas.
from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

from rcs.core.version import SCHEMA_VERSION, DEFAULT_CANVAS_MM, DEFAULT_GRID_MM
from rcs.utils.errors import RcsSchemaError

ObjectType = Literal["svg", "text", "raster"]


@dataclass
class GridSettings:
    size_mm: float = DEFAULT_GRID_MM
    snap_on: bool = False


@dataclass
class Transform:
    # Nota: en el schema se serializa como x/y (en mm). Se acepta x_mm/y_mm por compat.
    x: float = 0.0
    y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation_deg: float = 0.0
    flip_h: bool = False
    flip_v: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": float(self.x),
            "y": float(self.y),
            "scale_x": float(self.scale_x),
            "scale_y": float(self.scale_y),
            "rotation_deg": float(self.rotation_deg),
            "flip_h": bool(self.flip_h),
            "flip_v": bool(self.flip_v),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Transform":
        # Compat: x_mm/y_mm (v0.0.x)
        x = d.get("x", d.get("x_mm", 0.0))
        y = d.get("y", d.get("y_mm", 0.0))
        return Transform(
            x=_as_float(x, "transform.x"),
            y=_as_float(y, "transform.y"),
            scale_x=_as_float(d.get("scale_x", 1.0), "transform.scale_x"),
            scale_y=_as_float(d.get("scale_y", 1.0), "transform.scale_y"),
            rotation_deg=_as_float(d.get("rotation_deg", 0.0), "transform.rotation_deg"),
            flip_h=bool(d.get("flip_h", False)),
            flip_v=bool(d.get("flip_v", False)),
        )


@dataclass
class TextPayload:
    text: str = "Texto"
    font_family: str = "Arial"
    font_size_pt: float = 24.0
    bold: bool = False
    italic: bool = False
    line_height: float = 1.0   # interlineado relativo
    tracking: float = 0.0      # espaciado entre letras (futuro)
    align: Literal["left", "center", "right"] = "left"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": str(self.text),
            "font_family": str(self.font_family),
            "font_size_pt": float(self.font_size_pt),
            "bold": bool(self.bold),
            "italic": bool(self.italic),
            "line_height": float(self.line_height),
            "tracking": float(self.tracking),
            "align": str(self.align),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "TextPayload":
        align = str(d.get("align", "left"))
        if align not in ("left", "center", "right"):
            raise RcsSchemaError(f"text_payload.align inválido: {align!r}")
        return TextPayload(
            text=str(d.get("text", "Texto")),
            font_family=str(d.get("font_family", "Arial")),
            font_size_pt=_as_float(d.get("font_size_pt", 24.0), "text_payload.font_size_pt"),
            bold=bool(d.get("bold", False)),
            italic=bool(d.get("italic", False)),
            line_height=_as_float(d.get("line_height", 1.0), "text_payload.line_height"),
            tracking=_as_float(d.get("tracking", 0.0), "text_payload.tracking"),
            align=align,  # type: ignore[arg-type]
        )


@dataclass
class SceneObject:
    id: str
    type: ObjectType
    source: Optional[str] = None  # ruta relativa (SVG) dentro de componentes/
    transform: Transform = field(default_factory=Transform)
    z: int = 0
    group_id: Optional[str] = None  # grouping lógico (v1)
    text_payload: Optional[TextPayload] = None
    # Cuando está activo, el preview se recorta al contenido (ignora márgenes blancos
    # del SVG). Se serializa en .RCS.
    svg_fit_content: bool = False

    def to_dict(self) -> dict[str, Any]:
        # Nota: se serializa transform como dict, no como dataclass plano.
        d: dict[str, Any] = {
            "id": str(self.id),
            "type": str(self.type),
            "source": str(self.source) if self.source is not None else None,
            "transform": self.transform.to_dict(),
            "z": int(self.z),
            "group_id": str(self.group_id) if self.group_id else None,
            "text_payload": self.text_payload.to_dict() if self.text_payload else None,
            "svg_fit_content": bool(self.svg_fit_content),
        }

        # Limpieza: no escribir campos irrelevantes
        if self.type != "svg":
            d["source"] = None
            d["svg_fit_content"] = False
        if self.type != "text":
            d["text_payload"] = None
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "SceneObject":
        if not isinstance(d, dict):
            raise RcsSchemaError("Objeto inválido: se esperaba dict")
        oid = str(d.get("id", "")).strip()
        if not oid:
            raise RcsSchemaError("Objeto inválido: falta 'id'")

        otype = d.get("type")
        if otype not in ("svg", "text", "raster"):
            raise RcsSchemaError(f"Objeto {oid!r}: type inválido: {otype!r}")

        t_raw = d.get("transform") or {}
        if not isinstance(t_raw, dict):
            raise RcsSchemaError(f"Objeto {oid!r}: transform inválido")
        t = Transform.from_dict(t_raw)

        tp_raw = d.get("text_payload")
        text_payload = TextPayload.from_dict(tp_raw) if isinstance(tp_raw, dict) else None

        svg_fit_content = bool(d.get("svg_fit_content", False))

        return SceneObject(
            id=oid,
            type=otype,  # type: ignore[arg-type]
            source=(str(d.get("source")) if d.get("source") is not None else None),
            transform=t,
            z=_as_int(d.get("z", 0), f"objects[{oid}].z"),
            group_id=(str(d.get("group_id")) if d.get("group_id") not in (None, "") else None),
            text_payload=text_payload,
            svg_fit_content=svg_fit_content,
        )


@dataclass
class Project:
    schema_version: int = SCHEMA_VERSION
    canvas_mm: tuple[float, float] = DEFAULT_CANVAS_MM
    grid: GridSettings = field(default_factory=GridSettings)
    components_root: str = "componentes"
    objects: list[SceneObject] = field(default_factory=list)

    # Runtime (NO se serializa en .RCS)
    file_path: Optional[Path] = None
    dirty: bool = False

    # Runtime GMPR (NO se serializa en .RCS)
    # - gmpr_bundle: JSON completo (se mantiene intacto salvo updates mínimos)
    # - gmpr_svg_tmp_path: SVG materializado (cache temporal) para preview base
    # - gmpr_raster_png_by_uid: PNG decodificado (bytes) por uid para instanciar rasters
    gmpr_bundle: Optional[dict[str, Any]] = None
    gmpr_svg_tmp_path: Optional[Path] = None
    gmpr_raster_png_by_uid: dict[str, bytes] = field(default_factory=dict)

    # ----------------------------
    # Lifecycle / Dirty handling
    # ----------------------------
    # [RCS-KEEP] Esta API se considera base. Si se refactoriza, mantener comportamiento.
    def mark_dirty(self, reason: str | None = None) -> None:
        # [RCS-KEEP] Si se refactoriza, mantener comportamiento (marca dirty).
        # reason es informativo (debug/logging) y puede ignorarse.
        self.dirty = True

    # [RCS-KEEP]
    def clear_dirty(self) -> None:
        self.dirty = False

    # [RCS-KEEP]
    def set_file_path(self, path: Optional[str | Path]) -> None:
        self.file_path = Path(path) if path else None

    # [RCS-KEEP]
    def components_root_path(self, *, cwd: Optional[Path] = None) -> Path:
        """Ruta absoluta a la biblioteca de componentes.

        - Si components_root es absoluto: se usa tal cual.
        - Si es relativo y el proyecto tiene file_path (.RCS): relativo al archivo del proyecto.
        - Si es relativo y el proyecto es .GMPR: relativo al cwd (evita “secuestrar” la biblioteca al abrir un GMPR).
        - Si es relativo y no hay file_path: relativo al cwd (o Path.cwd()).
        """
        p = Path(self.components_root)
        if p.is_absolute():
            return p

        # Nota: el proyecto GMPR es un “bundle” de import/export; la biblioteca debe seguir apuntando
        # al root de trabajo del usuario (cwd) y NO al directorio donde vive el .GMPR.
        if self.file_path and self.file_path.suffix.lower() != ".gmpr":
            base = self.file_path.parent
        else:
            base = (cwd or Path.cwd())

        return (base / p).resolve()

    # ----------------------------
    # Canvas settings
    # ----------------------------
    def set_canvas_mm(self, w_mm: float, h_mm: float) -> None:
        """Actualiza el tamaño del lienzo (en mm) y marca dirty.

        No forma parte del Bloque 2: se usa en la UI (Bloque 3+).
        """
        w = float(w_mm)
        h = float(h_mm)
        if w <= 0 or h <= 0:
            raise RcsSchemaError("canvas_mm inválido: w/h deben ser > 0")
        self.canvas_mm = (w, h)
        self.mark_dirty("canvas_mm")

    # ----------------------------
    # Objects helpers (Bloque 2A)
    # ----------------------------
    def next_z(self) -> int:
        """Devuelve el siguiente Z disponible (max+1)."""
        if not self.objects:
            return 0
        return int(max(o.z for o in self.objects)) + 1

    def get_object(self, object_id: str) -> SceneObject | None:
        for o in self.objects:
            if o.id == object_id:
                return o
        return None


    # ---------------------------- Grouping (v1) ----------------------------

    def group_member_ids(self, group_id: str) -> list[str]:
        """Ids de objetos cuyo `group_id` coincide."""
        if not group_id:
            return []
        return [o.id for o in self.objects if o.group_id == group_id]

    def groups_of_ids(self, ids: list[str]) -> set[str]:
        """Set de group_id presentes en una lista de ids (ignorando None)."""
        out: set[str] = set()
        for oid in ids:
            o = self.get_object(oid)
            if o and o.group_id:
                out.add(o.group_id)
        return out

    def add_object(self, obj: SceneObject) -> None:
        if self.get_object(obj.id) is not None:
            raise RcsSchemaError(f"Ya existe un objeto con id={obj.id!r}")
        self.objects.append(obj)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "canvas_mm": [float(self.canvas_mm[0]), float(self.canvas_mm[1])],
            "grid": {"size_mm": float(self.grid.size_mm), "snap_on": bool(self.grid.snap_on)},
            "components_root": str(self.components_root),
            "objects": [o.to_dict() for o in self.objects],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Project":

        if not isinstance(d, dict):
            raise RcsSchemaError(".RCS inválido: raíz no es objeto JSON")

        missing = [k for k in ("schema_version", "canvas_mm", "grid", "components_root", "objects") if k not in d]
        if missing:
            raise RcsSchemaError(f".RCS inválido: faltan claves requeridas: {', '.join(missing)}")

        schema_version = _as_int(d.get("schema_version"), "schema_version")
        if schema_version != SCHEMA_VERSION:
            raise RcsSchemaError(
                f".RCS incompatible: schema_version={schema_version} (se espera {SCHEMA_VERSION})"
            )

        canvas = d.get("canvas_mm")
        if not (isinstance(canvas, (list, tuple)) and len(canvas) == 2):
            raise RcsSchemaError("canvas_mm inválido: se espera [w,h]")
        canvas_mm = (_as_float(canvas[0], "canvas_mm[0]"), _as_float(canvas[1], "canvas_mm[1]"))
        if canvas_mm[0] <= 0 or canvas_mm[1] <= 0:
            raise RcsSchemaError("canvas_mm inválido: w/h deben ser > 0")

        grid_d = d.get("grid")
        if not isinstance(grid_d, dict):
            raise RcsSchemaError("grid inválido: se espera objeto")
        grid = GridSettings(
            size_mm=_as_float(grid_d.get("size_mm", DEFAULT_GRID_MM), "grid.size_mm"),
            snap_on=bool(grid_d.get("snap_on", False)),
        )
        if grid.size_mm <= 0:
            raise RcsSchemaError("grid.size_mm inválido: debe ser > 0")

        components_root = str(d.get("components_root") or "componentes")
        objects_raw = d.get("objects")
        if not isinstance(objects_raw, list):
            raise RcsSchemaError("objects inválido: se espera lista")
        objects: list[SceneObject] = []
        for idx, x in enumerate(objects_raw):
            # Backward compatible: proyectos viejos pueden no traer 'z'.
            if isinstance(x, dict) and 'z' not in x:
                x = {**x, 'z': idx}
            objects.append(SceneObject.from_dict(x))
        _uniq_ids(objects)

        prj = Project(
            schema_version=schema_version,
            canvas_mm=canvas_mm,
            grid=grid,
            components_root=components_root,
            objects=objects,
        )
        prj.clear_dirty()
        return prj


def _as_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except Exception as e:
        raise RcsSchemaError(f"Campo {field} inválido (float): {value!r}") from e


def _as_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except Exception as e:
        raise RcsSchemaError(f"Campo {field} inválido (int): {value!r}") from e


def _uniq_ids(objs: Iterable[SceneObject]) -> None:
    seen: set[str] = set()
    for o in objs:
        if o.id in seen:
            raise RcsSchemaError(f"IDs duplicados en objects[]: {o.id!r}")
        seen.add(o.id)


# ----------------------------
# Helpers
# ----------------------------

def new_object_id(prefix: str = "obj") -> str:
    """Genera un id corto y único.

    Nota: se usa UUID truncado para evitar colisiones sin depender de estado global.
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
