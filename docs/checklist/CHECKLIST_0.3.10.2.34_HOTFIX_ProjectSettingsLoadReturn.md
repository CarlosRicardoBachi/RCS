# CHECKLIST — 0.3.10.2.34 — HOTFIX — ProjectSettingsLoadReturn

## Smoke (arranque)
- [ ] `python -m rcs.app` inicia sin traceback.
- [ ] En el log no aparece `ValueError: too many values to unpack`.

## CanvasPrefs (F10 / Nuevo)
- [ ] F10 abre diálogo, acepta valores mm y aplica al proyecto actual.
- [ ] Tras F10, `Archivo → Nuevo` hereda el canvas por defecto actualizado **sin reiniciar**.

## Scrollbars (Ver)
- [ ] Ver → Scrollbars → Horizontal: ON/OFF aplica en el canvas.
- [ ] Ver → Scrollbars → Vertical: ON/OFF aplica en el canvas.
- [ ] Al togglear H/V se actualiza el status inferior con ON/OFF.
- [ ] Cerrar y reabrir conserva H/V.

## Regressions obvias
- [ ] Abrir proyecto existente no cambia su canvas salvo que el usuario lo modifique.
- [ ] Render y thumbnails sin cambios visibles.
