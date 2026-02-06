# CHECKLIST — 0.3.10.2.6 (CORE) Render harness

## Smoke
- [ ] `python -m rcs.tools.render_debug --help` funciona.
- [ ] Renderiza 1 SVG válido y genera `_summary.json`.

## Regresión (mínima)
- [ ] Renderiza 10 SVGs (carpeta fixtures o biblioteca real) sin tirar excepción.
- [ ] Para al menos 1 SVG “problemático”, se ve diferencia entre `*_thumb_style.png` y `*_canvas_style.png` (si existe el bug), o se confirma que son equivalentes.

## Diagnóstico
- [ ] `_summary.json` contiene `alpha_nonzero` y `alpha_bbox` por cada modo.
- [ ] Un SVG inválido produce imagen vacía (alpha_nonzero=0) y no crashea.

## No-funcional (contrato)
- [ ] Ejecutar la app normal (`python -m rcs.app`) sigue funcionando.
