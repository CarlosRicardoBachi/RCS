# CHECKLIST — 0.3.10.2.68_HOTFIX_GMPR_CanvasSizing

## Preparación

- [ ] Aplicar el patch ZIP sobre el root del repo, manteniendo rutas.
- [ ] Ejecutar: `python -m rcs.app`
- [ ] Verificar que el log muestre: **v0.3.10.2.68**

## Regresiones clave (no romper)

- [ ] Biblioteca visible.
- [ ] Abrir varios SVG desde Biblioteca: previsualiza e inserta sin errores.

## GMPR import (objetivo del patch)

- [ ] Archivo → Importar GMPR… (proyecto real).
- [ ] Esperado: **no hay crash**.
- [ ] Raster: aparece **en posición y tamaño coherentes** respecto al SVG base.
- [ ] Rotar / Escalar / Mover raster: funciona.

## GMPR save

- [ ] Guardar GMPR.
- [ ] Cerrar app.
- [ ] Reabrir el mismo GMPR.
- [ ] Esperado: el raster reaparece en una posición/tamaño razonables (sin teletransporte).

## Limpieza

- [ ] Si el GMPR crea temporales (SVG embebido), no debe dejar archivos colgados luego de cerrar (se controla por la rutina existente de limpieza).
