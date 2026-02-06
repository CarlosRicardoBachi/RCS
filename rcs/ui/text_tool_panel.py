# File: rcs/ui/text_tool_panel.py
# Project: RusticCreadorSvg (RCS)
# Status: WIP / placeholder (maquetado)
# Purpose: Panel/dock para crear texto (futuro Smart Text Object). Por ahora: UI + preview + meta.
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QCheckBox,
    QComboBox,
    QFrame,
)


@dataclass
class TextToolMeta:
    # Basico
    text: str = "TEXTO"
    font_family: str = "Arial"
    font_size_pt: int = 48
    bold: bool = True
    italic: bool = False
    # Avanzado (placeholder / metadatos)
    line_spacing: float = 1.0               # multiplicador (1.0 = default)
    mode: str = "normal"                    # normal | placa | continuado
    engrave_islands: bool = True            # continuado (default ON)
    outer_margin_mm: float = 2.0            # placa (solo metadatos + maqueta)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TextToolPanel(QWidget):
    insertRequested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TextToolPanel")
        self._build_ui()
        self._connect()
        self._refresh_preview()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        title = QLabel("Texto (placeholder)")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)

        # --- Texto ---
        row_text = QHBoxLayout()
        row_text.addWidget(QLabel("Texto:"))
        self.ed_text = QLineEdit("TEXTO")
        self.ed_text.setPlaceholderText("Escribí acá (multilínea con \n)")
        row_text.addWidget(self.ed_text, 1)
        root.addLayout(row_text)

        # --- Modo + flags ---
        row_mode = QHBoxLayout()
        row_mode.addWidget(QLabel("Modo:"))
        self.cb_mode = QComboBox()
        self.cb_mode.addItem("Normal", "normal")
        self.cb_mode.addItem("Placa", "placa")
        self.cb_mode.addItem("Continuado", "continuado")
        row_mode.addWidget(self.cb_mode, 1)

        self.chk_islands = QCheckBox("Islas como grabado (continuado)")
        self.chk_islands.setChecked(True)
        row_mode.addWidget(self.chk_islands)
        root.addLayout(row_mode)

        # --- Tipografia ---
        row_font = QHBoxLayout()
        row_font.addWidget(QLabel("Fuente:"))
        self.ed_family = QLineEdit("Arial")
        row_font.addWidget(self.ed_family, 1)

        row_font.addWidget(QLabel("Pt:"))
        self.sp_size = QSpinBox()
        self.sp_size.setRange(6, 300)
        self.sp_size.setValue(48)
        row_font.addWidget(self.sp_size)

        self.chk_bold = QCheckBox("Negrita")
        self.chk_bold.setChecked(True)
        row_font.addWidget(self.chk_bold)

        self.chk_italic = QCheckBox("Itálica")
        row_font.addWidget(self.chk_italic)
        root.addLayout(row_font)

        # --- Interlineado + placa ---
        row_adv = QHBoxLayout()
        row_adv.addWidget(QLabel("Interlineado:"))
        self.sp_line = QDoubleSpinBox()
        self.sp_line.setRange(0.5, 3.0)
        self.sp_line.setSingleStep(0.1)
        self.sp_line.setValue(1.0)
        row_adv.addWidget(self.sp_line)

        row_adv.addWidget(QLabel("Outer margin (mm):"))
        self.sp_outer_margin = QDoubleSpinBox()
        self.sp_outer_margin.setRange(0.0, 50.0)
        self.sp_outer_margin.setSingleStep(0.5)
        self.sp_outer_margin.setValue(2.0)
        row_adv.addWidget(self.sp_outer_margin)
        row_adv.addStretch(1)
        root.addLayout(row_adv)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep)

        # Preview
        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedHeight(140)
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet("background:#111; border:1px solid #333;")
        root.addWidget(self.lbl_preview)

        # Insert
        self.btn_insert = QPushButton("Insertar (WIP)")
        root.addWidget(self.btn_insert)

        root.addStretch(1)

        self._update_mode_visibility()

    def _connect(self) -> None:
        # preview refresh
        self.ed_text.textChanged.connect(self._refresh_preview)
        self.ed_family.textChanged.connect(self._refresh_preview)
        self.sp_size.valueChanged.connect(self._refresh_preview)
        self.chk_bold.toggled.connect(self._refresh_preview)
        self.chk_italic.toggled.connect(self._refresh_preview)
        self.sp_line.valueChanged.connect(self._refresh_preview)
        self.sp_outer_margin.valueChanged.connect(self._refresh_preview)
        self.cb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self.chk_islands.toggled.connect(self._refresh_preview)

        # emit
        self.btn_insert.clicked.connect(self._emit_insert)

    def _on_mode_changed(self) -> None:
        self._update_mode_visibility()
        self._refresh_preview()

    def _update_mode_visibility(self) -> None:
        mode = self.cb_mode.currentData()
        self.chk_islands.setEnabled(mode == "continuado")
        self.sp_outer_margin.setEnabled(mode == "placa")

    def _collect_meta(self) -> TextToolMeta:
        return TextToolMeta(
            text=self.ed_text.text() or "",
            font_family=(self.ed_family.text() or "Arial"),
            font_size_pt=int(self.sp_size.value()),
            bold=bool(self.chk_bold.isChecked()),
            italic=bool(self.chk_italic.isChecked()),
            line_spacing=float(self.sp_line.value()),
            mode=str(self.cb_mode.currentData() or "normal"),
            engrave_islands=bool(self.chk_islands.isChecked()),
            outer_margin_mm=float(self.sp_outer_margin.value()),
        )

    def _emit_insert(self) -> None:
        meta = self._collect_meta()
        self.insertRequested.emit(meta.to_dict())

    def _refresh_preview(self) -> None:
        meta = self._collect_meta()

        w, h = 420, 140
        pm = QPixmap(w, h)
        pm.fill(Qt.black)

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Placa (maqueta simple)
        margin_px = 0
        if meta.mode == "placa":
            # representación: 1mm ~ 2px (solo visual)
            margin_px = int(max(0.0, meta.outer_margin_mm) * 2.0)
            painter.setPen(Qt.gray)
            painter.drawRect(10, 10, w - 20, h - 20)
            painter.setPen(Qt.darkGray)
            painter.drawRect(10 + margin_px, 10 + margin_px, (w - 20) - 2 * margin_px, (h - 20) - 2 * margin_px)

        # Texto multilínea real
        f = QFont(meta.font_family, meta.font_size_pt)
        f.setBold(meta.bold)
        f.setItalic(meta.italic)

        lines = (meta.text or "").split("\n")
        if not lines:
            lines = [""]

        # Layout vertical manual con interlineado
        from PySide6.QtGui import QFontMetricsF
        fm = QFontMetricsF(f)
        line_h = float(fm.lineSpacing()) * float(meta.line_spacing)

        # Construir paths por línea, usando baseline acumulada
        paths: list[QPainterPath] = []
        y = 0.0
        for ln in lines:
            p = QPainterPath()
            # baseline: y + ascent
            p.addText(0, y + fm.ascent(), f, ln)
            paths.append(p)
            y += line_h

        # Unir y centrar bloque
        block = QPainterPath()
        for p in paths:
            block.addPath(p)

        br = block.boundingRect()

        # Área útil (si placa, respetar margen)
        x0, y0 = 0, 0
        x1, y1 = w, h
        if meta.mode == "placa":
            x0 = 10 + margin_px
            y0 = 10 + margin_px
            x1 = (w - 10) - margin_px
            y1 = (h - 10) - margin_px

        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        tx = cx - (br.x() + br.width() / 2.0)
        ty = cy - (br.y() + br.height() / 2.0)

        painter.translate(tx, ty)

        painter.setPen(Qt.white)
        painter.drawPath(block)

        painter.end()

        self.lbl_preview.setPixmap(pm)

