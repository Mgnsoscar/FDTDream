from __future__ import annotations

import typing

from PyQt6.QtCore import pyqtSlot, QObject, QSettings
import matplotlib
from matplotlib import figure, text, axis, axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from .. import signals
from ...sharedCallbackHandlers import PlotSettingsCallbackHandler


class PlotController(QObject):

    _plotSettingsCallbackHandler: PlotSettingsCallbackHandler

    figure: matplotlib.figure.Figure
    ax: matplotlib.axes.Axes
    title: matplotlib.text.Text
    xlabel: matplotlib.text.Text
    ylabel: matplotlib.text.Text
    xaxis: matplotlib.axis.XAxis
    yaxis: matplotlib.axis.YAxis

    def __init__(self):
        super().__init__()

        # Init figure and artists
        self._initFigure()

        # Connect callbacks to artists
        self._plotSettingsCallbackHandler = PlotSettingsCallbackHandler(
            signals.canvasSignalBus.redrawRequested,
            self.title, signals.titleSignalBus,
            self.xlabel, signals.xlabelSignalBus,
            self.ylabel, signals.ylabelSignalBus,
            self.xaxis, signals.xticksSignalBus,
            self.yaxis, signals.yticksSignalBus
        )

        self._connectSignals()

    def _connectSignals(self) -> None:
        signals.canvasSignalBus.connectionRequested.connect(self._onCanvasConnectionRequested)
        signals.canvasSignalBus.sizeChanged.connect(self._onCanvasSizeChanged)

    def _initFigure(self) -> None:

        # Create the figure and ax.
        self.figure = matplotlib.figure.Figure()
        self.ax = self.figure.add_subplot(111)

        # Create references to the x and y axis
        self.xaxis = self.ax.xaxis
        self.yaxis = self.ax.yaxis

        # Fetch references to the title, x and y labels.
        self.title = self.ax.set_title("")
        self.xlabel = self.ax.set_xlabel("")
        self.ylabel = self.ax.set_ylabel("")

    @pyqtSlot(object)
    def _onCanvasConnectionRequested(self, canvas: FigureCanvasQTAgg) -> None:
        canvas.figure = self.figure
        signals.canvasSignalBus.redrawRequested.emit()

    @pyqtSlot(tuple)
    def _onCanvasSizeChanged(self, size: typing.Tuple[int, int]):
        #TODO Implement resize behaviour
        ...

    # region Plot settings callbacks

    # endregion
