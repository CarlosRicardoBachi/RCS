# RusticCreadorSvg (RCS)

Editor 2D orientado a **vectores para corte láser/CNC** (llaveros, placas, ensamblajes), basado en **Python + PySide6/Qt**.

## Ejecutar
```bash
python -m rcs.app
```

## Documentación (fuente de verdad)
Empezar siempre por:
- `docs/START_HERE.md` — cómo correr, orden de lectura y reglas.
- `docs/RCS_MAP.md` — mapa de archivos (dónde tocar qué).
- `docs/RCS_STATUS.md` — estado actual y foco inmediato.
- `docs/RCS_ROADMAP.md` — roadmap por bloques.
- `docs/RCS_SPEC.md` — formato `.RCS` y metadatos.
- `docs/patches/index.md` — índice de parches (histórico real).

## IA / continuidad
- `ai/README_AI.md` — reglas de colaboración (no romper lo que ya funciona).
- `ai/context.json` — contexto máquina-legible.
- `ai/BOOTSTRAP_0.3.10.2.51_TextTool.md` — prompt de arranque para continuar el Hotfix 0.3.10.2.51.
- `ai/CONTINUIDAD_0.3.10.2.51.md` — resumen extendido para retomar en otra sesión.

## Instalación
Runtime:
```bash
pip install -r requirements.txt
```
Dev/tests:
```bash
pip install -r requirements-dev.txt
```

---
> Nota: las notas de hotfix/versiones viven en `docs/patches/` (no en este README).
