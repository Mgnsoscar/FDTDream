import PyQt6.QtWidgets as Qw
import PyQt6.QtCore as Qc
from .canvas import Canvas
from .settingsPanel import SettingsPanel


class FieldPanel(Qw.QSplitter):

    def __init__(self):
        super().__init__(Qc.Qt.Orientation.Horizontal)

        # Add the canvas
        self.addWidget(Canvas())

        # Add the settings panel
        self.addWidget(SettingsPanel())
