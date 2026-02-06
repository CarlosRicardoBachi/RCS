# CHECKLIST — 0.3.10.2.65 (HOTFIX GMPR)

## Build / sanity

- [ ] `python -m py_compile rcs/ui/main_window.py`
- [ ] `python -m py_compile rcs/core/gmpr_io.py`
- [ ] `python -m py_compile rcs/core/models.py`
- [ ] App abre y muestra ventana principal.

## Repro 1: biblioteca SVG no desaparece al importar GMPR

1. Abrir RCS.
2. Ver panel Bibliotecas con thumbnails.
3. Archivo → Importar GMPR… y elegir un `.gmpr`.
4. Verificar:
   - Bibliotecas sigue mostrando los SVG (no queda vacía).
   - Doble click en un SVG de Bibliotecas inserta el componente.

## Repro 2: rasters conservan tamaño/posición

1. Importar el GMPR del caso reportado (con raster_meta.transform: sx/sy + s + rot).
2. Verificar:
   - Raster aparece en la posición esperada.
   - Raster conserva tamaño relativo correcto vs el SVG base.
3. Mover/escale el raster en RCS.
4. Guardar (Ctrl+S) y cerrar.
5. Reabrir el GMPR con Archivo → Importar GMPR….
6. Verificar que se conserva (pos/scale/rot).

## UI / menú

- [ ] Archivo muestra: Importar SVG…, Importar GMPR…, Guardar, Guardar como…
- [ ] Ctrl+O abre selector de SVG y lo inserta sin descartar el proyecto.
- [ ] Ctrl+I importa GMPR y descarta el proyecto previo (con prompt de guardado si está dirty).
