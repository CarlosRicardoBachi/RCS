# CHECKLIST — RCS 0.3.10.2.53 (CORE Transform Engine)

## Objetivo
Validar que la consolidación del motor de transformaciones no cambió comportamiento:
- move/rotate/scale siguen sincronizando modelo↔scene sin drift
- handles + pegar tamaño mantienen pivot correcto

## Validaciones base
- [ ] RCS inicia sin tracebacks.
- [ ] HUD/overlays amarillos siguen visibles (hoja/lienzo/zoom, etc.).

## Move (ToolMode.MOVE)
- [ ] Arrastrar un objeto mueve correctamente.
- [ ] Al soltar, re-seleccionar y mover otra vez no introduce “micro-saltos”.
- [ ] Multi-selección: mover grupo mantiene offsets.

## Rotate (ToolMode.ROTATE)
- [ ] Rueda rota el objeto.
- [ ] Overlay de ángulo aparece y actualiza.
- [ ] Shift+rueda rota fino.
- [ ] El centro del objeto se mantiene estable (no se “corre” al rotar repetidamente).

## Scale (ToolMode.SCALE)
- [ ] Se ven 4 handles (puntitos) en las esquinas del bbox.
- [ ] Drag desde una esquina escala sin saltos.
- [ ] Overlay “Objeto: W x H mm” aparece durante el escalado.
- [ ] SVG preview rerenderiza tras escala (no queda “viejo”).

## Pegar tamaño (Objeto → Pegar tamaño / o acción equivalente)
- [ ] Con 1 objeto: cambia tamaño objetivo, mantiene su centro.
- [ ] Con multi-selección:
  - [ ] Escala como grupo real (posiciones relativas se mantienen).
  - [ ] El pivot es coherente (no se desplaza el conjunto).

## Notas
- Si algo falla, el foco está en: `_apply_group_scale_about_pivot()` y `_sync_item_pos_to_model()`.
