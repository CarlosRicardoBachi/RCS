# Checklist – RCS v0.2.22 HOTFIX (Zoom + Grosor Preview)

## Pre-condiciones
- Tener el entorno/venv donde ya corría RCS (PySide6, etc.).

## Smoke test
1. Abrir RCS.
2. Importar/arrastrar 1 SVG al lienzo.
3. Hacer **Ctrl + rueda** (zoom in/out):
   - El contenido hace zoom.
   - El grosor del trazo del preview se mantiene “similar” (no se engorda al acercar ni se afina al alejar).
4. Menú **Ver → Vista previa → Grosor de línea**: cambiar entre 1..6
   - Se actualiza el preview.
5. Menú **Ver → Vista previa → Contorno/Halo**: cambiar 0..3
   - Se actualiza el preview.
6. Cerrar y reabrir RCS
   - Se conservan tema + grosor elegido.

## Notas
- La compensación de grosor es aproximada (pixel-based). A zooms extremos puede haber clamping (min/max) para evitar 0px o 200px.
