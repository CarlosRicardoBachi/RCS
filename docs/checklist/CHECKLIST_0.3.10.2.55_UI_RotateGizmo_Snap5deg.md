# CHECKLIST — RCS 0.3.10.2.55 (UI Rotate Gizmo + Snap 5°)

## Validaciones base
- [ ] RCS inicia sin tracebacks.
- [ ] HUD/overlays amarillos siguen visibles.

## ROTATE (gizmo)
- [ ] Con selección y ToolMode.ROTATE activo, aparece el handle circular arriba del bbox.
- [ ] Click+drag sobre el handle rota la selección.
- [ ] Por defecto: snap a 5° (ΔÁngulo muestra múltiplos de 5).
- [ ] Con Shift: snap fino a 1°.
- [ ] Multi-selección: rota como grupo (se conserva el offset relativo).
- [ ] Repetir rotaciones no introduce “corrimiento” del centro (sin drift visible).

## ZOOM (cursor)
- [ ] Al activar ToolMode.ZOOM el cursor cambia (lupa si Qt lo soporta; caso contrario crosshair).
