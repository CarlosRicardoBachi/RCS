ZIPFIX RCS - ImportError MainWindow

Problema:
- rcs/app.py importa MainWindow
- rcs/ui/main_window.py no la define
- El proyecto aún no tiene UI según la documentación

Solución:
- Se agrega un stub documentado de MainWindow
- No agrega UI ni dependencias
- Compatible con el roadmap

Uso:
1. Descomprimir sobre la raíz del repo RCS
2. Ejecutar: python -m rcs.app

Branch: main
Tipo: ZIPFIX
