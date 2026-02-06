# Checklist - 0.3.10.2.33 (CORE_CanvasPrefs)

## DoD
- [ ] F10: definir ancho/alto (mm) por defecto, persiste en `rcs_settings.json` y aplica al proyecto actual.
- [ ] Archivo -> Nuevo: el proyecto nuevo nace con el `default_canvas_mm` persistido.
- [ ] F11: guardar vista de inicio (centro + zoom) y al reiniciar RCS se recupera.
- [ ] F12: cambiar el factor de rango de zoom (presets + personalizado), persiste y afecta limites min/max.
- [ ] Ver -> Scroll del lienzo: toggles H/V, persisten en `rcs_settings.json`.
- [ ] Sin crash al iniciar (MainWindow, CanvasView).

## Prueba rapida (60s)
1. Abrir RCS, mover/zoomear a una vista arbitraria.
2. F11, cerrar y reabrir: arranca en la misma vista.
3. F12 y elegir 2.0x: se nota el cambio de clamp (mas zoom max / menos zoom min).
4. Ver -> Scroll del lienzo: activar Vertical; mover/pan para verificar.
5. F10 y setear 800x500; Archivo -> Nuevo: el nuevo proyecto nace 800x500.
