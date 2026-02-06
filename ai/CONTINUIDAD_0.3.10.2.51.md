# Continuidad — explicación completa (para retomar en nueva sesión)

## Qué se pidió
Antes de escribir código se pidió:
1) Un ZIP con documentación:
   - Roadmap actualizado y detallado del hotfix 0.3.10.2.51
   - Especificación clara del nuevo módulo de texto (pensada para IA)
2) Un prompt “bootstrap” para arrancar una nueva sesión:
   - fusiona el contexto de la conversación
   - indica qué buscar en el repo
   - define restricciones, checklist y entregables
3) Una explicación textual de todo lo anterior para continuidad.

## Qué se entrega aquí
Este paquete contiene 4 archivos:
- `ROADMAP_RCS_TextTool_and_SizePaste.md`:
  Roadmap global + plan de hotfix con etapas, alcance, checklist y criterios de aceptación.
- `SPEC_TextTool_Module.md`:
  Especificación del módulo de texto: UI, decisiones, modos y schema de metadatos.
- `PROMPT_NewSession_Context_and_Plan.md`:
  Prompt listo para pegar en una sesión nueva para que la IA retome el desarrollo.
- `CONTINUIDAD_EXPLICACION.md`:
  Esta explicación de continuidad.

## Cómo usar en una nueva sesión
1) Pegá el contenido de `PROMPT_NewSession_Context_and_Plan.md` tal cual.
2) Adjuntá el repo o ZIP de RCS para que la IA lo lea.
3) La IA implementa el hotfix y devuelve un ZIP patch con solo archivos tocados.

## Qué queda pendiente (y qué NO se hace aún)
Pendiente del hotfix:
- blindaje rotados/grupos + validación dura clipboard + log 1 línea
- placeholder texto: toolbar + interlineado + modos + metadatos

Explícitamente fuera de alcance por ahora:
- offsets/booleanos complejos (placa real con huecos)
- SmartText completo con frozen vector
- export real cut vs engrave (solo metadatos)
