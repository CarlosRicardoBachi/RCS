# CHECKLIST — 0.3.10.2.38 — CORE — Render/Geom Phase 1c: BBox Regression Harness

## Smoke (30–60s)
1. Ejecutar harness sobre 3–10 SVGs:
   - `python -m rcs.svg.render_debug <carpeta_o_svg> --out _dbg38 --recursive --modes raw --bbox-tol 3 --bbox-warn 8`
2. Verificar que existan en `_dbg38/`:
   - `_bbox_report.json`
   - `_bbox_failures.json`
   - `_summary.json`

## Ranking + repro
3. Abrir `_bbox_failures.json` y confirmar:
   - Está ordenado: primero INVISIBLE/FAIL, luego WARN.
   - Cada entrada trae `status`, `max_abs_err_px` y `repro`.
4. Copiar un `repro` y ejecutarlo: debe regenerar el mismo caso en otro `--out` sin crashear.

## Baseline compare
5. Guardar baseline:
   - Ejecutar una vez y copiar el reporte: `_dbg38/_bbox_report.json` → `baseline_bbox.json`
6. Ejecutar compare:
   - `python -m rcs.svg.render_debug <carpeta_o_svg> --out _dbg38b --recursive --modes raw --bbox-baseline baseline_bbox.json`
7. Verificar que existe `_dbg38b/_bbox_regressions.json` y que el resumen imprime counts (regressions/improvements/...).

## No romper nada
8. Confirmar que el uso normal de la app (`python -m rcs.app`) sigue funcionando.
