from __future__ import annotations

from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
import PyQt6.QtWidgets as Qw
from .signal_busses import dbRightClickMenuSignalBus
from .dbPanel import DatabasePanel
from .fieldPanel import FieldPanel


class Application(Qw.QMainWindow):

    menu_bar: MenuBar
    splitter: Qw.QSplitter
    database_panel: DatabasePanel
    fieldPanel: FieldPanel
    # field_plot_tab: FieldPlotTab

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize empty list of database handlers.
        self.db_handlers = []

        # Set title and initial size of the application
        self.setWindowTitle("FDTDiscover")

        # Set Central Widget and main layout
        central_widget = Qw.QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = Qw.QHBoxLayout()
        central_widget.setLayout(layout)

        # Initialize the top menu bar.
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        # Splitter between explorer and tab view
        self.splitter = Qw.QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # Database panel
        self.database_panel = DatabasePanel()
        self.splitter.addWidget(self.database_panel)

        # Field panel
        self.fieldPanel = FieldPanel()
        self.splitter.addWidget(self.fieldPanel)

    def layout(self) -> Qw.QVBoxLayout:
        return cast(super().layout(), Qw.QVBoxLayout)


class MenuBar(Qw.QMenuBar):
    """The top menu bar of the main application window."""

    # Menus
    file_menu: Qw.QMenu

    # Actions
    import_database: QAction

    def __init__(self, parent: Qw.QWidget) -> None:
        super().__init__(parent)

        # Create the file menu.
        self.file_menu = self.addMenu("File")

        # Create the import database action and add it to the file menu.
        self.import_database = QAction("Open Database...", self.file_menu)
        self.import_database.triggered.connect(  # type: ignore
            lambda: dbRightClickMenuSignalBus.databaseFileDialogRequested.emit("import database", [])
        )
        self.file_menu.addAction(self.import_database)

