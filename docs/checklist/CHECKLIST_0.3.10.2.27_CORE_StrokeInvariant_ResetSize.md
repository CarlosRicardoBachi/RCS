# Checklist — 0.3.10.2.27 — CORE — Stroke fijo preview + Restaurar tamaño

- [x] Bump de versión: `rcs/core/version.py` -> `0.3.10.2.27`
- [x] Fix de stroke/halo en previews SVG: compensación por escala del objeto
- [x] Re-render puntual al escalar (sin refresco global)
- [x] Re-render general (zoom) ahora preserva `svg_fit_content`
- [x] Acción "Restaurar tamaño (1:1)" en:
  - [x] Menú `Objeto`
  - [x] Menú contextual del canvas
  - [x] Panel `Objetos` (botón + menú contextual)
- [x] Documentación:
  - [x] `docs/patches/index.md`
  - [x] `docs/CHANGELOG.md`
  - [x] Nota de parche en `docs/patches/0.3/0.3.10.2.27/`
- [x] `ai/context.json` actualizado

## Smoke tests
- Insertar SVG, escalar con modo `SCALE` (rueda): el grosor de líneas se mantiene visualmente constante.
- Click en `1:1` o menú "Restaurar tamaño": vuelve a escala 1.0 sin desplazar el centro.
