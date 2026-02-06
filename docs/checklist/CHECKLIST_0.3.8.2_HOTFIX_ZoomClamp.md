# Checklist — HOTFIX 0.3.8.2 (2026-01-17)

## Objetivo
Evitar saltos de zoom luego de `fitInView()` y limitar escalas extremas sin cortar la continuidad del gesto.

## Smoke tests (manuales)
1. Abrir RCS.
2. Abrir un proyecto `.RCS` existente.
3. Sin tocar nada, hacer **Ctrl+rueda arriba** → el zoom debe aumentar suavemente (sin snap brusco).
4. Hacer **Ctrl+rueda abajo** repetidas veces → no debe ir a escalas cada vez más microscópicas si ya estaba muy lejos (debe frenar en el mínimo dinámico).
5. Activar herramienta **Zoom** (toolbar) y repetir rueda (sin Ctrl) → mismo comportamiento.
6. Usar menú **Ver → Zoom In / Zoom Out / Zoom Reset** → coherente.

## Regresión rápida
- Selección y mover SVG sigue igual.
- Rotar/Escalar por herramienta sigue igual.
- Preview (stroke/halo) se re-renderiza al cambiar zoom.

## Archivos tocados
- `rcs/ui/canvas_view.py`
- `rcs/core/version.py`
- `docs/CHANGELOG.md`
- `docs/RCS_STATUS.md`
- `docs/patches/index.md`
- `docs/patches/0.3/0.3.8.2/0.3.8.2_HOTFIX_ZoomClamp.md`
