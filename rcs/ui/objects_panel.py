# File: rcs/ui/objects_panel.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.25
# Status: beta
# Date: 2026-01-23
# Purpose: Panel "Objetos" (capas): lista de objetos + operaciones Z-order.
# Notes: Bloque 3J: capa mínima (lista + subir/bajar + menú contextual).

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from rcs.core.models import Project, SceneObject
from rcs.utils.log import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class _Row:
    oid: str
    z: int
    label: str


class ObjectsPanel(QWidget):
    """Panel de objetos/capas.

    - Lista ordenada por Z (arriba = frente).
    - Selección sincronizada con el canvas.
    - Botones + menú contextual para Z-order (front/back/up/down).
    """

    def __init__(self, canvas, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._project: Project | None = None
        self._sync_lock = False

        self._build_ui()
        self._wire()

    # ---------------------------
    # Public API
    # ---------------------------
    def set_project(self, project: Project | None) -> None:
        self._project = project
        self.refresh(reason="set_project")

    def refresh(self, *, reason: str = "") -> None:
        """Reconstruye la lista (preserva selección si puede)."""
        try:
            sel = set(self.selected_object_ids())
        except Exception:
            sel = set()

        rows = self._build_rows()

        self._sync_lock = True
        try:
            self._list.clear()
            for r in rows:
                it = QListWidgetItem(r.label)
                it.setData(Qt.UserRole, r.oid)
                self._list.addItem(it)
                if r.oid in sel:
                    it.setSelected(True)
        finally:
            self._sync_lock = False

        self._update_hint()
        self._update_buttons_enabled()

        if reason:
            log.debug("ObjectsPanel.refresh: %s (%d items)", reason, len(rows))

    def on_project_modified(self, reason: str) -> None:
        """Hook para el MainWindow: refrescar solo cuando aporta."""
        # Evitar refrescar en loops de drag/move: es caro y no cambia el orden.
        if not reason:
            return
        if reason.startswith("Z:"):
            self.refresh(reason="z")
            return
        if reason.startswith("Agrupado:") or reason.startswith("Desagrupado:"):
            self.refresh(reason="group")
            return
        if reason in {"insert", "delete", "paste", "insert_missing"}:
            self.refresh(reason=reason)
            return

    def selected_object_ids(self) -> list[str]:
        out: list[str] = []
        for it in self._list.selectedItems():
            oid = it.data(Qt.UserRole)
            if oid:
                out.append(str(oid))
        return out

    # ---------------------------
    # UI
    # ---------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self._title = QLabel("Objetos")
        self._title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Botonera compacta (capas)
        self._btn_front = QToolButton(self)
        self._btn_front.setText("↟")
        self._btn_front.setToolTip("Traer al frente")
        self._btn_front.setAutoRaise(True)

        self._btn_back = QToolButton(self)
        self._btn_back.setText("↡")
        self._btn_back.setToolTip("Enviar al fondo")
        self._btn_back.setAutoRaise(True)

        self._btn_up = QToolButton(self)
        self._btn_up.setText("↑")
        self._btn_up.setToolTip("Subir un nivel")
        self._btn_up.setAutoRaise(True)

        self._btn_down = QToolButton(self)
        self._btn_down.setText("↓")
        self._btn_down.setToolTip("Bajar un nivel")
        self._btn_down.setAutoRaise(True)

        self._btn_reset_scale = QToolButton(self)
        self._btn_reset_scale.setText("1:1")
        self._btn_reset_scale.setToolTip("Restaurar tamaño (escala 1:1)")
        self._btn_reset_scale.setAutoRaise(True)

        self._btn_group = QToolButton(self)
        self._btn_group.setText("G")
        self._btn_group.setToolTip("Agrupar selección")
        self._btn_group.setAutoRaise(True)

        self._btn_ungroup = QToolButton(self)
        self._btn_ungroup.setText("U")
        self._btn_ungroup.setToolTip("Desagrupar (grupo completo)")
        self._btn_ungroup.setAutoRaise(True)

        header.addWidget(self._title)
        header.addWidget(self._btn_front)
        header.addWidget(self._btn_back)
        header.addWidget(self._btn_up)
        header.addWidget(self._btn_down)
        header.addWidget(self._btn_reset_scale)
        header.addWidget(self._btn_group)
        header.addWidget(self._btn_ungroup)
        root.addLayout(header)

        self._hint = QLabel("Arriba = frente (Z mayor)")
        self._hint.setStyleSheet("color: #666;")
        root.addWidget(self._hint)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._list.setAlternatingRowColors(True)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        root.addWidget(self._list, 1)

    def _wire(self) -> None:
        # Lista → canvas
        self._list.itemSelectionChanged.connect(self._on_list_selection_changed)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemDoubleClicked.connect(self._on_double_click)

        # Canvas → lista
        try:
            scn = self._canvas.scene()
            if scn is not None:
                scn.selectionChanged.connect(self._on_canvas_selection_changed)
        except Exception:
            pass

        # Botones
        self._btn_front.clicked.connect(self._act_front)
        self._btn_back.clicked.connect(self._act_back)
        self._btn_up.clicked.connect(self._act_up)
        self._btn_down.clicked.connect(self._act_down)
        self._btn_reset_scale.clicked.connect(self._act_reset_scale)
        self._btn_group.clicked.connect(self._act_group)
        self._btn_ungroup.clicked.connect(self._act_ungroup)

    

    def _act_reset_scale(self) -> None:
        try:
            self._canvas.reset_selected_scale()
        except Exception:
            pass

    def _act_group(self) -> None:
        try:
            self._canvas.group_selected()
        except Exception:
            pass

    def _act_ungroup(self) -> None:
        try:
            self._canvas.ungroup_selected()
        except Exception:
            pass

    # ---------------------------
    # Data
    # ---------------------------
    def _build_rows(self) -> list[_Row]:
        p = self._project
        if not p:
            return []

        idx = {o.id: i for i, o in enumerate(p.objects)}
        objs = list(p.objects)
        objs.sort(key=lambda o: (int(o.z), idx.get(o.id, 0)))

        # Mostrar "arriba=frente": z mayor primero
        out: list[_Row] = []
        for o in reversed(objs):
            out.append(_Row(oid=o.id, z=int(o.z), label=self._fmt(o)))
        return out

    def _fmt(self, o: SceneObject) -> str:
        # Nombre amigable
        label = ""
        if o.type == "svg" and o.source:
            try:
                label = Path(o.source).name
            except Exception:
                label = str(o.source)
        elif o.type == "text":
            label = "Texto"
            try:
                if o.text_payload and o.text_payload.text:
                    t = str(o.text_payload.text).strip().replace("\n", " ")
                    if t:
                        label = f"Texto: {t[:18]}" + ("…" if len(t) > 18 else "")
            except Exception:
                pass
        else:
            label = o.type

        # Compacto: Z + label + id
        return f"Z={int(o.z):>4}  {label}  ({o.id})"

    # ---------------------------
    # Sync: selection
    # ---------------------------
    def _on_canvas_selection_changed(self) -> None:
        if self._sync_lock:
            return
        try:
            ids = set(self._canvas.selected_object_ids())
        except Exception:
            ids = set()
        self._sync_lock = True
        try:
            for i in range(self._list.count()):
                it = self._list.item(i)
                oid = str(it.data(Qt.UserRole))
                it.setSelected(oid in ids)
        finally:
            self._sync_lock = False
        self._update_buttons_enabled()

    def _on_list_selection_changed(self) -> None:
        if self._sync_lock:
            return
        ids = self.selected_object_ids()
        self._sync_lock = True
        try:
            self._select_in_canvas(ids)
        finally:
            self._sync_lock = False
        self._update_buttons_enabled()

    def _select_in_canvas(self, ids: list[str]) -> None:
        try:
            scn = self._canvas.scene()
            if scn is None:
                return
            scn.clearSelection()
            items = getattr(self._canvas, "_items", {})
            for oid in ids:
                it = items.get(oid)
                if it:
                    it.setSelected(True)
        except Exception:
            pass

    # ---------------------------
    # Actions
    # ---------------------------
    def _act_front(self) -> None:
        try:
            self._canvas.z_bring_to_front()
        finally:
            self.refresh(reason="front")

    def _act_back(self) -> None:
        try:
            self._canvas.z_send_to_back()
        finally:
            self.refresh(reason="back")

    def _act_up(self) -> None:
        try:
            self._canvas.z_raise_one()
        finally:
            self.refresh(reason="up")

    def _act_down(self) -> None:
        try:
            self._canvas.z_lower_one()
        finally:
            self.refresh(reason="down")

    # ---------------------------
    # Context menu
    # ---------------------------
    def _on_context_menu(self, pos: QPoint) -> None:
        it = self._list.itemAt(pos)
        if it is not None and not it.isSelected():
            # Comportamiento típico: click derecho selecciona el item.
            self._sync_lock = True
            try:
                self._list.clearSelection()
                it.setSelected(True)
            finally:
                self._sync_lock = False
            self._on_list_selection_changed()

        if not self.selected_object_ids():
            return

        menu = QMenu(self)
        a_front = QAction("Traer al frente", self)
        a_back = QAction("Enviar al fondo", self)
        a_up = QAction("Subir un nivel", self)
        a_down = QAction("Bajar un nivel", self)

        a_front.triggered.connect(self._act_front)
        a_back.triggered.connect(self._act_back)
        a_up.triggered.connect(self._act_up)
        a_down.triggered.connect(self._act_down)

        menu.addAction(a_front)
        menu.addAction(a_back)
        menu.addSeparator()
        menu.addAction(a_up)
        menu.addAction(a_down)

        menu.addSeparator()
        a_group = QAction("Agrupar", self)
        a_ungroup = QAction("Desagrupar", self)
        a_group.setEnabled(bool(getattr(self._canvas, 'can_group_selection', lambda: False)()))
        a_ungroup.setEnabled(bool(getattr(self._canvas, 'can_ungroup_selection', lambda: False)()))
        a_group.triggered.connect(self._act_group)
        a_ungroup.triggered.connect(self._act_ungroup)
        menu.addAction(a_group)
        menu.addAction(a_ungroup)

        menu.addSeparator()
        a_reset = QAction("Restaurar tamaño (1:1)", self)
        try:
            a_reset.setEnabled(bool(self._canvas.can_reset_scale_selection()))
        except Exception:
            a_reset.setEnabled(True)
        a_reset.triggered.connect(self._act_reset_scale)
        menu.addAction(a_reset)

        try:
            menu.exec(self._list.mapToGlobal(pos))
        except Exception:
            pass

    def _on_double_click(self, it: QListWidgetItem) -> None:
        # UX: doble click → encuadrar selección.
        try:
            self._canvas.frame_selection()
        except Exception:
            pass

    # ---------------------------
    # UX
    # ---------------------------
    def _update_hint(self) -> None:
        try:
            n = self._list.count()
            self._title.setText(f"Objetos ({n})")
        except Exception:
            pass

    def _update_buttons_enabled(self) -> None:
        has_sel = False
        try:
            has_sel = len(self.selected_object_ids()) > 0
        except Exception:
            has_sel = False
        for b in (self._btn_front, self._btn_back, self._btn_up, self._btn_down):
            try:
                b.setEnabled(bool(has_sel))
            except Exception:
                pass

        # Reset escala: solo si hace falta (algún item con escala != 1).
        try:
            self._btn_reset_scale.setEnabled(bool(self._canvas.can_reset_scale_selection()))
        except Exception:
            self._btn_reset_scale.setEnabled(bool(has_sel))

        # Grupo / desgrupo (coherente con el canvas).
        try:
            self._btn_group.setEnabled(bool(self._canvas.can_group_selection()))
        except Exception:
            self._btn_group.setEnabled(bool(has_sel))
        try:
            self._btn_ungroup.setEnabled(bool(self._canvas.can_ungroup_selection()))
        except Exception:
            self._btn_ungroup.setEnabled(bool(has_sel))
