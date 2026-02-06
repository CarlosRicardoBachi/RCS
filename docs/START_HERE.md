# START_HERE — RusticCreadorSvg (RCS)

Este repo incluye un “Context Pack” para retomar el desarrollo (humano o IA) sin prompt infinito.

## 1) Ejecutar

Requisitos:
- Python 3.11+
- PySide6

Comando:
- `python -m rcs.app`

Si usás venv:
- `python -m venv .venv`
- activar venv
- instalar deps: `pip install -r requirements.txt`

## 2) Arquitectura (alto nivel)
- `rcs/core/`: modelos + serialización `.RCS`
- `rcs/ui/`: ventana, lienzo, librería
- `rcs/svg/`: import/export + thumbnails
- `docs/`: especificación, mapa, estado, parches, obstáculos
- `ai/`: resumen máquina-legible (`context.json`) + guía

## 3) Antes de tocar código
Leé en este orden:
1) `docs/START_HERE.md`
2) `ai/README_AI.md` y `ai/context.json`
3) `docs/RCS_CONSTITUTION.md` (reglas duras)
4) `docs/RCS_STATUS.md` (estado actual)
5) `docs/patches/index.md` y `docs/OBSTACLES.md` (para no repetir errores)

## 4) Entregas (regla del proyecto)
Todo cambio se entrega como ZIP incremental con:
- solo los archivos modificados
- `docs/CHANGELOG.md` actualizado
- una nota en `docs/patches/...`
- checklist de pruebas manuales

## 5) Versionado
- `rcs/core/version.py` define `APP_VERSION`.
- Hotfix sube PATCH (ej: 0.3.10 → 0.3.10.1)
- Bloques suben MINOR cuando corresponda.
