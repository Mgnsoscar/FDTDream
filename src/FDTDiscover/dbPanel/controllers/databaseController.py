import uuid
from typing import List, Optional

from PyQt6.QtCore import QObject, QThreadPool, pyqtSlot
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QMessageBox, QWidget

from ..models import DBObject, DBObjects
from ..processes import PopulateTreeWorker, CopyWorker, CopyProgressDialog
from ..signals import dbPanelSignalBus, dbRightClickMenuSignalBus
from ....fdtdream.database import DatabaseHandler


class DatabaseController(QObject):
    _dbHandlers: List[DatabaseHandler]
    """List of the database handlers of the currently imported databases in the application."""

    _threadPool: QThreadPool
    """Connection to the global thread pool."""

    _populateTreeToken: Optional[str]
    """Unique token meant to keep track of which populate tree thread is the latest called one."""

    _copyInProgress: bool
    """Flag to indicate if a database copying process is currently running."""

    def __init__(self):
        super().__init__()

        # Init attributes
        self._dbHandlers = []
        self._threadPool = QThreadPool.globalInstance()
        self._populateTreeToken = None
        self._copyInProgress = False

        self._connectSignals()

    def _connectSignals(self) -> None:

        dbPanelSignalBus.importDatabase.connect(self._onImportDatabase)
        dbRightClickMenuSignalBus.deleteCategories.connect(self._onDeleteCategories)
        dbRightClickMenuSignalBus.deleteMonitors.connect(self._onDeleteMonitors)
        dbRightClickMenuSignalBus.deleteSimulations.connect(self._onDeleteSimulations)
        dbRightClickMenuSignalBus.removeDatabases.connect(self._onRemoveDatabases)
        dbPanelSignalBus.populateTreeRequested.connect(self._onPopulateTreeRequested)
        dbRightClickMenuSignalBus.renameSimulation.connect(self._onRenameSimulation)
        dbRightClickMenuSignalBus.renameMonitor.connect(self._onRenameMonitor)
        dbRightClickMenuSignalBus.renameCategory.connect(self._onRenameCategory)
        dbRightClickMenuSignalBus.copyToDatabase.connect(self._onCopyToDatabase)
        dbRightClickMenuSignalBus.changeCategory.connect(self._onChangeCategory)
        dbRightClickMenuSignalBus.editInfo.connect(self._onEditInfo)
        dbRightClickMenuSignalBus.editParams.connect(self._onEditParams)

    @pyqtSlot()
    def _onPopulateTreeRequested(self) -> None:
        """Starts the process to create a new model for the tree view and emits it to the tree view widget."""

        # Create and store unique token from this process request.
        token = str(uuid.uuid4())
        self._populateTreeToken = token

        # Start a worker thread and connect it's finished signal to the _onMonitorParamsReady() method.
        worker = PopulateTreeWorker(
            dbHandlers=self._dbHandlers.copy(),
            token=token
        )
        worker.signals.finished.connect(self._onTreeModelReady)
        self._threadPool.start(worker)

    @staticmethod
    @pyqtSlot(object)
    def _onTreeModelReady(model: QStandardItemModel) -> None:
        """Recieves the finished tree model from the populateTreeWorker thread."""

        # Emit the nothing selected signal
        dbPanelSignalBus.nothingSelected.emit()

        # Emit the model to the tree view.
        dbPanelSignalBus.populateTree.emit(model)

    @pyqtSlot(list)
    def _onImportDatabase(self, database_paths: List[str]) -> None:
        """
        Acts on the databaseImported signal.
        Imports one or more datatabases and adds it to the list of database handlers.
        """

        existingPaths = [dbHandler.path for dbHandler in self._dbHandlers]

        for path in database_paths:

            # Create a new database handler
            try:
                dbHandler = DatabaseHandler(path)

            except Exception as e:
                QMessageBox.warning(
                    parent=None,
                    title="Loading Error",
                    text=f"The file path '{path}' was not recognized as a valid database. Error message: {e}."
                )
                continue

            # Prevent duplicate imports
            if dbHandler.path in existingPaths:
                QMessageBox.warning(
                    parent=None,
                    title="Duplicate Database",
                    text=f"The database '{dbHandler.filename}' is already imported. Ignoring this."
                )
                return

            # Add to the list of handlers
            self._dbHandlers.append(dbHandler)

            # Add to list of existing paths.
            existingPaths.append(dbHandler.path)

        # Trigger tree repopulation
        dbPanelSignalBus.populateTreeRequested.emit()

    # region Delete/Remove methods
    @pyqtSlot(list)
    def _onRemoveDatabases(self, databases: DBObjects) -> None:
        for database in databases:
            self._dbHandlers.remove(database["dbHandler"])
        dbPanelSignalBus.populateTreeRequested.emit()

    @staticmethod
    @pyqtSlot(list)
    def _onDeleteCategories(categories: DBObjects) -> None:
        for category in categories:
            category["dbHandler"].delete_category(category["name"])
        dbPanelSignalBus.populateTreeRequested.emit()

    @staticmethod
    @pyqtSlot(list)
    def _onDeleteMonitors(monitors: DBObjects) -> None:
        for monitor in monitors:
            monitor["dbHandler"].delete_monitor_by_id(monitor["id"])
        dbPanelSignalBus.populateTreeRequested.emit()

    @staticmethod
    @pyqtSlot(list)
    def _onDeleteSimulations(simulations: DBObjects) -> None:
        for simulation in simulations:
            simulation["dbHandler"].delete_simulation_by_id(simulation["id"])
        dbPanelSignalBus.populateTreeRequested.emit()

    # endregion

    # region Rename methods
    @staticmethod
    @pyqtSlot(object, str)
    def _onRenameSimulation(simulation: DBObject, new_name: str) -> None:
        """Renames the selected simulation."""
        dbHandler = simulation["dbHandler"]
        dbHandler.rename_simulation(simulation["id"], new_name)
        dbPanelSignalBus.populateTreeRequested.emit()

    @staticmethod
    def _onRenameMonitor(monitor: DBObject, new_name: str) -> None:
        """Renames the selected monitor."""
        dbHandler = monitor["dbHandler"]
        dbHandler.rename_monitor(monitor["id"], new_name)
        dbPanelSignalBus.populateTreeRequested.emit()

    @staticmethod
    @pyqtSlot(object, str)
    def _onRenameCategory(category: DBObject, new_name: str) -> None:
        dbHandler = category["dbHandler"]
        dbHandler.rename_category(category["name"], new_name)
        dbPanelSignalBus.populateTreeRequested.emit()

    @staticmethod
    @pyqtSlot(list, str)
    def _onChangeCategory(simulations: DBObjects, new_category: str) -> None:
        for simulation in simulations:
            simulation["dbHandler"].change_simulation_category(simulation["id"], new_category)
        dbPanelSignalBus.populateTreeRequested.emit()

    # endregion

    # region Copy methods
    @pyqtSlot(list, str, object)
    def _onCopyToDatabase(self, objects: DBObjects, targetDBPath: str, progressWindowParent: QWidget) -> None:

        try:
            targetDBHandler = DatabaseHandler(targetDBPath)
        except Exception as e:
            QMessageBox.warning(
                parent=progressWindowParent,
                title="Import Error",
                text=f"Error importing database from path {targetDBPath}. Error message: {e}"
            )
            return

        worker = CopyWorker(progressWindowParent, objects, targetDBHandler)
        progress_dialog = CopyProgressDialog(progressWindowParent, "Copying Simulations", total=len(objects))
        progress_dialog.canceled.connect(  # type: ignore
            worker.cancel)
        worker.signals.progressUpdated.connect(progress_dialog.setValue)

        def show_result(cancelled: bool, copied: int, total: int, errors: list[str]):
            progress_dialog.close()

            self._copyInProgress = False

            if cancelled:
                QMessageBox.information(
                    progressWindowParent,
                    "Copy Cancelled",
                    "Operation cancelled. Nothing was copied."
                )
            else:
                msg = f"Copied {copied} of {total} simulations."
                if errors:
                    msg += "\n\nErrors:\n" + "\n".join(errors)
                QMessageBox.information(
                    progress_dialog,
                    "Copy Complete",
                    msg
                )

            dbPanelSignalBus.populateTreeRequested.emit()

        worker.signals.progressErrorSummary.connect(show_result)

        QThreadPool.globalInstance().start(worker)
        self._copyInProgress = True
        progress_dialog.exec()

    # endregion

    # region Edit params/info methods
    @pyqtSlot(object, str)
    def _onEditInfo(self, obj: DBObject, newInfo: str) -> None:
        objType = obj["type"]
        dbHandler = obj["dbHandler"]
        if objType == "simulation":
            dbHandler.update_simulation_info(obj["id"], newInfo)
            dbPanelSignalBus.populateSimulationParams.emit(
                dict(sorted(dbHandler.get_simulation_parameters(obj["id"]).items())))
        elif objType == "monitor":
            dbHandler.update_monitor_info(obj["id"], newInfo)
            dbPanelSignalBus.populateMonitorParams.emit(
                dict(sorted(dbHandler.get_monitor_parameters(obj["id"]).items())))  # Sort keys alphabetically
        else:
            raise ValueError(f"Expected object type 'simulation' or 'monitor', got '{objType}'.")

    @pyqtSlot(object, dict, dict)
    def _onEditParams(self, objects: DBObjects, originalParams: dict, newParams: dict) -> None:

        # Fetch object type
        objType = objects[0]["type"]

        # Validate correct object type
        if objType not in ["simulation", "monitor"]:
            raise ValueError(f"Expected object type 'simulation' or 'monitor', got '{objType}'.")

        # Find shared keys to remove and keys to add/update
        to_remove = set(originalParams.keys()) - set(newParams.keys())
        to_add_or_update = {k: v for k, v in newParams.items() if originalParams.get(k) != v}

        for obj in objects:
            # Fetch the object's dbHandler and database id
            dbHandler = obj["dbHandler"]
            objId = obj["id"]

            # Fetch the current parameters of the object
            current_params = getattr(dbHandler, f"get_{objType}_parameters")(objId)

            # Update new parameters and remove removed ones.
            current_params.update(to_add_or_update)
            for key in to_remove:
                current_params.pop(key, None)

            # Update parameters in database
            getattr(dbHandler, f"update_{objType}_parameters")(objId, current_params)

        # Finally request repopulation of the parameter tables
        getattr(dbPanelSignalBus, f"populate{objType.capitalize()}Params").emit(newParams)

    # endregion
