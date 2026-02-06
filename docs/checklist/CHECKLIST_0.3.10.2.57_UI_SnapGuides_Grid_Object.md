# CHECKLIST — 0.3.10.2.57_UI_SnapGuides_Grid_Object

## Preparación
- [ ] Repo limpio (sin archivos locales sin commitear) o backup.
- [ ] Aplicaste el ZIP en la raíz del repo (rcs/, docs/, ai/).

## Smoke test
- [ ] `python -m rcs.app` abre sin errores.
- [ ] Insertar SVG desde librería funciona.

## Snap (SELECT)
- [ ] Presionar **S** alterna Snap ON/OFF (overlay lo indica).
- [ ] Con Snap ON: drag mueve con pasos de **1.0 mm**.
- [ ] Con Snap ON + **Shift**: drag mueve con pasos de **0.1 mm**.
- [ ] Con Snap ON + **Alt** (mantener mientras arrastras): drag sin snap.

## Guías visuales
- [ ] Acercar borde/centro de la selección a otro objeto muestra línea amarilla y engancha.
- [ ] Guías desaparecen al soltar o al dejar de estar en threshold.

## No-regresión rápida
- [ ] ToolMode.SCALE: handles siguen funcionando.
- [ ] ToolMode.ROTATE: gizmo + snap 5°/1° sigue funcionando.
- [ ] Overlays amarillos (tamaño/ángulo/zoom/hoja/lienzo) siguen apareciendo.
