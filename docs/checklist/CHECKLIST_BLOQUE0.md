# Checklist — Bloque 0 (manual)

Entorno:
- [ ] Python 3.11+
- [ ] `pip install PySide6 pytest`

Smoke:
- [ ] `python -m rcs.app` abre la ventana.
- [ ] Menú Archivo visible.
- [ ] Archivo > Nuevo crea proyecto nuevo (título cambia a "Sin título").
- [ ] Archivo > Guardar como… genera un `.RCS` con JSON legible.
- [ ] Cerrar app y reabrir.
- [ ] Archivo > Abrir… carga el `.RCS` sin error.
- [ ] Archivo > Guardar no pregunta ruta si ya existe.
- [ ] Salir cierra sin crash.

Tests:
- [ ] `pytest -q` pasa (tests/core solamente).
