# Checklist — 0.3.10.2.56 — UI_ZoomSmoother_Wheel

## Setup
- Ejecutar: `python -m rcs.app`
- Abrir un proyecto o insertar un SVG para tener referencia visual.

## Verificación manual
1) **ToolMode.ZOOM**
- Seleccionar herramienta Zoom.
- Rueda hacia arriba: zoom in con salto **más suave** que antes.
- Rueda hacia abajo: zoom out con salto **más suave** que antes.

2) **ToolMode.ZOOM + Shift (fino)**
- Mantener Shift y repetir rueda.
- Confirmar que el zoom cambia **más lento** que sin Shift.

3) **Modo Select + Ctrl+Rueda**
- Volver a Select (o el modo normal de selección).
- Mantener Ctrl y usar rueda.
- Confirmar que la suavidad coincide con ToolMode.ZOOM.

4) **No-regresión en herramientas de objeto**
- Cambiar a ToolMode.SCALE y usar rueda sobre un objeto: debe seguir escalando el objeto (no zoom).
- Cambiar a ToolMode.ROTATE y usar rueda sobre un objeto: debe seguir rotando el objeto (no zoom).

## DoD
- No hay excepciones en consola.
- El zoom no “pega saltos” al primer gesto después de abrir proyecto.
