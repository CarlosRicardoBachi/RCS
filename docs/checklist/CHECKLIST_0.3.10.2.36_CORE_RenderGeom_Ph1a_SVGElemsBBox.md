# Checklist — 0.3.10.2.36 — CORE_RenderGeom_Ph1a_SVGElemsBBox

## Smoke
- [ ] `python -c "from rcs.core.version import APP_VERSION; print(APP_VERSION)"` → `0.3.10.2.36`
- [ ] `python -m rcs.app` inicia (sin cambios visibles).

## Harness (sin svgelements)
- [ ] `python -m rcs.svg.render_debug componentes/figuras --recursive --modes raw --out _render_dbg` termina OK.
- [ ] En un `*_summary.json`: `svgelements.available == false` + `svgelements.error` presente.

## Harness (con svgelements)
- [ ] `python -m pip install svgelements`
- [ ] Repetir harness.
- [ ] En `*_summary.json`: `svgelements.available == true`.
- [ ] `svgelements.bbox` presente y con 4 floats.
- [ ] `qtsvg_viewbox` presente y con 4 floats.

## Reversibilidad
- [ ] Si se desinstala `svgelements`, el harness vuelve a modo `available=false` sin crash.
