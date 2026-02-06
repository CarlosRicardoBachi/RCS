# Checklist de pruebas — 0.3.10.2.2

## 0) Preparación
- Confirmar versión en título o en `rcs/core/version.py`: **0.3.10.2.2**.
- (Opcional) activar logs si los usás.

## 1) Smoke test
- [ ] Abrir app: `python -m rcs.app` (debe abrir sin crash).
- [ ] Mover ventana / redimensionar: no debe crashear.

## 2) Inserción de SVG (regresión principal)
- [ ] Insertar un SVG desde Biblioteca (doble click / drag / lo que uses).
- [ ] No debe aparecer el error de `alphaChannel`.
- [ ] Debe verse el preview (stroke/halo) normal.

## 3) Selección interior (hit-fill)
- [ ] Con una figura cerrada (ej: corazón), click **dentro** del contorno debe seleccionar.
- [ ] Click en vacío NO debe seleccionar.
- [ ] (Opcional) Desactivar por env y verificar: `RCS_CANVAS_HIT_FILL=0` → vuelve a requerir click en línea.

## 4) Zoom / grilla
- [ ] Zoom mínimo: al alejar no debe irse a infinito; debe clamp.
- [ ] Grilla limitada a la hoja (no "cuadricula infinita").

## 5) Guardar / abrir
- [ ] Guardar proyecto `.RCS`.
- [ ] Cerrar y reabrir: objetos y posiciones ok.
