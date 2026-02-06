# OBSTACLES — Lista de riesgos y bloqueos

> Obstáculos = cosas que *rompen* el progreso o generan bugs “fantasma”.
> Se documentan con un ID estable para poder referenciarlos en patch notes.

---

## OPEN

- **OBS-008 — “Render invisible” (canvas en blanco / rectángulo vacío)**
  - Síntoma: SVG se carga pero no se ve (o se ve un rectángulo sin contenido).
  - Impacto: usuario queda ciego; difícil depurar sin evidencia.
  - Mitigación: fallback para que *siempre* haya algo visible.
  - Estado: **OPEN** (prioridad dentro de Render/Geom).

- **OBS-009 — Divergencia entre canvas y thumbnails**
  - Síntoma: canvas muestra una cosa, thumbs otra (o no actualizan).
  - Causa probable: pipelines distintos / parámetros distintos / cache sin invalidación uniforme.
  - Estado: **OPEN** (se ataca cuando exista “un solo camino” de render).

- **OBS-010 — Invalidación de cache incompleta (stale thumbs / stale canvas)**
  - Síntoma: cambios en SVG o en render no refrescan correctamente.
  - Impacto: bugs “fantasma” y reportes difíciles de reproducir.
  - Estado: **OPEN** (se formaliza en Fase 4 del roadmap).

---

## WATCH

- **OBS-007 — Texto importado como curvas (SVG)**
  - Síntoma: texto llega como paths/curvas y se pierde editabilidad.
  - Impacto: Bloque Texto queda limitado; no se puede editar como texto real.
  - Estado: **WATCH** (mitigación en marcha).
  - Mitigación:
    - Se arranca con `TextToolDock` (UI maquetada + payload) en v0.3.x.
    - Diseño y etapas: `docs/RCS_TEXT_TOOL.md`.
    - Objetivo final: SmartText (meta editable + vector cache + re-edición).

- **OBS-011 — Pegado de tamaño: rotación/grupos + validación dura del clipboard**
  - Problema: pegado de tamaño puede comportarse raro con items rotados o grupos (local vs scene), y el clipboard puede traer valores inválidos (0, negativos, bool camuflado).
  - Impacto: escalados inesperados / warnings (Shiboken) / UX inconsistente.
  - Estado: **WATCH** (no bloqueante; blindeo próximo hotfix).
  - Plan:
    1) Validación dura: ignorar valores inválidos y loggear 1 línea.
    2) Transform safe: aplicar escala respetando rotación; definir comportamiento para grupos.


---

## DONE

- (vacío por ahora) — mover acá solo cuando exista fix verificable + DoD cumplido.
