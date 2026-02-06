# Checklist manual — Bloque 3D (v0.3.4)

## Smoke
- [ ] La app abre y muestra ventana principal.
- [ ] La biblioteca carga carpetas y miniaturas.

## Inserción (fix del bug reportado)
- [ ] Doble click en una miniatura inserta el SVG y **se ve inmediatamente** en el lienzo (sin tocar tema).
- [ ] El objeto insertado queda seleccionado.

## Hoja + lienzo
- [ ] La escena muestra una hoja de trabajo mínima 500x500 mm (scrollbars disponibles si hace falta).
- [ ] Cambiar tamaño del lienzo (botón Tamaño lienzo...) dibuja un rectángulo proporcional (ej: 100x100) dentro de la hoja.

## Pan (mover vista)
- [ ] Activar herramienta **Pan**: arrastrar con mouse mueve la vista (ScrollHandDrag).
- [ ] Desactivar Pan y volver a Mover/Seleccionar: el pan deja de actuar.

## No-regresiones básicas
- [ ] Zoom del lienzo con slider funciona.
- [ ] DEL borra objeto seleccionado.
- [ ] Ctrl+C / Ctrl+V copia y pega objetos.
- [ ] Flechas mueven selección (nudge).
