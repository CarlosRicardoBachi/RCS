# CHECKLIST — 0.3.10.2.70 (GMPR RasterScale + BaseSVG Visible)

## TRIAGE
- [ ] El GMPR contiene `svg_embedded` (o `svg_path`) y al menos un raster en `objects[]` o en `custom_by_uid`.
- [ ] El raster tiene `w_px/h_px` y `transform` con `sx/sy` o `s`.

## IMPORT (visual)
- [ ] Abrir GMPR: el raster NO aparece gigante.
- [ ] El raster cae en posición razonable dentro del canvas.
- [ ] El SVG base embebido se ve (si el canvas es oscuro, ajustar `RCS_GMPR_BASE_OPACITY` si hace falta).

## SAVE / RE-IMPORT
- [ ] Mover/rotar/escalar raster en RCS.
- [ ] Guardar GMPR.
- [ ] Re-importar el GMPR guardado:
  - [ ] posición OK
  - [ ] escala OK (sin inflarse)
  - [ ] rotación OK
  - [ ] flips OK (si aplica)

## REGRESIÓN
- [ ] Import de SVG normal sigue funcionando.
- [ ] Import de raster normal sigue funcionando.
