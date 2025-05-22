from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from ..models import DBObject
from typing import Tuple, List
from ....fdtdream.database import DatabaseHandler
from ...shared import AutoSignalBusMeta, SignalProtocol


class PopulateTreeSignals(QObject, metaclass=AutoSignalBusMeta):
    _finished = pyqtSignal(object)
    finished: SignalProtocol[QStandardItemModel]
    """Signal emitted by a by the PopulateTreeWorker worker thread when it's finished."""


class PopulateTreeWorker(QRunnable):
    """
    Worker thread that queries the database for the parameters of selected objects, processes them and
    emits the result.
    """

    def __init__(self, dbHandlers: List[DatabaseHandler], token: str):
        super().__init__()
        self.dbHandlers = dbHandlers
        self.token = token
        self.signals = PopulateTreeSignals()

    def _createTreeModel(self) -> QStandardItemModel:
        """Creates a new tree view model from objects in the provided databases."""

        # Create an empty model
        model = QStandardItemModel()

        # Emit empty model if no databases are imported.
        if not self.dbHandlers:
            return model

        # Create a new root
        root = model.invisibleRootItem()

        # Fetch all imported database handlers
        for dbHandler in self.dbHandlers:

            # Create a DBObject typed dict.
            dbHandlerDBObject = DBObject(type="database", name=dbHandler.filename, dbHandler=dbHandler, id=None)

            # Create the item and assign data
            db_item = QStandardItem(f"Database: {dbHandlerDBObject['name']}")
            db_item.setEditable(False)
            db_item.setData(dbHandlerDBObject, Qt.ItemDataRole.UserRole)

            # Fetch all categories in the database
            categories = dbHandler.get_all_categories()
            for category in categories:

                # Create a DBObject typed dict.
                categoryDBObject = DBObject(type="category", name=category, dbHandler=dbHandler, id=None)

                # Create item and assign data.
                cat_item = QStandardItem(category)
                cat_item.setEditable(False)
                cat_item.setData(categoryDBObject, Qt.ItemDataRole.UserRole)

                # Fetch all simulations in the category
                simulations = dbHandler.get_simulations_by_category(category)
                for sim_id, sim_name in simulations:

                    # Create DBOject typed dict
                    simulationDBObject = DBObject(type="simulation", name=sim_name, dbHandler=dbHandler, id=sim_id)

                    # Create item and assign data.
                    sim_item = QStandardItem(sim_name)
                    sim_item.setEditable(False)
                    sim_item.setData(simulationDBObject, Qt.ItemDataRole.UserRole)

                    # Fetch all monitors in the simulation
                    monitors = dbHandler.get_monitors_for_simulation(sim_id)
                    for mon_id, mon_name in monitors:
                        # Create DBObject typed dict.
                        monitorDBObject = DBObject(type="monitor", name=mon_name, dbHandler=dbHandler, id=mon_id)

                        # Create item and assign data.
                        mon_item = QStandardItem(mon_name)
                        mon_item.setEditable(False)
                        mon_item.setData(monitorDBObject, Qt.ItemDataRole.UserRole)

                        # Add monitor to the simulation row
                        sim_item.appendRow(mon_item)

                    # Add simulation to the category row
                    cat_item.appendRow(sim_item)

                # Add category to the database row.
                db_item.appendRow(cat_item)

            # Add database to the root.
            root.appendRow(db_item)

        # Return the model
        return model

    @pyqtSlot()
    def run(self):
        model = self._createTreeModel()
        self.signals.finished.emit(model)
