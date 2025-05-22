from typing import Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QSplitter, QFileDialog, QHBoxLayout, QWidget

from .changeCategoryDialog import ChangeCategoryDialog
from .treeView import TreeView
from .parameterTable import ParameterTable
from .infoButton import InfoButton
from ..models import DBObject, DBObjects
from .editInfoDialog import EditInfoDialog
from .editParametersDialog import EditParametersDialog
from ..signals import dbRightClickMenuSignalBus, dbPanelSignalBus


class DatabasePanel(QSplitter):

    def __init__(self):
        super().__init__(Qt.Orientation.Vertical)

        # Add the Tree view
        self.addWidget(TreeView())

        # Add the simulation parameter table.
        self.addWidget(ParameterTable("Simulation Parameters", dbPanelSignalBus.populateSimulationParams))

        # Add the monitor parameter table.
        self.addWidget(ParameterTable("Monitor Parameters", dbPanelSignalBus.populateMonitorParams))

        # Add a widget with the two info buttons
        infoWidget = QWidget()
        infoButtonLayout = QHBoxLayout()
        infoWidget.setLayout(infoButtonLayout)
        infoButtonLayout.addWidget(InfoButton("Simulation Info", dbPanelSignalBus.populateSimulationParams))
        infoButtonLayout.addWidget(InfoButton("Monitor Info", dbPanelSignalBus.populateMonitorParams))
        self.addWidget(infoWidget)

        # Connect signals
        self._connectSignals()

    def _connectSignals(self):
        dbRightClickMenuSignalBus.changeCategoryDialogRequested.connect(self._onChangeCategoryDialogRequested)
        dbRightClickMenuSignalBus.confirmDeleteDialogRequested.connect(self._onConfirmDeleteDialogRequested)
        dbRightClickMenuSignalBus.renameDialogRequested.connect(self._onRenameDialogRequested)
        dbRightClickMenuSignalBus.databaseFileDialogRequested.connect(self._onDatabaseFileDialogRequested)
        dbRightClickMenuSignalBus.editInfoDialogRequested.connect(self._onEditInfoDialogRequested)
        dbRightClickMenuSignalBus.editParamsDialogRequested.connect(self._onEditParamsDialogRequested)

    @pyqtSlot(list)
    def _onChangeCategoryDialogRequested(self, simulations: DBObjects) -> None:
        dialog = ChangeCategoryDialog(simulations)

        dialog.exec()

    @pyqtSlot(list)
    def _onConfirmDeleteDialogRequested(self, objects: DBObjects) -> None:
        def confirm_delete(title_: str, message_: str) -> bool:
            """Confirms if the user wants to delete the given object."""
            reply = QMessageBox.question(
                self,
                title_,
                message_,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes

        isMultiple = len(objects) > 1
        objType = objects[0]["type"]

        if objType == "simulation":
            objType = "simulations" if isMultiple else "simulation"
            signal = dbRightClickMenuSignalBus.deleteSimulations
        elif objType == "monitor":
            objType = "monitors" if isMultiple else "monitor"
            signal = dbRightClickMenuSignalBus.deleteMonitors
        elif objType == "category":
            objType = "categories" if isMultiple else "category"
            signal = dbRightClickMenuSignalBus.deleteCategories
        elif objType == "database":
            dbRightClickMenuSignalBus.removeDatabases.emit(objects)
            return
        else:
            raise ValueError(f"Expected database, category, simulation or monitor, got {objType}")

        title = f"Delete {objType.capitalize()}"
        message = (
            f"Are you sure you want to delete these {len(objects)} {objType}?" if isMultiple else
            f"Are you sure you want to delete this {objType}?"
        )
        message2 = (
            f"Are you absolutely sure you want to delete these {len(objects)} {objType}?" if isMultiple else
            f"Are you absolutely sure you want to delete this {objType}?"
        )

        if not confirm_delete(title, message):
            return
        else:
            if not confirm_delete(title, message2):
                return
            else:
                # Signal for deletion.
                signal.emit(objects)

    @pyqtSlot(object)
    def _onRenameDialogRequested(self, obj: DBObject) -> None:
        """Replies to the renameDialogRequested signal by displaying an input dialog. Emitts the reply."""
        # Choose a new name
        new_name, ok = QInputDialog.getText(
            self,
            f"Rename {obj['type'].capitalize()}",
            f"Enter new {obj['type']} name:",
            text=obj["name"]
        )
        # Request the renaming
        if ok and new_name and new_name != obj["name"]:
            if obj["type"] == "simulation":
                dbRightClickMenuSignalBus.renameSimulation.emit(obj, new_name)
            elif obj["type"] == "monitor":
                dbRightClickMenuSignalBus.renameMonitor.emit(obj, new_name)
            elif obj["type"] == "category":
                dbRightClickMenuSignalBus.renameCategory.emit(obj, new_name)
            else:
                raise ValueError(f"Expected simulation, monitor or category, got {obj['type']}.")

    @pyqtSlot(str, list)
    def _onDatabaseFileDialogRequested(self, request_type: str, objects: Optional[DBObjects]) -> None:

        if request_type == "import database":

            # Let user select multiple files
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Select One or More Database Files",
                "",
                "SQLite Database Files (*.db);;All Files (*)"
            )

            if not paths:
                QMessageBox.warning(self, "No Database", "No database was selected.")
                return

            dbPanelSignalBus.importDatabase.emit(paths)

        elif request_type == "copy to database":

            # Prompt user to select a single database file
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Target Database",
                "",
                "Database Files (*.db);;All Files (*)"
            )

            if not path:
                QMessageBox.warning(self, "No Database", "No database was selected.")
                return
            dbRightClickMenuSignalBus.copyToDatabase.emit(objects, path, self)

        else:
            raise ValueError(f"Expected 'import database' or 'copy to database', got '{request_type}'.")

    @pyqtSlot(object, str)
    def _onEditInfoDialogRequested(self, obj: DBObject, originalInfo: str) -> None:
        dialog = EditInfoDialog(obj, originalInfo)
        dialog.exec()

    @pyqtSlot(list, dict)
    def _onEditParamsDialogRequested(self, objects: DBObjects, originalParams: dict) -> None:
        dialog = EditParametersDialog(objects, originalParams)
        dialog.exec()
