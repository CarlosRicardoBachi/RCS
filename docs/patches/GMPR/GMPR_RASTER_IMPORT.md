
# GMPR Import – Raster embebido (Hotfix)

## Qué cambia
- Se implementa restauración real de objetos custom desde `objects[]` del GMPR.
- Raster embebido (`custom_kind: raster`) se reconstruye desde `png_base64`.
- Transform aplicado en espacio SVG (user units post-viewBox).
- Compatibilidad legacy con escala uniforme (`s` / `scale`).

## Fuente de verdad
- `objects[]` define orden y contenido.
- No se infiere raster desde SVG.
- No se convierte a mm en import.

## Resultado esperado
- Abrir un GMPR reproduce el proyecto igual que Rustic Creator:
  SVG + raster con tamaño, posición, escala y rotación correctos.

## Archivos afectados
- app/ui/main_window_mixins_project_io.py
