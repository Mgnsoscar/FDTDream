from abc import ABC
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QSplitter
from PyQt6.QtCore import pyqtSignal
from ..fdtdream.database import DatabaseHandler
from typing import List


class AppInterface(QMainWindow):

    # region Signals
    databases_changed = pyqtSignal(list)
    """
    Signal emitted when the list of open databases in the application changes.
    It should be emitted when the application opens a new database or closes an open database.

    Emits:
        list[DatabaseHandler]: The new list of active/open DatabaseHandler instances.
    """
    # endregion Signals

    db_handlers: List[DatabaseHandler]
    splitter: QSplitter

    def get_db_handlers(self) -> List[DatabaseHandler]:
        ...
