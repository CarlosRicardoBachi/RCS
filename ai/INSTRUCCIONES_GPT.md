# INSTRUCCIONES_GPT — Contrato de trabajo (RCS)

Este proyecto usa documentación viva como **fuente de verdad**. La IA debe apoyarse en esa documentación, no en suposiciones.

## Flujo obligatorio
1) Leer: `docs/START_HERE.md` → `docs/RCS_MAP.md` → `docs/RCS_STATUS.md` → `docs/patches/index.md`
2) Hacer cambios mínimos y trazables (hotfix primero si hay regresión).
3) Entregar **ZIP incremental** con solo archivos modificados/nuevos.
4) Actualizar documentación del parche:
   - `docs/CHANGELOG.md`
   - `docs/patches/index.md`
   - nota en `docs/patches/<linea>/<version>/...`
   - checklist en `docs/checklist/` (o en la carpeta del parche si aplica)

## Reglas
- No eliminar funcionalidades ya probadas.
- No “simplificar” recortando comportamiento.
- Si hay ambigüedad crítica: pedir el dato mínimo indispensable.
- Evitar dependencias nuevas salvo justificación (y documentar).

## Entregables
- ZIP patch (solo cambios)
- Resumen: qué/cómo/por qué
- Pasos de prueba manual
