# CHECKLIST — 0.3.9 (Bloque 3H: Scrollbars + Pan/Zoom UX)

**Fecha:** 2026-01-17  
**Versión objetivo:** 0.3.9

## 0) Setup
- [ ] Confirmar `rcs/core/version.py` = `0.3.9`.
- [ ] (Opcional) borrar/rotar `logs/` para facilitar lectura.

## 1) Smoke test (arranque)
- [ ] `python -m rcs.app` abre sin tracebacks.
- [ ] Abrir un `.RCS` existente con varios objetos.

## 2) Scrollbars (default)
- [ ] Por defecto no se ven scrollbars (no deben estar “clavadas” en pantalla).
- [ ] Zoom in/out (rueda del mouse) no introduce saltos raros por aparición/desaparición de scrollbars.

## 3) Pan
- [ ] Herramienta PAN:
  - [ ] Click+drag con botón izquierdo mueve la vista (mano).
  - [ ] Al soltar no deja el cursor “pegado” ni deja el modo inestable.
- [ ] Pan rápido con botón medio (MMB):
  - [ ] Mantener MMB + arrastrar mueve la vista.
  - [ ] Soltar MMB restaura el cursor normal.

## 4) Zoom/Rotate/Scale (regresión)
- [ ] Zoom herramienta: rueda del mouse cambia zoom sin “snap” (regresión hotfix 0.3.8.2).
- [ ] Rotar herramienta: rueda del mouse rota selección sin jumps de cámara.
- [ ] Escalar herramienta: rueda del mouse escala selección sin jumps de cámara.

## 5) Fit to Content (regresión)
- [ ] Seleccionar un SVG y ejecutar Fit to Content (menú/contexto).
- [ ] Confirmar que el objeto queda ajustado sin perder la selección.
- [ ] Luego aplicar un gesto de zoom: no debe “saltar” a otra escala inesperada.

## 6) Override por env var
> Nota: requiere reiniciar la app.

- [ ] `RCS_CANVAS_SCROLLBARS=on`:
  - [ ] Scrollbars visibles siempre.
  - [ ] Pan (herramienta y MMB) sigue funcionando.
- [ ] `RCS_CANVAS_SCROLLBARS=needed`:
  - [ ] Scrollbars aparecen sólo si el contenido supera el viewport.
  - [ ] No hay crasheos ni warnings.

## 7) Cierre
- [ ] Cerrar la app sin errores.
