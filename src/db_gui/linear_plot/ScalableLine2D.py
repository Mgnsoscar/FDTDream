from __future__ import annotations
from matplotlib.lines import Line2D
from typing import Optional, Self
import numpy as np
from numpy.typing import NDArray
from PyQt6.QtCore import pyqtSignal, QObject


class ScalableLine2D(Line2D, QObject):
    changed = pyqtSignal()
    removed = pyqtSignal()

    def __init__(self, xdata, ydata, *args, **kwargs):
        QObject.__init__(self)
        Line2D.__init__(self, xdata, ydata, *args, **kwargs)
        self.true_xdata = np.array(xdata)
        self.true_ydata = np.array(ydata)
        self.yscalar = 1.0
        self.post_scalar = 1.0  # ✅ New post-normalization scalar
        self.normalized_to: Optional[ScalableLine2D] = None
        self.subtract_from: Optional[ScalableLine2D] = None

    def apply_scalar_operation(
        self,
        yscalar: float = None,
        post_scalar: float = None,
        normalized_to: Optional[ScalableLine2D] = None,
        subtract_from: Optional[ScalableLine2D] = None
    ) -> None:

        if yscalar is not None:
            self.yscalar = yscalar
        if post_scalar is not None:
            self.post_scalar = post_scalar

        # Handle subtract_from connection
        if subtract_from is not self.subtract_from:
            if self.subtract_from is not None:
                try:
                    self.subtract_from.changed.disconnect(self._on_subtract_source_changed)
                    self.subtract_from.removed.disconnect(self._on_subtract_source_removed)
                except TypeError:
                    pass
            self.subtract_from = subtract_from
            if self.subtract_from is not None:
                self.subtract_from.changed.connect(self._on_subtract_source_changed)
                self.subtract_from.removed.connect(self._on_subtract_source_removed)

        # Handle normalization connection
        if normalized_to is not self.normalized_to:
            if self.normalized_to is not None:
                try:
                    self.normalized_to.changed.disconnect(self._on_normalized_source_changed)
                    self.normalized_to.removed.disconnect(self._on_normalized_source_removed)
                except TypeError:
                    pass
            self.normalized_to = normalized_to
            if self.normalized_to is not None:
                self.normalized_to.changed.connect(self._on_normalized_source_changed)
                self.normalized_to.removed.connect(self._on_normalized_source_removed)

        # Step 1: scale/divide
        y = self.true_ydata * self.yscalar

        # Step 2: subtract
        if self.subtract_from is not None:
            y -= self.subtract_from.get_ydata()

        # Step 3: normalize
        if self.normalized_to is not None:
            y /= self.normalized_to.get_ydata()

        # Step 4: post normalization scale
        y *= self.post_scalar

        self.set_ydata(y)
        self.changed.emit()

    # Signal handlers unchanged, but now call apply_scalar_operation() with full state
    def _on_normalized_source_changed(self) -> None:
        self.apply_scalar_operation(normalized_to=self.normalized_to)

    def _on_normalized_source_removed(self) -> None:
        if self.normalized_to is not None:
            try:
                self.normalized_to.changed.disconnect(self._on_normalized_source_changed)
                self.normalized_to.removed.disconnect(self._on_normalized_source_removed)
            except TypeError:
                pass
        self.normalized_to = None
        self.apply_scalar_operation()

    def _on_subtract_source_changed(self) -> None:
        self.apply_scalar_operation(subtract_from=self.subtract_from)

    def _on_subtract_source_removed(self) -> None:
        if self.subtract_from is not None:
            try:
                self.subtract_from.changed.disconnect(self._on_subtract_source_changed)
                self.subtract_from.removed.disconnect(self._on_subtract_source_removed)
            except TypeError:
                pass
        self.subtract_from = None
        self.apply_scalar_operation()

    def on_removed(self) -> None:
        self.removed.emit()

    @classmethod
    def from_Line2D(cls, line: Line2D) -> Self:
        new_line = cls(line.get_xdata(), line.get_ydata())
        new_line.update_from(line)
        new_line.set_transform(line.get_transform())
        if line.axes is not None:
            line.axes.add_line(new_line)
            line.remove()
        return new_line
