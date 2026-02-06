# RCS_ROADMAP — Hoja de ruta (viva)

Versionado: MAJOR.MINOR.PATCH
- Los **bloques** suben **MINOR** (0.3 → 0.4 → 0.5...).
- Los **hotfix/docs** suben **PATCH** (0.3.9 → 0.3.9.1...).

> Nota: esta hoja de ruta es “viva”. Si se reprioriza, se deja asentado en el patch note.

## Bloque 0 — Esqueleto estable (v0.0.x)
- Repo, estructura, ventana, menú Archivo, logging
- Prueba: abre/cierra, crea proyecto vacío, guarda `.RCS`

## Bloque 1 — Modelo de proyecto + Save/Load (v0.1.x)
- `.RCS` funciona y reabre igual
- Prueba: crear→guardar→cerrar→abrir→verificar

## Bloque 2 — Biblioteca + thumbnails + insertar SVG (v0.2.x)
- Árbol de carpetas + mosaico thumbnails + inserción al lienzo
- Prueba: insertar 10 assets, guardar/abrir

## Bloque 3 — Manipulación + cámara del lienzo (v0.3.x)
Estado: **en cierre**.

Hecho (referencias en `docs/patches/`):
- 3F: **Fit to Content** (0.3.8)
- 3G: **Zoom sync + clamp** (0.3.8.2)
- 3H: **Scrollbars OFF por defecto + pan/zoom consistente** (0.3.9)

Pendiente (3I):
- **Frame selection / frame all / reset view** (encuadre consistente)
- Pruebas: no romper inserción ni dejar items fuera del viewport

## Bloque 4 — Texto como objeto (v0.4.x)
Objetivo: poder armar llaveros/nombres sin depender de un editor externo.

Referencia: ver `docs/RCS_TEXT_TOOL.md` (diseño del módulo de texto, modos y etapas de implementación).

### 4A — TextObject (modelo + persistencia)
- Nuevo tipo de objeto: `type="text"` con `text_payload`
- Render en lienzo + transform (mover/rotar/escalar) igual que SVG
- Prueba: guardar/abrir preserva texto y transform

### 4B — Barra de texto (WYSIWYG)
- Toolbar **movible** + Dock: fuente, tamaño, bold/italic, alineación básica, **interlineado**
- **Preview mientras editás** (sin “congelar” UI)
- Prueba: editar texto con live preview sin cuelgues

### 4C — Editable vs convertido
- Estado: **editable** (distinción visual, ej. azul) vs **convertido a curvas**
- Acción: **Convertir a curvas** → genera objetos SVG/paths y guarda metadatos del texto original
- Prueba: convertir no cambia tamaño/posición visual

### 4D — Diacríticos (Muñeca / Alí)
- Problema: tildes/virgulillas/puntos son “islas” y pueden quedar frágiles al cortar
- Solución: política explícita (ver Modo `continuous` en `docs/RCS_TEXT_TOOL.md`):
  - permitir separar diacríticos/islas en capa/objeto (p.ej. **grabado**) → “Islas como grabado”
  - o unirlos (si se implementa boolean/bridge más adelante)
- Prueba: “Muñeca”, “Alí”, “Pingüino” sin piezas colgantes si se elige modo grabado

### 4E — Herramienta “Texto → Placa/Contorno” (llavero)
- Entrada: texto (preferible editable) → curvas
- Salida: grupo con:
  - `LETTERS` (letras)
  - `PLATE` (placa/contorno que abraza)
- Parámetro mínimo (fase inicial):
  - `outer_margin_mm` (distancia entre letras y perímetro exterior)
- Nota de arquitectura:
  - el generador de “placa que abraza” debería ser **reutilizable** (futuro: *Wrap Selection → Plate*), no exclusivo del texto.
- El agujero/oreja del llavero se agrega como objeto aparte (círculo/placa)

## Bloque 5 — Export SVG contornos-only (v0.5.x)
- Export en mm reales, `fill="none"`, transforms aplicados, flatten final
- Rechazo claro para SVGs con mask/clip/filter (pedir “convertir a paths”)
- Si hay texto editable: opción “auto-bake al exportar”

## Bloque 6 — Componentes geométricos (v0.6.x)
- Ventana para crear rect/tri/circle/oval/polygon, guardar a biblioteca

## Bloque 7 — Quick tray + swap (v0.7.x)
- Pinned externos/internos + swap preserva transform
