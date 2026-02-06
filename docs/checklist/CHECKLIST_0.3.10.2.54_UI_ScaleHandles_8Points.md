# CHECKLIST — RCS 0.3.10.2.54 (UI Scale Handles 8 puntos)

## Validaciones base
- [ ] RCS inicia sin tracebacks.
- [ ] HUD/overlays amarillos siguen visibles.

## SCALE
- [ ] Con un objeto seleccionado y ToolMode.SCALE activo, aparecen 8 handles (4 esquinas + 4 medios).
- [ ] En MOVE y ROTATE NO aparecen handles de escala.
- [ ] Arrastrar esquina escala X/Y.
- [ ] Arrastrar handle medio lateral escala solo X.
- [ ] Arrastrar handle medio superior/inferior escala solo Y.
- [ ] Al soltar, re-seleccionar: el bbox y handles coinciden (sin drift).
