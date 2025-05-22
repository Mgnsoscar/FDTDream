from abc import ABC, abstractmethod
from typing import List, Dict, TypeVar, Union

import matplotlib.font_manager as fm
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QPushButton, QLineEdit, QSlider,
    QColorDialog, QSpinBox, QComboBox, )
from matplotlib.artist import Artist
from matplotlib.axis import Axis, XAxis, YAxis
from matplotlib.text import Text

from .subsettings import Subsetting
from ..dataset import Dataset


class TextSetting(Subsetting):

    artist: Union[Artist, Text]
    font: QComboBox
    fontsize: QSpinBox

    def _init_font_selection(self) -> None:
        available_fonts: List[str] = self.get_available_fonts()
        self.font = QComboBox()
        self.font.wheelEvent = lambda event: None
        self.font.addItems(available_fonts)
        index = self.font.findText(self.artist.get_fontname(), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.font.setCurrentIndex(index)
        self.font.currentTextChanged.connect(self.on_font_change)  # type: ignore
        self.addRow("Font:", self.font)

    def _init_font_size_selection(self) -> None:
        self.fontsize = QSpinBox()
        self.fontsize.wheelEvent = lambda event: None
        self.fontsize.setRange(1, 100)
        self.fontsize.setValue(int(self.artist.get_fontsize()))
        self.fontsize.valueChanged.connect(self.on_fontsize_change)  # type: ignore
        self.addRow("Font Size:", self.fontsize)

    def _init_color_selection(self) -> None:
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self.on_color_change)  # type: ignore
        self.selected_color = QColor(*[int(color) for color in self.artist.get_color()])
        self.set_button_color(self.color_button, self.selected_color)
        self.addRow("Color:", self.color_button)

    def __init__(self, name: str, plotter: Dataset, artist: Union[Artist, Text]):
        super().__init__(name, plotter, artist)

        self._link_checkbox()
        self._init_font_selection()
        self._init_font_size_selection()
        self._init_color_selection()

    @staticmethod
    def get_available_fonts() -> List[str]:
        # Get all available font file paths
        font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')

        # Extract just the font names
        font_names = sorted({fm.FontProperties(fname=fp).get_name() for fp in font_paths})

        return font_names

    # region Callbacks

    def on_font_change(self, font: str) -> None:
        self.artist.set_fontname(font)
        self.draw_idle()

    def on_fontsize_change(self, size: float) -> None:
        self.artist.set_fontsize(size)
        self.draw_idle()

    def update_color(self) -> None:
        color = self.selected_color
        self.set_button_color(self.color_button, self.selected_color)
        self.artist.set_color((color.redF(), color.greenF(), color.blueF()))
        self.draw_idle()

    def update_configuration(self) -> None:
        self.on_font_change(self.font.currentText())
        self.on_fontsize_change(self.fontsize.value())
        self.update_color()

    # endregion


class EditableTextSettings(TextSetting):

    input: QLineEdit

    def _init_text_input(self) -> None:
        self.input = QLineEdit()
        self.input.setText(self.artist.get_text())
        self.input.textChanged.connect(self.on_text_change)  # type: ignore
        self.insert_row(0, "Text:", self.input)

    def __init__(self, name: str, dataset: Dataset, artist: Text) -> None:
        super().__init__(name, dataset, artist)
        self._init_text_input()

    def on_text_change(self, text: str) -> None:
        self.artist.set_text(text)
        self.draw_idle()

    def update_configuration(self) -> None:
        super().update_configuration()
        self.on_text_change(self.input.text())


class TicksSetting(TextSetting):

    artist: Axis

    def _init_rotation_selection(self) -> None:
        # --- Rotation ---
        self.rotation = QSpinBox()
        self.rotation.wheelEvent = lambda event: None
        self.rotation.setRange(-180, 180)
        self.rotation.setValue(self.artist.get_tick_params()["rotation"])
        self.rotation.valueChanged.connect(self.on_rotation_change)  # type: ignore
        self.addRow("Rotation:", self.rotation)

    def _init_font_size_selection(self) -> None:
        self.fontsize = QSpinBox()
        self.fontsize.wheelEvent = lambda event: None
        self.fontsize.setRange(1, 100)
        self.fontsize.setValue(int(self.artist.get_tick_params()["labelsize"]))
        self.fontsize.valueChanged.connect(self.on_fontsize_change)  # type: ignore
        self.addRow("Font Size:", self.fontsize)

    def _init_color_selection(self) -> None:
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self.on_color_change)  # type: ignore
        self.selected_color = QColor(*[int(color) for color in self.artist.get_tick_params()["labelcolor"]])
        self.set_button_color(self.color_button, self.selected_color)
        self.addRow("Color:", self.color_button)

    def _init_font_selection(self) -> None:
        available_fonts: List[str] = self.get_available_fonts()
        self.font = QComboBox()
        self.font.wheelEvent = lambda event: None
        self.font.addItems(available_fonts)
        index = self.font.findText(self.artist.get_tick_params()["labelfontfamily"], flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.font.setCurrentIndex(index)
        self.font.currentTextChanged.connect(self.on_font_change)  # type: ignore
        self.addRow("Font:", self.font)

    def _link_checkbox(self) -> None:
        params = self.artist.get_tick_params()
        if "labelbottom" in params:
            self.checkbox.setChecked(self.artist.get_tick_params()['labelbottom'])
        else:
            self.checkbox.setChecked(self.artist.get_tick_params()['labelleft'])
        self.checkbox.clicked.connect(self.on_enabled_change)

    def __init__(self, name: str, plotter: Dataset, artist: Axis) -> None:
        super().__init__(name, plotter, artist)
        self._init_rotation_selection()

    def on_enabled_change(self, checked: bool) -> None:
        self.artist.set_tick_params("both", labelbottom=checked)
        self.draw_idle()

    def update_color(self) -> None:
        color = self.selected_color
        self.set_button_color(self.color_button, color)
        self.artist.set_tick_params("both", labelcolor=(color.redF(), color.greenF(), color.blueF()))
        self.draw_idle()

    def on_font_change(self, font: str) -> None:
        self.artist.set_tick_params("both", labelfontfamily=font)
        self.draw_idle()

    def on_fontsize_change(self, size: float) -> None:
        self.artist.set_tick_params("both", labelsize=size)
        self.draw_idle()

    def on_rotation_change(self, rotation: int) -> None:
        self.artist.set_tick_params("both", labelrotation=rotation)
        self.draw_idle()

    def update_configuration(self) -> None:
        super().update_configuration()
        self.on_rotation_change(self.rotation.value())


class GridSetting(Subsetting):

    def __init__(self, name: str, dataset: Dataset, artist: Axis) -> None:
        super().__init__(name, dataset, artist)

        # Check if the grid is on:
        xOn = dataset.ax.xaxis.get_tick_params()["gridOn"]
        yOn = dataset.ax.yaxis.get_tick_params()["gridOn"]
        if not xOn and yOn:
            if xOn:
                text = "x"
            elif yOn:
                text = "y"
            else:
                self.checkbox.setChecked(False)
                text = None
        else:
            text = "both"

        self._init_axis_selector(text)
        self._init_linewidth_slider()
        self._init_alpha_slider()
        self._init_color_button()

    def _init_axis_selector(self, text: Union[str, None]) -> None:
        self.axis_selector = QComboBox()
        self.axis_selector.addItems(["x", "y", "both"])
        self.axis_selector.setCurrentText(text if text else "both")
        self.axis_selector.currentTextChanged.connect(self.on_axis_change)
        self.addRow("Grid Axis:", self.axis_selector)

    def _init_linewidth_slider(self) -> None:
        self.linewidth = QSlider(Qt.Orientation.Horizontal)
        self.linewidth.setRange(1, 100)
        self.linewidth.setValue(int(self.dataset.xaxis.get_tick_params()["grid_linewidth"] * 100))
        self.linewidth.setSingleStep(1)
        self.linewidth.valueChanged.connect(self.on_linewidth_change)
        self.addRow("Grid Width:", self.linewidth)

    def _init_alpha_slider(self) -> None:
        self.alpha = QSlider(Qt.Orientation.Horizontal)
        self.alpha.setRange(0, 100)
        self.alpha.setValue(int(self.dataset.xaxis.get_tick_params()["grid_alpha"] * 100))
        self.alpha.setSingleStep(1)
        self.alpha.valueChanged.connect(self.on_alpha_change)
        self.addRow("Grid Alpha:", self.alpha)

    def _init_color_button(self) -> None:
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self.on_color_change)
        self.selected_color = QColor(*[int(color) for color in self.dataset.xaxis.get_tick_params()["grid_color"]])
        self.set_button_color(self.color_button, self.selected_color)
        self.addRow("Grid Color:", self.color_button)

    def update_color(self) -> None:
        color = self.selected_color
        self.set_button_color(self.color_button, self.selected_color)
        self.dataset.ax.tick_params('both', grid_color=(color.redF(), color.greenF(), color.blueF()))
        self.draw_idle()

    def on_alpha_change(self, alpha: float) -> None:
        self.dataset.ax.tick_params("both", grid_alpha=alpha/100)
        self.draw_idle()

    def on_linewidth_change(self, lw: float) -> None:
        self.dataset.ax.tick_params("both", grid_linewidth=lw/100)
        self.draw_idle()

    def on_axis_change(self, axis: str) -> None:
        if not self.checkbox.isChecked():
            self.dataset.ax.tick_params("both", gridOn=False)
            self.draw_idle()
            return

        if axis == "both":
            self.dataset.ax.tick_params("both", gridOn=True)
        elif axis == "x":
            self.dataset.ax.tick_params("x", gridOn=True)
            self.dataset.ax.tick_params("y", gridOn=False)
        else:
            self.dataset.ax.tick_params("y", gridOn=True)
            self.dataset.ax.tick_params("x", gridOn=False)
        self.draw_idle()

    def on_enabled_change(self, checked: bool) -> None:
        self.on_axis_change(self.axis_selector.currentText())
