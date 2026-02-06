# CHECKLIST — 0.3.10.2.71 HOTFIX GMPR Import (fix NameError canvas_w_mm)

## Build / Smoke
- [ ] `python -m py_compile rcs/core/gmpr_io.py`
- [ ] `python -m rcs.app` abre sin errores

## Repro
- [ ] Importar `proyectoabc.GMPR` ya no muestra el popup `canvas_w_mm is not defined`
- [ ] La app no crashea y completa el import (aunque el layout todavía pueda requerir ajustes en próximos hotfixes)

## No-regresión
- [ ] Importar SVG (Archivo → Importar SVG) sigue funcionando
- [ ] Guardar proyecto RCS sigue funcionando
