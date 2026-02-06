# RCS_TEXT_TOOL — Diseño del módulo de texto (WIP → SmartText)
Fecha: 2026-01-26

Este documento define **cómo** se implementa el módulo de texto orientado a corte láser en RCS, con foco en:
- Edición como texto (metadatos versionados).
- Visualización/manipulación como vector en el canvas.
- Re-edición (abrir el objeto y reconstruir el “texto original”).

> Estado: se arranca con un **placeholder utilizable** (UI + metadatos + preview). El SmartText completo (meta+cache) queda como siguiente fase.

---

## 1) Decisiones confirmadas
- **Toolbar separada y movible** para accesos rápidos de texto (para no contaminar la toolbar principal).
- **Dock flotable** para la UI “pesada” del editor de texto.
- Falta obligatoria en UI: **interlineado** (`line_spacing`).
- Se omiten parámetros (no hacen falta ahora):
  - `seat_clearance_mm` (no necesario por potencia/kerf actual del láser).
  - `shadow_offset_mm` (no se implementa por ahora).
- Para el modo “continuado”: usar **Islas como grabado**.

---

## 2) Concepto central: Objeto inteligente
Separación estricta:
1) **Modelo editable (meta)**: texto, fuente, layout, dimensiones en mm, modo, etc.
2) **Representación vectorial (cache)**: `QPainterPath`/paths para dibujar, seleccionar y exportar.

Regla práctica:
- En el canvas siempre se manipula **vector**.
- Si el objeto conserva metadatos, se puede **re-editar**.

---

## 3) UI / UX (mínimo viable)
### 3.1 Toolbar “Texto” (movible)
Acciones rápidas:
- Activar/mostrar Dock del editor
- Crear texto (insertar objeto)
- Editar texto (si selección tiene meta)
- Aplanar a vector (descartar meta; irreversible)

### 3.2 Dock “Editor de Texto”
Controles:
- `QTextEdit` multilinea: `text`
- Fuente: `QFontComboBox` → `font.family`
- `Bold` / `Italic`
- Alineación: `left | center | right`
- **Interlineado**: `line_spacing` (float, ej 0.8–2.5)
- Caja física: `box_mm.w`, `box_mm.h`
- Modo (selector): `normal | plate | continuous`
  - `plate`: `outer_margin_mm`
  - `continuous`: `islands_as_engrave` (on) y (futuro) `island_area_min_mm2`

Preview:
- Debe renderizar multilinea + alineación + interlineado.
- Ideal: usar el mismo motor de path que el canvas (no un render paralelo distinto).

---

## 4) Metadatos (Schema v1)
**Obligatorio versionar** para que otra IA pueda migrar sin romper proyectos.

```json
{
  "type": "text_placeholder",
  "schema": 1,
  "text": "Ricardo\nAiden",
  "font": {"family": "Forte", "bold": false, "italic": false},
  "layout": {"align": "center", "line_spacing": 1.0},
  "box_mm": {"w": 100.0, "h": 40.0},

  "mode": "normal",

  "outer_margin_mm": 3.0,

  "islands_as_engrave": true,
  "island_area_min_mm2": 5.0
}
```

Notas:
- En `normal` se ignoran `outer_margin_mm` y flags de continuado.
- En `plate` se usa solo `outer_margin_mm`.
- En `continuous` se usa `islands_as_engrave` (y a futuro `island_area_min_mm2`).

---

## 5) Dos herramientas/modos clave para llaveros

### A) Modo CONTINUADO — “Islas como grabado”
**Qué es:** el texto sale como una **pieza cortable continua** (un cuerpo principal). Fragmentos sueltos (punto de i, acentos, etc.) no se cortan: se marcan para **grabado** en su posición.

**Por qué:** evita piezas minúsculas que se pierden/rompen y simplifica armado.

**Pipeline geométrico (propuesto):**
1. Generar path relleno del texto (`P_text`) ya escalado a `box_mm`.
2. Normalizar en coordenadas locales del objeto.
3. Detectar componentes desconectados (islas) y calcular área.
4. Definir **cuerpo principal** = componente de mayor área.
5. Clasificar:
   - cuerpo principal → rol **CUT**
   - islas → rol **ENGRAVE**
   - (futuro) aplicar umbral `island_area_min_mm2`.
6. Preview: overlay/estilo distinto para ENGRAVE.

**Salida conceptual:**
- `cut_paths` (cuerpo principal)
- `engrave_paths` (islas)

> Nota: en esta etapa el export real por layers puede no existir; pero el objeto debe preservar el rol en metadatos para que el export lo use después.

---

### B) Modo PLACA CONTORNO + LETRAS DENTRO
**Qué es:** reproduce el look de llavero multicapa:
1) **LETRAS**: el texto como pieza superior.
2) **PLACA**: contorno exterior que abraza el texto y genera la cavidad interior para alojar las letras.

Parámetro único (por ahora):
- `outer_margin_mm`: distancia entre borde de letras y perímetro exterior.

**Pipeline geométrico (producción):**
1. `P_letters` = relleno del texto.
2. `P_outer` = contorno exterior a distancia `outer_margin_mm`:
   - método recomendado: **union + offset** (Clipper o equivalente) con joins redondeados.
   - fallback inicial (si evitamos deps): aproximación raster + contorno (menos elegante pero usable).
3. Placa para láser:
   - corte exterior: `P_outer`
   - cortes interiores: `P_letters` (como huecos)

**Salida conceptual:**
- `plate_cut_paths`: `P_outer` + `P_letters` (interiores)
- `letters_cut_paths`: `P_letters`

**Arquitectura recomendada:**
- El generador de “placa que abraza” debería ser reutilizable (no solo para texto):
  - Herramienta futura: **Wrap Selection → Plate** (seleccionás cualquier grupo/forma y creás placa).
  - El modo `plate` del texto puede llamar internamente a ese generador.

---

## 6) Etapas de implementación (sin romper el repo)
- **T0 (placeholder)**: toolbar + dock + metadatos + preview. Sin crear objetos reales todavía.
- **T1 (inserción básica)**: generar `QPainterPath` por línea (`addText`) y crear objeto vectorial en canvas con meta adjunta.
- **T2 (SmartText real)**: meta + **frozen vector** para abrir proyectos aunque falte la fuente (fallback).
- **T3 (modos avanzados)**:
  - `continuous`: detectar islas y separar CUT/ENGRAVE.
  - `plate`: offset geométrico robusto (Clipper).

---

## 7) Archivos / puntos de integración (plan)
- UI:
  - `rcs/ui/text_tool_dock.py` (Dock + lógica de UI)
  - `rcs/ui/text_tool_toolbar.py` (Toolbar movible, acciones)
  - Registro en `rcs/ui/main_window.py`
- Modelo:
  - `rcs/core/text_model.py` (dataclass/schema/validación)
- Motor:
  - `rcs/svg/text_to_path.py` o `rcs/geom/text_path_engine.py`

> Nota: nombres exactos se ajustan a la estructura real del repo, pero el objetivo es separar UI / Modelo / Motor.


#### Algoritmo de contorno (cómo lo haríamos)
**Entrada:** path relleno del texto (`P_text`) ya a escala final (mm→scene units).

1) **Contorno exterior:** `P_outer = OFFSET(P_text, +outer_margin_mm)`.
2) **Placa:** en la versión simple (sin cavidad), la placa puede ser solo `P_outer`.
3) **Placa con cavidad (cuando toque):** `P_plate = P_outer − P_text` (boolean difference).
4) **Salida en objetos/capas:**
   - `Letras` = `P_text` (CUT)
   - `Placa` = `P_outer` (CUT) o `P_plate` (CUT)

**Motor geométrico:**
- Etapa inicial: `QPainterPathStroker` (rápido, suficiente para prototipo).
- Etapa robusta: `pyclipper` (offset + boolean fiables en tipografías complejas).

**Nota (decisión actual):** no se usa `seat_clearance_mm` ni `shadow_offset_mm`. Solo `outer_margin_mm`.
