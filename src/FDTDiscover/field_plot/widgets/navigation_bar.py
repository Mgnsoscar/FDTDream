from __future__ import annotations

from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from ...signal_busses import SAVE_FIGURE_SIGNAL_BUS


class NavigationBar(NavigationToolbar2QT):

    def __init__(self, canvas: FigureCanvasQTAgg):
        super().__init__(canvas)

    def save_figure(self) -> None:
        """Emmits a request to open the SaveFigureWidget to the SaveFigureController."""
        SAVE_FIGURE_SIGNAL_BUS.save_figure_dialog_requested.emit()

