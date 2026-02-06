# CHECKLIST — 0.3.10.2.18

## Antes
- [ ] Estás sobre `0.3.10.2.17` o superior (arranca la app).
- [ ] Cerraste RCS antes de aplicar el zip.

## Aplicación
- [ ] Expand-Archive del zip en `C:\PROYECTOS\RCS` (NO_RCS_ROOT).
- [ ] `python -c "from rcs.core.version import APP_VERSION; print(APP_VERSION)"` → `0.3.10.2.18`.

## Pruebas rápidas
- [ ] Abrir RCS (`python -m rcs.app`).
- [ ] Insertar SVG desde biblioteca (ej: `corazon.svg`).
- [ ] Cambiar **Ver → Vista previa → Grosor de línea** (mínimo/medio/máximo) y confirmar diferencia.
- [ ] Cambiar **Ver → Vista previa → Contorno** y confirmar diferencia.
- [ ] Confirmar thumbnails OK (no deformados, grosor razonable).

## Si algo falla
- [ ] Copiar traceback completo.
- [ ] Confirmar que `rcs/ui/canvas_view.py` es el del parche (fecha/tamaño cambió).
