from abc import ABC
from PyQt6.QtWidgets import QMainWindow
from ..fdtdream.database.db import SimulationModel, MonitorModel
from ..fdtdream.database.handler import DatabaseHandler


class TopLevel(QMainWindow):
    callback_delay: int = 10  # ms
    selected_simulation: SimulationModel
    selected_monitor: MonitorModel
    db_handler: DatabaseHandler

