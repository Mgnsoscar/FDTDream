from __future__ import annotations

from PyQt6.QtCore import pyqtSlot
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from ..signals import canvasSignalBus


class Canvas(FigureCanvasQTAgg):

    def __init__(self):
        super().__init__()

        # Request connection with figure/ax
        canvasSignalBus.connectionRequested.emit(self)

        # Connect the redraw method
        canvasSignalBus.redrawRequested.connect(self.draw_idle)

    @pyqtSlot()
    def draw_idle(self) -> None:
        for ax in self.figure.axes:
            ax.set_anchor("C")
        self.figure.tight_layout()
        super().draw_idle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        canvasSignalBus.sizeChanged.emit(self.get_width_height())

