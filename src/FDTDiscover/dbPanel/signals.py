from __future__ import annotations

from typing import List, Optional, Literal, Union, Dict

from PyQt6.QtCore import pyqtSignal, QObject, QPoint
from PyQt6.QtGui import QStandardItemModel, QAction
from PyQt6.QtWidgets import QWidget

from .models import DBObject, DBObjects
from ..shared import SignalProtocol, AutoSignalBusMeta, SignalProtocolNone


class DBPanelSignalBus(QObject, metaclass=AutoSignalBusMeta):
    """Signals emitted to and from the database panel widget."""

    # region Database imported and populate tree signals
    _importDatabase = pyqtSignal(list)
    importDatabase: SignalProtocol[List[str]]
    """Signal emitted requesting a database to be imported. The list of strings is the paths to the databases."""

    _populateTreeRequested = pyqtSignal()
    populateTreeRequested: SignalProtocolNone
    """Signal prompting the tree view controller to create a new model for the tree view widget."""

    _populateTree = pyqtSignal(object)
    populateTree: SignalProtocol[QStandardItemModel]
    """Signal emitted to the tree view widget with the model it should display."""
    # endregion

    # region Objects selected signals
    _objectsSelected = pyqtSignal(list)
    objectsSelected: SignalProtocol[DBObjects]
    """Signal emitted when object(s) in the database tree view is selected."""

    _monitorsSelected = pyqtSignal(list)
    monitorsSelected: SignalProtocol[DBObjects]
    """Signal emitted when monitor(s) is selected from the database tree view."""

    _simulationSelected = pyqtSignal(list)
    simulationSelected: SignalProtocol[DBObjects]
    """Signal emitted when simulation(s) is selected from the database tree view."""

    _nothingSelected = pyqtSignal()
    nothingSelected: SignalProtocolNone
    """Signal emitted when the database tree view selection goes from an object to nothing."""
    # endregion

    # region Populate parameters signals
    _populateMonitorParams = pyqtSignal(dict)
    populateMonitorParams: SignalProtocol[dict]
    """Signal emitted to populate the monitor parameters."""

    _populateSimulationParams = pyqtSignal(dict)
    populateSimulationParams: SignalProtocol[dict]
    """Signal emitted to populate the simulation parameters."""
    # endregion

    # region Right clicked signals
    _objectsRightClicked = pyqtSignal(list, object)
    objectsRightClicked: SignalProtocol[DBObjects, QPoint]
    """Signal emitted when object(s) from the database tree view is right-clicked"""
    # endregion


class DBRightClickMenuSignalBus(QObject, metaclass=AutoSignalBusMeta):
    """
    Signals emitted from the right-click context manager appearing when an object in the databse tree view is
    right-clicked.
    """

    # region Delete/remove actions
    _removeDatabases = pyqtSignal(list)
    removeDatabases: SignalProtocol[DBObjects]
    """Signal emitted to remove the selected databases from the database tree view."""

    _deleteCategories = pyqtSignal(list)
    deleteCategories: SignalProtocol[DBObjects]
    """Signal emitted to delete the selected categories along with all contained simulations from the database."""

    _deleteSimulations = pyqtSignal(list)
    deleteSimulations: SignalProtocol[DBObjects]
    """Signal emitted to delete selected simulations from the database."""

    _deleteMonitors = pyqtSignal(list)
    deleteMonitors: SignalProtocol[DBObjects]
    """Signal emitted to delete selected monitors from the database."""
    # endregion

    # region Edit name/category actions
    _renameCategory = pyqtSignal(object, str)
    renameCategory: SignalProtocol[DBObject, str]
    """Signal emitted to rename a category."""

    _mergeCategories = pyqtSignal(object)
    mergeCategories: SignalProtocol[DBObjects]
    """Signal emitted to merge two categories in the same database."""

    _renameSimulation = pyqtSignal(object, str)
    renameSimulation: SignalProtocol[DBObject, str]
    """Signal emitted to rename a simulation."""

    _renameMonitor = pyqtSignal(object, str)
    renameMonitor: SignalProtocol[DBObject, str]
    """Signal emitted to rename a monitor."""

    _changeCategory = pyqtSignal(list, str)
    changeCategory: SignalProtocol[DBObjects, str]
    """Signal emitted to change the category of the selected simulations."""
    # endregion

    # region Edit parameters/info actions
    _editParams = pyqtSignal(object, dict, dict)
    editParams: SignalProtocol[DBObjects, Dict, Dict]
    """Signal emitted to edit the parameters of a simulation or a monitor. 
    The first dictionary is the original parameters, and the second is the new set of parameters."""

    _editInfo = pyqtSignal(object, str)
    editInfo: SignalProtocol[DBObject, str]
    """Signal emitted to edit the information text of a simulation or a monitor. The string is the new info text."""
    # endregion

    # region Copy/transfer actions.
    _copyToDatabase = pyqtSignal(list, str, object)
    copyToDatabase: SignalProtocol[DBObjects, str, QWidget]
    """
    Signal emitted to copy selected categories/simulations and all contents to another database.
    The parameters emitted are the list of objects, the path to the target database, and the database panel widget.
    """
    # endregion

    # region Plot actions
    _plotFields = pyqtSignal(object)
    plotFields: SignalProtocol[DBObject]
    """Signal emitted to plot the field data of the selected monitor."""

    _plotRawPower = pyqtSignal(list)
    plotRawPower: SignalProtocol[DBObjects]
    """Signal emitted to plot the raw power data of the selected monitors."""

    _plotPower = pyqtSignal(object)
    plotPower: SignalProtocol[DBObjects]
    """Signal emitted to plot the power data of the selected monitors."""

    _plotIndex = pyqtSignal(object)
    plotIndex: SignalProtocol[DBObject]
    """Signal emitted to plot the index data of the selected index monitor."""
    # endregion

    # region Export to Python actions
    _exportToPythonRequested = pyqtSignal(list)
    exportToPythonRequested: SignalProtocol[DBObjects]
    """Signal emitted when selected objects should be exported to python script. Should open an interactive menu."""
    # endregion

    # region Requests
    _requestContextMenu = pyqtSignal(list, object)
    requestContextMenu: SignalProtocol[List[QAction], QPoint]
    """Signal emitted to display a context menu with the list of actions."""

    _renameDialogRequested = pyqtSignal(object)
    renameDialogRequested: SignalProtocol[DBObject]
    """Signal emited requesting an input dialog box. The string parameter decides which signal to reply with."""

    _changeCategoryDialogRequested = pyqtSignal(list)
    changeCategoryDialogRequested: SignalProtocol[DBObjects]
    """Signal requesting the menu for changing simulation category to be displayed."""

    _confirmDeleteDialogRequested = pyqtSignal(list)
    confirmDeleteDialogRequested: SignalProtocol[DBObjects]
    """
    Signal requesting the dialog to confirm deleting something.
    """

    _databaseFileDialogRequested = pyqtSignal(str, list)
    databaseFileDialogRequested: SignalProtocol[str, Optional[DBObjects]]
    """
    Requests a file dialog prompting the user to select a database file. 
    The string decides what signal to should be emitted with the resulting database path.
    String should be 'import database', 'copy to database'.
    """

    _editInfoDialogRequested = pyqtSignal(object, str)
    editInfoDialogRequested: SignalProtocol[DBObject, str]
    """Requests a dialog window that let's users edit and save info strings for monitors or simulations."""
    # endregion

    _editParamsDialogRequested = pyqtSignal(list, dict)
    editParamsDialogRequested: SignalProtocol[DBObjects, Dict]
    """
    Requests a dialog windoe that lets users edit and save parameters of a single simulation/monitor, or 
    shared parameters of several. The dictionary is the original parameters.
    """


dbPanelSignalBus: DBPanelSignalBus = DBPanelSignalBus()
dbRightClickMenuSignalBus: DBRightClickMenuSignalBus = DBRightClickMenuSignalBus()
