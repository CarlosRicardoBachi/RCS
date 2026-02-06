# Checklist - v0.3.10.2.70 GMPR Base Align + Raster Anchor

## Básico
- [ ] `python -m rcs.app` muestra v0.3.10.2.70
- [ ] Biblioteca de componentes sigue visible y abre SVGs

## Importación GMPR
- [ ] Importar GMPR con SVG base + raster
- [ ] SVG base ocupa área completa del canvas (escala real)
- [ ] SVG base es seleccionable (solo inspección) y no se mueve
- [ ] Raster aparece alineado con el SVG base
- [ ] Raster NO aparece gigante (caso sx/sy ≈ 1.0)
- [ ] Raster mantiene proporción correcta

## Interacción
- [ ] Click en raster → se selecciona y se puede mover/escalar/rotar
- [ ] Herramientas ZOOM/PAN/SELECT siguen funcionando

## Persistencia
- [ ] Guardar, cerrar, reabrir → posiciones se mantienen
