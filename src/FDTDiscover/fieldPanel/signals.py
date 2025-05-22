import typing

from ..shared import AutoSignalBusMeta, SignalProtocol, SignalProtocolNone
from ..signal_busses import TextSettingsSignalBus, TickSettingsSignalBus
from PyQt6.QtCore import QObject, pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg


class CanvasSignalBus(QObject, metaclass=AutoSignalBusMeta):

    # region Recieved requests
    _redrawRequested = pyqtSignal()
    redrawRequested: SignalProtocolNone
    """Prompts the canvas to redraw."""
    # endregion

    # region Emitted requests
    _connectionRequested = pyqtSignal(object)
    connectionRequested: SignalProtocol[FigureCanvasQTAgg]
    """Requests the canvas to be connected to a figure/ax."""
    # endregion

    # region Canvas events
    _sizeChanged = pyqtSignal(tuple)
    sizeChanged: SignalProtocol[typing.Tuple[int, int]]
    """
    Emits a tuple of the width and height of the canvas in pixels. 
    NB! No need for redraw request, as this is always done right after the signal is emitted.
    """
    # endregion


canvasSignalBus: CanvasSignalBus = CanvasSignalBus()
titleSignalBus: TextSettingsSignalBus = TextSettingsSignalBus()
xlabelSignalBus: TextSettingsSignalBus = TextSettingsSignalBus()
ylabelSignalBus: TextSettingsSignalBus = TextSettingsSignalBus()
xticksSignalBus: TickSettingsSignalBus = TickSettingsSignalBus()
yticksSignalBus: TickSettingsSignalBus = TickSettingsSignalBus()


__all__ = [
    "canvasSignalBus", "titleSignalBus", "xlabelSignalBus", "ylabelSignalBus", "xticksSignalBus",
    "yticksSignalBus"
]
