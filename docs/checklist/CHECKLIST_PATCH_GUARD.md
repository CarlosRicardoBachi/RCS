# CHECKLIST — Patch Guard (Anti‑Desastres)

## Antes de generar el ZIP
- [ ] El patch declara **BASE exacta** (ej: 0.3.10.2.44).
- [ ] Lista de **archivos tocados**.
- [ ] `python -m py_compile` sobre *todos* los `.py` del patch.
- [ ] Si toca UI: smoke test manual mínimo (arranca, inserta SVG, guarda/carga, cierra).

## Antes de aplicar el ZIP
- [ ] Backup automático (carpeta `patch_backups/STEP_xxx...`).
- [ ] Pre‑flight:
  - [ ] No rutas absolutas.
  - [ ] No traversal (`..\`).
  - [ ] Todo cae bajo `$ROOT`.
  - [ ] `py_compile` pasa.

## Si falla
- [ ] **Rollback inmediato**: restaurar backup del paso.
- [ ] Registrar el error exacto (stacktrace completo).
- [ ] Congelar el patch en `parches/_cuarentena/`.

