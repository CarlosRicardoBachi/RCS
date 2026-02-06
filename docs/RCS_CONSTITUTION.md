# RCS_CONSTITUTION — Reglas duras + obsolescencia

Este archivo es el **contrato** del proyecto. Si alguien (humano o IA) lo rompe, el repo se convierte en una torre de Babel.

## 1) Reglas duras (innegociables)
1. **No se elimina** ninguna funcionalidad ya implementada y probada.
2. Refactor **solo** si mantiene comportamiento (mismo resultado para el usuario).
3. Cualquier función intocable se marca con `# [RCS-KEEP]` y **nunca se borra**.
4. Placeholders permitidos **solo** en v0.0.x (esqueleto). Después: cero placeholders.
   - Excepción (experimental): scaffolding/WIP **solo** si está **deshabilitado por defecto** (feature flag explícito),
     tiene doc de diseño en `docs/` y no rompe el flujo estable.
5. Si un bloque rompe algo probado → **HOTFIX inmediato** (ZIP aparte) antes de avanzar.
6. No crear archivos monstruo: **máximo 2000 líneas por archivo**. Modularizar.
7. En cada archivo Python, header obligatorio: File/Project/Version/Status/Date/Purpose/Notes.

## 2) Disciplina de parches
- Todo cambio se entrega como ZIP incremental.
- Cada ZIP debe incluir:
  - código tocado
  - `docs/CHANGELOG.md` actualizado
  - nota de parche en `docs/patches/...`
  - checklist de pruebas manuales

## 3) Política de obsolescencia (para no pagar impuestos mentales)
Objetivo: **no borrar historia**, pero sí evitar que el proyecto cargue con decisiones ya cerradas.

- Cuando un problema está resuelto y no tiene valor reabrirlo, se marca como **OBSOLETE** en `docs/OBSTACLES.md`.
- Un obstáculo OBSOLETE:
  - no se vuelve a discutir salvo que haya una regresión real
  - queda como referencia histórica (no se borra)
- Si aparece una regresión, el obstáculo vuelve a estado **WATCH** u **OPEN** con una nueva nota.

## 4) Mapa para IA (regla de continuidad)
- `ai/context.json` es el resumen máquina-legible.
- `docs/START_HERE.md` define el orden de lectura.
