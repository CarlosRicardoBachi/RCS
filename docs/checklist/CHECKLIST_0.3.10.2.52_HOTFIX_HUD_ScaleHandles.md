# CHECKLIST — RCS 0.3.10.2.52 (HOTFIX HUD + Scale Handles)

## Objetivo
Recuperar overlays (HUD) sin excepciones y habilitar escalado por handles (4 esquinas) en ToolMode.SCALE.

## Validaciones
- [ ] Al iniciar RCS no aparecen tracebacks en bucle en consola (drawForeground / overlays).
- [ ] HUD visible (amarillo) muestra:
  - [ ] Hoja (mm)
  - [ ] Lienzo (mm)
  - [ ] Zoom (%)
- [ ] ToolMode.ROTATE:
  - [ ] Con rueda se rota el objeto y se muestra overlay de **Ángulo**.
  - [ ] Shift+rueda mantiene rotación fina (no se rompió).
- [ ] ToolMode.SCALE:
  - [ ] Se ven 4 handles (puntitos) en esquinas del bbox de selección.
  - [ ] Drag desde una esquina escala sin saltos.
  - [ ] Shift+drag mantiene aspecto.
  - [ ] Overlay “Objeto: W x H mm” aparece durante el escalado.
- [ ] Multi-selección (si aplica):
  - [ ] Handles aparecen sobre bbox unido.
  - [ ] Drag escala grupo manteniendo posiciones relativas.

## Notas
- Los handles son overlay en viewport (tamaño constante en px), para que se vean igual con cualquier zoom.
