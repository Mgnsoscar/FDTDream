from typing import List, Optional

import uuid


from PyQt6.QtCore import QObject, QPoint, pyqtSlot, QThreadPool
from PyQt6.QtGui import QAction

from ..models import DBObjects, ParameterFetcherResult
from ..signals import dbRightClickMenuSignalBus, dbPanelSignalBus
from ..processes import ParameterFetcher


class RightClickController(QObject):
    """
    Recieves a signal when an object in the tree view is right clicked.
    Creates a list of actions and requests a context menu to be displayed with them.
    """

    _paramFetcherToken: Optional[str]
    _threadPool: QThreadPool

    def __init__(self):
        super().__init__()

        # Init attributes
        self._paramFetcherToken = None
        self._threadPool = QThreadPool.globalInstance()

        # Connect signals
        dbPanelSignalBus.objectsRightClicked.connect(self._onObjectsRightClicked)

    @pyqtSlot(list, object)
    def _onObjectsRightClicked(self, objects: DBObjects, pos: QPoint) -> None:
        """Acts on the objectsRightClicked signal."""

        # Fetch the object type:
        objectType = objects[0]["type"]
        isMultiple = len(objects) > 1

        if objectType == "simulation":
            self._onSimulationsRightClicked(objects, isMultiple, pos)
        elif objectType == "monitor":
            self._onMonitorsRightClicked(objects, isMultiple, pos)
        elif objectType == "category":
            self._onCategoriesRightClicked(objects, isMultiple, pos)
        elif objectType == "database":
            self._onDatabasesRightClicked(objects, isMultiple, pos)
        else:
            raise ValueError(f"Expected simulation, monitor, category or database, got {objectType}.")

    def _onSimulationsRightClicked(self, objects: DBObjects, isMultiple: bool, pos: QPoint) -> None:
        """Creates a set of actions for when a simulation or more is right-clicked, then requests a context menu."""

        # Init a list of actions
        actions: List[QAction] = []

        isSameDatabase = all([objects[0]["dbHandler"].path == obj["dbHandler"].path for obj in objects])

        # region If single-selection, create the rename simulation action
        if not isMultiple:
            renameSimulationAction = QAction("Rename simulation...")
            renameSimulationAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.renameDialogRequested.emit(objects[0])
            )
            actions.append(renameSimulationAction)
        # endregion

        # region If all simulations are in the same database -> Create the change category action.
        if isSameDatabase:
            changeCategoryAction = QAction("Change category...")
            changeCategoryAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.changeCategoryDialogRequested.emit(objects)
            )
            actions.append(changeCategoryAction)
        # endregion

        # region Create the edit parameters action.

        # Create the parameter fetcher process worker
        worker = self._createParameterFetcher(objects)

        editParamsAction = QAction("Edit parameters...")
        editParamsAction.triggered.connect(  # type: ignore
            lambda: self._threadPool.start(worker)
        )
        actions.append(editParamsAction)
        # endregion

        # region If single-selection, create the edit info action.
        if not isMultiple:
            # Fetch the original information text.
            infoText = objects[0]["dbHandler"].get_simulation_info(objects[0]["id"])

            editInfoAction = QAction("Edit information...")
            editInfoAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.editInfoDialogRequested.emit(objects[0], infoText)
            )
            actions.append(editInfoAction)
        # endregion

        # region Create the copy simulations to database action
        if isSameDatabase:
            copyToDatabaseAction = QAction("Copy simulations to another database..." if isMultiple else
                                           "Copy simulation to another database...")
            copyToDatabaseAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.databaseFileDialogRequested.emit("copy to database", objects)
            )
            actions.append(copyToDatabaseAction)
        # endregion

        # region Create the delete action
        deleteAction = QAction("Delete simulations..." if isMultiple else "Delete simulation...")
        deleteAction.triggered.connect(  # type: ignore
            lambda: dbRightClickMenuSignalBus.confirmDeleteDialogRequested.emit(objects)
        )
        actions.append(deleteAction)
        # endregion

        # Request context menu
        dbRightClickMenuSignalBus.requestContextMenu.emit(actions, pos)

    def _onMonitorsRightClicked(self, objects: DBObjects, isMultiple: bool, pos: QPoint) -> None:

        # Init list of actions
        actions: List[QAction] = []

        # region If single-selection and monitor has field data -> create the plot field action.
        if not isMultiple and objects[0]["dbHandler"].monitor_has_fields(objects[0]["id"]):
            plotFieldsAction = QAction("Plot fields...")
            plotFieldsAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.plotFields.emit(objects[0])
            )
            actions.append(plotFieldsAction)
        # endregion

        # region If all selected monitors has T data -> create the plot T data action
        if all(obj["dbHandler"].monitor_has_T_data(obj["id"]) for obj in objects):
            plotTAction = QAction("Plot T data...")
            plotTAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.plotPower.emit(objects)
            )
            actions.append(plotTAction)
        # endregion

        # region If all selected monitors has raw power data -> create the plot raw power action.
        if all(obj["dbHandler"].monitor_has_power_data(obj["id"]) for obj in objects):
            plotPowerAction = QAction("Plot raw power...")
            plotPowerAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.plotRawPower.emit(objects)
            )
            actions.append(plotPowerAction)
        # endregion

        # region If single-selection, create the rename simulation action
        if not isMultiple:
            renameSimulationAction = QAction("Rename monitor...")
            renameSimulationAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.renameDialogRequested.emit(objects[0])
            )
            actions.append(renameSimulationAction)
        # endregion

        # region Create the edit parameters action.

        # Create the parameter fetcher worker
        worker = self._createParameterFetcher(objects)

        editParamsAction = QAction("Edit parameters...")
        editParamsAction.triggered.connect(  # type: ignore
            lambda: self._threadPool.start(worker)
        )
        actions.append(editParamsAction)
        # endregion

        # region If single-selection, create the edit info action.
        if not isMultiple:
            # Fetch the original information text.
            infoText = objects[0]["dbHandler"].get_monitor_info(objects[0]["id"])

            editInfoAction = QAction("Edit information...")
            editInfoAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.editInfoDialogRequested.emit(objects[0], infoText)
            )
            actions.append(editInfoAction)
        # endregion

        # region  Create the export to python action
        exportToPythonAction = QAction("Export monitors to python script..." if isMultiple else
                                       "Export monitor to python script")
        exportToPythonAction.triggered.connect(  # type: ignore
            lambda: dbRightClickMenuSignalBus.exportToPythonRequested.emit(objects)
        )
        actions.append(exportToPythonAction)
        # endregion

        # region Create the delete action
        deleteAction = QAction("Delete monitors..." if isMultiple else "Delete monitor...")
        deleteAction.triggered.connect(  # type: ignore
            lambda: dbRightClickMenuSignalBus.confirmDeleteDialogRequested.emit(objects)
        )
        actions.append(deleteAction)
        # endregion

        # Request context menu
        dbRightClickMenuSignalBus.requestContextMenu.emit(actions, pos)

    @staticmethod
    def _onCategoriesRightClicked(objects: DBObjects, isMultiple, pos: QPoint) -> None:

        # Init list of actions
        actions: List[QAction] = []

        # If single-selection -> Create the rename category action
        if not isMultiple:
            renameCategoryAction = QAction("Rename category...")
            renameCategoryAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.renameDialogRequested.emit(objects[0])
            )
            actions.append(renameCategoryAction)

        # If all selected categories are in the same database -> create the merge categories action
        if isMultiple and all([objects[0]["dbHandler"].path == obj["dbHandler"].path for obj in objects]):
            mergeCategoriesAction = QAction("Merge categories...")
            mergeCategoriesAction.triggered.connect(  # type: ignore
                lambda: dbRightClickMenuSignalBus.mergeCategories.emit(objects)
            )
            actions.append(mergeCategoriesAction)

        # Create the copy to another database action
        copyToAnotherDatabaseAction = QAction("Copy categories to another database..." if isMultiple else
                                              "Copy category to another database...")
        copyToAnotherDatabaseAction.triggered.connect(  # type: ignore
            lambda: dbRightClickMenuSignalBus.databaseFileDialogRequested.emit("copy to database", objects)
        )
        actions.append(copyToAnotherDatabaseAction)

        # Create the delete categories action
        deleteCategoriesAction = QAction("Delete categories..." if isMultiple else
                                         "Delete category...")
        deleteCategoriesAction.triggered.connect(  # type: ignore
            lambda: dbRightClickMenuSignalBus.confirmDeleteDialogRequested.emit(objects)
        )
        actions.append(deleteCategoriesAction)

        # Request context menu:
        dbRightClickMenuSignalBus.requestContextMenu.emit(actions, pos)

    @staticmethod
    def _onDatabasesRightClicked(objects: DBObjects, isMultiple: bool, pos: QPoint) -> None:

        # Init list of actions
        actions: List[QAction] = []

        # Create the remove databases action
        removeDatabasesAction = QAction("Remove databases (non-destructive)..." if isMultiple else
                                        "Remove database (non-destructive)...")
        removeDatabasesAction.triggered.connect(  # type: ignore
            lambda: dbRightClickMenuSignalBus.removeDatabases.emit(objects)
        )
        actions.append(removeDatabasesAction)

        # Request context menu
        dbRightClickMenuSignalBus.requestContextMenu.emit(actions, pos)

    def _createParameterFetcher(self, objects: DBObjects) -> ParameterFetcher:

        # Init a worker to fetch shared parameters
        token = str(uuid.uuid4())
        self._paramFetcherToken = token
        worker = ParameterFetcher(
            objects=objects,
            token=token
        )
        # Connect the worker finished signal to the editParamsDialogRequested signal.
        # Pass on the worker result with the objects.
        worker.signals.finished.connect(
            lambda fetcherResults: self._onParameterFetcherFinished(objects, fetcherResults))

        return worker

    @pyqtSlot(list, dict)
    def _onParameterFetcherFinished(self, objects: DBObjects, fetcherResults: ParameterFetcherResult):

        if self._paramFetcherToken == fetcherResults["token"]:
            objType = objects[0]["type"]
            fetchedParameters = fetcherResults[f"{objType}Parameters"]  # type: ignore
            fetchedParameters.pop("__info__", None)  # Pop out the info text
            dbRightClickMenuSignalBus.editParamsDialogRequested.emit(
                objects,
                fetchedParameters
            )
            self._paramFetcherToken = None
        return

