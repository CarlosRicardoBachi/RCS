# File: rcs/ui/canvas_container.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.0
# Status: wip
# Date: 2026-01-16
# Purpose: Contenedor del lienzo: CanvasView + barra inferior de zoom.
# Notes: La barra inferior controla el zoom del view (no escala de objeto).

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider

from rcs.ui.canvas_view import CanvasView


class CanvasContainer(QWidget):
    """Widget central: lienzo + slider de zoom inferior."""

    def __init__(self, canvas: CanvasView, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas = canvas

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)
        root.addWidget(self.canvas, 1)

        bar = QWidget(self)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(6, 0, 6, 0)
        bl.setSpacing(8)

        self._lbl = QLabel("Zoom", bar)
        self._lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        bl.addWidget(self._lbl, 0)

        self._slider = QSlider(Qt.Horizontal, bar)
        zmin, zmax = self.canvas.zoom_limits()
        self._slider.setRange(int(round(zmin * 100)), int(round(zmax * 100)))
        self._slider.setSingleStep(10)
        self._slider.setPageStep(50)
        self._slider.setValue(int(round(self.canvas.zoom_factor() * 100)))
        self._slider.valueChanged.connect(self._on_slider)
        bl.addWidget(self._slider, 1)

        self._pct = QLabel("100%", bar)
        self._pct.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self._pct.setMinimumWidth(60)
        bl.addWidget(self._pct, 0)

        root.addWidget(bar, 0)

        # Sync desde el canvas (rueda / menú)
        self.canvas.zoom_changed.connect(self._on_canvas_zoom)
        self.canvas.zoom_limits_changed.connect(self._on_canvas_zoom_limits)
        self._on_canvas_zoom(self.canvas.zoom_factor())

    def _on_canvas_zoom_limits(self, zmin: float, zmax: float) -> None:
        mn = max(1, int(round(float(zmin) * 100)))
        mx = max(mn + 1, int(round(float(zmax) * 100)))
        # Mantener valor actual dentro del rango.
        cur = int(self._slider.value())
        self._slider.blockSignals(True)
        self._slider.setRange(mn, mx)
        if cur < mn:
            self._slider.setValue(mn)
        elif cur > mx:
            self._slider.setValue(mx)
        self._slider.blockSignals(False)

    def _on_slider(self, v: int) -> None:
        zmin, zmax = self.canvas.zoom_limits()
        z = max(float(zmin), min(float(zmax), float(v) / 100.0))
        self.canvas.set_zoom_factor(z)
        self._pct.setText(f"{int(round(z * 100))}%")

    def _on_canvas_zoom(self, z: float) -> None:
        v = int(round(float(z) * 100.0))
        v = max(int(self._slider.minimum()), min(int(self._slider.maximum()), v))
        if self._slider.value() != v:
            self._slider.blockSignals(True)
            self._slider.setValue(v)
            self._slider.blockSignals(False)
        self._pct.setText(f"{int(round(float(z) * 100))}%")
