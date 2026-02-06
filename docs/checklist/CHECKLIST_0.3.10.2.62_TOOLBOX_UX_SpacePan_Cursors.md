# CHECKLIST — 0.3.10.2.62 (TOOLBOX UX)

## Pre
- [ ] Backup/commit antes de aplicar.
- [ ] Confirmar que el repo raíz es `C:\PROYECTOS\RCS` (sin doble carpeta `RCS\RCS`).

## Instalación
- [ ] Extraer el ZIP en la raíz del repo con sobrescritura (por ejemplo con PowerShell `Expand-Archive -Force`).

## Smoke tests
- [ ] La app arranca (`python -m rcs.app`) sin tracebacks.
- [ ] Mantener presionado **Space** → cursor/mano + pan con arrastre.
- [ ] Soltar **Space** → vuelve al tool anterior (Select/Rotate/Scale/etc.).
- [ ] En tool **Rotate** el cursor cambia (si el cursor custom falla, debe caer a crosshair sin romper nada).
- [ ] En tool **Scale** el cursor cambia a “size”.
- [ ] Zoom (tool Zoom) mantiene cursor de lupa (o crosshair en fallback).

## Regresión rápida
- [ ] Insertar SVG desde librería funciona.
- [ ] Copiar/Pegar tamaño sigue funcionando.
- [ ] Rotate gizmo sigue funcionando y mantiene snap (5°/1° con Shift).
