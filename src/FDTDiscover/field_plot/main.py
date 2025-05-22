from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from .controllers import CanvasController, SaveFigureController
from .widgets import Canvas, SaveFigureWidget, NavigationBar
from ..signal_busses import SAVE_FIGURE_SIGNAL_BUS


class FieldPlotTab(QWidget):

    canvas_controller: CanvasController
    canvas_widget: Canvas

    save_figure_controller: SaveFigureController
    _save_figure_widget: SaveFigureWidget

    navigation_bar: NavigationBar

    def __init__(self):
        super().__init__()

        # Initialize a layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Initialize the controllers
        self.canvas_controller = CanvasController()
        self.save_figure_controller = SaveFigureController()

        # Initialize the widgets
        self.canvas_widget = Canvas()
        self.navigation_bar = NavigationBar(self.canvas_widget)
        layout.addWidget(self.navigation_bar)
        layout.addWidget(self.canvas_widget, stretch=1)

        # Connect to signals
        self.initialize_connections()

    def initialize_connections(self) -> None:
        """Connect signals from the signal busses."""
        SAVE_FIGURE_SIGNAL_BUS.save_figure_dialog_requested.connect(self.on_save_dialog_requested)

    @pyqtSlot()
    def on_save_dialog_requested(self) -> None:
        """Opens the SaveFigureWidget when rewuested by the navigation bar."""
        SaveFigureWidget(self, self.canvas_controller.fig)
