from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np
from ...shared import SignalProtocol


class ProcessingWorker(QObject):
    _finished = pyqtSignal(np.ndarray)
    finished: SignalProtocol[np.ndarray]

    def __init__(self, data: np.ndarray, func):
        super().__init__()
        self.data = data
        self.func = func

    def run(self):
        result = self.func(self.data)
        self.finished.emit(result)

