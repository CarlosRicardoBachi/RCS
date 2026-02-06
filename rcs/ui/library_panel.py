# File: rcs/ui/library_panel.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.40
# Status: hotfix
# Date: 2026-01-16
# Purpose: Panel Biblioteca: buscador + árbol de componentes + miniaturas.
# Notes: Render de miniaturas en hilo UI, sin loops de selección. No romper funcionalidades probadas.
from __future__ import annotations

import base64
import contextlib
import logging
from pathlib import Path
from typing import Optional, Iterator

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QLabel, QSplitter, QToolButton
)

from rcs.core.models import Project
from rcs.svg.thumbs import ThumbCache

log = logging.getLogger(__name__)


class LibraryPanel(QWidget):
    """Biblioteca de componentes.

    UI en una sola columna:
      1) Buscador (filtra árbol + miniaturas)
      2) Árbol (carpetas y archivos .svg)
      3) Miniaturas (archivos .svg del directorio seleccionado)

    Señal base:
      - asset_activated(rel_path): doble click en árbol o miniatura -> insertar en canvas.
    """

    asset_activated = Signal(str)

    # [RCS-KEEP] Señal pública y API base del panel.
    # No eliminar: otros módulos dependen de esto.

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._project: Optional[Project] = None
        self._root: Optional[Path] = None

        # Config thumb (más chico como pediste)
        self._thumb_size_px: int = 64
        self._thumb_cache = ThumbCache()

        # Estado / sincronización
        self._sync_depth: int = 0
        self._current_dir_rel: str = ""

        # Cola de render (UI thread)
        self._thumb_queue: list[str] = []  # rel_path svg (archivo)
        self._thumb_items_by_rel: dict[str, QListWidgetItem] = {}

        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.timeout.connect(self._process_thumb_queue)

        self._build_ui()

    # -----------------------------
    # Public API
    # -----------------------------
    def set_project(self, project: Project) -> None:
        self._project = project
        # Root de componentes: relativo al .RCS si aplica
        try:
            self._root = project.components_root_path(cwd=Path.cwd())
        except Exception:
            self._root = Path(project.components_root).resolve()
        self._rebuild_tree()

    # -----------------------------
    # UI State (splitter)
    # -----------------------------
    def save_splitter_state_b64(self) -> str:
        """Devuelve el estado del splitter (bytes) codificado en base64.

        Nota: Esto permite persistir el alto relativo entre Árbol y Miniaturas
        sin acoplar settings a Qt.
        """
        try:
            if not hasattr(self, "_splitter") or self._splitter is None:
                return ""
            b = bytes(self._splitter.saveState())
            return base64.b64encode(b).decode("ascii")
        except Exception:
            return ""

    def restore_splitter_state_b64(self, b64: str) -> bool:
        try:
            if not b64:
                return False
            if not hasattr(self, "_splitter") or self._splitter is None:
                return False
            raw = base64.b64decode(b64.encode("ascii"), validate=False)
            return bool(self._splitter.restoreState(raw))
        except Exception:
            return False

    # -----------------------------
    # UI
    # -----------------------------
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        title = QLabel("Biblioteca")
        title.setObjectName("lbl_library_title")

        self._btn_refresh = QToolButton(self)
        self._btn_refresh.setText("🔄")
        self._btn_refresh.setToolTip("Refrescar biblioteca (re-escanea carpetas y SVG)")
        self._btn_refresh.setAutoRaise(True)
        self._btn_refresh.clicked.connect(self._on_refresh_clicked)

        header.addWidget(title, 1)
        header.addWidget(self._btn_refresh, 0)
        lay.addLayout(header)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Buscar…")
        self._search.textChanged.connect(self._on_search_changed)
        lay.addWidget(self._search)

        self._tree = QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.setUniformRowHeights(True)
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        # Enter/Return o doble click
        self._tree.itemActivated.connect(self._on_tree_activated)
        self._thumbs = QListWidget(self)
        self._thumbs.setViewMode(QListWidget.IconMode)
        self._thumbs.setMovement(QListWidget.Static)
        self._thumbs.setResizeMode(QListWidget.Adjust)
        self._thumbs.setIconSize(QSize(self._thumb_size_px, self._thumb_size_px))
        self._thumbs.setSpacing(6)
        self._thumbs.setWordWrap(True)
        self._thumbs.itemSelectionChanged.connect(self._on_thumbs_selection_changed)
        # Enter/Return o doble click
        self._thumbs.itemActivated.connect(self._on_thumbs_activated)
        self._thumbs.setMinimumHeight(120)  # visible pero compacta

        # Splitter vertical: permite “tensar” alto de árbol vs miniaturas.
        self._splitter = QSplitter(Qt.Vertical, self)
        self._splitter.setObjectName("splitter_library")
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._tree)
        self._splitter.addWidget(self._thumbs)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)
        lay.addWidget(self._splitter, 1)

    # -----------------------------
    # Sync helpers
    # -----------------------------
    @contextlib.contextmanager
    def _syncing(self) -> Iterator[None]:
        self._sync_depth += 1
        try:
            yield
        finally:
            self._sync_depth -= 1

    def _is_syncing(self) -> bool:
        return self._sync_depth > 0

    @contextlib.contextmanager
    def _blocked(self, *widgets: QWidget) -> Iterator[None]:
        blockers = []
        try:
            from PySide6.QtCore import QSignalBlocker
            blockers = [QSignalBlocker(w) for w in widgets]
        except Exception:
            blockers = []
        try:
            yield
        finally:
            blockers.clear()

    
    # -----------------------------
    # Refresh (UI)
    # -----------------------------
    def _on_refresh_clicked(self) -> None:
        """Refresca el filesystem de componentes y re-renderiza thumbs.

        Best-effort: intenta mantener carpeta/archivo seleccionado.
        """
        prev_dir = self._current_dir_rel
        prev_file: Optional[str] = None

        try:
            tsel = self._tree.selectedItems()
            if tsel:
                kind = tsel[0].data(0, Qt.UserRole + 1)
                rel = tsel[0].data(0, Qt.UserRole)
                if isinstance(rel, str) and kind == "file":
                    prev_file = rel
                    prev_dir = str(Path(rel).parent).replace("\\", "/")
                    if prev_dir == ".":
                        prev_dir = ""
                elif isinstance(rel, str) and kind == "dir":
                    prev_dir = rel.replace("\\", "/").strip("/")
        except Exception:
            pass

        self._rebuild_tree()

        with self._syncing():
            if prev_file:
                self._select_tree_file(prev_file)
                self._load_folder(prev_dir, force=True)
                self._select_thumb(prev_file)
            else:
                if prev_dir:
                    self._select_tree_dir(prev_dir)
                self._load_folder(prev_dir, force=True)

        self._apply_filter(self._search.text())

    def _select_tree_dir(self, rel_dir: str) -> None:
        """Selecciona un nodo de tipo 'dir' por rel path (UserRole)."""
        rel_dir = (rel_dir or "").replace("\\", "/").strip("/")

        def walk(node: QTreeWidgetItem) -> Optional[QTreeWidgetItem]:
            if node.data(0, Qt.UserRole + 1) == "dir":
                rel = node.data(0, Qt.UserRole)
                if isinstance(rel, str) and rel.replace("\\", "/").strip("/") == rel_dir:
                    return node
            for i in range(node.childCount()):
                res = walk(node.child(i))
                if res:
                    return res
            return None

        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            found = walk(top)
            if found:
                p = found.parent()
                while p:
                    p.setExpanded(True)
                    p = p.parent()
                with self._blocked(self._tree):
                    self._tree.setCurrentItem(found)
                return
# -----------------------------
    # Tree build
    # -----------------------------
    def _rebuild_tree(self) -> None:
        root = self._root
        with self._syncing(), self._blocked(self._tree, self._thumbs):
            self._tree.clear()
            self._thumbs.clear()
            self._thumb_queue.clear()
            self._thumb_items_by_rel.clear()
            self._thumb_timer.stop()
            self._current_dir_rel = ""

            if not root or not root.exists():
                log.warning("components_root no existe: %s", root)
                return

            top = QTreeWidgetItem(["componentes"])
            top.setData(0, Qt.UserRole, "")  # rel dir
            top.setData(0, Qt.UserRole + 1, "dir")
            top.setExpanded(True)
            self._tree.addTopLevelItem(top)

            self._add_dir_nodes(top, root, rel_base="")

            self._tree.setCurrentItem(top)

    def _add_dir_nodes(self, parent_item: QTreeWidgetItem, abs_dir: Path, rel_base: str) -> None:
        # Directorios primero
        try:
            dirs = sorted([p for p in abs_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
        except Exception:
            log.exception("No se pudo listar carpetas: %s", abs_dir)
            dirs = []

        for d in dirs:
            rel_dir = str(Path(rel_base) / d.name) if rel_base else d.name
            it = QTreeWidgetItem([d.name])
            it.setData(0, Qt.UserRole, rel_dir)
            it.setData(0, Qt.UserRole + 1, "dir")
            parent_item.addChild(it)
            self._add_dir_nodes(it, d, rel_dir)

        # Archivos .svg como hojas (dentro del dir)
        try:
            svgs = sorted(
                [p for p in abs_dir.iterdir() if p.is_file() and p.suffix.lower() == ".svg"],
                key=lambda p: p.name.lower(),
            )
        except Exception:
            log.exception("No se pudo listar SVGs: %s", abs_dir)
            svgs = []

        for f in svgs:
            rel_file = str(Path(rel_base) / f.name) if rel_base else f.name
            itf = QTreeWidgetItem([f.name])
            itf.setData(0, Qt.UserRole, rel_file)
            itf.setData(0, Qt.UserRole + 1, "file")
            parent_item.addChild(itf)

    # -----------------------------
    # Tree handlers
    # -----------------------------
    def _on_tree_selection_changed(self) -> None:
        if self._is_syncing():
            return
        items = self._tree.selectedItems()
        if not items:
            return

        it = items[0]
        kind = it.data(0, Qt.UserRole + 1)
        rel = it.data(0, Qt.UserRole)

        if not isinstance(rel, str):
            return

        # Si selecciona archivo: mostrar carpeta y seleccionar miniatura
        if kind == "file":
            rel_dir = str(Path(rel).parent).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""
            with self._syncing():
                self._load_folder(rel_dir)
                self._select_thumb(rel)
            return

        # Si selecciona carpeta: cargar miniaturas de esa carpeta
        if kind == "dir":
            with self._syncing():
                self._load_folder(rel)
            return

    def _on_tree_activated(self, item: QTreeWidgetItem, column: int) -> None:
        """Activación por Enter/Return o doble click."""
        self._on_tree_double_clicked(item, column)

    def _on_thumbs_activated(self, item: QListWidgetItem) -> None:
        """Activación por Enter/Return o doble click."""
        self._on_thumbs_double_clicked(item)

    def _on_tree_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        kind = item.data(0, Qt.UserRole + 1)
        rel = item.data(0, Qt.UserRole)
        if kind == "file" and isinstance(rel, str):
            self.asset_activated.emit(rel)

    # -----------------------------
    # Folder -> thumbs
    # -----------------------------
    def _load_folder(self, rel_dir: str, *, force: bool = False) -> None:
        root = self._root
        if not root:
            return

        rel_dir = rel_dir.replace("\\", "/").strip("/")
        if (rel_dir == self._current_dir_rel) and (not force):
            return

        abs_dir = (root / Path(rel_dir)).resolve()

        with self._blocked(self._thumbs):
            self._current_dir_rel = rel_dir
            self._thumbs.clear()
            self._thumb_items_by_rel.clear()
            self._thumb_queue.clear()
            self._thumb_timer.stop()

            if not abs_dir.exists() or not abs_dir.is_dir():
                return

            try:
                svgs = sorted(
                    [p for p in abs_dir.iterdir() if p.is_file() and p.suffix.lower() == ".svg"],
                    key=lambda p: p.name.lower(),
                )
            except Exception:
                log.exception("No se pudo listar SVGs en: %s", abs_dir)
                svgs = []

            # Creamos items primero (rápido), luego render en cola
            q = self._search.text().strip().lower()
            for p in svgs:
                rel_file = str(Path(rel_dir) / p.name) if rel_dir else p.name
                if q and q not in p.name.lower():
                    continue

                item = QListWidgetItem(p.stem)
                item.setData(Qt.UserRole, rel_file)

                # icon placeholder por ahora
                item.setIcon(self._thumb_cache.placeholder_icon(self._thumb_size_px))

                self._thumbs.addItem(item)
                self._thumb_items_by_rel[rel_file] = item
                self._thumb_queue.append(rel_file)

            # Arrancar cola render
            if self._thumb_queue:
                self._thumb_timer.start(0)

    def _process_thumb_queue(self) -> None:
        # Procesa pocos por tick para mantener UI fluida.
        root = self._root
        if not root or not self._thumb_queue:
            return

        per_tick = 4
        processed = 0

        while self._thumb_queue and processed < per_tick:
            rel_file = self._thumb_queue.pop(0)
            item = self._thumb_items_by_rel.get(rel_file)
            if not item:
                continue

            abs_path = (root / Path(rel_file)).resolve()
            try:
                icon = self._thumb_cache.icon_for(abs_path, self._thumb_size_px)
                item.setIcon(icon)
            except Exception:
                log.exception("Thumb failed: %s", abs_path)
            processed += 1

        if self._thumb_queue:
            self._thumb_timer.start(0)

    # -----------------------------
    # Thumb handlers
    # -----------------------------
    def _on_thumbs_selection_changed(self) -> None:
        if self._is_syncing():
            return
        items = self._thumbs.selectedItems()
        if not items:
            return
        rel = items[0].data(Qt.UserRole)
        if not rel or not isinstance(rel, str):
            return

        # Selección en thumbs -> reflejar en árbol (archivo)
        with self._syncing():
            self._select_tree_file(rel)

    def _on_thumbs_double_clicked(self, item: QListWidgetItem) -> None:
        rel = item.data(Qt.UserRole)
        if rel and isinstance(rel, str):
            self.asset_activated.emit(rel)

    # -----------------------------
    # Selection utils
    # -----------------------------
    def _select_thumb(self, rel_file: str) -> None:
        it = self._thumb_items_by_rel.get(rel_file)
        if not it:
            return
        with self._blocked(self._thumbs):
            self._thumbs.setCurrentItem(it)

    def _select_tree_file(self, rel_file: str) -> None:
        # Busca un item en el árbol con rel_file (UserRole) y lo selecciona.
        def walk(node: QTreeWidgetItem) -> Optional[QTreeWidgetItem]:
            if node.data(0, Qt.UserRole + 1) == "file" and node.data(0, Qt.UserRole) == rel_file:
                return node
            for i in range(node.childCount()):
                res = walk(node.child(i))
                if res:
                    return res
            return None

        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            found = walk(top)
            if found:
                # expand parents
                p = found.parent()
                while p:
                    p.setExpanded(True)
                    p = p.parent()
                with self._blocked(self._tree):
                    self._tree.setCurrentItem(found)
                return

    # -----------------------------
    # Filter
    # -----------------------------
    def _on_search_changed(self, text: str) -> None:
        self._apply_filter(text)

    def _apply_filter(self, text: str) -> None:
        q = text.strip().lower()

        # Filtra árbol: oculta nodos no coincidentes y sin hijos visibles.
        def filter_item(item: QTreeWidgetItem) -> bool:
            label = (item.text(0) or "").lower()
            kind = item.data(0, Qt.UserRole + 1)

            match = (q in label) if q else True

            any_child_visible = False
            for j in range(item.childCount()):
                if filter_item(item.child(j)):
                    any_child_visible = True

            visible = match or any_child_visible
            item.setHidden(not visible)
            if visible and any_child_visible and kind != "file":
                item.setExpanded(True)
            return visible

        with self._syncing():
            for i in range(self._tree.topLevelItemCount()):
                filter_item(self._tree.topLevelItem(i))

            # Re-cargar thumbs del folder actual aplicando q
            self._load_folder(self._current_dir_rel, force=True)
