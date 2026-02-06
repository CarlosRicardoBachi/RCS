# RCS_ROADMAP_RENDER_GEOM — Render/Geometría (Skia + svgelements)

Objetivo general: que **canvas** y **thumbnails** salgan del *modo brujería* y pasen a un pipeline determinista:

`SVG -> DOM -> Geometría (truth) -> Render (backend)`

Principios:
- **No romper nada:** cada ZIP es pequeño, aplicable y con rollback fácil.
- **Un solo “source of truth”:** si canvas y thumbs difieren, el bug es del pipeline, no del usuario.
- **Backends pluggables:** QtSvg puede seguir viviendo, pero detrás de una interfaz (y Skia entra sin reescribir UI).

---

## Fase 0 — Instrumentación mínima (reproducible y medible)

### Entregable ZIP-0001 — “Harness” de render (sin UI)
**Meta:** poder reproducir: (a) *render invisible*, (b) divergencia canvas/thumbs, (c) diferencias por SVG específico.

**DoD**
- [ ] Existe un script/harness que procesa un SVG “fixture” y produce:
  - [ ] salida *raw* (render directo),
  - [ ] salida *canvas-like*,
  - [ ] salida *thumbnail-like*.
- [ ] El harness guarda evidencia: imágenes + log con parámetros (dpi, viewbox, size, backend).
- [ ] Corre sin abrir la UI principal.

**Checklist**
- [ ] Ejecutar harness con 2 SVG: uno “OK” y uno se sabe problemático.
- [ ] Verificar que las 3 salidas se generen y se guarden.
- [ ] Adjuntar 1 screenshot en la patch note (opcional pero recomendado).

---

## Fase 1 — Geometría como “truth” (bbox, hit-test, unidades)

### Entregable ZIP-0002 — Parse DOM + bbox determinista (svgelements)
**Meta:** tener bbox confiable por elemento y por documento, independientemente del backend de render.

**DoD**
- [ ] Se puede cargar un SVG y obtener bbox global (doc) y bbox por elemento (cuando aplique).
- [ ] Unidades y viewBox se normalizan (no “pixeles mágicos”).
- [ ] Se loguean diferencias detectadas entre bbox actual (legacy) y bbox nuevo (svgelements).

**Checklist**
- [ ] Probar 3 SVG distintos (simple, con transforms, con viewBox raro).
- [ ] Comparar bbox viejo vs bbox nuevo y registrar diferencias esperables.

### Entregable ZIP-0003 — Hit-test básico desde Geometría
**Meta:** selección no depende del renderer; depende de la geometría.

**DoD**
- [ ] Hit-test punto→elemento usa el motor geométrico (svgelements) como fuente.
- [ ] Mantiene compatibilidad: si no hay geometría para un elemento, fallback al método actual.
- [ ] No degrada performance perceptible (se cachea cuando conviene).

**Checklist**
- [ ] Seleccionar elementos superpuestos: el hit-test es estable (mismo click → mismo elemento).
- [ ] Confirmar que el fallback sigue funcionando.

---

## Fase 2 — Pipeline unificado (canvas y thumbs comparten cadena)

### Entregable ZIP-0004 — Interfaz de RenderBackend + “un solo camino”
**Meta:** el render para canvas y thumbnails pasa por una API común.

**DoD**
- [ ] Existe `RenderBackend` (interfaz) con al menos 1 implementación (QtSvg o la actual).
- [ ] Canvas y thumbs llaman al mismo método de alto nivel (mismos parámetros/normalización).
- [ ] Se documenta dónde se cachea y cuándo se invalida.

**Checklist**
- [ ] Render de un mismo SVG → canvas y thumb coinciden visualmente (o la diferencia está explicada).
- [ ] Cambiar zoom/size no deja thumbs “stale”.

---

## Fase 3 — Backend Skia (entrada gradual, sin reemplazo big-bang)

### Entregable ZIP-0005 — Skia backend “MVP” (fills/strokes básicos)
**Meta:** Skia entra como alternativa, no como reemplazo inmediato.

**DoD**
- [ ] Skia renderiza un subconjunto: paths + fill/stroke (sin gradientes complejos).
- [ ] Hay un switch de backend (config / flag) sin tocar UI.
- [ ] Si Skia falla, fallback automático al backend actual.

**Checklist**
- [ ] Renderizar 2 SVG con Skia: uno simple y uno mediano.
- [ ] Comparar contra backend actual (no tiene que ser pixel-perfect; sí consistente).

---

## Fase 4 — Consistencia + cache + regresión (lo aburrido que evita incendios)

### Entregable ZIP-0006 — Invalidador de cache + suite mínima de fixtures
**Meta:** evitar “fantasmas” (thumbs viejos, canvas sin update) y congelar casos de prueba.

**DoD**
- [ ] Hay reglas explícitas de invalidación (cambió SVG / cambió size / cambió backend → qué se invalida).
- [ ] Existe una carpeta de fixtures (mínimo 5 SVG) + script de regresión.
- [ ] Se puede correr la regresión en < 30s y detectar divergencias.

**Checklist**
- [ ] Cambiar un SVG y verificar que thumbs/canvas se regeneran.
- [ ] Correr regresión y confirmar que reporta PASS/FAIL con evidencia.

---

## Nota sobre texto (backlog)

Bloque Texto se mantiene backlog hasta cerrar Fase 2 (pipeline unificado).  
Razón: texto depende fuertemente de bbox/hit-test y de la consistencia canvas/thumbs.
