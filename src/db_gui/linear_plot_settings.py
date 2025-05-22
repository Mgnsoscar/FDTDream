from __future__ import annotations
from typing import TypedDict, Dict, Optional, Any, List, Tuple, Union
from abc import ABC, abstractmethod

import matplotlib.font_manager as fm
import numpy as np
from PyQt6.QtCore import Qt, QTimer, QObject, QEvent
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QPushButton, QWidget,
    QVBoxLayout, QDialog, QGroupBox, QFormLayout, QLineEdit,
    QCheckBox, QColorDialog, QSpinBox, QComboBox, QScrollArea, QSlider, QHBoxLayout, QSizePolicy, QLabel,
)
from matplotlib.axes import Axes
from matplotlib.axis import XAxis, YAxis
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.text import Text
from numpy.typing import NDArray
from .widgets import CollapsibleGroupBox, ClickableLabel
from .fieldplot_tab_interface import FieldPlotTabInterface
# from .linear_plt_subsettings.text_settings import Title, LinearXLabel, LinearYLabel, XTicksSettings, YTicksSettings


class ArtistGroupBox(CollapsibleGroupBox):
    name: str
    artist: Line2D
    _parent: TPlotSettings
    label: str
    color_button: QPushButton
    color_timer: QTimer
    artist_color: Optional[QColor]
    x_units: Optional[str]
    y_units: Optional[str]
    original_x: NDArray
    original_y: NDArray
    XUNITS = ["Unitless", "nm", "um", "mm", "cm", "m"]
    YUNITS = ["Unitless", "%"]

    def __init__(self, name: str, parent: TPlotSettings, label: str, artist: Line2D,
                 x_label: str = None, y_label: str = None) -> None:
        super().__init__(name)
        self.name = name
        self.x_units = x_label
        self.y_units = y_label
        self.original_x = artist.get_xdata(orig=True)  # type: ignore
        self.original_y = artist.get_ydata(orig=True)  # type: ignore

        updownwidget = QWidget()
        updownlayout = QHBoxLayout()
        updownwidget.setLayout(updownlayout)
        self.move_artist_up_button = QPushButton("↑")
        self.move_artist_down_button = QPushButton("↓")
        for btn in [self.move_artist_up_button, self.move_artist_down_button]:
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn.setMinimumSize(24, 24)
        self.move_artist_up_button.clicked.connect(self.on_move_artist_up)  # type: ignore
        self.move_artist_down_button.clicked.connect(self.on_move_artist_down)  # type: ignore
        updownlayout.addWidget(self.move_artist_up_button)
        updownlayout.addWidget(self.move_artist_down_button)

        self.header.insertWidget(1, updownwidget)

        clickable_label = ClickableLabel(name, _parent=self)
        self.header.layout().removeWidget(self.title_label)
        self.title_label = clickable_label
        self.header.layout().insertWidget(2, self.title_label)

        self.checkbox.setChecked(True)
        self._parent = parent
        self.artist = artist if type(artist) is not list else artist[0]
        self.label = label
        self.artist_color = None
        self.checkbox.clicked.connect(self._on_artist_enabled_change)

        self._init_timers()
        self._init_ui()

    def _init_timers(self) -> None:
        self.color_timer = QTimer()
        self.color_timer.setSingleShot(True)
        self.color_timer.timeout.connect(self._update_artist_color)  # type: ignore

    def _init_ui(self) -> None:

        # Checkbox for inclusion in legend
        self.include_in_legend_checkbox = QCheckBox()
        self.include_in_legend_checkbox.setChecked(True)
        self.include_in_legend_checkbox.clicked.connect(self._on_include_in_legend_checked)  # type: ignore
        self.addRow("Include in legend", self.include_in_legend_checkbox)

        # Label input
        self.legend_label_edit = QLineEdit()
        self.legend_label_edit.setText(self.label)
        self.legend_label_edit.textChanged.connect(self._on_artist_label_change)  # type: ignore
        self.addRow("Legend label", self.legend_label_edit)

        # Line style dropdown
        self.linestyle_combo = QComboBox()
        linestyles = {
            "solid": "-",
            "dashed": "--",
            "dashdot": "-.",
            "dotted": ":"
        }
        for name in linestyles.keys():
            self.linestyle_combo.addItem(name)
        self.linestyle_combo.currentTextChanged.connect(self._on_artist_linestyle_change)  # type: ignore
        self.addRow("Line style", self.linestyle_combo)

        # Linewidth slider
        self.linewidth_slider = QSlider(Qt.Orientation.Horizontal)
        self.linewidth_slider.setRange(0, 1000)
        self.linewidth_slider.setValue(100)
        self.linewidth_slider.valueChanged.connect(self._on_artist_linewidth_change)  # type: ignore
        self.addRow("Linewidth", self.linewidth_slider)

        # Color picker button
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self._on_select_color)  # type: ignore
        self.addRow("Line color", self.color_button)

        # Alpha slider
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(int(self.artist.get_alpha() * 100) if self.artist.get_alpha() is not None else 100)
        self.alpha_slider.valueChanged.connect(self._on_artist_alpha_change)  # type: ignore
        self.addRow("Alpha (%)", self.alpha_slider)

        self._init_units()

    def _init_units(self) -> None:
        # --- Units settings group ---
        self.units_group = CollapsibleGroupBox("Units")
        self.units_group.checkbox.setVisible(False)

        # --- X Units row ---
        self.xunitswidget = QWidget()
        x_units_layout = QHBoxLayout()
        self.xunitswidget.setLayout(x_units_layout)

        # Original
        x_original_widget = QWidget()
        x_original_layout = QVBoxLayout()
        x_original_widget.setLayout(x_original_layout)
        x_original_label = QLabel("Original Units")
        self.x_original_units_combo = QComboBox()
        self.x_original_units_combo.addItems(self.XUNITS)
        x_original_layout.addWidget(x_original_label)
        x_original_layout.addWidget(self.x_original_units_combo)

        # New
        x_new_widget = QWidget()
        x_new_layout = QVBoxLayout()
        x_new_widget.setLayout(x_new_layout)
        x_new_label = QLabel("New Units")
        self.x_new_units_combo = QComboBox()
        self.x_new_units_combo.addItems(self.XUNITS)
        x_new_layout.addWidget(x_new_label)
        x_new_layout.addWidget(self.x_new_units_combo)

        # Add to main layout
        x_units_layout.addWidget(x_original_widget)
        x_units_layout.addWidget(x_new_widget)

        if self.x_units:
            for unit in self.XUNITS[::-1]:  # reverse to check longest units first
                if unit in self.x_units:
                    index = self.x_original_units_combo.findText(unit)
                    self.x_original_units_combo.setCurrentIndex(index)
                    self.x_new_units_combo.setCurrentIndex(index)

        self.units_group.addRow("X Units:", self.xunitswidget)

        # --- Y Units row ---
        self.yunitswidget = QWidget()
        y_units_layout = QHBoxLayout()
        self.yunitswidget.setLayout(y_units_layout)

        # Original
        y_original_widget = QWidget()
        y_original_layout = QVBoxLayout()
        y_original_widget.setLayout(y_original_layout)
        y_original_label = QLabel("Original Units")
        self.y_original_units_combo = QComboBox()
        self.y_original_units_combo.addItems(self.YUNITS)
        y_original_layout.addWidget(y_original_label)
        y_original_layout.addWidget(self.y_original_units_combo)

        # New
        y_new_widget = QWidget()
        y_new_layout = QVBoxLayout()
        y_new_widget.setLayout(y_new_layout)
        y_new_label = QLabel("New Units")
        self.y_new_units_combo = QComboBox()
        self.y_new_units_combo.addItems(self.YUNITS)
        y_new_layout.addWidget(y_new_label)
        y_new_layout.addWidget(self.y_new_units_combo)

        # Add to main layout
        y_units_layout.addWidget(y_original_widget)
        y_units_layout.addWidget(y_new_widget)

        if self.y_units:
            for unit in self.YUNITS:
                if unit in self.y_units:
                    index = self.y_original_units_combo.findText(unit)
                    self.y_original_units_combo.setCurrentIndex(index)
                    self.y_new_units_combo.setCurrentIndex(index)

        self.units_group.addRow("Y Units:", self.yunitswidget)

        # --- Connect signals ---
        self.x_original_units_combo.currentTextChanged.connect(self._on_x_convert)
        self.x_new_units_combo.currentTextChanged.connect(self._on_x_convert)
        self.y_original_units_combo.currentTextChanged.connect(self._on_y_convert)
        self.y_new_units_combo.currentTextChanged.connect(self._on_y_convert)

        # --- Add units group ---
        self.addRow("", self.units_group)

    def _on_x_convert(self) -> None:
        original = self.x_original_units_combo.currentText()
        new = self.x_new_units_combo.currentText()

        # Conversion factors in meters
        length_units = {
            "nm": 1e-9,
            "um": 1e-6,
            "mm": 1e-3,
            "cm": 1e-2,
            "m": 1.0,
        }
        if original == self.XUNITS[0] or new == self.XUNITS[0]:
            factor = 1
        else:
            factor = length_units[original] / length_units[new]

        xdata = self.original_x.copy()
        xdata = np.round(xdata * factor, decimals=15)
        self.artist.set_xdata(xdata)
        self._parent.apply_limits(update=True)

    def _on_y_convert(self) -> None:
        original = self.y_original_units_combo.currentText()
        new = self.y_new_units_combo.currentText()

        ydata = self.original_y.copy()

        if original == "%" and new == self.YUNITS[0]:
            ydata = np.round(ydata / 100.0, decimals=15)
        elif original == self.YUNITS[0] and new == "%":
            ydata = np.round(ydata * 100.0, decimals=15)
        else:
            pass

        self.artist.set_ydata(ydata)
        self._parent.apply_limits(update=True)

    def on_move_artist_up(self) -> None:

        artist_list = []
        for artist in self._parent.ax.lines:
            artist_list.append(artist)
            artist.remove()
        artist = self.artist

        if artist in artist_list:
            index = artist_list.index(artist)
            if index > 0:
                artist_list.pop(index)
                self._parent.artists.pop(index)
                artist_list.insert(index - 1, artist)
                self._parent.artists.insert(index - 1, self)
                self._parent.rebuild_artist_widgets()

        for artist in artist_list:
            self._parent.ax.add_artist(artist)

        self._parent.apply_legend_settings()

    def on_move_artist_down(self) -> None:
        artist_list = []
        for artist in self._parent.ax.lines:
            artist_list.append(artist)
            artist.remove()
        artist = self.artist

        if artist in artist_list:
            index = artist_list.index(artist)
            if index < len(artist_list) - 1:
                artist_list.pop(index)
                self._parent.artists.pop(index)
                artist_list.insert(index + 1, artist)
                self._parent.artists.insert(index + 1, self)
                self._parent.rebuild_artist_widgets()

        for artist in artist_list:
            self._parent.ax.add_artist(artist)

        self._parent.apply_legend_settings()

    def _on_select_color(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_artist_color_delayed)  # type: ignore
        dialog.open()  # non-blocking open, live color updates

    def _update_artist_color_delayed(self, color: QColor) -> None:
        self.artist_color = color
        self.color_timer.start(10)

    def _update_artist_color(self):
        color = self.artist_color
        if color.isValid():
            self.artist.set_color((
                color.redF(), color.greenF(), color.blueF()
            ))
            self.set_button_color(self.color_button, color)
            self._update_legend_handle()

    def _on_artist_linestyle_change(self, linestyle: str) -> None:
        self.artist.set_linestyle(linestyle)
        self._update_legend_handle()

    def _on_artist_linewidth_change(self, linewidth: float) -> None:
        self.artist.set_linewidth(linewidth / 100)
        self._update_legend_handle()

    def _on_artist_alpha_change(self, value: int) -> None:
        self.artist.set_alpha(value / 100)
        self._update_legend_handle()

    def _update_legend_handle(self) -> None:
        if self._parent.legend_group.checkbox.isChecked() and self.include_in_legend_checkbox.isChecked():
            self._parent.ax.legend(*self._parent.ax.get_legend_handles_labels())
            self._parent.apply_legend_settings()
        else:
            self._parent.update_fig()

    def _on_include_in_legend_checked(self, checked: bool) -> None:
        # for btn in [self.move_up_button, self.move_down_button]:
        #     btn.setEnabled(checked)

        if checked and self.checkbox.isChecked():
            label = self.legend_label_edit.text()
            self.artist.set_label(label)
        else:
            self.artist.set_label('_nolegend_')  # Exclude artist by label

        self._parent.apply_legend_settings()

    def _on_artist_label_change(self):
        self._on_include_in_legend_checked(self.include_in_legend_checkbox.isChecked())

    def _on_artist_enabled_change(self, enabled: bool) -> None:
        self.artist.set_visible(enabled)
        self.artist.set_label(self.legend_label_edit.text() if enabled else '_nolegend_')
        self._update_legend_handle()

    def _on_move_up_in_legend(self) -> None:
        handles, labels = self._parent.ax.get_legend_handles_labels()

        try:
            index = handles.index(self.artist)
        except ValueError:
            return  # Artist not found, do nothing

        if index > 0:
            # Swap with the one above
            handles[index], handles[index - 1] = handles[index - 1], handles[index]
            labels[index], labels[index - 1] = labels[index - 1], labels[index]

            self._parent.ax.legend(handles, labels)
            self._parent.apply_legend_settings()

    def _on_move_down_in_legend(self) -> None:
        handles, labels = self._parent.ax.get_legend_handles_labels()

        try:
            index = handles.index(self.artist)
        except ValueError:
            return  # Artist not found, do nothing

        if index < len(handles) - 1:
            # Swap with the one below
            handles[index], handles[index + 1] = handles[index + 1], handles[index]
            labels[index], labels[index + 1] = labels[index + 1], labels[index]

            self._parent.ax.legend(handles, labels)
            self._parent.apply_legend_settings()

    @staticmethod
    def set_button_color(button: QPushButton, color: QColor) -> None:
        """Apply a background color to a button."""
        button.setStyleSheet(f"""
                                QPushButton {{
                                    background-color: {color.name()};
                                    color: {'black' if color.lightness() > 128 else 'white'};
                                }}
                            """)


class AxisDict(TypedDict, total=False):
    ax: Axes
    title: Text
    x_label: Text
    y_label: Text
    xticks: XAxis
    yticks: YAxis
    legend: Optional[Legend]
    artists: Dict[str, Line2D]


class PlotSettingsWindow(QDialog):

    # region Defaults
    CALLBACK_DELAY = 10
    TITLE_DEFAULTS = {
        "text": "",
        "font": "Arial",
        "fontsize": 25,
        "color": QColor("black"),
        "placement": "center"
    }
    XLABEL_DEFAULTS = {
        "text": "",
        "font": "Arial",
        "fontsize": 25,
        "color": QColor("black"),
    }
    YLABEL_DEFAULTS = {
        "text": "",
        "font": "Arial",
        "fontsize": 25,
        "color": QColor("black"),
    }
    XTICK_DEFAULTS = {
        "font": "Arial",
        "fontsize": 12,
        "color": QColor("black"),
        "rotation": 0
    }
    YTICK_DEFAULTS = {
        "font": "Arial",
        "fontsize": 12,
        "color": QColor("black"),
        "rotation": 0
    }
    GRID_DEFAULTS = {
        "color": QColor("gray"),
        "alpha": 0.5,  # 50% transparent
        "linewidth": 1
    }
    # endregion Default

    # region Timers
    title_color_timer: QTimer
    xlabel_color_timer: QTimer
    ylabel_color_timer: QTimer
    xtick_color_timer: QTimer
    ytick_color_timer: QTimer
    grid_color_timer: QTimer
    legend_color_timer: QTimer
    # endregion Timers

    # region Vars
    _parent: FieldPlotTabInterface
    layout: QVBoxLayout
    title_selected_color: QColor
    xlabel_selected_color: QColor
    ylabel_selected_color: QColor
    xtick_selected_color: QColor
    ytick_selected_color: QColor
    grid_selected_color: QColor
    legend_selected_facecolor: QColor
    legend_selected_edgecolor: QColor

    title_group: CollapsibleGroupBox
    title_text: QLineEdit
    title_font: QComboBox
    title_fontsize: QSpinBox
    title_color_button: QPushButton
    title_placement: QComboBox

    xlabel_group: CollapsibleGroupBox
    xlabel_text: QLineEdit
    xlabel_font: QComboBox
    xlabel_fontsize: QSpinBox
    xlabel_color_button: QPushButton

    ylabel_group: CollapsibleGroupBox
    ylabel_text: QLineEdit
    ylabel_font: QComboBox
    ylabel_fontsize: QSpinBox
    ylabel_color_button: QPushButton

    xtick_group: CollapsibleGroupBox
    xtick_font: QComboBox
    xtick_fontsize: QSpinBox
    xtick_color_button: QPushButton
    xtick_rotation: QSpinBox

    ytick_group: CollapsibleGroupBox
    ytick_font: QComboBox
    ytick_fontsize: QSpinBox
    ytick_color_button: QPushButton
    ytick_rotation: QSpinBox

    grid_group: CollapsibleGroupBox
    grid_color_button: QPushButton
    grid_alpha: QSlider
    grid_linewidth: QSlider

    legend_group: CollapsibleGroupBox
    legend_location: QComboBox
    legend_font: QComboBox
    legend_fontsize: QSpinBox
    legend_facecolor_button: QPushButton
    legend_edgecolor_button: QPushButton
    legend_linewidth: QSlider
    legend_alpha: QSlider
    # endregion

    def __init__(self, parent: FieldPlotTabInterface):
        super().__init__()
        self._parent = parent
        self.setWindowTitle("Plot Settings")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.setMaximumWidth(600)
        self.setMaximumHeight(800)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        scroll.setWidget(content)
        self.layout = QVBoxLayout(content)

        self._init_timers()
        self.title_group = Title(self._parent)  # type: ignore
        self.xlabel_group = LinearXLabel(self._parent)  # type: ignore
        self.ylabel_group = LinearYLabel(self._parent)  # type: ignore
        self.xtick_group = XTicksSettings(self._parent)  # type: ignore
        self.ytick_group = YTicksSettings(self._parent)  # type: ignore
        self.layout.addWidget(self.title_group)
        self.layout.addWidget(self.xlabel_group)
        self.layout.addWidget(self.ylabel_group)
        self.layout.addWidget(self.xtick_group)
        self.layout.addWidget(self.ytick_group)
        self._add_grid_settings()

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        self.resize(self.sizeHint())  # <- resize nicely based on current widgets

    # region Inits
    def _init_timers(self) -> None:
        self.title_color_timer = QTimer(self)
        self.title_color_timer.setSingleShot(True)
        self.title_color_timer.timeout.connect(self._update_title_color)  # type: ignore

        self.xlabel_color_timer = QTimer(self)
        self.xlabel_color_timer.setSingleShot(True)
        self.xlabel_color_timer.timeout.connect(self._update_xlabel_color)  # type: ignore

        self.ylabel_color_timer = QTimer(self)
        self.ylabel_color_timer.setSingleShot(True)
        self.ylabel_color_timer.timeout.connect(self._update_ylabel_color)  # type: ignore

        self.xtick_color_timer = QTimer(self)
        self.xtick_color_timer.setSingleShot(True)
        self.xtick_color_timer.timeout.connect(self._update_xtick_color)  # type: ignore

        self.ytick_color_timer = QTimer(self)
        self.ytick_color_timer.setSingleShot(True)
        self.ytick_color_timer.timeout.connect(self._update_ytick_color)  # type: ignore

        self.grid_color_timer = QTimer(self)
        self.grid_color_timer.setSingleShot(True)
        self.grid_color_timer.timeout.connect(self._update_grid_color)  # type: ignore

    def _add_collapsible_group(self, title) -> Tuple[QFormLayout, QGroupBox]:
        group = QGroupBox(title)
        group.setCheckable(True)
        group.setChecked(True)
        form = QFormLayout()
        group.setLayout(form)
        self.layout.addWidget(group)
        return form, group
    # endregion Inits

    # region Helper Methods
    @staticmethod
    def get_available_fonts() -> List[str]:
        # Get all available font file paths
        font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')

        # Extract just the font names
        font_names = sorted({fm.FontProperties(fname=fp).get_name() for fp in font_paths})

        return font_names

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
    # endregion

    # region Properties
    @property
    @abstractmethod
    def title(self) -> Text:
        ...

    @property
    @abstractmethod
    def xlabel(self) -> Text:
        ...

    @property
    @abstractmethod
    def ylabel(self) -> Text:
        ...

    @property
    @abstractmethod
    def xticks(self) -> XAxis:
        ...

    @property
    @abstractmethod
    def yticks(self) -> YAxis:
        ...

    @property
    @abstractmethod
    def ax(self) -> Axes:
        ...

    @property
    def legend(self) -> Legend:
        return self.ax.legend()
    # endregion

    # region Title
    def _add_title_settings(self):
        available_fonts: List[str] = self.get_available_fonts()

        self.title_group = CollapsibleGroupBox("Title")
        self.title_group.checkbox.clicked.connect(self.on_title_visibility_change)
        self.on_title_visibility_change(self.title_group.checkbox.isChecked())
        self.layout.addWidget(self.title_group)

        # --- Title text input ---
        self.title_text = QLineEdit()
        self.title_text.setText(self.TITLE_DEFAULTS.get("text"))
        self.title_text.textChanged.connect(self.on_title_text_change)  # type: ignore
        self.title_group.addRow("Text:", self.title_text)

        # --- Font selection ---
        self.title_font = QComboBox()
        self.title_font.addItems(available_fonts)
        index = self.title_font.findText(self.TITLE_DEFAULTS.get("font"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.title_font.setCurrentIndex(index)
        self.title_font.currentTextChanged.connect(self.on_title_font_change)  # type: ignore
        self.title_group.addRow("Font:", self.title_font)

        # --- Font size selection ---
        self.title_fontsize = QSpinBox()
        self.title_fontsize.setRange(1, 100)
        self.title_fontsize.setValue(self.TITLE_DEFAULTS.get("fontsize"))
        self.title_fontsize.valueChanged.connect(self.on_title_fontsize_change)  # type: ignore
        self.title_group.addRow("Font Size:", self.title_fontsize)

        # --- Color selection ---
        self.title_color_button = QPushButton("Select Color")
        self.title_color_button.clicked.connect(self.on_title_color_change)  # type: ignore
        self.title_selected_color = self.TITLE_DEFAULTS.get("color")  # Will store selected QColor
        self.title_group.addRow("Color:", self.title_color_button)

        # --- Placement selection ---
        self.title_placement = QComboBox()
        self.title_placement.addItems(["center", "left", "right"])
        index = self.title_placement.findText(self.TITLE_DEFAULTS.get("placement"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.title_placement.setCurrentIndex(index)
        self.title_placement.currentTextChanged.connect(self.on_title_placement_change)  # type: ignore
        self.title_group.addRow("Placement:", self.title_placement)

        self.update_title()

    def on_title_color_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_title_color_delayed)  # type: ignore
        dialog.open()  # <- non-blocking open, not exec()

    def _update_title_color_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.title_selected_color = color
        self.title_color_timer.start(self.CALLBACK_DELAY)

    def _update_title_color(self) -> None:
        self.title_selected_color = self.title_selected_color
        self.set_button_color(self.title_color_button, self.title_selected_color)
        self.title.set_color((self.title_selected_color.redF(), self.title_selected_color.greenF(),
                             self.title_selected_color.blueF()))
        self.update_fig()

    def on_title_visibility_change(self, checked: bool) -> None:
        self.title.set_visible(checked)
        self.update_fig()

    def on_title_text_change(self, text: str) -> None:
        self.title.set_text(text)
        self.update_fig()

    def on_title_font_change(self, font: str) -> None:
        self.title.set_fontname(font)
        self.update_fig()

    def on_title_fontsize_change(self, size: float) -> None:
        self.title.set_fontsize(size)
        self.update_fig()

    def on_title_placement_change(self, placement: str) -> None:
        if placement == "right":
            self.title.set_horizontalalignment("left")
        elif placement == "left":
            self.title.set_horizontalalignment("right")
        else:
            self.title.set_horizontalalignment("center")
        self.update_fig()

    def update_title(self) -> None:
        self.on_title_text_change(self.title_text.text())
        self.on_title_font_change(self.title_font.currentText())
        self.on_title_fontsize_change(self.title_fontsize.value())
        self.on_title_placement_change(self.title_placement.currentText())
        self._update_title_color()

    # endregion Title

    # region X Label
    def _add_xlabel_settings(self):
        available_fonts: List[str] = self.get_available_fonts()

        self.xlabel_group = CollapsibleGroupBox("X Label")
        self.xlabel_group.checkbox.clicked.connect(self.on_xlabel_visibility_change)
        self.on_xlabel_visibility_change(self.xlabel_group.checkbox.isChecked())
        self.layout.addWidget(self.xlabel_group)

        # --- XLabel text input ---
        self.xlabel_text = QLineEdit()
        self.xlabel_text.setText(self.XLABEL_DEFAULTS.get("text"))
        self.xlabel_text.textChanged.connect(self.on_xlabel_text_change)  # type: ignore
        self.xlabel_group.addRow("Text:", self.xlabel_text)

        # --- Font selection ---
        self.xlabel_font = QComboBox()
        self.xlabel_font.addItems(available_fonts)
        index = self.xlabel_font.findText(self.XLABEL_DEFAULTS.get("font"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.xlabel_font.setCurrentIndex(index)
        self.xlabel_font.currentTextChanged.connect(self.on_xlabel_font_change)  # type: ignore
        self.xlabel_group.addRow("Font:", self.xlabel_font)

        # --- Font size selection ---
        self.xlabel_fontsize = QSpinBox()
        self.xlabel_fontsize.setRange(1, 100)
        self.xlabel_fontsize.setValue(self.XLABEL_DEFAULTS.get("fontsize"))
        self.xlabel_fontsize.valueChanged.connect(self.on_xlabel_fontsize_change)  # type: ignore
        self.xlabel_group.addRow("Font Size:", self.xlabel_fontsize)

        # --- Color selection ---
        self.xlabel_color_button = QPushButton("Select Color")
        self.xlabel_color_button.clicked.connect(self.on_xlabel_color_change)  # type: ignore
        self.xlabel_selected_color = self.XLABEL_DEFAULTS.get("color")
        self.xlabel_group.addRow("Color:", self.xlabel_color_button)

        self.update_xlabel()

    def on_xlabel_color_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_xlabel_color_delayed)  # type: ignore
        dialog.open()

    def _update_xlabel_color_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.xlabel_selected_color = color
        self.xlabel_color_timer.start(self.CALLBACK_DELAY)

    def _update_xlabel_color(self) -> None:
        self.xlabel_selected_color = self.xlabel_selected_color
        self.set_button_color(self.xlabel_color_button, self.xlabel_selected_color)
        self.xlabel.set_color((
            self.xlabel_selected_color.redF(),
            self.xlabel_selected_color.greenF(),
            self.xlabel_selected_color.blueF()
        ))
        self.update_fig()

    def on_xlabel_visibility_change(self, checked: bool) -> None:
        self.xlabel.set_visible(checked)
        self.update_fig()

    def on_xlabel_text_change(self, text: str) -> None:
        self.xlabel.set_text(text)
        self.update_fig()

    def on_xlabel_font_change(self, font: str) -> None:
        self.xlabel.set_fontname(font)
        self.update_fig()

    def on_xlabel_fontsize_change(self, size: float) -> None:
        self.xlabel.set_fontsize(size)
        self.update_fig()

    def update_xlabel(self) -> None:
        self.on_xlabel_text_change(self.xlabel_text.text())
        self.on_xlabel_font_change(self.xlabel_font.currentText())
        self.on_xlabel_fontsize_change(self.xlabel_fontsize.value())
        self._update_xlabel_color()

    # endregion X Label

    # region Y Label
    def _add_ylabel_settings(self):
        available_fonts: List[str] = self.get_available_fonts()

        self.ylabel_group = CollapsibleGroupBox("Y Label")
        self.ylabel_group.checkbox.clicked.connect(self.on_ylabel_visibility_change)
        self.on_ylabel_visibility_change(self.ylabel_group.checkbox.isChecked())
        self.layout.addWidget(self.ylabel_group)

        # --- YLabel text input ---
        self.ylabel_text = QLineEdit()
        self.ylabel_text.setText(self.YLABEL_DEFAULTS.get("text"))
        self.ylabel_text.textChanged.connect(self.on_ylabel_text_change)  # type: ignore
        self.ylabel_group.addRow("Text:", self.ylabel_text)

        # --- Font selection ---
        self.ylabel_font = QComboBox()
        self.ylabel_font.addItems(available_fonts)
        index = self.ylabel_font.findText(self.YLABEL_DEFAULTS.get("font"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.ylabel_font.setCurrentIndex(index)
        self.ylabel_font.currentTextChanged.connect(self.on_ylabel_font_change)  # type: ignore
        self.ylabel_group.addRow("Font:", self.ylabel_font)

        # --- Font size selection ---
        self.ylabel_fontsize = QSpinBox()
        self.ylabel_fontsize.setRange(1, 100)
        self.ylabel_fontsize.setValue(self.YLABEL_DEFAULTS.get("fontsize"))
        self.ylabel_fontsize.valueChanged.connect(self.on_ylabel_fontsize_change)  # type: ignore
        self.ylabel_group.addRow("Font Size:", self.ylabel_fontsize)

        # --- Color selection ---
        self.ylabel_color_button = QPushButton("Select Color")
        self.ylabel_color_button.clicked.connect(self.on_ylabel_color_change)  # type: ignore
        self.ylabel_selected_color = self.YLABEL_DEFAULTS.get("color")
        self.ylabel_group.addRow("Color:", self.ylabel_color_button)

        self.update_ylabel()

    def on_ylabel_color_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_ylabel_color_delayed)  # type: ignore
        dialog.open()

    def _update_ylabel_color_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.ylabel_selected_color = color
        self.ylabel_color_timer.start(self.CALLBACK_DELAY)

    def _update_ylabel_color(self) -> None:
        self.ylabel_selected_color = self.ylabel_selected_color
        self.set_button_color(self.ylabel_color_button, self.ylabel_selected_color)
        self.ylabel.set_color((
            self.ylabel_selected_color.redF(),
            self.ylabel_selected_color.greenF(),
            self.ylabel_selected_color.blueF()
        ))
        self.update_fig()

    def on_ylabel_visibility_change(self, checked: bool) -> None:
        self.ylabel.set_visible(checked)
        self.update_fig()

    def on_ylabel_text_change(self, text: str) -> None:
        self.ylabel.set_text(text)
        self.update_fig()

    def on_ylabel_font_change(self, font: str) -> None:
        self.ylabel.set_fontname(font)
        self.update_fig()

    def on_ylabel_fontsize_change(self, size: float) -> None:
        self.ylabel.set_fontsize(size)
        self.update_fig()

    def update_ylabel(self) -> None:
        self.on_ylabel_text_change(self.ylabel_text.text())
        self.on_ylabel_font_change(self.ylabel_font.currentText())
        self.on_ylabel_fontsize_change(self.ylabel_fontsize.value())
        self._update_ylabel_color()

    # endregion Y Label

    # region X Ticks
    def _add_xtick_settings(self):
        available_fonts: List[str] = self.get_available_fonts()

        self.xtick_group = CollapsibleGroupBox("X Ticks")
        self.xtick_group.checkbox.clicked.connect(self.on_xtick_visibility_change)
        self.xtick_group.checkbox.setChecked(True)
        self.layout.addWidget(self.xtick_group)

        # --- Font selection ---
        self.xtick_font = QComboBox()
        self.xtick_font.addItems(available_fonts)
        index = self.xtick_font.findText(self.XTICK_DEFAULTS.get("font"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.xtick_font.setCurrentIndex(index)
        self.xtick_font.currentTextChanged.connect(self.on_xtick_font_change)  # type: ignore
        self.xtick_group.addRow("Font:", self.xtick_font)

        # --- Font size selection ---
        self.xtick_fontsize = QSpinBox()
        self.xtick_fontsize.setRange(1, 100)
        self.xtick_fontsize.setValue(self.XTICK_DEFAULTS.get("fontsize"))
        self.xtick_fontsize.valueChanged.connect(self.on_xtick_fontsize_change)  # type: ignore
        self.xtick_group.addRow("Font Size:", self.xtick_fontsize)

        # --- Color selection ---
        self.xtick_color_button = QPushButton("Select Color")
        self.xtick_color_button.clicked.connect(self.on_xtick_color_change)  # type: ignore
        self.xtick_selected_color = self.XTICK_DEFAULTS.get("color")
        self.xtick_group.addRow("Color:", self.xtick_color_button)

        # --- Rotation ---
        self.xtick_rotation = QSpinBox()
        self.xtick_rotation.setRange(-180, 180)
        self.xtick_rotation.setValue(self.XTICK_DEFAULTS.get("rotation"))
        self.xtick_rotation.valueChanged.connect(self.on_xtick_rotation_change)  # type: ignore
        self.xtick_group.addRow("Rotation:", self.xtick_rotation)

        self.update_xtick()

    def on_xtick_color_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_xtick_color_delayed)  # type: ignore
        dialog.open()

    def _update_xtick_color_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.xtick_selected_color = color
        self.xtick_color_timer.start(self.CALLBACK_DELAY)

    def _update_xtick_color(self) -> None:
        self.xtick_selected_color = self.xtick_selected_color
        self.set_button_color(self.xtick_color_button, self.xtick_selected_color)

        # Apply color to all xtick labels
        for label in self.xticks.get_ticklabels():
            label.set_color((
                self.xtick_selected_color.redF(),
                self.xtick_selected_color.greenF(),
                self.xtick_selected_color.blueF()
            ))

        self.update_fig()

    def on_xtick_visibility_change(self, checked: bool) -> None:
        self.xticks.set_visible(checked)
        self.update_fig()

    def on_xtick_font_change(self, font: str) -> None:
        for label in self.xticks.get_ticklabels():
            label.set_fontname(font)
        self.update_fig()

    def on_xtick_fontsize_change(self, size: float) -> None:
        for label in self.xticks.get_ticklabels():
            label.set_fontsize(size)
        self.update_fig()

    def on_xtick_rotation_change(self, rotation: int) -> None:
        for label in self.xticks.get_ticklabels():
            label.set_rotation(rotation)
        self.update_fig()

    def update_xtick(self) -> None:
        self.on_xtick_font_change(self.xtick_font.currentText())
        self.on_xtick_fontsize_change(self.xtick_fontsize.value())
        self.on_xtick_rotation_change(self.xtick_rotation.value())
        self._update_xtick_color()

    # endregion X Ticks

    # region Y Ticks
    def _add_ytick_settings(self):
        available_fonts: List[str] = self.get_available_fonts()

        self.ytick_group = CollapsibleGroupBox("Y Ticks")
        self.ytick_group.checkbox.setChecked(True)
        self.ytick_group.checkbox.clicked.connect(self.on_ytick_visibility_change)
        self.layout.addWidget(self.ytick_group)

        # --- Font selection ---
        self.ytick_font = QComboBox()
        self.ytick_font.addItems(available_fonts)
        index = self.ytick_font.findText(self.YTICK_DEFAULTS.get("font"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.ytick_font.setCurrentIndex(index)
        self.ytick_font.currentTextChanged.connect(self.on_ytick_font_change)  # type: ignore
        self.ytick_group.addRow("Font:", self.ytick_font)

        # --- Font size selection ---
        self.ytick_fontsize = QSpinBox()
        self.ytick_fontsize.setRange(1, 100)
        self.ytick_fontsize.setValue(self.YTICK_DEFAULTS.get("fontsize"))
        self.ytick_fontsize.valueChanged.connect(self.on_ytick_fontsize_change)  # type: ignore
        self.ytick_group.addRow("Font Size:", self.ytick_fontsize)

        # --- Color selection ---
        self.ytick_color_button = QPushButton("Select Color")
        self.ytick_color_button.clicked.connect(self.on_ytick_color_change)  # type: ignore
        self.ytick_selected_color = self.YTICK_DEFAULTS.get("color")
        self.ytick_group.addRow("Color:", self.ytick_color_button)

        # --- Rotation ---
        self.ytick_rotation = QSpinBox()
        self.ytick_rotation.setRange(-180, 180)
        self.ytick_rotation.setValue(self.YTICK_DEFAULTS.get("rotation"))
        self.ytick_rotation.valueChanged.connect(self.on_ytick_rotation_change)  # type: ignore
        self.ytick_group.addRow("Rotation:", self.ytick_rotation)

        self.update_ytick()

    def on_ytick_color_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_ytick_color_delayed)  # type: ignore
        dialog.open()

    def _update_ytick_color_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.ytick_selected_color = color
        self.ytick_color_timer.start(self.CALLBACK_DELAY)

    def _update_ytick_color(self) -> None:
        self.ytick_selected_color = self.ytick_selected_color
        self.set_button_color(self.ytick_color_button, self.ytick_selected_color)

        for label in self.yticks.get_ticklabels():
            label.set_color((
                self.ytick_selected_color.redF(),
                self.ytick_selected_color.greenF(),
                self.ytick_selected_color.blueF()
            ))

        self.update_fig()

    def on_ytick_visibility_change(self, checked: bool) -> None:
        self.yticks.set_visible(checked)
        self.update_fig()

    def on_ytick_font_change(self, font: str) -> None:
        for label in self.yticks.get_ticklabels():
            label.set_fontname(font)
        self.update_fig()

    def on_ytick_fontsize_change(self, size: float) -> None:
        for label in self.yticks.get_ticklabels():
            label.set_fontsize(size)
        self.update_fig()

    def on_ytick_rotation_change(self, rotation: int) -> None:
        for label in self.yticks.get_ticklabels():
            label.set_rotation(rotation)
        self.update_fig()

    def update_ytick(self) -> None:
        self.on_ytick_font_change(self.ytick_font.currentText())
        self.on_ytick_fontsize_change(self.ytick_fontsize.value())
        self.on_ytick_rotation_change(self.ytick_rotation.value())
        self._update_ytick_color()

    # endregion Y Ticks

    # region Grid
    def _add_grid_settings(self):
        self.grid_group = CollapsibleGroupBox("Grid")
        self.grid_group.checkbox.setChecked(False)
        self.grid_group.checkbox.clicked.connect(self.on_grid_visibility_change)
        self.layout.addWidget(self.grid_group)

        # --- Color selection ---
        self.grid_color_button = QPushButton("Select Color")
        self.grid_color_button.clicked.connect(self.on_grid_color_change)  # type: ignore
        self.grid_selected_color = self.GRID_DEFAULTS.get("color")
        self.grid_group.addRow("Color:", self.grid_color_button)

        # --- Alpha selection ---
        self.grid_alpha = QSlider()
        self.grid_alpha.setOrientation(Qt.Orientation.Horizontal)
        self.grid_alpha.setRange(0, 100)  # 0% to 100% transparency
        self.grid_alpha.setSingleStep(1)
        self.grid_alpha.setValue(int(self.GRID_DEFAULTS.get("alpha") * 100))
        self.grid_alpha.valueChanged.connect(self.on_grid_alpha_change)  # type: ignore
        self.grid_group.addRow("Alpha (%):", self.grid_alpha)

        # --- Line Width selection ---
        self.grid_linewidth = QSlider()
        self.grid_linewidth.setOrientation(Qt.Orientation.Horizontal)
        self.grid_linewidth.setRange(1, 1000)
        self.grid_linewidth.setSingleStep(1)
        self.grid_linewidth.setValue(self.GRID_DEFAULTS.get("linewidth") * 100)
        self.grid_linewidth.valueChanged.connect(self.on_grid_linewidth_change)  # type: ignore
        self.grid_group.addRow("Line Width:", self.grid_linewidth)

        self.update_grid()

    def on_grid_color_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_grid_color_delayed)  # type: ignore
        dialog.open()

    def _update_grid_color_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.grid_selected_color = color
        self.grid_color_timer.start(self.CALLBACK_DELAY)

    def _update_grid_color(self) -> None:
        self.grid_selected_color = self.grid_selected_color
        self.set_button_color(self.grid_color_button, self.grid_selected_color)
        self.apply_grid_settings()

    def on_grid_visibility_change(self, checked: bool) -> None:
        self.ax.grid(checked)
        self.apply_grid_settings()

    def on_grid_alpha_change(self, value: int) -> None:
        self.apply_grid_settings()

    def on_grid_linewidth_change(self, value: int) -> None:
        self.apply_grid_settings()

    def apply_grid_settings(self) -> None:
        """Applies color, alpha, and linewidth to the grid lines."""
        color = (
            self.grid_selected_color.redF(),
            self.grid_selected_color.greenF(),
            self.grid_selected_color.blueF()
        )

        gridlines = self.ax.get_xgridlines() + self.ax.get_ygridlines()
        for line in gridlines:
            line.set_color(color)
            line.set_alpha(self.grid_alpha.value() / 100)
            line.set_linewidth(self.grid_linewidth.value() / 100)

        self.update_fig()

    def update_grid(self) -> None:
        self._update_grid_color()
        self.on_grid_alpha_change(self.grid_alpha.value())
        self.on_grid_linewidth_change(self.grid_linewidth.value())

    # endregion Grid

    # region Methods
    def update_fig(self) -> None:
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)
    # endregion


class TPlotSettings(PlotSettingsWindow):

    # region Timers
    legend_color_timer: QTimer
    limit_timer: QTimer
    # endregion

    # region Defaults
    LEGEND_DEFAULTS = {
        "location": "best",
        "font": "Arial",
        "fontsize": 12,
        "facecolor": QColor("white"),
        "edgecolor": QColor("grey"),
        "fontcolor": QColor("black"),
        "alpha": 1.0,
        "linewidth": 0.5
    }
    # endregion

    # region Vars
    _parent: Any
    artists: List[ArtistGroupBox]
    # endregion

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)

        self.legend_color_timer = QTimer()
        self.legend_color_timer.setSingleShot(True)
        self.legend_color_timer.timeout.connect(self.apply_legend_settings)  # type: ignore
        self.limit_timer = QTimer()
        self.limit_timer.setSingleShot(True)
        self.limit_timer.timeout.connect(self.apply_limits)  # type: ignore
        self.artists = []
        self._add_legend_settings()
        self._add_plot_limits_settings()
        self._add_aspect_ratio_settings()
        self._add_artist_settings()

    #region Artists
    def _add_artist_settings(self) -> None:
        self.artist_form = CollapsibleGroupBox("Artists")
        self.artist_form.checkbox.setVisible(False)
        self.layout.addWidget(self.artist_form)

    def add_artist(self, name: str, label: str, artist: Union[Line2D, List[Line2D]],
                   xlabel: str = None, ylabel: str = None) -> None:
        if type(artist) is list:
            artist = artist[0]

        new_artist = ArtistGroupBox(name, self, label, artist, x_label=xlabel, y_label=ylabel)
        self.artists.append(new_artist)
        self.artist_form.addRow("", new_artist)

        if self.legend_group.checkbox.isChecked():
            handles, labels = self.ax.get_legend_handles_labels()
            handles.append(artist)
            labels.append(label)
            self.ax.legend(handles, labels)
            self.apply_legend_settings()

    def add_existing_artist(self, artist: ArtistGroupBox) -> None:

        artist.artist.remove()
        artist._parent.artists.remove(artist)
        artist.setParent(None)
        artist._parent.clear_artists()
        artist._parent = self
        self.artists.append(artist)
        self.artist_form.addRow("", artist)
        self.ax.add_artist(artist.artist)
        artist.artist.set_transform(self.ax.transData)  # IMPORTANT: update data transform
        self.apply_legend_settings()
        self.update_fig()

    def rebuild_artist_widgets(self) -> None:
        layout = self.artist_form.content_area.layout()

        # Remove all widgets from layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if isinstance(widget, ArtistGroupBox):
                widget.setParent(None)  # Detach safely

        # Re-add all widgets in new order
        for widget in self.artists:
            layout.addWidget(widget)

    def clear_artists(self) -> None:
        layout = self.artist_form.content_area.layout()
        self.artist_form.remove_rows()
        self.artists.clear()

    # endregion

    # region Aspect Ratio
    def _add_aspect_ratio_settings(self) -> None:
        self.aspect_group = CollapsibleGroupBox("Aspect Ratio")
        self.aspect_group.checkbox.setVisible(False)
        self.layout.addWidget(self.aspect_group)

        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(["Auto", "1:1", "1:2", "2:1", "16:9", "4:3", "3:2"])
        self.aspect_ratio_combo.currentTextChanged.connect(self._on_aspect_ratio_changed)  # type: ignore

        self.aspect_group.addRow("Aspect:", self.aspect_ratio_combo)

    def _on_aspect_ratio_changed(self, ratio: str) -> None:
        ax = self.ax

        if ratio == "Auto":
            ax.set_box_aspect(None)  # Remove any fixed aspect
        else:
            try:
                w, h = map(float, ratio.split(":"))
                ax.set_box_aspect(h / w)  # Height relative to width!
            except Exception:
                ax.set_box_aspect(None)

        self.update_fig()

    # endregion

    # region Plot limits
    def _add_plot_limits_settings(self) -> None:

        self.limits_group = CollapsibleGroupBox("Plot Limits")
        self.limits_group.checkbox.setVisible(False)
        self.layout.addWidget(self.limits_group)

        # --- X Axis Limits ---
        x_widget = QWidget()
        x_layout = QHBoxLayout()
        x_widget.setLayout(x_layout)
        self.x_limit_mode = QComboBox()
        self.x_limit_mode.addItems(["Automatic", "Custom"])
        self.x_limit_mode.currentTextChanged.connect(self._on_x_limit_mode_changed)  # type: ignore

        self.x_min_edit = QLineEdit()
        self.x_max_edit = QLineEdit()
        self.x_min_edit.setPlaceholderText("Min")
        self.x_max_edit.setPlaceholderText("Max")
        self.x_min_edit.setEnabled(False)
        self.x_max_edit.setEnabled(False)

        x_layout.addWidget(self.x_limit_mode)
        x_layout.addWidget(self.x_min_edit)
        x_layout.addWidget(self.x_max_edit)

        self.limits_group.addRow("X Axis:", x_widget)

        # --- Y Axis Limits ---
        y_widget = QWidget()
        y_layout = QHBoxLayout()
        y_widget.setLayout(y_layout)
        self.y_limit_mode = QComboBox()
        self.y_limit_mode.addItems(["Automatic", "Custom"])
        self.y_limit_mode.currentTextChanged.connect(self._on_y_limit_mode_changed)  # type: ignore

        self.y_min_edit = QLineEdit()
        self.y_max_edit = QLineEdit()
        self.y_min_edit.setPlaceholderText("Min")
        self.y_max_edit.setPlaceholderText("Max")
        self.y_min_edit.setEnabled(False)
        self.y_max_edit.setEnabled(False)

        y_layout.addWidget(self.y_limit_mode)
        y_layout.addWidget(self.y_min_edit)
        y_layout.addWidget(self.y_max_edit)

        self.limits_group.addRow("Y Axis:", y_widget)

        # Connect changes to trigger update
        self.x_min_edit.textChanged.connect(self._apply_limits_delayed)  # type: ignore
        self.x_max_edit.textChanged.connect(self._apply_limits_delayed)  # type: ignore
        self.y_min_edit.textChanged.connect(self._apply_limits_delayed)  # type: ignore
        self.y_max_edit.textChanged.connect(self._apply_limits_delayed)  # type: ignore

    def _on_x_limit_mode_changed(self, mode: str) -> None:
        is_custom = mode == "Custom"
        self.x_min_edit.setEnabled(is_custom)
        self.x_max_edit.setEnabled(is_custom)
        self.apply_limits()

    def _on_y_limit_mode_changed(self, mode: str) -> None:
        is_custom = mode == "Custom"
        self.y_min_edit.setEnabled(is_custom)
        self.y_max_edit.setEnabled(is_custom)
        self.apply_limits()

    def _apply_limits_delayed(self):
        self.limit_timer.start(300)

    def apply_limits(self, update: bool = True) -> None:
        ax = self.ax

        # --- X Axis ---
        if self.x_limit_mode.currentText() == "Custom":
            xmin_text = self.x_min_edit.text()
            xmax_text = self.x_max_edit.text()

            try:
                xmin = float(xmin_text) if xmin_text else None
            except ValueError:
                xmin = None

            try:
                xmax = float(xmax_text) if xmax_text else None
            except ValueError:
                xmax = None

            ax.autoscale(enable=True, axis='x')
            ax.relim()
            ax.set_xlim(left=xmin if xmin is not None else None,
                        right=xmax if xmax is not None else None)
        else:
            ax.autoscale(enable=True, axis='x')
            ax.relim()

        # --- Y Axis ---
        if self.y_limit_mode.currentText() == "Custom":
            ymin_text = self.y_min_edit.text()
            ymax_text = self.y_max_edit.text()

            try:
                ymin = float(ymin_text) if ymin_text else None
            except ValueError:
                ymin = None

            try:
                ymax = float(ymax_text) if ymax_text else None
            except ValueError:
                ymax = None

            ax.autoscale(enable=True, axis='y')
            ax.relim()
            ax.set_ylim(bottom=ymin if ymin is not None else None,
                        top=ymax if ymax is not None else None)
        else:
            ax.autoscale(enable=True, axis='y')
            ax.relim()

        if update:
            self.update_fig()
    # endregion

    # region Legend
    def _add_legend_settings(self):
        available_fonts: List[str] = self.get_available_fonts()

        self.legend_group = CollapsibleGroupBox("Legend")
        self.legend_group.checkbox.setChecked(True)
        self.legend_group.checkbox.clicked.connect(self.on_legend_visibility_change)
        self.layout.addWidget(self.legend_group)

        # --- Location selection ---
        self.legend_location = QComboBox()
        locations = [
            "best", "upper right", "upper left", "lower left", "lower right",
            "right", "center left", "center right", "lower center", "upper center", "center"
        ]
        self.legend_location.addItems(locations)
        index = self.legend_location.findText(self.LEGEND_DEFAULTS.get("location"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.legend_location.setCurrentIndex(index)
        self.legend_location.currentTextChanged.connect(self.on_legend_location_change)  # type: ignore
        self.legend_group.addRow("Location:", self.legend_location)

        # --- Font selection ---
        self.legend_font = QComboBox()
        self.legend_font.addItems(available_fonts)
        index = self.legend_font.findText(self.LEGEND_DEFAULTS.get("font"), flags=Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.legend_font.setCurrentIndex(index)
        self.legend_font.currentTextChanged.connect(self.on_legend_font_change)  # type: ignore
        self.legend_group.addRow("Font:", self.legend_font)

        # --- Font size selection ---
        self.legend_fontsize = QSpinBox()
        self.legend_fontsize.setRange(1, 100)
        self.legend_fontsize.setValue(self.LEGEND_DEFAULTS.get("fontsize"))
        self.legend_fontsize.valueChanged.connect(self.on_legend_fontsize_change)  # type: ignore
        self.legend_group.addRow("Font Size:", self.legend_fontsize)

        # --- Font Color selection ---
        self.legend_fontcolor_button = QPushButton("Select Font Color")
        self.legend_fontcolor_button.clicked.connect(self.on_legend_fontcolor_change)  # type: ignore
        self.legend_selected_fontcolor = QColor(self.LEGEND_DEFAULTS.get("fontcolor"))  # Default: Black
        self.legend_group.addRow("Font Color:", self.legend_fontcolor_button)

        # --- Background Color selection ---
        self.legend_facecolor_button = QPushButton("Select Face Color")
        self.legend_facecolor_button.clicked.connect(self.on_legend_facecolor_change)  # type: ignore
        self.legend_selected_facecolor = self.LEGEND_DEFAULTS.get("facecolor")
        self.legend_group.addRow("Face Color:", self.legend_facecolor_button)

        # --- Edge Color selection ---
        self.legend_edgecolor_button = QPushButton("Select Edge Color")
        self.legend_edgecolor_button.clicked.connect(self.on_legend_edgecolor_change)  # type: ignore
        self.legend_selected_edgecolor = self.LEGEND_DEFAULTS.get("edgecolor")
        self.legend_group.addRow("Edge Color:", self.legend_edgecolor_button)

        # ---  Edge Linewidth ---
        self.legend_linewidth = QSlider()
        self.legend_linewidth.setOrientation(Qt.Orientation.Horizontal)
        self.legend_linewidth.setRange(1, 1000)
        self.legend_linewidth.setSingleStep(1)
        self.legend_linewidth.setValue(int(self.LEGEND_DEFAULTS.get("linewidth") * 100))
        self.legend_linewidth.valueChanged.connect(self.on_legend_linewidth_change)  # type: ignore
        self.legend_group.addRow("Edge Width:", self.legend_linewidth)

        # ---  Alpha ---
        self.legend_alpha = QSlider()
        self.legend_alpha.setOrientation(Qt.Orientation.Horizontal)
        self.legend_alpha.setRange(0, 100)
        self.legend_alpha.setSingleStep(1)
        self.legend_alpha.setValue(int(self.LEGEND_DEFAULTS.get("alpha") * 100))
        self.legend_alpha.valueChanged.connect(self.on_legend_alpha_change)  # type: ignore
        self.legend_group.addRow("Alpha (%):", self.legend_alpha)

        self.apply_legend_settings()

    def on_legend_facecolor_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_legend_facecolor_delayed)  # type: ignore
        dialog.open()

    def on_legend_edgecolor_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_legend_edgecolor_delayed)  # type: ignore
        dialog.open()

    def on_legend_fontcolor_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_legend_fontcolor_delayed)  # type: ignore
        dialog.open()

    def _update_legend_fontcolor_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.legend_selected_fontcolor = color
        self.legend_color_timer.start(self.CALLBACK_DELAY)

    def _update_legend_facecolor_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.legend_selected_facecolor = color
        self.legend_color_timer.start(self.CALLBACK_DELAY)

    def _update_legend_edgecolor_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.legend_selected_edgecolor = color
        self.legend_color_timer.start(self.CALLBACK_DELAY)

    def on_legend_visibility_change(self, checked: bool = None) -> None:
        if self.ax.legend_:
            has_handles = bool(self.ax.get_legend_handles_labels()[0])
            if checked is not None:
                self.ax.legend_.set_visible(checked and has_handles)
            else:
                self.ax.legend_.set_visible(self.legend_group.checkbox.isChecked() and has_handles)
        self.update_fig()

    def on_legend_location_change(self, location: str) -> None:
        if self.ax.legend_:
            self.ax.legend_.set_loc(location)
            self.update_fig()

    def on_legend_font_change(self, font: str) -> None:
        if self.ax.legend_:
            for text in self.ax.legend_.get_texts():
                text.set_fontname(font)
            self.update_fig()

    def on_legend_fontsize_change(self, size: int) -> None:
        if self.ax.legend_:
            for text in self.ax.legend_.get_texts():
                text.set_fontsize(size)
            self.update_fig()

    def on_legend_alpha_change(self, value: int) -> None:
        if self.ax.legend_:
            self.ax.legend_.get_frame().set_alpha(value / 100)
            self.update_fig()

    def on_legend_linewidth_change(self, width: int) -> None:
        if self.ax.legend_:
            self.ax.legend_.get_frame().set_linewidth(width / 100)
            self.update_fig()

    def apply_legend_settings(self) -> None:
        handles, labels = self.ax.get_legend_handles_labels()

        if not handles:
            self.on_legend_visibility_change(False)
            return
        else:
            self.on_legend_visibility_change()

        legend = self.ax.legend()
        if legend:
            face_color = (
                self.legend_selected_facecolor.redF(),
                self.legend_selected_facecolor.greenF(),
                self.legend_selected_facecolor.blueF()
            )
            edge_color = (
                self.legend_selected_edgecolor.redF(),
                self.legend_selected_edgecolor.greenF(),
                self.legend_selected_edgecolor.blueF()
            )
            frame = legend.get_frame()
            frame.set_facecolor(face_color)
            frame.set_edgecolor(edge_color)
            frame.set_alpha(self.legend_alpha.value() / 100.0)
            frame.set_linewidth(self.legend_linewidth.value() / 100)
            legend.set_loc(self.legend_location.currentText())
            for text in self.ax.legend_.get_texts():
                text.set_fontname(self.legend_font.currentText())
                text.set_fontsize(self.legend_fontsize.value())
                text.set_color((
                    self.legend_selected_fontcolor.redF(),
                    self.legend_selected_fontcolor.greenF(),
                    self.legend_selected_fontcolor.blueF()
                ))

            self.update_fig()

    def update_legend(self):
        self.ax.legend(*self.ax.get_legend_handles_labels())
        self.apply_legend_settings()

    # endregion Legend

    # region Properties
    @property
    def title(self) -> Text:
        return self._parent.get_current_ax().get("title")

    @property
    def xlabel(self) -> Text:
        return self._parent.get_current_ax().get("x_label")

    @property
    def ylabel(self) -> Text:
        return self._parent.get_current_ax().get("y_label")

    @property
    def xticks(self) -> XAxis:
        return self._parent.get_current_ax().get("xticks")

    @property
    def yticks(self) -> YAxis:
        return self._parent.get_current_ax().get("yticks")

    @property
    def ax(self) -> Axes:
        return self._parent.get_current_ax().get("ax")

    @property
    def legend(self) -> Legend:
        return self.ax.legend()
    # endregion
