from __future__ import annotations

from typing import Optional, Dict

from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QPushButton, QDialog, QTextEdit, QDialogButtonBox, QVBoxLayout
)

from ...shared import SignalProtocol


class InfoButton(QPushButton):
    """
    A button that shows a read-only info dialog containing the '__info__' string from parameters.
    """

    class Dialog(QDialog):
        dialog_closed = pyqtSignal()
        text_edit: QTextEdit

        def __init__(self, parent: InfoButton):
            super().__init__(parent)
            self.setWindowTitle("Information")
            layout = QVBoxLayout(self)
            self.text_edit = QTextEdit()
            self.text_edit.setReadOnly(True)
            layout.addWidget(self.text_edit)

            # Close button only
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(  # type: ignore
                self.reject)
            layout.addWidget(buttons)

            self.setMinimumSize(400, 300)

        def set_text(self, content: str) -> None:
            self.text_edit.setPlainText(content)

        def closeEvent(self, event):
            self.dialog_closed.emit()  # type: ignore
            super().closeEvent(event)

    info: Optional[str]
    dialog: Optional[Dialog]

    def __init__(self, button_text: str, population_requested: SignalProtocol[Dict]):
        super().__init__(button_text)
        self.info = None
        self.dialog = None
        self.setEnabled(False)

        population_requested.connect(self.populate_info)  # type: ignore
        self.clicked.connect(self.toggle_info_dialog)     # type: ignore

    @pyqtSlot(dict)
    def populate_info(self, params: dict) -> None:
        """
        Called when a new object is selected in the tree. Updates stored info and dialog.
        """
        self.info = params.get("__info__", None)
        self.setEnabled(bool(self.info))

        if self.dialog:
            if self.info:
                self.dialog.set_text(self.info)
            else:
                self.dialog.close()

    @pyqtSlot()
    def toggle_info_dialog(self):
        """
        Handles dialog open/close toggle behavior.
        """
        if not self.info:
            return

        if self.dialog and self.dialog.isVisible():
            self.dialog.close()
        else:
            self.dialog = self.Dialog(self)
            self.dialog.set_text(self.info)
            self.dialog.dialog_closed.connect(  # type: ignore
                self.clear_dialog_reference)
            self.dialog.show()

    @pyqtSlot()
    def clear_dialog_reference(self):
        """
        Clears the dialog reference when it is closed.
        """
        self.dialog = None

