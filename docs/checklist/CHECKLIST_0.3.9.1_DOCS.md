# Checklist — 0.3.9.1 (DOCS)

## Documentación
- [ ] `docs/RCS_STATUS.md` muestra **0.3.9.1** y refleja lo que ya funciona en 0.3.9.
- [ ] `docs/RCS_ROADMAP.md` incluye Bloque 4 (Texto) con sub-fases 4A..4E.
- [ ] `docs/RCS_SPEC.md` no contradice la roadmap (Texto=Bloque 4, Export=Bloque 5).
- [ ] `docs/OBSTACLES.md` contiene OBS-007.
- [ ] `docs/patches/index.md` lista 0.3.9.1.
- [ ] `ai/context.json` está en 0.3.9.1 y apunta al patch note.

## Run (sanidad)
- [ ] `python -m rcs.app` abre la app.
- [ ] Cerrar la app no deja tracebacks.

## Regression (versionado)
- [ ] `rcs/core/version.py` devuelve `APP_VERSION == "0.3.9.1"`.