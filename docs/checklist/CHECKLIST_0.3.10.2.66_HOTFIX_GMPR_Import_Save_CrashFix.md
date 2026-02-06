# CHECKLIST — 0.3.10.2.66 (HOTFIX GMPR Import/Save CrashFix)

## Build / sanity

- [ ] `python -m py_compile rcs/ui/main_window.py`
- [ ] `python -m py_compile rcs/core/gmpr_io.py`
- [ ] App inicia y muestra la ventana principal.

## Repro 1: Importar GMPR no crashea por firma

1. Abrir RCS.
2. Archivo → **Importar GMPR…** y elegir un `.GMPR`.
3. Esperado:
   - No aparece `TypeError: gmpr_to_project() got an unexpected keyword argument 'file_path'`.
   - No crashea por `transform=tr` (NameError / UnboundLocal).
   - El proyecto se carga (canvas se actualiza).

## Repro 2: Raster aparece con transform razonable

1. Con el GMPR importado, ubicar el raster.
2. Verificar:
   - Se ve en una posición/tamaño razonables (no “minúsculo” ni “gigante”).
   - Rotación visible si el GMPR la tenía.

## Repro 3: Guardar GMPR no crashea (retorno Path)

1. Con el GMPR importado, mover el raster un poco.
2. Archivo → Guardar (Ctrl+S).
3. Esperado:
   - No crashea por retorno `None` (UI usa `p.name`).
   - El archivo se escribe.

## Repro 4: Persistencia mínima (import → mover → guardar → reimport)

1. Cerrar la app.
2. Reabrir y **reimportar** el mismo GMPR.
3. Verificar:
   - El raster reaparece en una posición/tamaño razonables (sin teletransporte extremo).

