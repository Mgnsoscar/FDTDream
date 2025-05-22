import PyQt6.QtWidgets as Qw
import PyQt6.QtCore as Qc
from ...sharedWidgets import PlotSettings
from .. import signals


class SettingsPanel(Qw.QTabWidget):

    def __init__(self):
        super().__init__()

        # Add the plot settings
        self.addTab(PlotSettings(
            titleSignalBus=signals.titleSignalBus,
            xlabelSignalBus=signals.xlabelSignalBus,
            ylabelSignalBus=signals.ylabelSignalBus,
            xticksSignalBus=signals.xticksSignalBus,
            yticksSignalBus=signals.yticksSignalBus
        ), "Plot Settings")
        print("hei2")
