# README_AI — Cómo colaborar con RCS sin romperlo

Este repo tiene una “constitución” y un flujo de parches. La idea es simple: **hacer cambios pequeños, trazables y reversibles**.

## Orden de lectura
1) `docs/START_HERE.md`
2) `ai/context.json`
3) `docs/RCS_CONSTITUTION.md`
4) `docs/RCS_STATUS.md`
5) `docs/patches/index.md` + `docs/OBSTACLES.md`

## Reglas operativas
- No remover funcionalidades ya probadas.
- Si hay regresión: hotfix primero.
- Cambios como ZIP incremental (solo archivos tocados).

## Entrega mínima por parche
- Archivos modificados
- `docs/CHANGELOG.md`
- Patch note en `docs/patches/...`
- Checklist de pruebas manuales

## Env vars relevantes
- `RCS_CANVAS_OPENGL=1` habilita viewport OpenGL (opt-in).
- `RCS_CANVAS_PREVIEW_DPR` (1..4) controla nitidez de previews raster.
- `RCS_CANVAS_PREVIEW_PX` (96..1024) tamaño lógico base de preview.
