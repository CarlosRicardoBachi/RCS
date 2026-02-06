# CHECKLIST — 0.3.10.2.63 — UI Move SNAP (raster drag)

## Setup
- [ ] Abrir RCS con un proyecto que contenga **≥2 raster** en el canvas.
- [ ] Verificar que el modo activo sea **ToolMode.SELECT** (drag activo).

## Toggle / overlay
- [ ] Presionar **S** → aparece overlay persistente **“SNAP ON”**.
- [ ] Presionar **S** nuevamente → el overlay **“SNAP ON”** desaparece (snap OFF).

## Grid snap (1.0 mm)
Con SNAP ON:
- [ ] Arrastrar un raster a posiciones arbitrarias → al soltar / durante drag queda en múltiplos de **1.0 mm** (X/Y).
- [ ] Repetir en distintos niveles de zoom (zoom out / zoom in) → el comportamiento no cambia.

## Fine snap (0.1 mm con Shift)
Con SNAP ON:
- [ ] Mantener **Shift** durante drag → el raster queda en múltiplos de **0.1 mm** (X/Y).
- [ ] Soltar Shift y seguir moviendo → vuelve a 1.0 mm.

## Alt override (snap temporal OFF)
Con SNAP ON:
- [ ] Mantener **Alt** durante drag → movimiento **libre**, sin cuantización de grilla y sin object-snap.
- [ ] Soltar Alt sin soltar el drag → vuelve a aplicar snap.

## Object-snap + guías (prioridad sobre grilla)
Con SNAP ON:
- [ ] Arrastrar raster A cerca de raster B hasta alinear:
  - [ ] borde izquierdo con borde izquierdo
  - [ ] borde derecho con borde derecho
  - [ ] centro X con centro X
  - [ ] borde superior con borde superior
  - [ ] borde inferior con borde inferior
  - [ ] centro Y con centro Y
- [ ] Al enganchar: aparecen guías amarillas y el raster “salta” a la alineación.
- [ ] Confirmar que, si engancha por object-snap, **no se fuerza** grid-snap en ese eje (prioridad object > grid).

## Limpieza de guías
- [ ] Durante drag, alejarse de la zona de enganche → guías desaparecen.
- [ ] Soltar botón del mouse → guías se limpian siempre.

## Riesgo controlado: selección múltiple
- [ ] Seleccionar **2 rasters** y arrastrar → **NO** debe aplicar snap (ni guías, ni cuantización).
- [ ] Volver a selección simple → snap vuelve a funcionar.
