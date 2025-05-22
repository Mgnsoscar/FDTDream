from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QVBoxLayout, QDialog, QTextEdit, QDialogButtonBox
)

from ..models import DBObject
from ..signals import dbRightClickMenuSignalBus


class EditInfoDialog(QDialog):

    original_info: str
    obj: DBObject

    def __init__(self, obj: DBObject, originalInfo: str) -> None:
        super().__init__()

        # Set window modality
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Store attributes
        self.original_info = originalInfo
        self.obj = obj

        # Set title
        title = "Edit Simulation Information" if obj["type"] == "simulation" else "Edit Monitor Information"
        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)

        # Create main layout
        layout = QVBoxLayout(self)

        # Add the text edit
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.original_info)
        self.original_info = self.text_edit.toPlainText()
        layout.addWidget(self.text_edit)

        # Create the buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        # Add the save button.
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setEnabled(False)

        self.text_edit.textChanged.connect(  # type: ignore
            self.on_text_changed)
        buttons.accepted.connect(  # type: ignore
            self.on_save)
        buttons.rejected.connect(  # type: ignore
            self.reject)

    @pyqtSlot()
    def on_text_changed(self):
        self.save_button.setEnabled(self.text_edit.toPlainText() != self.original_info)

    @pyqtSlot()
    def on_save(self):
        new_text = self.text_edit.toPlainText()
        dbRightClickMenuSignalBus.editInfo.emit(self.obj, new_text)
        self.close()