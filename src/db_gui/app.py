import sys

from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter,
    QTabWidget, QVBoxLayout, QListWidget, QWidget, QFileDialog, QMessageBox
)
from typing import List
from ..fdtdream.results.field_and_power_monitor import FieldAndPower
from .object_explorer import ObjectExplorer
from .field_plotter import FieldPlotTab
from ..fdtdream.database.handler import DatabaseHandler
from .top_level import TopLevel
from .linear_plot.linear_plot import LinearPlotTab
from ..FDTDiscover.dbPanel import DatabasePanel, signals
from ..FDTDiscover.dbPanel.models import DBObjects, DBObject
from ..FDTDiscover.application import MenuBar
from typing import Tuple


class MainWindow(TopLevel):

    # region Class Body
    tabs: QTabWidget
    splitter: QSplitter
    explorer: DatabasePanel
    tabs: QTabWidget
    field_tab: FieldPlotTab
    monitors: List[FieldAndPower]

    last_monitor: FieldAndPower

    callback_delay: float = 10
    # endregion

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.selected_monitor = None
        self.selected_simulation = None
        self.db_handler = None  # Placeholder for your DatabaseHandler

        self.init_menu_bar()
        self.prompt_for_database()

        # Set title and initial size of the application
        self.setWindowTitle("FDTDiscover")

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Splitter between explorer and tab view
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # Explorer
        self.explorer = DatabasePanel()
        # self.explorer = ObjectExplorer(self)
        signals.dbRightClickMenuSignalBus.plotFields.connect(self.on_monitor_selected)
        signals.dbPanelSignalBus.simulationSelected.connect(self.on_simulation_selected)
        self.splitter.addWidget(self.explorer)

        # Tabs
        tab_wrapper = QWidget(self)
        tab_wrapper_layout = QVBoxLayout()
        tab_wrapper_layout.setContentsMargins(10, 0, 0, 0)
        tab_wrapper.setLayout(tab_wrapper_layout)

        self.tabs = QTabWidget()
        self.field_tab = FieldPlotTab(self)
        self.t_plotter = LinearPlotTab(self)
        self.tabs.addTab(self.field_tab, "Plot Fields")
        self.tabs.addTab(self.t_plotter, "T/power")
        tab_wrapper_layout.addWidget(self.tabs)
        self.splitter.addWidget(tab_wrapper)

        self.splitter.setStretchFactor(0, 1)  # ObjectExplorer
        self.splitter.setStretchFactor(1, 3)  # TabWidget

        self.apply_styles()

    def on_simulation_selected(self, sim_id: int):
        ...

    def on_monitor_selected(self, monitor: DBObject):
        self.selected_monitor = monitor["dbHandler"].get_monitor_by_id(monitor["id"])
        self.selected_simulation = monitor["dbHandler"].get_simulation_by_id(self.selected_monitor.simulation_id)
        if self.selected_monitor.fields:
            self.field_tab.set_new_monitor()

    def init_menu_bar(self):
        # menubar = self.menuBar()
        # file_menu = menubar.addMenu("File")
        #
        # open_db_action = QAction("Open Database...", self)
        # open_db_action.triggered.connect(self.prompt_for_database)
        # file_menu.addAction(open_db_action)
        self.setMenuBar(MenuBar(self))

    def prompt_for_database(self):
        self.db_handler = DatabaseHandler(
            r"C:\Users\mgnso\Desktop\Master thesis\Code\FDTDreamNew\tests\SimulationDatabase.db")
        # path, _ = QFileDialog.getOpenFileName(
        #     self,
        #     "Select Database File",
        #     "",
        #     "SQLite Database Files (*.db);;All Files (*)"
        # )
        #
        # if path:
        #     try:
        #         self.db_handler = DatabaseHandler(path)
        #         print(f"Loaded database: {path}")
        #         # TODO: call a method to populate the ObjectExplorer using self.db_handler
        #     except Exception as e:
        #         QMessageBox.critical(self, "Error", f"Failed to load database:\n{e}")
        # else:
        #     QMessageBox.warning(self, "No Database", "No database was selected.")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }

            QListWidget, QTabWidget, QWidget {
                background-color: #313335;
                color: #ffffff;
                font-family: Segoe UI, sans-serif;
                font-size: 14px;
            }

            QTabBar::tab {
                background: #444;
                padding: 8px 20px;
                border: 1px solid #555;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 1px;
                margin-top: 2px;
            }

            QTabBar::tab:selected {
                background: #313335; /* Same as content area */
                color: white;
                margin-bottom: -1px;
            }

            QTabWidget::pane {
                border: 1px solid #555;
                top: -1px; /* So selected tab appears merged */
            }

            QSplitter::handle {
                background-color: #555;
            }

            QListWidget::item:selected {
                background-color: #00aaff;
                color: white;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
