from __future__ import annotations

import typing

from .shared import AutoSignalBusMeta, SignalProtocol, SignalProtocolNone
from .sharedModels import TextSettingsState, TicksSettingsState
from PyQt6.QtCore import QObject, pyqtSignal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from .dbPanel.signals import dbPanelSignalBus, dbRightClickMenuSignalBus


class TextSettingsSignalBus(QObject, metaclass=AutoSignalBusMeta):

    _initialStateRequested = pyqtSignal()
    initialStateRequested: SignalProtocolNone
    """Requests the intial state of the widgets in the text settings module."""

    _initialStateGranted = pyqtSignal(object)
    initialStateGranted: SignalProtocol[TextSettingsState]
    """Reply to the state request with the state as a typed dictionary."""

    _textChanged = pyqtSignal(str)
    textChanged: SignalProtocol[str]
    """Signal requesting new text."""

    _enabledChanged = pyqtSignal(bool)
    enabledChanged: SignalProtocol[bool]
    """Requests change of visibility."""

    _fontsizeChanged = pyqtSignal(int)
    fontsizeChanged: SignalProtocol[int]
    """Requests change of fontsize."""

    _fontChanged = pyqtSignal(str)
    fontChanged: SignalProtocol[str]
    """Requests change of font."""

    _fontColorChanged = pyqtSignal(str)
    fontColorChanged: SignalProtocol[str]
    """Requests change of font color."""

    _fontAlphaChanged = pyqtSignal(float)
    fontAlphaChanged: SignalProtocol[float]
    """Requests change of font opacity."""

    _fontColorPreviewRequested = pyqtSignal(str)
    fontColorPreviewRequested: SignalProtocol[str]
    """
    Requests a preview of the currently probed font color.
    """


class TickSettingsSignalBus(TextSettingsSignalBus, metaclass=AutoSignalBusMeta):

    _rotationChanged = pyqtSignal(float)
    rotationChanged: SignalProtocol[float]
    """Requests change of tick rotation."""


class LegendSettingsSignalBus(TextSettingsSignalBus, metaclass=AutoSignalBusMeta):

    _frameEnabledChanged = pyqtSignal(bool)
    _frameEnabledChanged: SignalProtocol[bool]
    """Requests change of legend frame visibility."""

    _frameFacecolorChanged = pyqtSignal(str)
    _frameFacecolorChanged: SignalProtocol[str]
    """Requests change of legend frame face color."""

    _frameFacecolorPreviewRequested = pyqtSignal(str)
    frameFacecolorPreviewRequested: SignalProtocol[str]
    """
    Requests a preview of a currently probed color for the legend frame face color.
    """

    _frameEdgecolorChanged = pyqtSignal(str)
    _frameEdgecolorChanged: SignalProtocol[str]
    """Requests change of legend frame edge color."""

    _frameEdgecolorPreviewRequested = pyqtSignal(str)
    frameEdgecolorPreviewRequested: SignalProtocol[str]
    """
    Requests a preview of a currently probed color for the legend frame edge. 
    """