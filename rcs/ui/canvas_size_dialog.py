# File: rcs/ui/canvas_size_dialog.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.0
# Status: wip
# Date: 2026-01-16
# Purpose: Diálogo para ajustar el tamaño del lienzo en mm.
# Notes: Actualiza Project.canvas_mm via CanvasView.set_canvas_mm().

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QDoubleSpinBox,
    QVBoxLayout,
)


class CanvasSizeDialog(QDialog):
    def __init__(self, w_mm: float, h_mm: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tamaño del lienzo (mm)")

        root = QVBoxLayout(self)
        form = QFormLayout()

        self._w = QDoubleSpinBox(self)
        self._w.setRange(1.0, 5000.0)
        self._w.setDecimals(2)
        self._w.setValue(float(w_mm))
        form.addRow("Ancho (mm)", self._w)

        self._h = QDoubleSpinBox(self)
        self._h.setRange(1.0, 5000.0)
        self._h.setDecimals(2)
        self._h.setValue(float(h_mm))
        form.addRow("Alto (mm)", self._h)

        root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def values(self) -> tuple[float, float]:
        return float(self._w.value()), float(self._h.value())
