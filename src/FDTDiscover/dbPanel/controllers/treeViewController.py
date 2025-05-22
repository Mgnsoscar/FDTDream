import uuid
from typing import Optional

from PyQt6.QtCore import QObject, QThreadPool, pyqtSlot

from ..models import DBObjects, ParameterFetcherResult
from ..processes import ParameterFetcher
from ..signals import dbPanelSignalBus


class TreeViewController(QObject):
    """Controller managing the database panel TreeView widget."""

    _threadPool: QThreadPool
    """Connection to the global thread pool."""

    _paramToken: Optional[str]
    """Unique token meant to keep track of which parameter fetcher thread is the latest called one."""

    def __init__(self):
        super().__init__()

        # Assign attributes.
        self._threadPool = QThreadPool.globalInstance()
        self._paramToken = None

        # Connect to signals
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect signals to methods."""
        dbPanelSignalBus.objectsSelected.connect(self._onObjectsSelected)
        dbPanelSignalBus.nothingSelected.connect(self._onNothingSelected)

    @staticmethod
    def _onNothingSelected() -> None:
        """Clears the parameter views."""
        dbPanelSignalBus.populateMonitorParams.emit({})
        dbPanelSignalBus.populateSimulationParams.emit({})

    @pyqtSlot()
    def _onObjectsSelected(self, obj: DBObjects) -> None:
        """Acts on the objectsSelected signal."""

        obj_type = obj[0]["type"]
        if obj_type == "monitor":
            self._onMonitorsSelected(obj)
        elif obj_type == "simulation":
            self._onSimulationsSelected(obj)
        else:
            # Clear the parameter views:
            dbPanelSignalBus.populateMonitorParams.emit({})
            dbPanelSignalBus.populateSimulationParams.emit({})

    def _onMonitorsSelected(self, monitors: DBObjects) -> None:
        """Acts on the monitorsSelected signal."""

        # Create and store unique token from this process request.
        token = str(uuid.uuid4())
        self._paramToken = token

        # Start a worker thread and connect it's finished signal to the _onMonitorParamsReady() method.
        worker = ParameterFetcher(
            objects=monitors,
            token=token
        )
        worker.signals.finished.connect(self._onParamsReady)
        self._threadPool.start(worker)

    def _onSimulationsSelected(self, simulations: DBObjects) -> None:
        """Acts on the simulationsSelected signal."""

        # Create and store unique token from this process request.
        token = str(uuid.uuid4())
        self._paramToken = token

        # Start a worker thread and connect it's finished signal to the _onParamsReady() method.
        worker = ParameterFetcher(
            objects=simulations,
            token=token
        )
        worker.signals.finished.connect(self._onParamsReady)
        self._threadPool.start(worker)

    @pyqtSlot(object)
    def _onParamsReady(self, result: ParameterFetcherResult) -> None:
        if result["token"] == self._paramToken:
            dbPanelSignalBus.populateSimulationParams.emit(result["simulationParameters"])
            dbPanelSignalBus.populateMonitorParams.emit(result["monitorParameters"])


