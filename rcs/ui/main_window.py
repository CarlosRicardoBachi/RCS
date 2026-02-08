# File: rcs/ui/main_window.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10
# Status: stable
# Date: 2026-01-17
# Purpose: Ventana principal + acciones base (Archivo) + dock Biblioteca.
# Notes: Bloque 3I: acciones de encuadre (selección / todo / hoja) + shortcuts.
from __future__ import annotations

import base64
import os
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence, QCursor
from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QStatusBar,
    QLabel,
    QDockWidget,
    QToolBar,
    QStyle,
    QDialog,
    QInputDialog,
    QMenu,
)

from rcs.core.models import Project
from rcs.core.gmpr_io import gmpr_to_project, load_gmpr_json, save_gmpr_project
from rcs.core.settings import AppSettings, apply_project_settings, load_project_settings, save_project_settings
from rcs.core.tool_mode import ToolMode
from rcs.core.version import APP_NAME, APP_VERSION, DEFAULT_CANVAS_MM
from rcs.ui.canvas_view import CanvasView
from rcs.ui.canvas_container import CanvasContainer
from rcs.ui.canvas_size_dialog import CanvasSizeDialog
from rcs.ui.library_panel import LibraryPanel
from rcs.ui.objects_panel import ObjectsPanel
from rcs.ui.text_tool_panel import TextToolPanel
from rcs.utils.log import get_logger

log = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("{} v{}".format(APP_NAME, APP_VERSION))
        self.resize(1200, 800)
        self._project: Project = Project()

        # Preferencias usuario (tema, etc.)
        self._settings = AppSettings.load()
        # Proyecto (repo): defaults compartibles (rcs_settings.json)
        apply_project_settings()
        self._apply_default_canvas_mm_to_project(self._project)

        self._build_ui()
        self._build_menu()

        # Restaurar layout (dock/toolbar/geometry) si hay settings previos.
        # [RCS-KEEP] No debe romper el arranque.
        self._restore_ui_state()

        self._update_title()

    def _build_ui(self) -> None:
        # [RCS-KEEP] La ventana principal y sus acciones de Archivo no se eliminan.
        self._canvas = CanvasView(self)
        self._canvas.set_theme(self._settings.canvas_theme)
        # Preview thickness (persistente)
        self._canvas.set_preview_style(
            stroke_thick=self._settings.canvas_stroke_thick,
            outline_thick=self._settings.canvas_outline_thick,
        )

        # Tool mode persistente
        self._canvas.set_tool_mode(self._settings.tool_mode)

        self._canvas_container = CanvasContainer(self._canvas, self)
        self.setCentralWidget(self._canvas_container)
        # CanvasView compat: algunos patches pueden dejar API incompleta; no crashear.
        if hasattr(self._canvas, "set_project") and callable(getattr(self._canvas, "set_project", None)):
            self._canvas.set_project(self._project)
        else:
            try:
                self._canvas._project = self._project
                fn = getattr(self._canvas, "_rebuild_scene_from_project", None)
                if callable(fn):
                    fn()
            except Exception:
                pass
        self._canvas.project_modified.connect(self._on_project_modified)

        self._build_toolbar()

        # Dock: Biblioteca
        self._library = LibraryPanel(self)
        self._library.set_project(self._project)
        self._library.asset_activated.connect(self._on_asset_activated)

        self._dock_library = QDockWidget("Biblioteca", self)
        self._dock_library.setObjectName("dock_library")
        self._dock_library.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._dock_library.setWidget(self._library)
        self._dock_library.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._dock_library)

        # Dock: Objetos (capas)
        self._objects_panel = ObjectsPanel(self._canvas, self)
        self._objects_panel.set_project(self._project)

        self._dock_objects = QDockWidget("Objetos", self)
        self._dock_objects.setObjectName("dock_objects")
        self._dock_objects.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._dock_objects.setWidget(self._objects_panel)
        self._dock_objects.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, self._dock_objects)

        # Dock: Texto (WIP / placeholder)
        # [RCS-KEEP] Maquetado de herramienta de texto. Inserción real como objeto vendrá en hotfix posterior.
        self._text_panel = TextToolPanel(self)
        self._text_panel.insertRequested.connect(self._on_text_insert_requested)

        self._dock_text = QDockWidget("Texto", self)
        self._dock_text.setObjectName("dock_text")
        self._dock_text.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._dock_text.setWidget(self._text_panel)
        self._dock_text.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, self._dock_text)

        sb = QStatusBar(self)
        self.setStatusBar(sb)
        self._status_label = QLabel("Listo", self)
        sb.addPermanentWidget(self._status_label)

    def _on_text_insert_requested(self, meta: dict) -> None:
        """Placeholder: el panel ya emite metadatos; la creación del objeto real vendrá luego."""
        try:
            # No hacemos nada con el lienzo todavía: evitamos romper export/selección.
            txt = (meta or {}).get('text', '')
            txt_one = (txt.splitlines()[0] if isinstance(txt, str) else '')
            self._status(f"Texto (WIP): listo para insertar: {txt_one[:32]}")
        except Exception:
            self._status("Texto (WIP): listo para insertar")

    def _toolbar_qt_style(self) -> Qt.ToolButtonStyle:
        """Devuelve el estilo de botones de la toolbar.

        Orden de prioridad:
        1) env var RCS_TOOLBAR_STYLE (rcs_settings.json puede setearla via apply_project_settings)
        2) user settings (settings.json)

        Valores: icon_only, text_only, text_beside_icon, text_under_icon
        """
        raw = (os.environ.get('RCS_TOOLBAR_STYLE') or getattr(self._settings, 'toolbar_style', '') or '').strip().lower()
        if raw in ('icon_only', 'icononly', 'icons'):
            return Qt.ToolButtonIconOnly
        if raw in ('text_beside_icon', 'textbesideicon', 'beside'):
            return Qt.ToolButtonTextBesideIcon
        if raw in ('text_under_icon', 'textundericon', 'under'):
            return Qt.ToolButtonTextUnderIcon
        # default: texto
        return Qt.ToolButtonTextOnly



    def _toolbar_icon_size(self) -> QSize:
        """Tamaño de icono para QToolBar.

        Orden de prioridad:
        1) env var RCS_TOOLBAR_ICON_SIZE (ej: "20" o "20x20")
        2) user settings toolbar_icon_size (si existe)

        Default: 22
        """
        raw = (os.environ.get('RCS_TOOLBAR_ICON_SIZE') or getattr(self._settings, 'toolbar_icon_size', '') or '').strip().lower().replace(' ', '')
        if raw:
            try:
                if 'x' in raw:
                    a, b = raw.split('x', 1)
                    w = int(a)
                    h = int(b)
                else:
                    w = h = int(raw)
                w = max(8, min(64, w))
                h = max(8, min(64, h))
                return QSize(w, h)
            except Exception:
                pass
        return QSize(22, 22)

    def _build_toolbar(self) -> None:
        # Toolbars flotantes (dock/undock)
        tstyle = self._toolbar_qt_style()

        # ------------------------------------------------
        # Barra 1: Herramientas (modos)
        # ------------------------------------------------
        tb_tools = QToolBar("Herramientas", self)
        tb_tools.setObjectName("tb_tools")
        tb_tools.setMovable(True)
        tb_tools.setFloatable(True)
        tb_tools.setIconSize(self._toolbar_icon_size())
        tb_tools.setToolButtonStyle(tstyle)

        grp = QActionGroup(self)
        grp.setExclusive(True)

        def _add_tool(text: str, tip: str, mode: ToolMode) -> QAction:
            a = QAction(text, self)
            a.setCheckable(True)
            a.setToolTip(tip)
            a.setData(mode.value)
            a.triggered.connect(lambda _=False, m=mode: self._set_tool_mode(m))
            grp.addAction(a)
            tb_tools.addAction(a)
            return a

        act_select = _add_tool("Seleccionar", "Seleccionar (sin arrastrar)", ToolMode.PICK)
        act_move = _add_tool("Mover", "Seleccionar + mover (arrastrar)", ToolMode.SELECT)
        act_zoom = _add_tool("Zoom", "Zoom (rueda/arrastrar)", ToolMode.ZOOM)
        act_pan = _add_tool("Pan", "Pan (arrastrar)", ToolMode.PAN)
        act_rotate = _add_tool("Rotar", "Rotar selección", ToolMode.ROTATE)
        act_scale = _add_tool("Escalar", "Escalar selección", ToolMode.SCALE)

        # Estado inicial según settings
        wanted = str(getattr(self._settings, "tool_mode", ToolMode.SELECT.value)).strip().lower()
        for a in (act_select, act_move, act_zoom, act_pan, act_rotate, act_scale):
            if str(a.data() or "").strip().lower() == wanted:
                a.setChecked(True)
                break
        else:
            act_select.setChecked(True)

        # ------------------------------------------------
        # Barra 2: Acciones rápidas
        # ------------------------------------------------
        tb_actions = QToolBar("Acciones", self)
        tb_actions.setObjectName("tb_actions")
        tb_actions.setMovable(True)
        tb_actions.setFloatable(True)
        tb_actions.setIconSize(self._toolbar_icon_size())
        tb_actions.setToolButtonStyle(tstyle)

        act_dup = QAction("Duplicar", self)
        act_dup.setToolTip("Duplicar selección")
        act_dup.triggered.connect(lambda: self._canvas.duplicate_selected())
        tb_actions.addAction(act_dup)

        act_fit = QAction("Ajustar", self)
        act_fit.setToolTip("Ajustar SVG al bounding-box (recorte interno)")
        act_fit.triggered.connect(lambda: self._canvas.fit_selected_to_content())
        tb_actions.addAction(act_fit)

        act_canvas_auto = QAction("Lienzo automático", self)
        act_canvas_auto.setToolTip("Ajusta el lienzo al contenido (sin márgenes)")
        act_canvas_auto.triggered.connect(self._action_canvas_auto)
        tb_actions.addAction(act_canvas_auto)

        act_obj_size = QAction("Medida objeto", self)
        act_obj_size.setToolTip("Ajustar medida (mm) del objeto seleccionado")
        act_obj_size.triggered.connect(self._action_image_size_mm)
        tb_actions.addAction(act_obj_size)

        act_text = QAction("Texto", self)
        act_text.setToolTip("Mostrar/ocultar panel Texto (dock)")
        act_text.triggered.connect(self._toggle_text_dock)
        tb_actions.addAction(act_text)

        self.addToolBar(Qt.TopToolBarArea, tb_tools)
        self.addToolBar(Qt.TopToolBarArea, tb_actions)


    def _toggle_text_dock(self) -> None:
        """Mostrar/ocultar el dock de Texto (placeholder).

        [RCS-KEEP] No debe romper el arranque aunque el dock todavía no exista.
        """
        dock = getattr(self, "_dock_text", None)
        if dock is None:
            self._status("Texto: dock no disponible")
            return
        new_vis = not dock.isVisible()
        dock.setVisible(new_vis)
        if new_vis:
            try:
                dock.raise_()
                panel = getattr(self, "_text_panel", None)
                if panel is not None and hasattr(panel, "focus_first"):
                    panel.focus_first()
            except Exception:
                pass
        self._status("Texto: {}".format("visible" if new_vis else "oculto"))



    def _set_tool_mode(self, mode: ToolMode) -> None:
        self._canvas.set_tool_mode(mode)
        # Persistencia
        self._settings.tool_mode = mode.value
        self._settings.save()
        self._status(f"Herramienta: {mode.value}")

    def _action_canvas_size(self) -> None:
        # Diálogo: tamaño en mm
        w, h = self._project.canvas_mm
        dlg = CanvasSizeDialog(float(w), float(h), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            nw, nh = dlg.values()
            self._canvas.set_canvas_mm(nw, nh)
            self._status(f"Lienzo: {nw:g} x {nh:g} mm")


    
    def _action_image_size_mm(self) -> None:
        """Abre un diálogo para ajustar tamaño (mm) del objeto seleccionado."""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QCheckBox, QPushButton, QMessageBox
        except Exception:
            return

        if not getattr(self, "_canvas", None):
            return

        # Obtener tamaño actual del seleccionado (si hay)
        sel = self._canvas.scene().selectedItems() if hasattr(self._canvas, "scene") else []
        cur_w = cur_h = None
        if sel:
            rect = sel[0].sceneBoundingRect()
            cur_w = float(rect.width())
            cur_h = float(rect.height())

        dlg = QDialog(self)
        dlg.setWindowTitle("Ajustar medida de objeto (mm)")
        lay = QVBoxLayout(dlg)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Ancho (mm):"))
        sp_w = QDoubleSpinBox()
        sp_w.setRange(0.01, 100000.0)
        sp_w.setDecimals(3)
        sp_w.setSingleStep(1.0)
        if cur_w:
            sp_w.setValue(cur_w)
        row1.addWidget(sp_w)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Alto (mm):"))
        sp_h = QDoubleSpinBox()
        sp_h.setRange(0.01, 100000.0)
        sp_h.setDecimals(3)
        sp_h.setSingleStep(1.0)
        if cur_h:
            sp_h.setValue(cur_h)
        row2.addWidget(sp_h)
        lay.addLayout(row2)

        chk = QCheckBox("Mantener relación de aspecto")
        chk.setChecked(True)
        lay.addWidget(chk)

        # Si conocemos el tamaño actual, sincronizamos ancho/alto cuando se pide mantener aspecto.
        ratio = None
        if cur_w and cur_h and cur_w > 0:
            ratio = float(cur_h) / float(cur_w)
        _sync_guard = {"on": False}

        def _sync_from_w(val: float) -> None:
            if not chk.isChecked() or ratio is None or _sync_guard["on"]:
                return
            _sync_guard["on"] = True
            try:
                sp_h.setValue(float(val) * ratio)
            finally:
                _sync_guard["on"] = False

        def _sync_from_h(val: float) -> None:
            if not chk.isChecked() or ratio is None or _sync_guard["on"]:
                return
            _sync_guard["on"] = True
            try:
                sp_w.setValue(float(val) / ratio)
            finally:
                _sync_guard["on"] = False

        sp_w.valueChanged.connect(_sync_from_w)
        sp_h.valueChanged.connect(_sync_from_h)

        btns = QHBoxLayout()
        btn_ok = QPushButton("Aplicar")
        btn_cancel = QPushButton("Cancelar")
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        lay.addLayout(btns)

        def _apply():
            if not sel:
                QMessageBox.information(self, "Ajustar tamaño", "No hay un objeto seleccionado.")
                return
            ok = False
            try:
                ok = self._canvas.set_selected_size_mm(float(sp_w.value()), float(sp_h.value()), keep_aspect=bool(chk.isChecked()))
            except Exception as e:
                QMessageBox.critical(self, "Ajustar tamaño", f"Error aplicando tamaño: {e}")
                return
            if not ok:
                # no cambió o algo inválido; no lo tratamos como error.
                pass
            dlg.accept()

        btn_ok.clicked.connect(_apply)
        btn_cancel.clicked.connect(dlg.reject)

        dlg.exec()

    def _action_canvas_auto(self) -> None:
        """Ajusta el tamaño del lienzo para encerrar el contenido (sin márgenes)."""
        try:
            ok = bool(getattr(self._canvas, "auto_canvas_to_content")(padding_mm=0.0))
        except Exception:
            ok = False

        if ok:
            w, h = self._project.canvas_mm
            self._status(f"Lienzo automático: {float(w):g} x {float(h):g} mm")
        else:
            self._status("Lienzo automático: no hay contenido para ajustar")

    def _action_frame_selection(self) -> None:
        """Encuadra la selección en la vista."""
        try:
            ok = bool(getattr(self._canvas, "frame_selection")())
        except Exception:
            ok = False
        self._status("Encuadre: selección" if ok else "No hay selección para encuadrar")

    def _action_frame_all(self) -> None:
        """Encuadra todos los objetos del proyecto (no la hoja)."""
        try:
            ok = bool(getattr(self._canvas, "frame_all_objects")())
        except Exception:
            ok = False
        self._status("Encuadre: todo" if ok else "No hay objetos para encuadrar")

    def _action_view_reset_to_sheet(self) -> None:
        """Reset de vista: encuadra la hoja."""
        try:
            getattr(self._canvas, "view_reset_to_sheet")()
            self._status("Vista: hoja")
        except Exception as e:
            self._status(f"Reset vista falló: {e}")



    # ------------------------------ Preferencias persistentes (rcs_settings.json)
    def _apply_default_canvas_mm_to_project(self, project: Project) -> None:
        """Aplica tamaño de lienzo por defecto a proyectos nuevos (sin marcar dirty)."""
        # Preferimos ENV (ya aplicado por apply_project_settings en el arranque),
        # y caemos a archivo solo si faltan las variables.
        w_env = os.environ.get("RCS_CANVAS_DEFAULT_W_MM")
        h_env = os.environ.get("RCS_CANVAS_DEFAULT_H_MM")
        if w_env and h_env:
            try:
                w = float(w_env)
                h = float(h_env)
            except Exception:
                w = h = None
            if w and h and w > 0 and h > 0:
                project.canvas_mm = (w, h)
                return

        settings = load_project_settings()
        ui = settings.get("ui", {}) if isinstance(settings, dict) else {}
        canvas = ui.get("canvas", {}) if isinstance(ui, dict) else {}
        default_mm = canvas.get("default_canvas_mm") if isinstance(canvas, dict) else None

        if isinstance(default_mm, (list, tuple)) and len(default_mm) == 2:
            try:
                w = float(default_mm[0])
                h = float(default_mm[1])
            except Exception:
                return
            if w > 0 and h > 0:
                project.canvas_mm = (w, h)

    @staticmethod
    def _deep_merge_dict(base: dict, incoming: dict) -> dict:
        """Merge recursivo simple (incoming pisa base)."""
        out = dict(base)
        for k, v in incoming.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = MainWindow._deep_merge_dict(out[k], v)
            else:
                out[k] = v
        return out

    def _update_project_settings(self, incoming: dict) -> None:
        settings = load_project_settings()
        if not isinstance(settings, dict):
            settings = {}
        settings = self._deep_merge_dict(settings, incoming)
        save_project_settings(settings)
        # Relee desde disco y fuerza ENV con los nuevos valores (sin respetar overrides previos).
        apply_project_settings(prefer_env=False)

    def _unset_env(self, *names: str) -> None:
        import os
        for n in names:
            try:
                os.environ.pop(n, None)
            except Exception:
                pass

    def _delete_project_setting(self, dotted_path: str) -> None:
        """Elimina una key (por path con puntos) del rcs_settings.json.

        Esto permite "resetear" preferencias sin dejar `null` y sin tocar otros keys.
        """
        settings = load_project_settings()
        if not isinstance(settings, dict):
            return

        keys = [k for k in str(dotted_path).split('.') if k]
        if not keys:
            return

        cur = settings
        parents: list[tuple[dict, str]] = []
        for k in keys[:-1]:
            nxt = cur.get(k)
            if not isinstance(nxt, dict):
                return
            parents.append((cur, k))
            cur = nxt

        last = keys[-1]
        if isinstance(cur, dict) and last in cur:
            del cur[last]

        # Prune dicts vacíos hacia arriba
        for parent, k in reversed(parents):
            try:
                if isinstance(parent.get(k), dict) and not parent[k]:
                    del parent[k]
            except Exception:
                pass

        save_project_settings(settings)
        apply_project_settings(prefer_env=False)

    # ------------------------------ Acciones: F10/F11/F12 + scrollbars
    def _action_set_default_page_size(self) -> None:
        settings = load_project_settings()
        ui = settings.get("ui", {}) if isinstance(settings, dict) else {}
        canvas = ui.get("canvas", {}) if isinstance(ui, dict) else {}
        default_mm = canvas.get("default_canvas_mm") if isinstance(canvas, dict) else None

        # Fallback: tamaño actual del proyecto
        w0, h0 = self._project.canvas_mm
        if isinstance(default_mm, (list, tuple)) and len(default_mm) == 2:
            try:
                w0 = float(default_mm[0])
                h0 = float(default_mm[1])
            except Exception:
                pass

        dlg = CanvasSizeDialog(w0, h0, self)
        dlg.setWindowTitle("Página por defecto (mm)")
        if dlg.exec() != QDialog.Accepted:
            return

        w, h = dlg.values()

        # Aplica al proyecto actual
        self._canvas.set_canvas_mm(w, h)

        # Persiste
        self._update_project_settings({"ui": {"canvas": {"default_canvas_mm": [float(w), float(h)]}}})
        self.statusBar().showMessage(f"Página por defecto guardada: {w:.1f}×{h:.1f} mm", 3000)


    def _action_reset_default_page_size(self) -> None:
        """Restaura el tamaño por defecto de página a DEFAULT_CANVAS_MM."""
        w, h = DEFAULT_CANVAS_MM
        # Borra override y env vars relacionadas
        self._unset_env("RCS_CANVAS_DEFAULT_W_MM", "RCS_CANVAS_DEFAULT_H_MM")
        self._delete_project_setting("ui.canvas.default_canvas_mm")

        # Aplica al proyecto actual para coherencia visual
        try:
            self._canvas.set_canvas_mm(float(w), float(h))
        except Exception:
            pass

        self._status(f"Página por defecto restaurada: {w:g}×{h:g} mm")

    def _action_reset_start_view(self) -> None:
        """Elimina start_view guardado y vuelve al comportamiento default."""
        self._unset_env("RCS_CANVAS_START_VIEW")
        self._delete_project_setting("ui.canvas.start_view")
        try:
            self._canvas.clear_startup_view_state()
        except Exception:
            pass
        self._status("Vista de inicio restaurada (sin posición guardada)")

    def _action_reset_zoom_range(self) -> None:
        """Restaura el rango de zoom a ×1.0."""
        self._unset_env("RCS_CANVAS_ZOOM_RANGE")
        try:
            self._canvas.set_zoom_range_factor(1.0)
        except Exception:
            pass
        self._update_project_settings({"ui": {"canvas": {"zoom_range": 1.0}}})
        self._status("Rango de zoom restaurado: ×1.0")

    def _action_set_canvas_scroll_policy(self, axis: str, policy: str) -> None:
        axis = (axis or "").lower().strip()
        policy = (policy or "").lower().strip()
        if policy not in ("off", "needed", "on"):
            return

        if axis in ("h", "horizontal"):
            try:
                self._canvas.set_scrollbars_policy(horizontal=policy)
            except Exception:
                pass
            self._update_project_settings({"ui": {"canvas": {"scroll_h_policy": policy, "scroll_h": (policy != "off")}}})
            self._status(f"Scroll horizontal: {policy}")
        elif axis in ("v", "vertical"):
            try:
                self._canvas.set_scrollbars_policy(vertical=policy)
            except Exception:
                pass
            self._update_project_settings({"ui": {"canvas": {"scroll_v_policy": policy, "scroll_v": (policy != "off")}}})
            self._status(f"Scroll vertical: {policy}")


    def _action_save_start_view(self) -> None:
        state = self._canvas.get_view_state_canvas()
        # Hace que un "Nuevo" proyecto en esta misma sesión use esta vista
        try:
            cx, cy = state.get("center_canvas", [0.0, 0.0])
            zoom = float(state.get("zoom", 1.0))
            self._canvas.set_startup_view_state((float(cx), float(cy)), zoom)
        except Exception:
            pass
        self._update_project_settings({"ui": {"canvas": {"start_view": state}}})
        self.statusBar().showMessage("Vista de inicio guardada", 3000)

    def _set_zoom_range_factor(self, factor: float) -> None:
        self._canvas.set_zoom_range_factor(float(factor))
        self._update_project_settings({"ui": {"canvas": {"zoom_range": float(factor)}}})
        self.statusBar().showMessage(f"Rango de zoom: ×{factor:g}", 3000)

    def _action_zoom_range_menu(self) -> None:
        current = self._canvas.zoom_range_factor()
        menu = QMenu(self)

        presets = [
            (0.5, "×0.5 (más estrecho)"),
            (0.75, "×0.75"),
            (1.0, "×1.0 (default)"),
            (1.5, "×1.5"),
            (2.0, "×2.0 (más amplio)"),
            (3.0, "×3.0 (muy amplio)"),
        ]

        for f, label in presets:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(abs(current - f) < 1e-6)
            act.triggered.connect(lambda _checked=False, ff=f: self._set_zoom_range_factor(ff))
            menu.addAction(act)

        menu.addSeparator()
        act_custom = QAction("Personalizado…", self)
        act_custom.triggered.connect(self._action_zoom_range_custom)
        menu.addAction(act_custom)

        menu.exec(QCursor.pos())

    def _action_zoom_range_custom(self) -> None:
        current = self._canvas.zoom_range_factor()
        val, ok = QInputDialog.getDouble(
            self,
            "Rango de zoom",
            "Factor (0.25 a 4.0):",
            value=float(current),
            min=0.25,
            max=4.0,
            decimals=2,
        )
        if not ok:
            return
        self._set_zoom_range_factor(val)

    def _action_toggle_canvas_scroll_h(self, checked: bool) -> None:
        # Compat: mapea ON/OFF a una política
        self._action_set_canvas_scroll_policy('h', 'needed' if bool(checked) else 'off')

    def _action_toggle_canvas_scroll_v(self, checked: bool) -> None:
        # Compat: mapea ON/OFF a una política
        self._action_set_canvas_scroll_policy('v', 'needed' if bool(checked) else 'off')

    def _build_menu(self) -> None:
        m_file = self.menuBar().addMenu("&Archivo")

        act_new = QAction("&Nuevo", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self.action_new)
        m_file.addAction(act_new)

        act_open = QAction("Importar &SVG…", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.action_open)
        m_file.addAction(act_open)

        act_import_gmpr = QAction("Importar &GMPR…", self)
        act_import_gmpr.setShortcut("Ctrl+I")
        act_import_gmpr.triggered.connect(self.action_import_gmpr)
        m_file.addAction(act_import_gmpr)

        m_file.addSeparator()

        act_save = QAction("&Guardar", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.action_save)
        m_file.addAction(act_save)

        act_save_as = QAction("Guardar &como…", self)
        act_save_as.setShortcut("Ctrl+Shift+S")
        act_save_as.triggered.connect(self.action_save_as)
        m_file.addAction(act_save_as)

        m_file.addSeparator()

        act_exit = QAction("&Salir", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        # Menú: Edición
        m_edit = self.menuBar().addMenu("&Edición")

        act_copy = QAction("&Copiar", self)
        act_copy.setShortcut(QKeySequence.Copy)
        act_copy.triggered.connect(lambda: self._canvas.copy_selected())
        m_edit.addAction(act_copy)

        act_paste = QAction("&Pegar", self)
        act_paste.setShortcut(QKeySequence.Paste)
        act_paste.triggered.connect(lambda: self._canvas.paste_copied())
        m_edit.addAction(act_paste)

        act_dup = QAction("&Duplicar", self)
        act_dup.setShortcut(QKeySequence("Ctrl+D"))
        act_dup.triggered.connect(lambda: self._canvas.duplicate_selected())
        m_edit.addAction(act_dup)

        act_fit = QAction("Ajustar al &objeto", self)
        act_fit.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_fit.setToolTip("Ajustar marco al contenido del SVG (recorta márgenes blancos internos)")
        def _do_fit_menu() -> None:
            n = self._canvas.fit_selected_to_content()
            if n:
                self._status(f"Ajustado {n} objeto(s)")
            else:
                self._status("No hay SVG seleccionado para ajustar")
        act_fit.triggered.connect(_do_fit_menu)
        m_edit.addAction(act_fit)

        act_del = QAction("&Eliminar", self)
        act_del.setShortcut(QKeySequence.Delete)
        act_del.triggered.connect(lambda: self._canvas.delete_selected())
        m_edit.addAction(act_del)
        # Menú: Lienzo
        m_canvas = self.menuBar().addMenu("&Lienzo")
        act_auto = QAction("Lienzo &automático", self)
        act_auto.setToolTip("Ajusta el tamaño del lienzo al contenido (sin márgenes)")
        act_auto.triggered.connect(self._action_canvas_auto)
        m_canvas.addAction(act_auto)
        m_canvas.addSeparator()
        act_size = QAction("Tamaño en &mm…", self)
        act_size.triggered.connect(self._action_canvas_size)
        m_canvas.addAction(act_size)

        act_def_size = QAction("Página por &defecto…", self)
        act_def_size.setShortcut(QKeySequence("F10"))
        act_def_size.setToolTip("Define el tamaño (mm) por defecto para proyectos nuevos y lo aplica al proyecto actual")
        act_def_size.triggered.connect(self._action_set_default_page_size)
        m_canvas.addAction(act_def_size)

        act_def_size_reset = QAction("Restaurar página por defecto (app)", self)
        act_def_size_reset.setStatusTip("Restaurar tamaño por defecto de la página y limpiar preferencia guardada")
        act_def_size_reset.triggered.connect(self._action_reset_default_page_size)
        m_canvas.addAction(act_def_size_reset)

        # Menú: Objeto (Z-order)
        m_obj = self.menuBar().addMenu("&Objeto")

        act_z_front = QAction("Traer al &frente", self)
        act_z_front.setShortcut(QKeySequence("Ctrl+Shift+]"))
        act_z_front.setToolTip("Traer la selección al frente (Z máximo + 1)")
        act_z_front.triggered.connect(self._canvas.z_bring_to_front)
        m_obj.addAction(act_z_front)

        act_z_back = QAction("Enviar al &fondo", self)
        act_z_back.setShortcut(QKeySequence("Ctrl+Shift+["))
        act_z_back.setToolTip("Enviar la selección al fondo (Z mínimo - n)")
        act_z_back.triggered.connect(self._canvas.z_send_to_back)
        m_obj.addAction(act_z_back)

        m_obj.addSeparator()

        act_z_up = QAction("&Subir un nivel", self)
        act_z_up.setShortcut(QKeySequence("Ctrl+]"))
        act_z_up.setToolTip("Sube 1 nivel en el apilado (swap mínimo)")
        act_z_up.triggered.connect(self._canvas.z_raise_one)
        m_obj.addAction(act_z_up)

        act_z_down = QAction("&Bajar un nivel", self)
        act_z_down.setShortcut(QKeySequence("Ctrl+["))
        act_z_down.setToolTip("Baja 1 nivel en el apilado (swap mínimo)")
        act_z_down.triggered.connect(self._canvas.z_lower_one)
        m_obj.addAction(act_z_down)

        m_obj.addSeparator()

        act_group = QAction("&Agrupar", self)
        act_group.setShortcut(QKeySequence("Ctrl+G"))
        act_group.setToolTip("Agrupa la selección actual")
        act_group.triggered.connect(self._canvas.group_selected)
        m_obj.addAction(act_group)

        act_ungroup = QAction("&Desagrupar", self)
        act_ungroup.setShortcut(QKeySequence("Ctrl+Shift+G"))
        act_ungroup.setToolTip("Desagrupa el grupo seleccionado")
        act_ungroup.triggered.connect(self._canvas.ungroup_selected)
        m_obj.addAction(act_ungroup)

        m_obj.addSeparator()

        act_reset_scale = QAction("Restaurar tamaño (1:1)", self)
        act_reset_scale.setShortcut(QKeySequence("Ctrl+1"))
        act_reset_scale.setToolTip("Resetea la escala de la selección a 1.0")
        act_reset_scale.triggered.connect(self._canvas.reset_selected_scale)
        m_obj.addAction(act_reset_scale)


        # Menú: Ver (tema del lienzo)
        m_view = self.menuBar().addMenu("&Ver")
        m_theme = m_view.addMenu("Tema del &lienzo")

        grp = QActionGroup(self)
        grp.setExclusive(True)

        # Orden fijo
        theme_items = [
            ("Oscuro", "dark"),
            ("Medio", "mid"),
            ("Claro", "light"),
        ]

        for label, tid in theme_items:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(tid == self._settings.canvas_theme)
            act.triggered.connect(lambda checked=False, _tid=tid: self._set_canvas_theme(_tid))
            grp.addAction(act)
            m_theme.addAction(act)

        # ---- Paneles
        m_view.addSeparator()
        m_panels = m_view.addMenu("&Paneles")

        act_toggle_lib = self._dock_library.toggleViewAction()
        act_toggle_lib.setText("&Biblioteca")
        m_panels.addAction(act_toggle_lib)

        act_toggle_obj = self._dock_objects.toggleViewAction()
        act_toggle_obj.setText("&Objetos")
        m_panels.addAction(act_toggle_obj)

        act_toggle_txt = self._dock_text.toggleViewAction()
        act_toggle_txt.setText("&Texto")
        m_panels.addAction(act_toggle_txt)

        # ---- Zoom
        m_view.addSeparator()

        act_zoom_in = QAction("Zoom &In", self)
        act_zoom_in.setShortcut(QKeySequence.ZoomIn)
        act_zoom_in.triggered.connect(self._canvas.zoom_in)
        m_view.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom &Out", self)
        act_zoom_out.setShortcut(QKeySequence.ZoomOut)
        act_zoom_out.triggered.connect(self._canvas.zoom_out)
        m_view.addAction(act_zoom_out)

        act_zoom_reset = QAction("Zoom &Reset", self)
        act_zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_zoom_reset.triggered.connect(self._canvas.zoom_reset)
        m_view.addAction(act_zoom_reset)

        # ---- Encuadre
        act_frame_sel = QAction("Encuadrar &selección", self)
        act_frame_sel.setShortcut(QKeySequence("F"))
        act_frame_sel.triggered.connect(self._action_frame_selection)
        m_view.addAction(act_frame_sel)

        act_frame_all = QAction("Encuadrar &todo", self)
        act_frame_all.setShortcut(QKeySequence("Shift+F"))
        act_frame_all.triggered.connect(self._action_frame_all)
        m_view.addAction(act_frame_all)

        act_view_sheet = QAction("&Ver hoja", self)
        act_view_sheet.setShortcut(QKeySequence("Ctrl+Shift+0"))
        act_view_sheet.triggered.connect(self._action_view_reset_to_sheet)
        m_view.addAction(act_view_sheet)

        m_view.addSeparator()

        act_start_view = QAction("Guardar vista de &inicio", self)
        act_start_view.setShortcut(QKeySequence("F11"))
        act_start_view.setToolTip("Guarda el centro+zoom actuales como vista de inicio")
        act_start_view.triggered.connect(self._action_save_start_view)
        m_view.addAction(act_start_view)

        act_start_view_reset = QAction("Restaurar vista de inicio", self)
        act_start_view_reset.setStatusTip("Quitar start_view guardado y volver al comportamiento por defecto")
        act_start_view_reset.triggered.connect(self._action_reset_start_view)
        m_view.addAction(act_start_view_reset)

        act_zoom_range = QAction("Rango de &zoom…", self)
        act_zoom_range.setShortcut(QKeySequence("F12"))
        act_zoom_range.setToolTip("Aumenta/recorta el rango mínimo y máximo de zoom")
        act_zoom_range.triggered.connect(self._action_zoom_range_menu)
        m_view.addAction(act_zoom_range)

        act_zoom_range_reset = QAction("Restaurar rango de zoom (×1.0)", self)
        act_zoom_range_reset.setStatusTip("Volver al rango de zoom por defecto")
        act_zoom_range_reset.triggered.connect(self._action_reset_zoom_range)
        m_view.addAction(act_zoom_range_reset)

        m_scroll = m_view.addMenu("Scroll del &lienzo")

        try:
            h_pol, v_pol = self._canvas.scrollbars_policy()
        except Exception:
            h_pol, v_pol = ("off", "off")

        def _mk_policy_submenu(parent, axis: str, current: str):
            title = "Horizontal" if axis == "h" else "Vertical"
            sm = parent.addMenu(title)
            grp = QActionGroup(self)
            grp.setExclusive(True)
            opts = [("OFF", "off"), ("Auto", "needed"), ("Siempre", "on")]
            for label, pol in opts:
                act = QAction(label, self)
                act.setCheckable(True)
                act.setChecked(current == pol)
                act.triggered.connect(lambda _checked=False, _axis=axis, _pol=pol: self._action_set_canvas_scroll_policy(_axis, _pol))
                grp.addAction(act)
                sm.addAction(act)
            return grp

        self._scroll_grp_h = _mk_policy_submenu(m_scroll, "h", h_pol)
        self._scroll_grp_v = _mk_policy_submenu(m_scroll, "v", v_pol)

        # ---- Preview (grosor)
        m_view.addSeparator()
        m_preview = m_view.addMenu("Vista previa")

        m_stroke = m_preview.addMenu("Grosor de línea")
        grp_stroke = QActionGroup(self)
        grp_stroke.setExclusive(True)
        for label, val in [("1 (fino)", 1), ("2 (normal)", 2), ("3 (grueso)", 3), ("4 (extra)", 4), ("5", 5), ("6", 6)]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(val == int(self._settings.canvas_stroke_thick))
            act.triggered.connect(lambda checked=False, _v=val: self._set_canvas_preview_style(stroke_thick=_v, outline_thick=None))
            grp_stroke.addAction(act)
            m_stroke.addAction(act)

        m_outline = m_preview.addMenu("Contorno / halo")
        grp_outline = QActionGroup(self)
        grp_outline.setExclusive(True)
        for label, val in [("0 (sin halo)", 0), ("1 (suave)", 1), ("2 (fuerte)", 2), ("3", 3)]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(val == int(self._settings.canvas_outline_thick))
            act.triggered.connect(lambda checked=False, _v=val: self._set_canvas_preview_style(stroke_thick=None, outline_thick=_v))
            grp_outline.addAction(act)
            m_outline.addAction(act)


    def _set_canvas_theme(self, theme_id: str) -> None:
        """Cambia el tema del lienzo y lo persiste en settings.json."""
        theme_id = (theme_id or "").strip().lower()
        self._settings.canvas_theme = theme_id
        self._settings.save()

        if hasattr(self._canvas, "set_theme"):
            self._canvas.set_theme(theme_id)

        label = {"dark": "Oscuro", "mid": "Medio", "light": "Claro"}.get(theme_id, theme_id)
        self._status(f"Tema del lienzo: {label}")

    def _set_canvas_preview_style(self, *, stroke_thick: int | None = None, outline_thick: int | None = None) -> None:
        """Cambia el estilo del preview del lienzo y lo persiste."""

        if stroke_thick is not None:
            self._settings.canvas_stroke_thick = int(stroke_thick)
        if outline_thick is not None:
            self._settings.canvas_outline_thick = int(outline_thick)

        self._settings.save()

        self._canvas.set_preview_style(
            stroke_thick=self._settings.canvas_stroke_thick,
            outline_thick=self._settings.canvas_outline_thick,
        )

        # Ajuste de escala: los niveles 1..6 se mapean a grosores reales con un factor global
        scale = 0.5
        try:
            scale = float(os.environ.get("RCS_CANVAS_PREVIEW_THICK_SCALE", "0.5"))
        except Exception:
            scale = 0.5
        scale = max(0.1, min(4.0, scale))
        eff_st = float(self._settings.canvas_stroke_thick) * scale
        eff_ot = float(self._settings.canvas_outline_thick) * scale

        self._status(
            f"Vista previa: línea {self._settings.canvas_stroke_thick} (≈{eff_st:g}px), contorno {self._settings.canvas_outline_thick} (≈{eff_ot:g}px)"
        )

    def _update_title(self) -> None:
        name = self._project.file_path.name if self._project.file_path else "Sin título"
        dirty = " *" if self._project.dirty else ""
        self.setWindowTitle("{} v{} — {}{}".format(APP_NAME, APP_VERSION, name, dirty))

    def _refresh_project(self) -> None:
        # CanvasView compat: algunos patches pueden dejar API incompleta; no crashear.
        if hasattr(self._canvas, "set_project") and callable(getattr(self._canvas, "set_project", None)):
            self._canvas.set_project(self._project)
        else:
            try:
                self._canvas._project = self._project
                fn = getattr(self._canvas, "_rebuild_scene_from_project", None)
                if callable(fn):
                    fn()
            except Exception:
                pass
        self._library.set_project(self._project)
        try:
            self._objects_panel.set_project(self._project)
        except Exception:
            pass
        self._update_title()

    # ----------------------------
    # Signals / slots
    # ----------------------------
    # ----------------------------
    # Compat helpers (MainWindow)
    # ----------------------------
    def set_project(self, project: Project) -> None:
        """Setea el proyecto actual y refresca UI (compat con patches previos)."""
        self._project = project
        self._refresh_project()

    def _refresh_title(self) -> None:
        """Alias de compatibilidad (algunos paths llamaban _refresh_title)."""
        self._update_title()

    def _on_project_modified(self, reason: str) -> None:
        # El Canvas ya marcó dirty. Solo refrescamos título/estado.
        self._update_title()
        if reason:
            self._status(reason)

        # Panel Objetos: refresco selectivo (evita repintar lista en drag/move).
        try:
            self._objects_panel.on_project_modified(reason)
        except Exception:
            pass

    def _on_asset_activated(self, rel_path: str) -> None:
        try:
            self._canvas.insert_svg_from_library(rel_path)
            self._status(f"Insertado: {rel_path}")
            self._update_title()
        except Exception as e:
            log.exception("Error al insertar SVG")
            QMessageBox.critical(self, "Error al insertar SVG", str(e))

    # ----------------------------
    # Actions
    # ----------------------------
    def action_new(self) -> None:
        if not self._maybe_save_before_discard():
            return
        self._project = Project()
        self._apply_default_canvas_mm_to_project(self._project)
        self._project.set_file_path(None)
        # Un proyecto nuevo aún no fue guardado => se considera “con trabajo pendiente”.
        self._project.mark_dirty("new")
        self._refresh_project()
        self._status("Proyecto nuevo")

    def action_open(self) -> None:
        """Importar/insertar un SVG externo como componente en el lienzo.

        Nota: esto NO descarta el proyecto actual; agrega un objeto nuevo.
        """
        if self._project is None:
            self.action_new()

        start_dir = str(Path.cwd())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar SVG",
            start_dir,
            "SVG (*.svg *.SVG *.svgz *.SVGZ);;Todos (*.*)",
        )
        if not path:
            return

        try:
            self._canvas.insert_svg_from_library(path)
            self._refresh_title()
        except Exception as e:
            log.exception("Error al importar SVG")
            QMessageBox.critical(self, "Error al importar SVG", str(e))

    def action_import_gmpr(self) -> None:
        """Importar (abrir) un proyecto GMPR y reconstruir el lienzo."""
        if not self._maybe_save_before_discard():
            return

        fp, _ = QFileDialog.getOpenFileName(
            self,
            "Importar proyecto GMPR",
            str(Path.cwd()),
            "GMPR (*.GMPR *.gmpr)",
        )
        if not fp:
            return

        try:
            bundle = load_gmpr_json(Path(fp))
            proj = gmpr_to_project(bundle, gmpr_path=Path(fp))
            self.set_project(proj)
            self._refresh_title()
            self._status(f"Importado GMPR: {Path(fp).name}")
        except Exception as e:
            log.exception("Error al importar GMPR")
            QMessageBox.critical(self, "Error al importar GMPR", str(e))

    def action_save(self) -> bool:
        if self._project.file_path is None:
            return self.action_save_as()
        try:
            p = save_gmpr_project(self._project, self._project.file_path)
            self._refresh_project()
            self._status("Guardado: {}".format(p.name))
            return True
        except Exception as e:
            log.exception("Error al guardar GMPR")
            QMessageBox.critical(self, "Error al guardar", str(e))
            return False

    def action_save_as(self) -> bool:
        start = str(self._project.file_path) if self._project.file_path else str(Path.cwd() / "proyecto.GMPR")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar proyecto GMPR",
            start,
            "Proyecto GMPR (*.GMPR *.gmpr)"
        )
        if not path:
            return False

        if not path.lower().endswith(".gmpr"):
            path = path + ".GMPR"

        try:
            p = save_gmpr_project(self._project, Path(path))
            self._refresh_project()
            self._status("Guardado: {}".format(p.name))
            return True
        except Exception as e:
            log.exception("Error al guardar GMPR (save as)")
            QMessageBox.critical(self, "Error al guardar", str(e))
            return False

    # ----------------------------
    # Close behavior
    # ----------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        if self._maybe_save_before_discard():
            # Persistimos UI state (aunque el proyecto no se guarde).
            self._persist_ui_state()
            event.accept()
        else:
            event.ignore()

    # ----------------------------
    # UI state persistente (layout)
    # ----------------------------
    def _restore_ui_state(self) -> None:
        """Restaura geometry/state del QMainWindow + splitter de la biblioteca."""
        try:
            # Main window geometry
            if self._settings.ui_main_geometry_b64:
                raw = base64.b64decode(self._settings.ui_main_geometry_b64.encode("ascii"), validate=False)
                self.restoreGeometry(raw)
            # Dock/toolbar state
            if self._settings.ui_main_state_b64:
                raw = base64.b64decode(self._settings.ui_main_state_b64.encode("ascii"), validate=False)
                self.restoreState(raw)
        except Exception:
            # No romper arranque
            pass

        # Splitter Biblioteca
        try:
            if getattr(self, "_library", None) is not None:
                self._library.restore_splitter_state_b64(self._settings.ui_library_splitter_b64)
        except Exception:
            pass

    def _persist_ui_state(self) -> None:
        """Captura geometry/state y lo guarda en AppSettings (base64)."""
        try:
            self._settings.ui_main_geometry_b64 = base64.b64encode(bytes(self.saveGeometry())).decode("ascii")
            self._settings.ui_main_state_b64 = base64.b64encode(bytes(self.saveState())).decode("ascii")
        except Exception:
            # No romper cierre
            pass

        # Splitter Biblioteca
        try:
            if getattr(self, "_library", None) is not None:
                self._settings.ui_library_splitter_b64 = self._library.save_splitter_state_b64()
        except Exception:
            pass

        # Persist settings
        try:
            self._settings.save()
        except Exception:
            pass

    def _maybe_save_before_discard(self) -> bool:
        """Si hay cambios, ofrece Guardar / Descartar / Cancelar."""
        if not self._project.dirty:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Cambios sin guardar")
        box.setText("El proyecto tiene cambios sin guardar.")
        box.setInformativeText("¿Querés guardar antes de continuar?")

        b_save = box.addButton("Guardar", QMessageBox.AcceptRole)
        b_discard = box.addButton("Descartar", QMessageBox.DestructiveRole)
        b_cancel = box.addButton("Cancelar", QMessageBox.RejectRole)
        box.setDefaultButton(b_save)

        box.exec()
        clicked = box.clickedButton()

        if clicked == b_cancel:
            return False
        if clicked == b_discard:
            return True
        if clicked == b_save:
            return bool(self.action_save())

        return False

    def _status(self, text: str) -> None:
        self._status_label.setText(text)
