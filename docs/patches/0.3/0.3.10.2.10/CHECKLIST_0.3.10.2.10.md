# CHECKLIST — 0.3.10.2.10 (HOTFIX)

## Precondición
- Estás parado en el root del repo (`C:\PROYECTOS\RCS`).
- Venv activa.

## Smoke
- [ ] `python -c "from rcs.core.version import APP_VERSION; print(APP_VERSION)"` → `0.3.10.2.10`
- [ ] `python -m rcs.app` abre sin errores.

## Repro del bug (debe NO ocurrir)
- [ ] Abrir RCS → doble click en un SVG de Biblioteca.
  - Esperado: **no** aparece dialog de error.
  - Esperado: aparece el item (o al menos el rectángulo de selección + preview visible).

## Env vars de preview (no deben romper)
- [ ] En `cmd.exe`:
  - `set RCS_PREVIEW_STROKE_THICK=6 && set RCS_PREVIEW_OUTLINE_THICK=3 && python -m rcs.app`
  - Insertar un SVG → no explota.
- [ ] `set RCS_PREVIEW_THEME=light && python -m rcs.app`
  - Insertar un SVG → no explota.

## Harness (sanity)
- [ ] `python -m rcs.tools.render_debug "...\componentes\figuras\casa.svg"` genera salida en `render_debug_out` y termina OK.

## Regresión a vigilar
- [ ] Si vuelve a aparecer `unexpected keyword argument` en helpers, revisar wrappers locales: deben aceptar kwargs y delegar (OBS-011).
