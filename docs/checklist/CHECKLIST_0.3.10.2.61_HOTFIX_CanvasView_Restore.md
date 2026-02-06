# CHECKLIST — 0.3.10.2.61 HOTFIX CanvasView Restore

## Instalación
- [ ] Descomprimir el ZIP en la raíz del repo (donde están `rcs/`, `docs/`, `ai/`).
- [ ] Confirmar que **se sobreescribió** `rcs/ui/canvas_view.py` (fecha/hora de modificación).

## Smoke test (obligatorio)
- [ ] `python -m rcs.app` inicia sin tracebacks.
- [ ] Se ve el **lienzo/hoja** y la grilla.
- [ ] Doble click en un SVG de la biblioteca → inserta sin error.
- [ ] Escalar: handles aparecen con ToolMode.SCALE y permiten drag.
- [ ] Rotar: gizmo ⟲ aparece en ToolMode.ROTATE y se ve ΔÁngulo en overlay amarillo.
- [ ] Zoom: cursor de zoom se aplica (lupita si Qt lo expone, si no crosshair) y el zoom es suave (según hotfix 0.56).

## Si falla
- [ ] Verificar que NO quedó una carpeta anidada (ej: `RCS_HOTFIX_.../rcs/...`) dentro del repo.
- [ ] Abrir `rcs/ui/canvas_view.py` y buscar `def insert_svg_from_library` y `def set_project` (deben existir dentro de la clase CanvasView).
