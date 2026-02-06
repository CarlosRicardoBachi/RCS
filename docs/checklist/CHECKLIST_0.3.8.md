# RCS v0.3.8 — Bloque 3F — Fit to Content

## Qué incluye
- Botón + menú **“Ajustar al objeto”**: recorta márgenes internos del SVG (viewBox grande / blancos) para que el marco se ajuste a la figura.
- Persistencia por objeto: se guarda `svg_fit_content` dentro del `.RCS`.
- Re-render (cambio de tema, etc.) vuelve a aplicar el recorte si el flag está activo.

## Archivos tocados
- `rcs/ui/main_window.py`
- `rcs/ui/canvas_view.py`
- `rcs/core/models.py` (nuevo flag `svg_fit_content`)
- `rcs/core/version.py`
- `CHANGELOG.md`

## Pruebas manuales (rápidas)
1) Abrí el proyecto y cargá un SVG con margen blanco (como el auto).
2) Seleccioná el objeto.
3) Click en toolbar **“Ajustar”** o menú **Editar → Ajustar al objeto**.
   - Esperado: el marco se achica y ahora el centro de rotación/escala queda más lógico (centrado en la figura).
4) Cambiá el tema del lienzo.
   - Esperado: el objeto **sigue** ajustado (no vuelve a aparecer el margen blanco).
5) Guardá `.RCS`, cerrá y reabrí.
   - Esperado: el ajuste persiste.

## Notas
- El recorte se hace por alpha (pixeles no transparentes). Si tu SVG usa trazos MUY finos, el recorte puede variar 1px por antialias.
