# RCS_SPEC — Especificación (MVP + límites)

## Qué es RCS
Editor de escritorio (PySide6) para **ensamblar** objetos SVG (y texto) sobre un lienzo en mm.

## Objetivos (sí)
- Insertar SVG desde biblioteca (carpetas).
- Manipular como objetos: seleccionar, mover, rotar, escalar (ratio lock), duplicar/borrar, z-order, snap a grilla opcional.
- Insertar texto como objeto (próximo Bloque 4).
- Crear componentes geométricos (futuro Bloque 6).
- Exportar SVG final con regla **contornos-only** (Bloque 5, a endurecer).
- Guardar/abrir proyectos `.RCS` (JSON).

## No-objetivos (no convertirlo en Inkscape)
- Sin edición por nodos / pluma Bezier.
- Sin booleanos automáticos obligatorios.
- Sin colorimetría, degradados, filtros, rellenos “de diseño”.
- Sin nesting/plancha avanzada (eso lo hace Rustic Creador post).

## Regla “solo contornos”
En import y export se fuerza (o se validará de forma estricta):
- `fill="none"`
- `stroke` normalizado (p.ej. `stroke="black"`)
- SVGs complejos (mask/clip/filter) se rechazan con mensaje claro: “Convertir a paths antes de usar”.

## Formato `.RCS` (JSON legible)
Campos esperados (schema_version=1):
- `schema_version`
- `canvas_mm`: `{ "w": <float>, "h": <float> }`
- `grid`: `{ "size_mm": <float>, "snap_on": <bool> }`
- `components_root`: ruta (string)
- `objects[]`:
  - `id`: string
  - `type`: `"svg" | "text"`
  - `source`: ruta relativa dentro de `components_root` (para SVG)
  - `transform`: `{ x, y, scale_x, scale_y, rotation_deg, flip_h, flip_v }`
  - `z`: int
  - `text_payload`: (solo si type=text)
  - opcional: `svg_fit_content`: bool (recorte al contenido)

### Texto como objeto (SmartText) — plan (v0.3.x → v0.4.x)

**Idea clave:** en el lienzo se ve como **vector**, pero se guarda un **modelo editable** (metadatos) para poder reabrirlo y cambiar el texto.

- En v0.3.x se maquetará como `type="text_placeholder"` (o `type="text"` con `payload.schema=1`) para permitir iterar UI/flujo.
- En v0.4.x se formaliza como `type="text"` estable.

**Payload sugerido (schema=1):**
- `schema`: `1`
- `text`: string (soporta multi-línea)
- `font`: `{ family, bold, italic }`
- `layout`: `{ align: left|center|right, line_spacing: float }`  ← incluye **interlineado**
- `box_mm`: `{ w, h }`  ← caja objetivo en mm
- `mode`: `normal | continous | plate`
  - `continous`: “letra continuada” / puenteado para corte; **islas/diacríticos como grabado**
  - `plate`: “contorno + letras dentro” (placa que abraza)
- `plate`: `{ outer_margin_mm: float }` (solo modo plate)
- `frozen_vector`: opcional (paths “horneados” para abrir igual aunque falte la fuente)

**Documento de referencia (detalles y etapas):** ver `docs/RCS_TEXT_TOOL.md`.

## Biblioteca de componentes (carpetas)
Estructura recomendada:
- `componentes/externos/`
- `componentes/internos/`
- `componentes/figuras/`
- `componentes/geometricas/`
- `componentes/emojis/` (solo SVG simplificado)
- `componentes/logos/` (opcional)

