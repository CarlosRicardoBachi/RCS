# Checklist — Pruebas manuales (v0.2.24 / HOTFIX)

1. **Arranque**
   - `python -m rcs.app` abre la ventana sin errores.

2. **Biblioteca: mosaico + thumbnails**
   - Confirmar que existe una carpeta `componentes/` con varias subcarpetas y **>= 30 SVG**.
   - Abrir el dock “Biblioteca”.
   - Seleccionar una carpeta con SVG:
     - Debe aparecer el **mosaico** (iconos + nombre).
     - Los thumbnails deben “aparecer progresivamente” (sin congelar la UI).

3. **Cache (reapertura)**
   - Cerrar la app y volver a abrir.
   - Ir a la misma carpeta: los thumbnails deben cargar mucho más rápido (usa cache).

4. **Búsqueda**
   - Escribir en “Buscar…” una parte del nombre (ej: `boca`, `star`, `escudo`).
   - Verificar que filtra items del mosaico y al borrar el texto vuelve todo.

5. **Insertar SVG**
   - Doble click en un SVG del mosaico.
   - Debe aparecer en el lienzo.

6. **Validación básica**
   - Intentar insertar un SVG que use `mask/clipPath/filter/pattern`.
   - Debe dar error claro (convertir a paths antes de usar).
