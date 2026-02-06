# CHECKLIST — 0.3.10.2.1 (HOTFIX) Arranque: zoom mínimo

## Objetivo
Validar que la app **ya no crashea** al iniciar y que el cálculo de zoom mínimo sigue comportándose bien.

## Pruebas
- [ ] **Arranque**: ejecutar `python -m rcs.app` → abre sin traceback.
- [ ] **Resize**: redimensionar la ventana 10+ veces (arrastrar bordes) → sin crash.
- [ ] **Zoom**: usar rueda y slider en ambos sentidos → el mínimo no permite perder la hoja “en el infinito”.
- [ ] **Regresión**: insertar una figura cerrada y seleccionar con click dentro → sigue funcionando.

## Entorno recomendado
- Misma venv que venís usando (`.venv`).
- Si usás OpenGL opt-in: probar también con `RCS_CANVAS_OPENGL=1`.
