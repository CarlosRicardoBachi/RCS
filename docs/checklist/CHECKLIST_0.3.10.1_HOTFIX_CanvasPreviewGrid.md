# CHECKLIST — 0.3.10.1 (HOTFIX) Canvas Preview/Grid

## Precondiciones
- Estás en **0.3.10** (o 0.3.10 + tus cambios locales) y aplicás este ZIP arriba.

## Smoke test (5 min)
- [ ] Abrir la app.
- [ ] Abrir un proyecto con varios SVG (o insertar 3–5 desde biblioteca).
- [ ] Zoom in/out fuerte (rueda) y pan (Space+drag o MMB según configuración).

## Validaciones específicas
### 1) Nitidez de preview
- [ ] A zoom 1.0: bordes se ven más definidos que antes.
- [ ] A zoom 3–4: el preview aguanta mejor sin “escalera” agresiva.

### 2) Menú Ver → Preview Style
- [ ] Cambiar Stroke thickness de 1→4: debe notarse.
- [ ] Cambiar Outline/halo de 0→3: debe notarse.
- [ ] Volver a 0: debe desaparecer.

### 3) Grilla limitada
- [ ] Hacer zoom out extremo: la grilla **no** debe seguir dibujándose por fuera de la hoja/escena.

### 4) OpenGL (opcional)
- [ ] Probar con `RCS_CANVAS_OPENGL=1`.
- [ ] Ver que no crashea. Si hay glitches, volver a default (sin env var).

## Regressions a vigilar
- [ ] Insertar desde biblioteca sigue funcionando.
- [ ] Fit to Content sigue recortando correctamente.
- [ ] Encuadre de vista (F / Shift+F / Ctrl+Shift+0) sigue ok.
