# Checklist — HOTFIX 0.3.7 (2026-01-16)

## Objetivo
Corregir inserción de SVG desde la biblioteca cuando la señal entrega una **ruta relativa** (caso real). Debe verse el objeto inmediatamente.

## Smoke tests (manuales)
1. Abrir RCS.
2. Seleccionar carpeta en Biblioteca → se ven miniaturas.
3. Doble click en una miniatura → **aparece inmediatamente** en el lienzo.
4. Insertar 5 assets seguidos → todos visibles.
5. Guardar proyecto `.RCS` → cerrar → abrir → los 5 siguen visibles.

## Regresión rápida
- Cambiar tema del lienzo (menú Ver) no debe afectar visibilidad (solo estética).
- Zoom/rotar/escalar siguen funcionando como antes.

## Archivos tocados
- `rcs/ui/canvas_view.py`
- `rcs/ui/library_panel.py`
- `rcs/core/version.py`
- `CHANGELOG.md`
