# RCS_MAP — Mapa del proyecto (dónde tocar qué)

## Entrypoints
- `app.py`: bootstrap (si existe en root)
- `rcs/app.py`: entry real para `python -m rcs.app`

## UI
- `rcs/ui/main_window.py`
  - Menú/toolbar
  - Acciones globales (Nuevo/Abrir/Guardar, etc.)
  - Wiring entre LibraryPanel ↔ CanvasView ↔ Project

- `rcs/ui/canvas_view.py`
  - Scene/View (QGraphicsView)
  - Cámara: zoom/pan/centrado
  - Selección, drag, nudge (flechas), borrado (DEL)
  - Transformaciones (rotación/escalado) según modo

- `rcs/ui/library_panel.py`
  - Árbol de carpetas + mosaico thumbnails
  - Inserción: genera `SceneObject` con `source` relativo

- `rcs/ui/text_tool_dock.py` *(nuevo, WIP)*  
  - Dock/toolbar **movible** para edición de Texto (fuente, tamaño, alineación, **interlineado**, caja W/H).  
  - Fase 0–1: maquetado UI + payload; Fase 2+: generación vector + re-edición.

## Core
- `rcs/core/models.py`
  - `Project`, `SceneObject`, `Transform`
  - Estado serializable (nunca mezclar GUI acá)

- `rcs/core/serialization.py`
  - load/save `.RCS`

- `rcs/core/settings.py`
  - settings de usuario (tema, zoom, etc.)

## SVG
- `rcs/svg/importer.py`
  - parse/validación/normalización (contrato estable)
- `rcs/svg/exporter.py`
  - export contornos-only (pendiente endurecer)
- `rcs/svg/thumbs.py`
  - cache de thumbnails
- `rcs/svg/qpath_render.py`
  - render de paths (si aplica)

## Dónde implementar X (atajos)
- “No se ve el objeto al insertar”: `library_panel.py` (source path) y `canvas_view.py` (creación del item/render)
- “Rotación/escala pivote”: `canvas_view.py` (transformOriginPoint / pivot lógico)
- “Copy/Paste / Duplicar”: `canvas_view.py` (clonar objeto) + `main_window.py` (acciones/shortcuts)
- “Export contornos-only”: `svg/exporter.py` + pruebas con pipeline
