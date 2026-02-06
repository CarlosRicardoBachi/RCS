# Checklist — 0.3.10.2.59 (HOTFIX CanvasView API)

## Arranque
- [ ] `python -m rcs.app` inicia sin excepciones.
- [ ] En consola no aparece `AttributeError` relacionado con `CanvasView`.

## Preview style (menú/ajustes)
- [ ] Cambiar stroke/outline del preview no crashea.
- [ ] Si el rerender no se ejecuta por guard, aparece **1 warning** y la UI sigue usable.

## Canvas operativo
- [ ] Insertar un SVG desde la librería funciona.
- [ ] Selección + mover/zoom/escala/rotación siguen funcionando.
