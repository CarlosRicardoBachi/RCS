# Checklist — 0.3.10.2.37 — CORE_RenderGeom_Ph1b_BBoxDiff

## Smoke
- [ ] `python -c "from rcs.core.version import APP_VERSION; print(APP_VERSION)"` → `0.3.10.2.37`
- [ ] `python -m rcs.app` inicia (sin cambios visibles).

## Harness (sin svgelements)
- [ ] `python -m rcs.svg.render_debug componentes/figuras --recursive --modes raw --out _render_dbg` termina OK.
- [ ] `_render_dbg/_bbox_report.json` existe.
- [ ] En `_bbox_report.json`: al menos 1 ítem con `status == "NO_GEOM"`.

## Harness (con svgelements)
- [ ] `python -m pip install svgelements`
- [ ] Repetir harness.
- [ ] En `_bbox_report.json`: `status` no es siempre `NO_GEOM`.
- [ ] Para un ítem `PASS|WARN|FAIL`: existen `qt_bbox_xyxy`, `geom_bbox_xyxy`, `diff` y `max_abs_err_px`.

## Config
- [ ] `--bbox-tol 1 --bbox-warn 2` hace más estricto (aparecen WARN/FAIL en algún SVG si hay divergencias).
- [ ] `--bbox-report otro.json` escribe el reporte con ese nombre dentro de `--out`.

## Reversibilidad
- [ ] Si se desinstala `svgelements`, el harness vuelve a `NO_GEOM` sin crash.
