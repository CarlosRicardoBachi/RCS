# CHECKLIST — 0.3.10.2.58 (Preview rerender guard)

## Smoke
- [ ] `python -m rcs.app` abre sin crash.
- [ ] Toolbar/menús cargan y la escena se renderiza.

## Preview style
- [ ] Cambiar `stroke_thick` / `outline_thick` desde UI no crashea.
- [ ] Si el rerender existe, el cambio se refleja en previews (sin artefactos).

## Regresión
- [ ] Insertar SVG y mover/rotar/escalar sigue funcionando.
- [ ] Snap (tecla `S`) sigue funcionando (sin cambios).
