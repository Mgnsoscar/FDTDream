from typing import List, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QWidget, QProgressDialog

from ..models import DBObjects, DBObject
from ...shared import AutoSignalBusMeta, SignalProtocolNone, SignalProtocol
from ....fdtdream.database import DatabaseHandler
from ....fdtdream.database import SimulationPydanticModel


class CopySignals(QObject, metaclass=AutoSignalBusMeta):

    _progressUpdated = pyqtSignal(int)
    progressUpdated: SignalProtocol[int]
    """Emits a signal with the current progress."""

    _progressErrorSummary = pyqtSignal(bool, int, int, list)
    progressErrorSummary: SignalProtocol[bool, int, int, List[str]]
    """Summary of the errors during copying. Arguments are: was it canceled, nr. succesfull copied, total nr, errors"""


class CopyWorker(QRunnable):
    """
    Worker thread that copies a simulation or a category of simulations from one or more databases to a new one.
    """

    totalNrSimulations: Optional[int]
    progress: int = 0
    progressWindowParent: QWidget
    errors: List[str]
    targetDB: DatabaseHandler
    token: str
    signals: CopySignals
    cancelled: bool

    def __init__(self, progressWindowParent: QWidget, objects: DBObjects, targetDB: DatabaseHandler):
        super().__init__()

        # Init attributes
        self.totalNrSimulations = None
        self.progress = 0
        self.errors = []
        self.cancelled = False
        self.progressWindowParent = progressWindowParent
        self.objects = objects
        self.objectType = self.objects[0]["type"]
        self.targetDB = targetDB
        self.signals = CopySignals()

    def _copySimulationsToDatabase(self, simulations: DBObjects, session) -> None:
        for simulation in simulations:
            if self.cancelled:
                break

            # Check if the target db is the same as the simulations db. If so, skip it.
            if simulation["dbHandler"].path == self.targetDB.path:
                self.progress += 1
                continue

            sim_model = simulation["dbHandler"].get_simulation_by_id(simulation["id"])
            if not sim_model:
                self.errors.append(
                    f"DB: {simulation['dbHandler'].filename}: {simulation['name']}"
                )
            else:
                pydantic_model = SimulationPydanticModel.from_model(sim_model)
                self.targetDB.add_simulation(pydantic_model, session=session)

            self.progress += 1
            self.signals.progressUpdated.emit(self.progress)

    def _copyCategoriesToDatabase(self, session):
        all_sims: DBObjects = []
        for category in self.objects:
            sims = category["dbHandler"].get_simulations_by_category(category["name"])
            all_sims.extend(
                [
                    DBObject(
                        type="simulation",
                        id=sim_id,
                        name=sim_name,
                        dbHandler=category["dbHandler"]
                    )
                    for sim_id, sim_name in sims
                ]
            )

        self.totalNrSimulations = len(all_sims)
        self._copySimulationsToDatabase(all_sims, session)

    def cancel(self):
        self.cancelled = True

    @pyqtSlot()
    def run(self):
        try:
            with self.targetDB.Session() as session:
                if self.objectType == "simulation":
                    self.totalNrSimulations = len(self.objects)
                    self._copySimulationsToDatabase(self.objects, session)
                elif self.objectType == "category":
                    self._copyCategoriesToDatabase(session)

                if self.cancelled:
                    session.rollback()
                    self.signals.progressErrorSummary.emit(True, 0, self.totalNrSimulations or 0, [])
                    return

                session.commit()

        except Exception as e:
            session.rollback()
            self.errors.append(str(e))

        copied = self.progress - len(self.errors)
        self.signals.progressErrorSummary.emit(False, copied, self.totalNrSimulations or 0, self.errors)


class CopyProgressDialog(QProgressDialog):
    def __init__(self, parent: QWidget, title: str, total: int):
        super().__init__("Copying simulations...", "Cancel", 0, total, parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setMinimumDuration(0)
