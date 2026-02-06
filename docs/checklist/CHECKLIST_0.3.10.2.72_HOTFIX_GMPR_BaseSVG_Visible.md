# Checklist — 0.3.10.2.72 HOTFIX GMPR Base SVG Visible

- [ ] `python -m py_compile rcs/ui/canvas_view.py`
- [ ] `python -m rcs.app` abre sin errores
- [ ] Importar `.GMPR` con SVG embebido
- [ ] El fondo (SVG base) se ve en tema oscuro (alto contraste)
- [ ] El fondo respeta escala real (mm) y queda en el origen del lienzo
- [ ] El raster aparece (aunque aún no esté perfecto), y se puede comparar contra el fondo
- [ ] (Opcional) Probar env: `RCS_GMPR_BASE_OPACITY`, `RCS_GMPR_BASE_STROKE_PX`
