# RCS_STATUS — Estado actual y foco inmediato
Fecha: 2026-01-26

## Versión de trabajo (última confirmada)
- App: **0.3.10.2.49**
- Línea: hotfixes v0.3.x (estabilidad/UX) mientras se prepara Bloque 4 (Texto).

## Lo último que quedó funcionando (hotfixes recientes)
### Canvas / mediciones
- Overlays de medición en `CanvasView.drawForeground()` sin crashear.
- Fix de import faltante `QFontMetrics` (era `NameError`).

### Clipboard de tamaño (copy/paste dimensiones)
- Copiar ancho/alto desde selección funciona.
- Pegado de tamaño a otro objeto funciona (sin warnings Shiboken, sin tuples mal tipadas).

> Nota: aunque hoy ande, es un área donde suelen aparecer bugs con rotación/grupos → ver “pendientes”.

## Pendientes inmediatos (blindaje)
1) **Rotación / grupos**
- Verificar que “pegar tamaño” se aplique en el espacio correcto (local vs scene) cuando:
  - el ítem está rotado
  - el ítem es un grupo
- El bug típico es que el usuario “pega tamaño” pero la geometría termina con escala rara o el bbox no coincide.

2) **Validación dura del clipboard**
- Impedir definitivamente valores inválidos (0, negativos, NaN, bool camuflado).
- Log simple en 1 línea cuando un pegado se ignora (para no spammear stacktraces).

## Próximo frente: módulo de Texto (maquetado)
Se habilita empezar por UI/flujo, sin “Inkscape dentro de RCS”.

Requisitos inmediatos (WIP):
- Herramienta en **barra/dock movible** (no panel fijo “pegado”).
- Parámetro faltante: **interlineado** (`line_spacing`).
- Dos modos orientados a llaveros:
  1) **Modo CONTINUO** (texto de una sola pieza para corte):
     - letras puenteadas/unionadas para que no se caigan islas.
     - submodo decidido: **“Islas como grabado”** (diacríticos, puntos, etc. → grabado, no corte separado).
  2) **Modo PLACA** (contorno + letras dentro):
     - genera `LETTERS` + `PLATE` (placa que abraza) con parámetro `outer_margin_mm`.

Decisiones ya tomadas:
- `seat_clearance_mm`: no se usa (no hace falta con potencia del láser).
- `shadow_offset_mm`: se omite (si alguna vez se agrega, será decorativo, no core).

Documento base (todo el diseño): `docs/RCS_TEXT_TOOL.md`.

## Archivos relevantes
- Canvas overlays / clipboard tamaño: `rcs/ui/canvas_view.py`
- Guía del módulo texto: `docs/RCS_TEXT_TOOL.md`
- Roadmap general: `docs/RCS_ROADMAP.md`
- Prompt de continuidad para IA: `ai/BOOTSTRAP_0.3.10.2.51_TextTool.md`
