# File: rcs/ui/items/object_items.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.3.0
# Status: stable
# Date: 2026-01-16
# Purpose: Items movibles/seleccionables con snap opcional y commit al modelo (.RCS).
# Notes: Bloque 3A: mover + persistir x/y en el Project sin spamear cambios.

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem


class RcsMoveCommitMixin:
    """Mixin que define el contrato mínimo para commit de movimiento.

    Se usa para que el item no conozca detalles internos del modelo.
    """

    def rcs_snap_position(self, pos: QPointF) -> QPointF:  # pragma: no cover (UI)
        return pos

    def rcs_commit_move(self, object_id: str, pos: QPointF) -> None:  # pragma: no cover (UI)
        _ = (object_id, pos)
        return


class RcsSvgPixmapItem(QGraphicsPixmapItem):
    """Item para objetos SVG rasterizados (preview) con commit de movimiento."""

    def __init__(self, *args, object_id: str, owner: RcsMoveCommitMixin, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._object_id = str(object_id)
        self._owner = owner
        # Necesario para ItemPositionChange.
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):  # pragma: no cover (UI)
        if change == self.GraphicsItemChange.ItemPositionChange:
            try:
                if isinstance(value, QPointF):
                    return self._owner.rcs_snap_position(value)
            except Exception:
                return value
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event) -> None:  # pragma: no cover (UI)
        super().mouseReleaseEvent(event)
        try:
            self._owner.rcs_commit_move(self._object_id, self.pos())
        except Exception:
            # Nunca romper UI por un commit.
            return


class RcsUnsupportedRectItem(QGraphicsRectItem):
    """Item placeholder para SVG no soportado, pero movible/persistente."""

    def __init__(self, *args, object_id: str, owner: RcsMoveCommitMixin, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._object_id = str(object_id)
        self._owner = owner
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):  # pragma: no cover (UI)
        if change == self.GraphicsItemChange.ItemPositionChange:
            try:
                if isinstance(value, QPointF):
                    return self._owner.rcs_snap_position(value)
            except Exception:
                return value
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event) -> None:  # pragma: no cover (UI)
        super().mouseReleaseEvent(event)
        try:
            self._owner.rcs_commit_move(self._object_id, self.pos())
        except Exception:
            return
