# CHECKLIST — 0.3.10.2.64 Hotfix GMPR I/O

## Objetivo
Validar que RCS ya no use `.RCS` como formato de proyecto y que abra/guarde `.GMPR` restaurando rasters.

## Pruebas manuales
### A) Abrir GMPR
- [ ] Archivo > Abrir proyecto GMPR
- [ ] Seleccionar un `.GMPR` válido
- [ ] El canvas muestra el **SVG base** (fondo, no seleccionable)
- [ ] Los rasters aparecen en sus posiciones (y tamaños) correctos
- [ ] Move-snap (patch 63) funciona con rasters cargados desde GMPR
- [ ] No hay crashes en consola

### B) Guardar GMPR
- [ ] Mover un raster
- [ ] Archivo > Guardar
- [ ] Se crea backup `.bak_YYYYMMDD_HHMMSS` (si el archivo ya existía)
- [ ] Reabrir el GMPR: la posición/tamaño del raster persiste

### C) Guardar como
- [ ] Archivo > Guardar como
- [ ] Guardar sin extensión -> se fuerza `.GMPR`
- [ ] Reabrir guardado -> ok

## Pruebas técnicas
- [ ] `python -m py_compile rcs/ui/main_window.py rcs/ui/canvas_view.py rcs/core/gmpr_io.py rcs/core/models.py`
- [ ] No hay dependencias Qt dentro de `rcs/core/gmpr_io.py`

