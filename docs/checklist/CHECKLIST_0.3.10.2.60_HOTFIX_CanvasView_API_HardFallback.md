# CHECKLIST — 0.3.10.2.60 HOTFIX CanvasView API HardFallback

## Archivos tocados
- `rcs/ui/canvas_view.py`
- `rcs/ui/main_window.py`
- `rcs/core/version.py`
- `docs/CHANGELOG.md`
- `docs/patches/index.md`
- `docs/patches/0.3/0.3.10.2.60/0.3.10.2.60_HOTFIX_CanvasView_API_HardFallback.md`
- `ai/context.json`

## Smoke tests (manual)
1. `python -m rcs.app` desde el root del repo.
2. Verificar que NO aparece `AttributeError: 'CanvasView' object has no attribute 'set_project'`.
3. Si faltan métodos por algún merge raro, debe aparecer un log `CanvasView: installed API fallbacks: ...` pero la app debe abrir.
4. Abrir un proyecto con objetos SVG en escena.
5. Cambiar preview style (si está en UI) y confirmar que no crashea.
6. Importar un SVG desde la librería (si estás usando el flujo) y verificar que inserta.

## Regresión
- Zoom con snap: validar que el zoom y el pan siguen funcionando.
- Render previews: no debe quedar en loop ni congelar.

## Criterios de aceptación
- La app arranca incluso si `CanvasView` llega incompleto.
- Si el método existe, no se sobreescribe (fallback solo si falta).
- `MainWindow` ya no depende 100% de `CanvasView.set_project`.
