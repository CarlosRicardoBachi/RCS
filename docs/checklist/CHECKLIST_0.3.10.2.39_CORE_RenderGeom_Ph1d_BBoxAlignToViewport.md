# CHECKLIST — 0.3.10.2.39 — CORE — Render/Geom Phase 1d: BBox Align to QtSvg Viewport

## Smoke (60s)
1. Ejecutar harness sobre una carpeta de SVGs (idealmente los que te daban FAIL ~200px):
   - `python -m rcs.svg.render_debug componentes/figuras --recursive --modes raw --out _dbg39`
2. Verificar que existan en `_dbg39/`:
   - `_bbox_report.json`
   - `_bbox_failures.json`
   - `_summary.json`

## Verificación de alineación
3. Abrir `_dbg39/_bbox_report.json` y revisar 2–3 entradas:
   - Deben incluir `geom_align`.
   - `geom_align.chosen` debería ser **distinto de `raw`** cuando había desalineación.
4. Confirmar que el log muestre:
   - `bbox: <status> err=<...> align=<kind>` en los casos alineados.

## Señal útil
5. Comparar contra tu corrida anterior:
   - los FAIL “en masa” por error sistemático deben bajar,
   - los WARN/FAIL restantes deben ser interpretables (stroke, invisibles, casos raros).

