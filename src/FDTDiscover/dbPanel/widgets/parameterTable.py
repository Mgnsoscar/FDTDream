from __future__ import annotations

from typing import cast, Dict

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QTableWidget, QVBoxLayout, QLabel, QTableWidgetItem,
    QHeaderView
)

from ...shared import SignalProtocol


class ParameterTable(QWidget):

    # Attributes
    label: QLabel
    table: QTableWidget
    header: QHeaderView

    def __init__(self, label: str, population_requested: SignalProtocol[Dict]):
        super().__init__()

        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 5)

        # Add the label
        self.label = QLabel(label)
        layout.addWidget(self.label)

        # Create the table widget
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Resize behavior
        self.header = self.table.horizontalHeader()
        self.header.setStretchLastSection(True)
        self.header.setSectionResizeMode(0, self.header.ResizeMode.Stretch)

        # Connect the population_requested signal to the population method.
        population_requested.connect(self.populate_parameters)  # type: ignore

    @pyqtSlot(dict)
    def populate_parameters(self, params: dict):

        # Pop out the __info__ parameter if any.
        params = params.copy()  # Make sure original dictionary is not change by the popping.
        params.pop("__info__", None)

        # Populate the parameters
        self.table.setRowCount(len(params))
        for row, (key, value) in enumerate(params.items()):
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))

    def layout(self) -> QVBoxLayout:
        return cast(super().layout(), QVBoxLayout)
