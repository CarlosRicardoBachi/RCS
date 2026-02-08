# CHANGELOG — RusticCreadorSvg (RCS)

## 0.3.10.2.69 — 2026-02-05

- HOTFIX: GMPR base SVG (preview): render a escala real del lienzo (mm), evitando el “preview 240px” que desalineaba rasters.
- HOTFIX: GMPR base SVG: selección exclusiva (se puede clickear para inspección, pero no queda seleccionada junto a otros objetos).

## 0.3.10.2.68 — 2026-02-04

- HOTFIX: GMPR import: canvas_mm se infiere (bundle o SVG embebido) para alinear (x,y) en mm.
- HOTFIX: GMPR import: heurística sx/sy (mm/px vs factor relativo) para evitar escalas absurdas.

## 0.3.10.2.67 — 2026-02-04

- HOTFIX: `MainWindow.set_project()` restaurado (wrapper a `_refresh_project()`), usado por Import GMPR.
- HOTFIX: `MainWindow._refresh_title()` agregado como alias de compatibilidad (evita crash en paths legacy).


## 0.3.10.2.66 — 2026-02-04

- HOTFIX: GMPR: `Archivo → Importar GMPR…` usa `load_gmpr_json()` + `gmpr_to_project(bundle, gmpr_path=...)` (sin `file_path`).
- HOTFIX: GMPR: `gmpr_to_project()` crea el Transform del raster con `_gmpr_raster_transform_to_rcs_transform()` (evita crash por `tr` no definido).
- HOTFIX: GMPR: `save_gmpr_project()` retorna `Path` como espera la UI (evita crash al guardar).
- Guardado: actualización de transforms pasa por `_update_gmpr_raster_transform_dict()` (sx/sy mm/px + `s` coherentes).


## 0.3.10.2.65 — 2026-02-02

- HOTFIX: GMPR: conservar biblioteca de SVG (components_root) al importar GMPR.
- HOTFIX: GMPR: escala de rasters (sx/sy mm/px + s) corregida en carga y guardado.
- UI: menú Archivo ahora incluye "Importar GMPR…"; "Importar SVG…" (Ctrl+O) inserta un SVG externo.


## 0.3.10.2.64 — 2026-02-02

- Core: nuevo módulo `gmpr_io` para abrir/guardar `.GMPR` (bundle) sin reestructurar JSON.
- UI: `Archivo > Abrir/Guardar` ahora opera exclusivamente sobre `.GMPR`.
- Canvas: preview de SVG base embebido como fondo no seleccionable.
- Canvas: restauración de rasters (PNGs embebidos) como objetos `type=raster`, con transforms y snap.

## 0.3.10.2.63 — 2026-01-31

- UI: Move SNAP para drag de raster (toggle **S** + overlay “SNAP ON”).
- Grid-snap 1.0 mm (Shift → 0.1 mm) y override temporal con Alt (snap OFF).
- Object-snap (bordes/centros) con guías amarillas cosméticas; prioridad object > grid.
- Riesgo controlado: snap deshabilitado con selección múltiple de raster.

## 0.3.10.2.62 (2026-01-29)
- `UX(TOOLBOX)` — **Space = PAN temporal**: mantiene presionado para panear (ScrollHandDrag) y al soltar vuelve al tool anterior, sin cambiar tu selección.
- `UX(CURSOR)` — Cursor dedicado por tool: PAN (mano), ROTATE (flecha curva), SCALE (tamaño). Se aplica tanto al view como al viewport (evita “cursor pegado”).

## 0.3.10.2.61 (2026-01-29)
- HOTFIX: restaurado **CanvasView** a snapshot estable (0.3.10.2.56) para recuperar API completa (set_project, insert_svg_from_library, _rerender_svg_previews) y el lienzo.
- Eliminados fallbacks/avisos de “API incompleta” introducidos en 0.3.10.2.60.
- Nota: el experimento de snap/preview iniciado en 0.57–0.60 se pausa hasta reintroducirlo de forma incremental (hotfix dedicado).


## 0.3.10.2.60
- Hotfix: refuerzo de compatibilidad de CanvasView. Si faltan métodos críticos (set_project / _rerender_svg_previews) se instalan fallbacks y se evita el crash.
- MainWindow: llamada a set_project ahora es segura (fallback a asignar _project + rebuild si existe).
- CanvasView: el chequeo de API intenta autoreparar antes de reportar incompleto.

## 0.3.10.2.59 - Hotfix (regresión CanvasView API)
- FIX: restaura compatibilidad de API esperada por la UI (CanvasView._rerender_svg_previews / set_project) y evita crash al iniciar cuando el archivo quedó desfasado.
- SAFE: set_preview_style ya no rompe el arranque si falta el rerender (log de 1 línea + continúa).

## 0.3.10.2.58
- `HOTFIX(UI)` — Guard + compat para `_rerender_svg_previews`: evita crash al iniciar cuando se aplica `set_preview_style()` en builds donde ese método no existe.
- `UI(SNAP)` — Sin cambios funcionales vs 0.3.10.2.57 (se mantiene Snap grilla + guías).

## 0.3.10.2.57
- `UI(SNAP)` — Snap ON/OFF (tecla **S**): grilla en mm + guías de alineación (bordes/centros) con líneas amarillas.
- `UI(SNAP)` — Default step: **1.0 mm**. Con **Shift**: step fino **0.1 mm**. Con **Alt** durante drag: snap temporal OFF.

## 0.3.10.2.56
- `UI(ZOOM)` — Zoom por rueda más suave (≈40% menos agresivo). Con Shift: ajuste aún más fino (≈60% menos agresivo).

## 0.3.10.2.55
- `UI(ROTATE)` — Gizmo de rotación (handle arriba del bbox): click+drag rota la selección completa alrededor del centro del bbox.
- `UI(ROTATE)` — Snap por defecto a 5° (más CNC-friendly). Con Shift: snap fino a 1°.
- `UI(ZOOM)` — Cursor tipo “lupita” (ZoomInCursor) cuando Qt lo soporta; fallback a crosshair.

## 0.3.10.2.54
- `UI(SCALE)` — Handles de escala en 8 puntos (esquinas + medios). Se muestran solo con ToolMode.SCALE (evita ruido visual).

## 0.3.10.2.53
- `CORE(Canvas Transform)` — Consolidación del motor de transformaciones (move/rotate/scale): helpers únicos para sync modelo↔scene y escalado de grupo alrededor de pivot.
- `UI` — Sin cambios visibles esperados; refactor interno para reducir drift y duplicación de lógica.

## 0.3.10.2.52
- HOTFIX: HUD overlays no vuelven a romper el render (init + guards).
- Overlay restaurado y ampliado: Hoja/Lienzo/Zoom + tamaño de selección + ángulo de rotación.
- ToolMode.SCALE: handles en 4 esquinas para estirar/agrandar con drag (Shift mantiene aspecto).

## 0.3.10.2.51
- Canvas: copiar/pegar tamaño blindado (valida bool/None/NaN/Inf/<=0) + log 1 línea si se ignora.
- Canvas: pegar tamaño en multi-selección escala como grupo (bbox unido + pivot centro), incluyendo posiciones relativas.
- Canvas: HUD de rotación muestra ángulo (igual estilo que medidas); Shift ajusta rotación fina (0.5° por notch).
- Text Tool (placeholder): preview multilínea real + interlineado + modos Normal/Placa/Continuado (metadatos).
## 0.3.10.2.49
- HOTFIX: overlays de medidas: import de QDateTime (evita NameError en drawForeground).
- HOTFIX: clipboard de tamaño (_copied_size_mm) nunca None; evita crash en menú contextual (y el parpadeo).

## 0.3.10.2.48
- UX(Canvas): restaurados overlays de medidas en mm:
  - HUD de lienzo (W x H) siempre visible.
  - HUD temporal de objeto (W x H) al escalar y con tecla V (3s).
- UX(Canvas): menú contextual en objeto — Copiar/Pegar medidas (alto/ancho/ancho+alto).
- UI: botón “Medida objeto” en toolbar (ancho/alto + checkbox para mantener relación de aspecto).

## 0.3.10.2.44
- CORE(Render/Geom): cableado runtime de `normalize_svg_viewport()` en canvas previews (QtSvg) para usar `viewBox` como "truth" cuando está disponible.
- CORE(Render/Geom): thumbs + canvas ahora loggean (una vez por archivo) units/ppi/doc/viewbox para cazar divergencias reales sin spameo.

## 0.3.10.2.43
- UX(Canvas): cota de dimensiones del lienzo anclada al rectángulo del canvas (referencia real, no HUD fijo).
- UX(Canvas): al escalar un objeto, muestra un label temporal (amarillo) con su tamaño real en mm (W x H) por ~2s.

## 0.3.10.2.41
- HOTFIX: Biblioteca 🔄 (faltaba handler _on_refresh_clicked) + filtro recarga thumbs (force reload)

## 0.3.10.2.40
- CORE(Render/Geom): Phase 2a — contrato `normalize_svg_viewport()` + reporte más rico en harness.
- CORE(Render/Geom): modo `--modes thumbs` en `rcs.svg.render_debug` para detectar divergencias canvas vs thumbs.
- UI(Biblioteca): botón 🔄 Refrescar (re-escaneo de filesystem; mantiene carpeta/selección best-effort).

## 0.3.10.2.39
- CORE: Render/Geom — Phase 1d: BBox alignment (svgelements → viewport QtSvg) para evitar FAILs sistemáticos en el harness.

## 0.3.10.2.38
- `CORE` — Render/Geom Phase 1c (harness): regresiones bbox + ranking.
  - El harness `python -m rcs.svg.render_debug` ahora genera `_bbox_failures.json` (ranking de casos no-PASS con comando `repro`).
  - Soporta baseline compare con `--bbox-baseline` y genera `_bbox_regressions.json`.
  - Nuevo helper `rcs.geom.bbox_report` para ranking y comparación baseline.

## 0.3.10.2.37
- `CORE` — Render/Geom Phase 1b (harness):
  - Comparación automática de bbox: QtSvg (bbox alfa del render crudo) vs geometría (`svgelements` bbox).
  - Nuevos umbrales configurables: `--bbox-tol` (PASS) y `--bbox-warn` (WARN) + env `RCS_DBG_BBOX_TOL` / `RCS_DBG_BBOX_WARN`.
  - Genera reporte JSON compacto: `_bbox_report.json` (configurable con `--bbox-report`) con stats PASS/WARN/FAIL/INVISIBLE/NO_GEOM.

## 0.3.10.2.36
- `CORE` — Render/Geom Phase 1a:
  - Adapter opcional `svgelements` para calcular bbox de documento (sin tocar runtime de la app).
  - El harness `python -m rcs.svg.render_debug` ahora anota `qtsvg_viewbox` + `svgelements.bbox` (cuando está disponible) para comparar y detectar divergencias.

## 0.3.10.2.35
- `CORE` — CanvasPrefs: resets (página por defecto, vista de inicio, rango de zoom) + scroll OFF/AUTO/ON + fix en actualización de settings (aplicar prefs sin TypeError).

## 0.3.10.2.34
- `HOTFIX` — Fix crash al iniciar por contrato de retorno de `load_project_settings()` (ya no devuelve `(settings, path)`).
- `CORE` — CanvasPrefs: tras cambiar defaults (F10/scroll H/V) se sincroniza ENV en la sesión para que **Archivo→Nuevo** herede lo nuevo sin reiniciar.
- `UX` — Feedback en status al togglear scroll H/V.

## 0.3.10.2.33
- Preferencias persistentes del lienzo en `rcs_settings.json`:
  - F10: tamaño de página/canvas por defecto (y se aplica al proyecto actual).
  - F11: guardar vista de inicio (centro + zoom) para próximos arranques.
  - F12: presets de rango de zoom (x0.5/x1/x2/x4 + personalizado).
  - Scroll horizontal/vertical independientes (on/off).

## 0.3.10.2.32
- `HOTFIX` — Toolbar flotante: corrige ToolMode inválido (MOVE→SELECT/PICK) y selección inicial por settings. (2026-01-23)

## 0.3.10.2.31
- HOTFIX — Fix crash al iniciar: toolbar style estaba usando atributos inexistentes (`iconSize`, `toolButtonStyle`) sobre `Qt.ToolButtonStyle`.
- HOTFIX — Nuevo helper de tamaño de iconos: env `RCS_TOOLBAR_ICON_SIZE` (ej: `20` o `20x20`).


## 0.3.10.2.30
- CORE — 2 toolbars flotantes: herramientas y acciones (duplicar/ajustar/lienzo automático)
- CORE — Lienzo automático: ajusta tamaño del lienzo al contenido (sin márgenes)



## 0.3.10.2.29
- CORE — Preview SVG: escala global de grosor para niveles (x0.5 por defecto) para un rango más fino; env: `RCS_CANVAS_PREVIEW_THICK_SCALE`.

## 0.3.10.2.28
- `CORE` — Preview SVG: stroke subpixel + DPR adaptivo por buckets (evita que el trazo/halo engorde al escalar).
- `CORE` — Outline más estable al escalar: DPR adaptivo antes del redondeo (menos saltos visibles).

## 0.3.10.2.27
- `CORE` — Stroke fijo en preview SVG al escalar (compensación por escala + re-render puntual al cambiar escala).
- `CORE` — Acción "Restaurar tamaño (1:1)" (menú Objeto + panel Objetos + menú contextual).

## 0.3.10.2.26
- Group/Ungroup: selección por grupo (auto-expande) + acciones en canvas/lista/menú.
- Z-order por grupo: subir/bajar un nivel y front/back ahora mueven el grupo como bloque (seleccionando cualquier miembro).
- Clipboard: pega con `group_id` remapeado para evitar enlazar con el original.

## 0.3.10.2.25

- `CORE` — **Panel Objetos (capas)**: lista de objetos ordenada por Z (arriba = frente) para operar el apilado desde UI.
  - Acciones: Traer al frente / Enviar al fondo / Subir un nivel / Bajar un nivel.
  - Selección bidireccional: seleccionar en la lista selecciona en canvas, y viceversa.
- `UI` — Menú **Ver → Paneles → Objetos** para mostrar/ocultar el panel.
- `UX` — Menú contextual con **click derecho en el canvas**: Traer/Enviar/Subir/Bajar (sin ir al menú superior).

Notas:
- No toca render/thumbnails ni el sistema de estilos.
- No cambia el schema `.RCS` (usa `z` existente).

## 0.3.10.2.24

- `CORE` — **Z-Order mínimo (capas)**: nuevas acciones para manipular el apilado sin pelearte con objetos superpuestos.
  - Traer al frente / Enviar al fondo
  - Subir un nivel / Bajar un nivel (swap mínimo, sin reordenar todo)
- `UI` — Menú **Objeto** + atajos por defecto: `Ctrl+]`, `Ctrl+[`, `Ctrl+Shift+]`, `Ctrl+Shift+[`.
- `UX` — Feedback en statusbar: mensajes tipo `Z: 12 → 13` o resúmenes por selección múltiple.
- `Persistencia` — Se guarda/restaura `z` por item (y al cargar proyectos viejos sin `z` se asigna por orden de carga).

Notas:
- No toca render/thumbnails ni el sistema de estilos.
- No cambia el schema `.RCS` (solo aprovecha el campo `z` ya existente).

## 0.3.10.2.5

- `DOCS` — Se formaliza el roadmap **Render/Geometría (Skia + svgelements)** en fases 0..4 con entregables pequeños.
- `DOCS` — `docs/RCS_ROADMAP_RENDER_GEOM.md` con DoD + checklist por ZIP.
- `DOCS` — `docs/RCS_STATUS.md`: prioridad actual = Render/Geom; Bloque Texto pasa a backlog explícito.
- `DOCS` — `docs/OBSTACLES.md`: nuevos OBS para render invisible, divergencia canvas/thumbs e invalidación de cache.
- `DOCS` — `docs/patches/index.md`: entrada 0.3.10.2.5 + ruta de patch note/checklist.
- `AI` — `ai/context.json` actualizado (foco: Render/Geom).

## 0.3.10.2.2 (HOTFIX) — Qt6/PySide6: alfa estable al insertar SVG

- Fix: compat PySide6/Qt6: reemplaza uso directo de `QImage.alphaChannel()` / `setAlphaChannel()` por extracción y aplicación segura de máscara alfa (Alpha8).
  - Evita el error al insertar SVG: `'PySide6.QtGui.QImage' object has no attribute 'alphaChannel'`.
- Fix: hit-fill interno (selección por click dentro del contorno) ahora respeta `bytesPerLine()` tanto en Alpha8 como en ARGB32 para no leer memoria corrupta cuando hay alineación.

Notas:
- No cambia el schema `.RCS`.

## 0.3.10.2.1 (HOTFIX) — Arranque: fix crash en resizeEvent

- Fix: corrige crash al iniciar cuando el cálculo del **zoom mínimo adaptativo** intenta usar `_sheet_rect` como QRectF pero en algunos flujos queda como **callable** (función/método). Ahora se normaliza invocando si corresponde.
- Docs: se agrega la nota de parche faltante de **0.3.10.2** para que el índice `docs/patches/index.md` no quede apuntando a un archivo inexistente.

Notas:
- No cambia el schema `.RCS`.
- Parche seguro: solo afecta el cálculo de límites de zoom en el arranque/redimensionado.

## 0.3.10.2 (HOTFIX) — UX: zoom mínimo adaptativo + selección interior + UI persistente

- Canvas: **zoom mínimo adaptativo** (según tamaño de hoja vs viewport). Evita zoom-out extremo.
- Canvas: **selección “fácil”** en figuras cerradas: click dentro del contorno selecciona el objeto (hit-test por relleno alfa casi-cero).
- UI: persistencia de **geometría/layout** (dock/toolbar) entre sesiones.
- Biblioteca: panel con **splitter** (árbol vs thumbnails) ajustable en altura + persistente.

Env:
- `RCS_CANVAS_HIT_FILL=0/1` (default 1) para desactivar/activar el relleno alfa interno.

## 0.3.10.1 (HOTFIX) — Preview nítido + grilla limitada

- Canvas: preview SVG rasterizado ahora usa devicePixelRatio (DPR) → líneas más nítidas y menos pixelación al zoom.
- Canvas: `Preview Style` (stroke/halo) ahora se percibe correctamente (se renderiza en la resolución real, sin ‘achicarse’ por downscale).
- Canvas: grilla limitada a la hoja/escena (evita la ‘cuadricula casi infinita’ al zoom-out).
- Opt-in: viewport OpenGL por env `RCS_CANVAS_OPENGL=1` (puede depender del driver).
- Nuevos env: `RCS_CANVAS_PREVIEW_DPR` (1..4) y `RCS_CANVAS_PREVIEW_PX` (96..1024) para afinar calidad/perf.

## 0.3.10 — Bloque 3I: Encuadre de vista (2026-01-17)

- Canvas: acciones de encuadre (selección/todo/hoja) basadas en `sceneBoundingRect()` + `fitInView()`.
- MainWindow: atajos F / Shift+F / Ctrl+Shift+0 en menú Ver.

## 0.3.9.1 — DOCS (2026-01-17)

### Changed
- Roadmap/Status/Spec alineados al estado real 0.3.9 y al plan inmediato: Bloque 4 (Texto).
- Obstacle nuevo: diacríticos colgantes al vectorizar texto (OBS-007).

### Notes
- No cambia el schema `.RCS`.
- No se eliminó ninguna funcionalidad probada.


## 0.3.9 (2026-01-17)
- Lienzo: scrollbars OFF por defecto (evita ruido visual y micro-saltos por cambios del viewport); override por env `RCS_CANVAS_SCROLLBARS`.
- UX cámara: pan (herramienta y MMB) y zoom siguen funcionando igual con scrollbars ocultos.

## 0.3.8.2 — HOTFIX (2026-01-17)

### Fixed
- **Cámara / Zoom**: sincronización coherente del zoom interno con el `transform()` real luego de `fitInView()`, evitando saltos bruscos al primer gesto de zoom.
- **Clamp dinámico**: si el zoom actual quedó fuera del rango normal (0.1..8.0) por un ajuste automático, el límite se “pega” al zoom actual para impedir ir a escalas ridículas **sin** forzar un snap inmediato.

### Notes
- No cambia el schema `.RCS`.
- No se eliminó ninguna funcionalidad probada.

## 0.3.8.1 — DOCS (2026-01-17)

### Added
- **Context Pack** dentro del repo: `docs/START_HERE.md`, `docs/RCS_SPEC.md`, `docs/RCS_MAP.md`, `docs/RCS_ROADMAP.md`, `docs/RCS_STATUS.md`.
- **Constitución del proyecto**: `docs/RCS_CONSTITUTION.md` (reglas duras + política de obsolescencia de obstáculos superados).
- **Registro estructurado de parches**: `docs/patches/` (índice + notas por versión).
- **Registro de obstáculos**: `docs/OBSTACLES.md` (OPEN/WATCH/CLOSED/OBSOLETE).
- **Paquete de orientación para IA**: `ai/README_AI.md`, `ai/context.json`, `readmeIA.prompt`.

### Changed
- Bump de versión a **0.3.8.1** (parche documental).

### Notes
- No cambia el schema `.RCS`.
- No se eliminó ninguna funcionalidad probada.

## 0.3.8 — WIP (2026-01-16)

### Added
- **Ajustar al objeto (Fit to Content)**: acción (toolbar + menú Editar) que recorta márgenes internos del SVG para que el marco se ajuste a la figura.
- Persistencia por objeto: nuevo flag opcional `svg_fit_content` en `.RCS` para que el recorte se reaplique al re-render (cambio de tema) y al reabrir.

### Changed
- Render/re-render de previews: si el objeto tiene `svg_fit_content=true`, se recorta el pixmap antes de aplicar transform/pivot.

### Notes
- Cambio compatible hacia atrás: proyectos viejos cargan con `svg_fit_content=false`.

## 0.3.7 — HOTFIX (2026-01-16)

### Fixed
- **Inserción desde Biblioteca**: `insert_svg_from_library()` volvió a ser compatible con el contrato del `LibraryPanel` (recibe *ruta relativa* dentro de `components_root`). Ahora acepta **ruta relativa o absoluta**, resuelve correctamente el `abs_path`, y guarda `source` normalizado (con `/`) en el `.RCS`.
- **Root de componentes consistente**: el `LibraryPanel` ahora usa `Project.components_root_path()` (cuando está disponible) para que el árbol/mosaico y la inserción resuelvan la biblioteca desde el mismo lugar (especialmente cuando el `.RCS` está en otra carpeta).

### Notes
- No se eliminó ninguna funcionalidad probada.
- No cambia el schema `.RCS`.
