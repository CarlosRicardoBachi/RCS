# Checklist — Hotfix 0.3.10.2.4

## Pre-condiciones
- Descomprimir este ZIP **encima** del proyecto (manteniendo estructura de carpetas).
- Asegurar que no queden duplicados (si Windows pregunta, elegir *Reemplazar*).

## Pruebas mínimas
1. Ejecutar la app.
2. Confirmar versión en título: **0.3.10.2.4**.
3. Doble click en Biblioteca:
   - `componentes/figuras/casa.svg`
   - `auto.svg`, `corazon.svg`, `llave.svg`, `nube.svg`

   Resultado esperado: **la figura se ve** (no solo el rectángulo de selección).

4. Selección/movimiento:
   - Clic en cualquier parte del bounding del objeto → selecciona.
   - Arrastrar → se mueve.

5. Consola:
   - No hay traceback / exceptions durante inserción.

## Criterio de aceptación
- Si el objeto aparece visible y la selección es fácil, el hotfix se da por válido.
