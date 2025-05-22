from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from ..models import DBObjects, ParameterFetcherResult
from typing import Tuple
from ...shared import AutoSignalBusMeta, SignalProtocol


class ParameterFectherSignals(QObject, metaclass=AutoSignalBusMeta):
    _finished = pyqtSignal(object)
    finished: SignalProtocol[ParameterFetcherResult]
    """Signal emitted by a ParameterFecther worker thread when it's finished."""


class ParameterFetcher(QRunnable):
    """
    Worker thread that queries the database for the parameters of selected objects, processes them and
    emits the result.
    """

    def __init__(self, objects: DBObjects, token: str):
        super().__init__()
        self.objects = objects
        self.token = token
        self.signals = ParameterFectherSignals()

    @staticmethod
    def _processParameters(objects: DBObjects) -> Tuple[dict, dict]:
        """
        Get a dictionary with the shared parameters between the provided database objects.
        Returns a tuple with the simulation parameters first, then the monitor parameters.
        """

        # Check if the objects are monitors
        isMonitors = objects[0]["type"] == "monitor"

        # Init dict lists
        monitorParamDicts = []
        simulationParamDicts = []

        # Fetch monitor params
        if isMonitors:

            for obj in objects:
                dbHandler = obj["dbHandler"]
                monitorParams = dbHandler.get_monitor_parameters(obj["id"])
                monitorParamDicts.append(monitorParams)

                # Fetch the parameters of the monitor's parent simulation.
                simulationParams = dbHandler.get_simulation_parameters_for_monitor(obj["id"])
                simulationParamDicts.append(simulationParams)

        # Fetch simulations params
        else:
            for obj in objects:
                dbHandler = obj["dbHandler"]
                simulationParams = dbHandler.get_simulation_parameters(obj["id"])
                simulationParamDicts.append(simulationParams)

        commonMonitorParams = set(monitorParamDicts[0].items()) if monitorParamDicts else set()
        if commonMonitorParams and len(commonMonitorParams) > 1:
            for d in monitorParamDicts[1:]:
                commonMonitorParams &= set(d.items())

        commonSimulationParams = set(simulationParamDicts[0].items()) if simulationParamDicts else set()
        if commonSimulationParams and len(commonSimulationParams) > 1:
            for d in simulationParamDicts[1:]:
                commonSimulationParams &= set(d.items())

        # Convert to dictionaries with keys sorted alphabetically.
        simulationParams = dict(sorted(dict(commonSimulationParams).items()))
        monitorParams = dict(sorted(dict(commonMonitorParams).items()))

        return simulationParams, monitorParams

    @pyqtSlot()
    def run(self):
        simulationParameters, monitorParameters = self._processParameters(self.objects)
        result = ParameterFetcherResult(
            simulationParameters=simulationParameters,
            monitorParameters=monitorParameters,
            token=self.token
        )
        self.signals.finished.emit(result)
