# RCS v0.2.22 – HOTFIX (Zoom + Grosor Preview)

Fecha: 2026-01-16

## Objetivo
- Incorporar zoom en el lienzo sin que cambie el grosor percibido del trazo del preview.
- Permitir ajustar el grosor del trazo del preview desde menú, guardado en settings.

## Cambios
### Canvas
- Zoom con **Ctrl + rueda**.
- Menú: **Ver → Zoom In / Zoom Out / Zoom Reset**.
- El preview recompensa el grosor: al cambiar zoom se re-renderiza el SVG con grosor inverso al zoom para que en pantalla quede estable.

### Configuración persistente
- `settings.json` ahora incluye:
  - `canvas_stroke_thick` (default 3)
  - `canvas_outline_thick` (default 1)
  - (se mantienen theme y valores para thumbs)

### Menú de grosor
- Menú: **Ver → Vista previa → Grosor de línea** (1..6)
- Menú: **Ver → Vista previa → Contorno/Halo** (0..3)
- Al cambiar, se guarda automáticamente y se actualiza el preview.

## Archivos tocados
- `rcs/ui/canvas_view.py`
- `rcs/ui/main_window.py`
- `rcs/core/settings.py`
- `rcs/core/version.py`
