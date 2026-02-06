# CHECKLIST — 0.3.10.2.67 (HOTFIX MainWindow ProjectSet Compat)

## Precondición
- Estás sobre 0.3.10.2.66 aplicado.

## 1) Sanidad rápida
- [ ] `python -m py_compile rcs/ui/main_window.py rcs/core/version.py`
- [ ] `python -m rcs.app` inicia y muestra `v0.3.10.2.67`.

## 2) GMPR Import (bloqueante)
- [ ] Archivo → Importar GMPR… abre un `.GMPR`.
- [ ] Esperado: NO aparece `AttributeError ... set_project`.
- [ ] Esperado: NO aparece error por `_refresh_title`.

## 3) Regresión básica
- [ ] Biblioteca visible: miniaturas SVG siguen funcionando.
- [ ] Insertar SVG desde Biblioteca sigue funcionando.
