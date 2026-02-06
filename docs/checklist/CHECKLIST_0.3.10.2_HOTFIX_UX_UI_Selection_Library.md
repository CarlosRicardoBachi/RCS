# CHECKLIST — 0.3.10.2 (HOTFIX) UX/UI

## Precondiciones
- Estás en **0.3.10.1** (o 0.3.10.1 + tus cambios locales) y aplicás este ZIP arriba.

## Smoke test (5 min)
- [ ] Abrir la app.
- [ ] Abrir un proyecto con varios SVG (o insertar 3–5 desde biblioteca).
- [ ] Probar zoom (rueda) + pan + selección de objetos.

## Validaciones específicas
### 1) Zoom mínimo adaptativo
- [ ] Hacer zoom out: debe frenar automáticamente cuando la hoja ya está “a tamaño visible” (no microscópica).
- [ ] Redimensionar la ventana (más chica): el mínimo puede subir; el zoom se clampa sin romper.
- [ ] El slider de zoom debe actualizar su mínimo cuando cambia el viewport.

### 2) Selección por interior (figuras cerradas)
- [ ] Insertar un SVG que sea contorno (outline) cerrado.
- [ ] Click en el interior: **selecciona** sin necesidad de pegarle al borde.
- [ ] Click fuera del objeto: no selecciona.
- [ ] Si la figura está abierta (no cerrada), el interior NO se rellena (comportamiento esperado).

### 3) Biblioteca (splitter ajustable)
- [ ] En el dock “Biblioteca”, arrastrar el divisor entre árbol y miniaturas: debe cambiar altura.
- [ ] Cerrar la app y reabrir: el splitter debe restaurar la última posición.

### 4) Layout persistente (dock/toolbar)
- [ ] Mover el dock Biblioteca a la derecha.
- [ ] Cerrar y reabrir: debe quedar donde lo dejaste.

## Flags/Diagnóstico
- [ ] (Opcional) `RCS_CANVAS_HIT_FILL=0` vuelve al hit-test viejo (solo contorno).

## Regressions a vigilar
- [ ] Preview (nitidez + halo) sigue igual que en 0.3.10.1.
- [ ] Grilla sigue limitada a la hoja.
- [ ] Guardar/abrir proyectos no se ve afectado.
