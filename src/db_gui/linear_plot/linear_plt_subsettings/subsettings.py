from typing import TypeVar

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QPushButton, QColorDialog, )
from matplotlib.artist import Artist

from ..dataset import Dataset
from ...widgets import CollapsibleGroupBox


class Subsetting(CollapsibleGroupBox):

    color_timer: QTimer
    color_button: QPushButton
    selected_color: QColor
    dataset: Dataset
    artist: Artist

    def _init_color_timer(self) -> None:
        self.color_timer = QTimer()
        self.color_timer.setSingleShot(True)
        self.color_timer.timeout.connect(self.update_color)  # type: ignore

    def _link_checkbox(self) -> None:
        self.checkbox.setChecked(self.artist.get_visible())
        self.checkbox.clicked.connect(self.on_enabled_change)

    def __init__(self, name: str, plotter: Dataset, artist: Artist) -> None:
        super().__init__(name)
        self.dataset = plotter
        self.artist = artist
        self._init_color_timer()
        self._link_checkbox()


    def draw_idle(self):
        self.dataset.redraw()

    @staticmethod
    def select_color() -> QColor:
        color = QColorDialog.getColor()
        if color.isValid():
            return color

    @staticmethod
    def set_button_color(button: QPushButton, color: QColor) -> None:
        """Apply a background color to a button."""
        button.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: {color.name()};
                                    color: {'black' if color.lightness() > 128 else 'white'};
                                }}
                            """)

    def on_color_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self.update_color_delayed)  # type: ignore
        dialog.open()  # <- non-blocking open, not exec()

    def update_color_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.selected_color = color
        self.color_timer.start(10)

    def update_color(self) -> None:
        ...

    def on_enabled_change(self, checked: bool) -> None:
        self.artist.set_visible(checked)
        self.draw_idle()

    def update_configuration(self) -> None:
        self.on_enabled_change(self.checkbox.isChecked())
        self.update_color()
