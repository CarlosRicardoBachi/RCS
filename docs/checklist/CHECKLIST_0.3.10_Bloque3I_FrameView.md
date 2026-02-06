# CHECKLIST — 0.3.10 (Bloque 3I: Frame View)

**Objetivo:** validar encuadre de vista sin romper cámara/zoom/pan existentes.

## Preparación
- [ ] Confirmar versión en `Ayuda → Acerca` o en log: `0.3.10`.
- [ ] Abrir un `.RCS` existente con varios objetos.

## Casos
### 1) Encuadrar selección (F)
- [ ] Seleccionar 1 objeto → presionar `F` → objeto queda centrado y visible con margen.
- [ ] Seleccionar 2+ objetos separados → `F` → encuadra el conjunto.
- [ ] Sin selección → `F` → no crashea, status dice “No hay selección para encuadrar”.

### 2) Encuadrar todo (Shift+F)
- [ ] Con 1+ objetos en escena → `Shift+F` → encuadra todos.
- [ ] Con 0 objetos → `Shift+F` → no crashea, status dice “No hay objetos para encuadrar”.

### 3) Ver hoja (Ctrl+Shift+0)
- [ ] Estando muy zoomeado/paneado lejos → `Ctrl+Shift+0` → vuelve a ver la hoja completa.

### 4) Integración con zoom/pan
- [ ] Luego de `F` o `Shift+F`, usar `Ctrl++`/`Ctrl+-` (o rueda) → zoom no “salta” raro.
- [ ] Pan (MMB) sigue funcionando.
- [ ] Insertar desde biblioteca un SVG estando encuadrado en un rincón → el objeto aparece en viewport (comportamiento actual).

## Criterio de OK
- [ ] 0 crashes.
- [ ] Los 3 encuadres funcionan y no degradan zoom/pan.
