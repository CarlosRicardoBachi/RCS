# Checklist — 0.3.10.2.3

## Smoke
- [ ] Abrir app y verificar título: **RusticCreadorSvg v0.3.10.2.3**
- [ ] Abrir un proyecto nuevo (o existente) y confirmar que no cambia el schema (.RCS)

## Biblioteca
- [ ] Abrir panel Biblioteca → la grilla de miniaturas aparece.
- [ ] Miniaturas con alta visibilidad: **tinta + contorno** (no “apagadas/oscuras” bajo Qt6)
- [ ] No hay excepciones al cargar/recorrer carpetas.

## Inserción
- [ ] Doble click en `componentes/figuras/casa.svg` → aparece en lienzo.
- [ ] Doble click en `componentes/figuras/Auto.svg` → aparece en lienzo.

## Selección/Movimiento (objetivo del hotfix)
- [ ] Click en zonas internas/transparente del objeto (dentro de su caja) → **selecciona**.
- [ ] Drag con mouse → **mueve** el objeto sin “tener que acertarle al borde”.
- [ ] (Opcional) Probar revertir: set `RCS_CANVAS_PICK_BOUNDING=0` y confirmar que vuelve a máscara alfa.

---

## Notas extra (migradas desde root)
# CHECKLIST — 0.3.10.2.3 (HOTFIX) SVG visible

## Precondiciones
- Usar el ZIP incremental (solo archivos modificados) sobre tu repo/ZIP base 0.3.10.2.2.

## Smoke test (5 min)
1) Abrir la app.
   - Debe mostrar **0.3.10.2.3** en el título.

2) Biblioteca → doble click:
   - `components/figuras/casa.svg` → **se ve** en el lienzo (no solo rectángulo vacío).
   - Probar 2 SVG adicionales (uno simple y uno complejo) → también se ven.

3) Interacción básica:
   - Seleccionar, mover, zoom/pan.
   - No debe crashear.

## Test de regresión mínimo
- Abrir un `.RCS` existente, insertar 3 SVG, guardar, cerrar, reabrir.
- Verificar que lo insertado sigue visible.
