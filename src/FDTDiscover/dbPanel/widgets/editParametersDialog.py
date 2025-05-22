from __future__ import annotations

import textwrap
from enum import Enum
from typing import Any, cast, List, Tuple, Optional, Union, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QPoint, pyqtSlot
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction, QFont, QCursor
from PyQt6.QtWidgets import (
    QTreeView, QVBoxLayout, QLabel, QMenu, QDialog, QTextEdit, QPushButton, QApplication,
    QMessageBox, QFileDialog, QInputDialog, QProgressDialog, QListWidget, QDialogButtonBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QAbstractItemView
)

from ..models import DBObjects
from ..signals import dbRightClickMenuSignalBus


class EditParametersDialog(QDialog):

    objects: DBObjects
    originalParameters: dict
    parameters: dict

    def __init__(self, objects: DBObjects, originalParameters: dict[str, str]):
        super().__init__()

        # Copy the original parameters for reference and copy to new parameter dict for changes.
        self.originalParameters = originalParameters.copy()
        self.parameters = originalParameters.copy()

        # Store the objects
        self.objects = objects

        # Set window modality
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Set title and size
        isMultiple = len(objects) > 1
        objType = objects[0]["type"]
        if objType == "simulation":
            title = "Edit Shared Simulation Paramerters" if isMultiple else "Edit Simulation Parameters"
        elif objType == "monitor":
            title = "Edit Shared Monitor Parameters" if isMultiple else "Edit Monitor Parameters"
        else:
            raise ValueError(f"Expected object type 'simulation' or 'monitor', got '{objType}'.")
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)

        # Create main layout
        layout = QVBoxLayout(self)

        self.table = QTableWidget(len(self.parameters), 2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Populate table and add to layout
        for row, (key, value) in enumerate(originalParameters.items()):
            self.table.setItem(row, 0, QTableWidgetItem(key))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))
        layout.addWidget(self.table)

        # Add buttons
        btn_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Row")
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.setEnabled(False)
        btn_layout.addWidget(self.add_button)
        btn_layout.addWidget(self.remove_button)
        layout.addLayout(btn_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setEnabled(False)
        layout.addWidget(buttons)

        # Connect signals
        self.table.itemChanged.connect(  # type: ignore
            self._onItemChanged)
        self.table.itemSelectionChanged.connect(  # type: ignore
            self._onSelectionChanged)
        self.add_button.clicked.connect(  # type: ignore
            self._addRow)
        self.remove_button.clicked.connect(  # type: ignore
            self._removeSelectedRows)
        buttons.accepted.connect(  # type: ignore
            self.accept)
        buttons.rejected.connect(  # type: ignore
            self.reject)

    @pyqtSlot()
    def accept(self):
        # Fetch parameters, sort keys alphabetically and emit signal
        newParameters = dict(sorted(self._getUpdatedParameters().items()))
        dbRightClickMenuSignalBus.editParams.emit(self.objects, self.originalParameters, newParameters)
        super().accept()

    @pyqtSlot()
    def _onItemChanged(self):
        self.save_button.setEnabled(self.originalParameters != self._getUpdatedParameters())

    @pyqtSlot()
    def _onSelectionChanged(self):
        selected_rows = {index.row() for index in self.table.selectedIndexes()}
        rows_to_remove = []

        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            key_empty = not key_item or not key_item.text().strip()
            val_empty = not val_item or not val_item.text().strip()

            if key_empty and val_empty and row not in selected_rows:
                rows_to_remove.append(row)

        for row in reversed(rows_to_remove):
            self.table.removeRow(row)

        has_selection = bool(selected_rows)
        self.remove_button.setEnabled(has_selection)

    @pyqtSlot()
    def _addRow(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        key_item = QTableWidgetItem("")
        self.table.setItem(row, 0, key_item)
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setCurrentCell(row, 0)
        self.table.editItem(key_item)

    @pyqtSlot()
    def _removeSelectedRows(self):
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            self.table.itemSelectionChanged.disconnect(  # type: ignore
                self._onSelectionChanged)

            self.table.removeRow(row)

            self.table.itemSelectionChanged.connect(  # type: ignore
                self._onSelectionChanged)

        self._onSelectionChanged()
        self._onItemChanged()

    def _getUpdatedParameters(self) -> dict[str, str]:
        updated = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            if key_item and val_item and key_item.text().strip():
                updated[key_item.text()] = val_item.text()
        return updated
