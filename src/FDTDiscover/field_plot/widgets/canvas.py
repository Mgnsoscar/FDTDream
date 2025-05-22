from __future__ import annotations

from PyQt6.QtCore import pyqtSlot
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from ...signal_busses import CANVAS_SIGNAL_BUS


class Canvas(FigureCanvasQTAgg):

    def __init__(self):
        super().__init__()

        # Connect signals and request a connection to the figure held in the controller.
        self.initialize_connections()
        CANVAS_SIGNAL_BUS.connection_requested.emit(self)

    def initialize_connections(self) -> None:
        """Connect signals from the signal bus to methods in this class."""
        CANVAS_SIGNAL_BUS.redraw_requested.connect(self.draw_idle)

    @pyqtSlot()
    def draw_idle(self) -> None:
        self.ax.set_anchor("C")
        self.figure.tight_layout()
        super().draw_idle()
