# File: rcs/ui/image_size_dialog.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.10.2.45
# Date: 2026-01-24
# Purpose: Diálogo para ajustar tamaño de imagen/objeto en mm.

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QDoubleSpinBox,
    QVBoxLayout,
    QCheckBox,
)


class ImageSizeDialog(QDialog):
    def __init__(self, w_mm: float, h_mm: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajustar tamaño de imagen (mm)")

        self._ratio = float(h_mm) / float(w_mm) if float(w_mm) > 0 else 1.0
        self._lock = False
        self._last = "w"  # "w" o "h"

        root = QVBoxLayout(self)
        form = QFormLayout()

        self._w = QDoubleSpinBox(self)
        self._w.setRange(0.1, 5000.0)
        self._w.setDecimals(2)
        self._w.setValue(float(w_mm))
        self._w.valueChanged.connect(self._on_w_changed)
        form.addRow("Ancho (mm)", self._w)

        self._h = QDoubleSpinBox(self)
        self._h.setRange(0.1, 5000.0)
        self._h.setDecimals(2)
        self._h.setValue(float(h_mm))
        self._h.valueChanged.connect(self._on_h_changed)
        form.addRow("Alto (mm)", self._h)

        self._keep = QCheckBox("Mantener relación de aspecto", self)
        self._keep.setChecked(True)
        form.addRow("", self._keep)

        root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_w_changed(self, v: float) -> None:
        if self._lock:
            return
        self._last = "w"
        if not self._keep.isChecked():
            # Si cambia w y keep está off, actualizamos ratio “implícito”.
            h = float(self._h.value())
            self._ratio = (h / v) if v > 0 else self._ratio
            return
        # Keep aspect: ajustar h según ratio
        self._lock = True
        try:
            self._h.setValue(float(v) * float(self._ratio))
        finally:
            self._lock = False

    def _on_h_changed(self, v: float) -> None:
        if self._lock:
            return
        self._last = "h"
        if not self._keep.isChecked():
            w = float(self._w.value())
            self._ratio = (v / w) if w > 0 else self._ratio
            return
        # Keep aspect: ajustar w según ratio
        self._lock = True
        try:
            if float(self._ratio) != 0:
                self._w.setValue(float(v) / float(self._ratio))
        finally:
            self._lock = False

    def values(self) -> tuple[float, float, bool]:
        return float(self._w.value()), float(self._h.value()), bool(self._keep.isChecked())
