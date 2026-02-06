# 0.3.10.2.15 - HOTFIX - Canvas preview thickness (menú 'Ver')

## Problema
En algunas máquinas, el menú **Ver → Vista previa → Grosor de línea / Contorno** parecía no tener efecto sobre las líneas del lienzo.

## Causa raíz (probable)
El re-render de previews dependía de un timer y, además, la conversión a enteros truncaba valores, haciendo que varias opciones terminaran con el mismo grosor efectivo.

## Fix
- Aplicación inmediata del cambio: cuando se ajusta desde el menú, se fuerza un re-render en caliente.
- Conversión a px físicos (DPR) con redondeo y mínimo 1 cuando el valor es > 0.

## No cambios
- No se toca el estilo de thumbnails (thumbs) ni su cache.

## Archivos tocados
- `rcs/ui/canvas_view.py`
- `rcs/core/version.py`
- `docs/CHANGELOG.md`
- `docs/patches/index.md`
- `docs/patches/0.3/0.3.10.2.15/index.md`
