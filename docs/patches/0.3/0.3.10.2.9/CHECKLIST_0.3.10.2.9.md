# Checklist — Patch 0.3.10.2.9 (CORE)

## 1) Versionado
- [ ] `rcs/core/version.py` muestra `0.3.10.2.9` y fecha `2026-01-21`.
- [ ] `ai/context.json` actualizado a `0.3.10.2.9`.

## 2) RenderDebug (diagnóstico rápido)
Ejecutar:
- [ ] `python -m rcs.tools.render_debug "<archivo.svg>"`

Verificar en `out_debug/`:
- [ ] `thumb_stylized.png` y `canvas_stylized.png` se ven coherentes (mismo color/halo/grosor).
- [ ] No hay crash por `memoryview has no attribute setsize`.

## 3) Cache de miniaturas

Tip (debug):
- [ ] `python -c "import rcs.svg.thumbs as t; print(t.THUMB_CACHE_DIR)"` devuelve el directorio real de cache.

- [ ] Abrir un proyecto con thumbnails ya cacheadas.
- [ ] Cambiar `RCS_PREVIEW_STROKE_THICK` y reiniciar.
- [ ] Confirmar que se regeneran miniaturas (cache-key `thumb-v3` + firma de estilo).

## 4) Smoke test en UI
- [ ] Canvas: selección de objetos se sigue viendo y no desaparece.
- [ ] Doble click / selección no produce transparencias inesperadas.
- [ ] Miniaturas: no aparecen “viejas” tras cambiar grosor/tema.

## 5) Reversibilidad
- [ ] Si aparece regresión visual, bajar a `thumb-v2` debería reproducir la “falta de invalidación” (solo para diagnóstico).
