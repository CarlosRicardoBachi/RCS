# CHECKLIST — 0.3.10.2.51 (HOTFIX)

## Canvas — Copy/Paste size (grupo)
- [ ] Selección múltiple (2+ objetos) → Copy W/H/WxH funciona y habilita/inhabilita menú correctamente.
- [ ] Paste W: escala uniforme (mantiene aspecto), sin deformar.
- [ ] Paste H: escala uniforme (mantiene aspecto), sin deformar.
- [ ] Paste WxH: escala no uniforme (si corresponde) y mueve posiciones relativas (grupo real).
- [ ] Con objetos rotados: bbox visible coincide con lo copiado/pegado.

## Robustez (clipboard interno)
- [ ] Forzar clipboard inválido (None/bool/NaN/Inf/<=0) no crashea.
- [ ] Se registra **1 línea** de log al ignorar valor inválido.

## Rotación — HUD de ángulo + Shift fino
- [ ] Al rotar con rueda aparece overlay de ángulo.
- [ ] Shift rota en pasos más finos que sin Shift.

## Text Tool (placeholder)
- [ ] Preview multilínea (`\n`) renderiza todas las líneas.
- [ ] Interlineado cambia spacing.
- [ ] Modo placa muestra maqueta de margen (outer_margin_mm).
- [ ] Modo continuado: checkbox “Islas como grabado” activo (default ON).
- [ ] Botón “Texto” en toolbar muestra/oculta dock sin errores.

