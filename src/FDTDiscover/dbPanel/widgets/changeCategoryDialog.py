from __future__ import annotations

from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QDialog, QListWidget, QDialogButtonBox, QLineEdit
                             )
from PyQt6.QtCore import pyqtSlot, Qt

from ..models import DBObjects
from ..signals import dbRightClickMenuSignalBus


class ChangeCategoryDialog(QDialog):
    """Dialog that allows the user to change the category of one or more simulations in a database."""

    simulations: DBObjects

    def __init__(self, simulations: DBObjects):
        super().__init__()
        self.setWindowTitle("Change Simulation Category")
        self.setMinimumWidth(300)

        # Set window modality
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Store the simulations
        self.simulations = simulations

        # Create layout
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select an existing category or type a new one:"))

        # Fetch all existing categories.
        categories = simulations[0]["dbHandler"].get_all_categories()

        # Create a list widget and add existing categories
        self.listWidget = QListWidget()
        self.listWidget.addItems(categories)
        layout.addWidget(self.listWidget)

        # Create an input field
        self.inputField = QLineEdit()
        self.inputField.setPlaceholderText("Enter or select a category...")
        layout.addWidget(self.inputField)

        # Sync list -> input field
        self.listWidget.itemClicked.connect(  # type: ignore
            self.syncListToInput)

        # Sync input -> list
        self.inputField.textChanged.connect(  # type: ignore
            self.syncInputToList)

        # Init buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(  # type: ignore
            self.accept)
        buttons.rejected.connect(  # type: ignore
            self.reject)
        layout.addWidget(buttons)

    @pyqtSlot()
    def accept(self):
        newCategory = self.getSelectedCategory()
        dbRightClickMenuSignalBus.changeCategory.emit(self.simulations, newCategory)
        super().accept()

    @pyqtSlot()
    def syncListToInput(self):
        item = self.listWidget.currentItem()
        if item:
            self.inputField.setText(item.text())

    @pyqtSlot(str)
    def syncInputToList(self, text: str):
        text = text.strip()
        found = False
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            if item.text() == text:
                self.listWidget.setCurrentItem(item)
                found = True
                break
        if not found:
            self.listWidget.clearSelection()

    def getSelectedCategory(self) -> str:
        return self.inputField.text().strip()
