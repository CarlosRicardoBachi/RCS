# Checklist — 0.3.10.2.35 — `CORE` — CanvasPrefs reset + scroll OFF/AUTO/ON

## Smoke test
1) Abrir la app y verificar que no crashea.
2) **Ver → Scroll del lienzo**
   - Horizontal: OFF / AUTO / ON.
   - Vertical: OFF / AUTO / ON.
   Confirmar que el comportamiento coincide con la política elegida.
3) Cerrar y reabrir: confirmar que se conserva la política.
4) **Ver → Guardar vista de inicio (F11)** y reiniciar: confirmar que arranca en esa vista.
5) **Ver → Restaurar vista de inicio** y reiniciar: confirmar que vuelve al comportamiento por defecto (sin start_view).
6) **Ver → Rango de zoom (F12)** → probar presets; luego **Restaurar rango de zoom** y verificar que queda ×1.0.
7) **Lienzo → Página por defecto (F10)**: setear un tamaño, reiniciar y confirmar que se aplica.
8) **Lienzo → Restaurar página por defecto (app)**: confirmar que limpia `default_canvas_mm` y vuelve al tamaño por defecto.

## Validación técnica
- Verificar que `rcs_settings.json` refleja:
  - `ui.canvas.scroll_h_policy` / `ui.canvas.scroll_v_policy` (preferidos)
  - y que los bool legacy `scroll_h` / `scroll_v` siguen existiendo (compat).
- Confirmar que no aparece `TypeError` por `apply_project_settings` al guardar settings.
