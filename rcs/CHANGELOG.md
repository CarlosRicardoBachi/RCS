# Patch Changelog — 0.3.10.2.9

## Incluye
- PreviewStyle unificado (canvas + thumbs): tinta + contorno (Qt6-safe) desde un pipeline único.
- Thumbs: cache-key robusta (`thumb-v3` + firma de estilo) para evitar miniaturas “viejas” al cambiar theme/grosor/escala.
- Canvas: delega stylize a PreviewStyle (evita duplicación y divergencia).
- Debug: `rcs.svg.thumbs` expone `THUMB_CACHE_DIR` / `CACHE_DIR` para ubicar rápido el cache.

## Archivos tocados
- rcs/svg/preview_style.py
- rcs/svg/thumbs.py
- rcs/ui/canvas_view.py
- rcs/svg/render_debug.py
- rcs/tools/render_debug.py
- rcs/core/version.py
- ai/context.json
- docs/RCS_STATUS.md
- docs/OBSTACLES.md
- docs/CHANGELOG.md
- docs/patches/index.md
- docs/patches/0.3/0.3.10.2.9/*
