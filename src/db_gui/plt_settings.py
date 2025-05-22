from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QWidget,
    QVBoxLayout, QDialog, QGroupBox, QFormLayout, QLineEdit,
    QCheckBox, QColorDialog, QLabel, QSpinBox, QComboBox, QScrollArea, QSlider
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
import sys
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.axis import XAxis, YAxis
from matplotlib.axes import Axes
from typing import TypedDict, Dict, Optional, Any, List, Tuple
from matplotlib.legend import Legend
from matplotlib.text import Text
from .widgets import CollapsibleGroupBox
from .fieldplot_tab_interface import FieldPlotTabInterface


class AxisDict(TypedDict, total=False):
    ax: Axes
    title: Text
    x_label: Text
    y_label: Text
    xticks: XAxis
    yticks: YAxis
    legend: Optional[Legend]
    artists: Dict[str, Line2D]


class PlotSettings(QDialog):

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
        "text": "x [nm]",
        "font": "Arial",
        "fontsize": 18,
        "color": QColor("black"),
    }
    YLABEL_DEFAULTS = {
        "text": "y [nm]",
        "font": "Arial",
        "fontsize": 18,
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
    LEGEND_DEFAULTS = {
        "location": "best",
        "font": "Arial",
        "fontsize": 12,
        "facecolor": QColor("white"),
        "edgecolor": QColor("black"),
        "alpha": 1.0,
        "linewidth": 1.0
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
    title_selected_color: QColor
    # endregion

    def __init__(self, parent: Any):
        super().__init__()
        self._parent = parent
        self.setWindowTitle("Plot Settings")
        self.setMinimumWidth(400)

        # Scrollable area for many settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Main widget inside scroll
        content = QWidget()
        scroll.setWidget(content)
        self.layout = QVBoxLayout(content)

        # --- Add collapsible sections ---
        self._init_timers()
        self._add_title_settings()
        self._add_xlabel_settings()
        self._add_ylabel_settings()
        self._add_xtick_settings()
        self._add_ytick_settings()
        self._add_grid_settings()
        # self._add_legend_settings()

        self.equal_aspect = CollapsibleGroupBox("Equal Aspect Ratio")
        self.equal_aspect.toggle_button.setVisible(False)
        self.equal_aspect.checkbox.clicked.connect(self.on_equal_aspect_change)
        self.layout.addWidget(self.equal_aspect)

        # self._add_artist_settings()

        # Set scroll area layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        self.on_title_visibility_change(self.title_group.checkbox.isChecked())

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

        self.legend_color_timer = QTimer(self)
        self.legend_color_timer.setSingleShot(True)
        self.legend_color_timer.timeout.connect(self.apply_legend_settings)  # type: ignore

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
    def title(self) -> Text:
        return self._parent.title

    @property
    def xlabel(self) -> Text:
        return self._parent.x_label

    @property
    def ylabel(self) -> Text:
        return self._parent.y_label

    @property
    def xticks(self) -> XAxis:
        return self._parent.ax.xaxis

    @property
    def yticks(self) -> YAxis:
        return self._parent.ax.yaxis

    @property
    def ax(self) -> Axes:
        return self._parent.ax

    @property
    def legend(self) -> Legend:
        return self.ax.get_legend()
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
        self.xlabel_group.checkbox.setChecked(True)
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
        self.ylabel_group.checkbox.setChecked(True)
        self.ylabel_group.checkbox.clicked.connect(self.on_ylabel_visibility_change)
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
        self.ax.tick_params(axis="x", labelbottom=checked)
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
        self.ax.tick_params(axis="y", labelleft=checked)
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

    # region Legend
    def _add_legend_settings(self):
        available_fonts: List[str] = self.get_available_fonts()

        self.legend_group = CollapsibleGroupBox("Legend")
        self.legend_group.checkbox.setChecked(False)
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

        self.update_legend()

    def on_legend_facecolor_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_legend_facecolor_delayed)  # type: ignore
        dialog.open()

    def on_legend_edgecolor_change(self) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(self._update_legend_edgecolor_delayed)  # type: ignore
        dialog.open()

    def _update_legend_facecolor_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.legend_selected_facecolor = color
        self.legend_color_timer.start(self.CALLBACK_DELAY)

    def _update_legend_edgecolor_delayed(self, color: QColor) -> None:
        if color.isValid():
            self.legend_selected_edgecolor = color
        self.legend_color_timer.start(self.CALLBACK_DELAY)

    def on_legend_visibility_change(self, checked: bool) -> None:
        if self.legend:
            self.legend.set_visible(checked)
        self.update_fig()

    def on_legend_location_change(self, location: str) -> None:
        if self.legend:
            self.legend.set_loc(location)
        self.update_fig()

    def on_legend_font_change(self, font: str) -> None:
        if self.legend:
            for text in self.legend.get_texts():
                text.set_fontname(font)
        self.update_fig()

    def on_legend_fontsize_change(self, size: int) -> None:
        if self.legend:
            for text in self.legend.get_texts():
                text.set_fontsize(size)
        self.update_fig()

    def on_legend_alpha_change(self, value: int) -> None:
        self.apply_legend_settings()

    def on_legend_linewidth_change(self, width: int) -> None:
        self.apply_legend_settings()

    def apply_legend_settings(self) -> None:
        """Apply face and edge colors and alpha separately."""
        if self.legend:
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
            frame = self.legend.get_frame()
            frame.set_facecolor(face_color)
            frame.set_edgecolor(edge_color)
            frame.set_alpha(self.legend_alpha.value() / 100.0)
            frame.set_linewidth(self.legend_linewidth.value() / 100)
        self.update_fig()

    def update_legend(self) -> None:
        self._parent.legend = self._parent.ax.legend()
        self._update_legend_facecolor_delayed(self.legend_selected_facecolor)
        self._update_legend_edgecolor_delayed(self.legend_selected_edgecolor)
        self.on_legend_font_change(self.legend_font.currentText())
        self.on_legend_fontsize_change(self.legend_fontsize.value())
        self.on_legend_location_change(self.legend_location.currentText())

    # endregion Legend

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

    #region Artists
    def _add_artist_settings(self):
        self.artist_form = CollapsibleGroupBox("Artists")
        self.artist_form.checkbox.setVisible(False)
        self.layout.addWidget(self.artist_form)

        # Field Map Artist
        self.quadmesh_artist = CollapsibleGroupBox("Field Map")
        self.artist_form.addRow("", self.quadmesh_artist)
        self._setup_artist_controls(
            self.quadmesh_artist,
            default_label="Field Map",
            on_include=self.on_quadmesh_include_change,
            on_label=self.on_quadmesh_label_change,
        )

        # Vector Plot Artist
        self.quiver_artist = CollapsibleGroupBox("Vector Plot")
        self.artist_form.addRow("", self.quiver_artist)
        self._setup_artist_controls(
            self.quiver_artist,
            default_label="Vector Plot",
            on_include=self.on_quiver_include_change,
            on_label=self.on_quiver_label_change,
        )

    def _setup_artist_controls(self, group: CollapsibleGroupBox, default_label: str, on_include, on_label) -> None:
        group.checkbox.setVisible(False)

        # Include in Legend checkbox
        group.include_checkbox = QCheckBox()
        group.include_checkbox.clicked.connect(on_include)
        group.addRow("Include in legend", group.include_checkbox)

        # Label input
        group.label_edit = QLineEdit()
        group.label_edit.setText(default_label)
        group.label_edit.textChanged.connect(on_label)
        group.addRow("Label:", group.label_edit)

    def on_quadmesh_include_change(self, checked: bool) -> None:
        if self._parent.quadmesh:
            self._parent.quadmesh.set_label(None if not checked else self.quadmesh_artist.label_edit.text())
            print(self._parent.quadmesh.get_label())
            self.update_legend()
            self.update_fig()

    def on_quadmesh_label_change(self, text: str) -> None:
        if self._parent.quadmesh and self.quadmesh_artist.include_checkbox.isChecked():
            self._parent.quadmesh.set_label(text)
            self.update_legend()

    def on_quiver_include_change(self, checked: bool) -> None:
        if self._parent.quiver:
            self._parent.quiver.set_label(None if not checked else self.quiver_artist.label_edit.text())
            self.update_legend()

    def on_quiver_label_change(self, text: str) -> None:
        if self._parent.quiver and self.quiver_artist.include_checkbox.isChecked():
            self._parent.quiver.set_label(text)
            self.update_legend()

    # endregion Artists

    def on_equal_aspect_change(self, checked: bool) -> None:
        self._parent.ax.set_aspect("equal" if checked else "auto")
        self.update_fig()

    def update_fig(self) -> None:
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)
