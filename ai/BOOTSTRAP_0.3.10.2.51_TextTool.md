Eres un asistente técnico trabajando con el proyecto **RCS** (Python + PySide6/Qt).
Tu tarea es continuar el desarrollo desde una sesión nueva sin perder contexto.

# 0) Contexto (estado del proyecto)
- RCS es un editor con canvas orientado a geometrías/vectores para corte láser.
- Se corrigieron fallos recientes en `rcs/ui/canvas_view.py`:
  - `QFontMetrics` faltante (overlay de medidas crasheaba).
  - `save()` sin `restore()` al explotar (warning de estados guardados).
  - Copiar tamaño tratando `(w,h)` como QRect (AttributeError).
  - Warning Shiboken: bool→C++ por encadenado `QTransform().scale(...)` (evitar encadenar).
- El flujo copiar/pegar tamaño ya funciona en casos simples.

# 1) Objetivo inmediato: Hotfix 0.3.10.2.51
Implementar dos bloques:

A) Blindaje de “Copiar/Pegar tamaño”:
- Validación dura del clipboard: rechazar bool/None/<=0/NaN/Inf.
- Rotados: medir tamaño visible con `sceneBoundingRect()`.
- Selección múltiple: pegar tamaño como escalado de grupo real (bbox unido + pivot centro + reubicación relativa).
- Log de 1 línea cuando se ignora por inválido.

B) Herramienta Texto (placeholder):
- `QToolBar("Texto")` movible (acciones rápidas) + Dock flotable (UI pesada).
- Interlineado (`line_spacing`).
- Modos: normal / placa contorno / continuado.
- Decisiones: NO `seat_clearance_mm`, NO `shadow_offset_mm`.
- Continuado: **Islas como grabado** (`islands_as_engrave=true`).
- Placa: `outer_margin_mm`.
- Metadatos versionados (schema 1) generados por la UI.
- Preview multilínea con alineación e interlineado (sin offsets/booleanos complejos aún).

# 2) Restricciones
- No dependencias geométricas pesadas aún.
- No SmartText completo aún; solo placeholder + metadatos.
- No romper funcionalidades existentes; cambios incrementales.
- Entregar ZIP con SOLO archivos modificados.
- Actualizar docs: `docs/patches/index.md` y `docs/CHANGELOG.md`.

# 3) Qué buscar en el repo (para ubicarse rápido)
- `rcs/ui/canvas_view.py`:
  - `_draw_measure_overlays`
  - `_copy_selected_size_to_clipboard`
  - función de aplicar tamaño (pegar) y uso de `sceneBoundingRect()`
  - uso de `setTransform(QTransform, True)` sin encadenados

- `rcs/ui/main_window.py`:
  - registro de toolbars/docks
  - menú Ver → Paneles (si existe)

- `rcs/ui/`:
  - crear/ubicar dock de texto: `text_tool_dock.py` (o equivalente)

# 4) Metadatos del texto (schema v1 obligatorio)
{
  "type": "text_placeholder",
  "schema": 1,
  "text": "...",
  "font": {"family":"...", "bold":false, "italic":false},
  "layout": {"align":"left|center|right", "line_spacing":1.0},
  "box_mm": {"w":100.0, "h":40.0},
  "mode": "normal|plate|continuous",
  "outer_margin_mm": 3.0,
  "islands_as_engrave": true,
  "island_area_min_mm2": 5.0
}

# 5) Checklist de pruebas manuales (definición de listo)
- Tamaño:
  - 1 objeto sin rotación
  - 1 objeto rotado
  - 2+ objetos (selección múltiple)
  - clipboard inválido → no aplica + log 1 línea
- Texto:
  - toolbar movible + dock flotable
  - multiline + interlineado en preview
  - cambios de modo actualizan metadatos

# 6) Entregables
- ZIP patch con solo archivos modificados.
- Docs actualizadas.
- Nota breve de cambios + checklist.
