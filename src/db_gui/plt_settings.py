import re
from typing import Dict, List, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QLineEdit, QPushButton, QSpinBox,
    QToolBox, QVBoxLayout, QWidget, QLabel, QSizePolicy, QColorDialog
)

from .fieldplot_tab_interface import FieldPlotTabInterface
import matplotlib.font_manager as fm


class PlotSettings(QWidget):
    """Widget providing user-configurable plot appearance settings."""

    # region Signals
    title_settings_changed = pyqtSignal(dict)
    xlabel_settings_changed = pyqtSignal(dict)
    ylabel_settings_changed = pyqtSignal(dict)
    tick_settings_changed = pyqtSignal(dict)
    grid_settings_changed = pyqtSignal(dict)
    legend_settings_changed = pyqtSignal(dict)
    equal_aspect_changed = pyqtSignal(bool)
    # endregion

    # region Member variables
    _parent: FieldPlotTabInterface
    _layout = QVBoxLayout

    toolbox: QToolBox
    sections: Dict[str, QWidget]

    title_edit: QLineEdit
    title_font_combo: QComboBox
    title_size_spin: QSpinBox
    title_color_btn: QPushButton
    title_align_combo: QComboBox

    xlabel_edit: QLineEdit
    xlabel_font_combo: QComboBox
    xlabel_size_spin: QSpinBox
    xlabel_color_btn: QPushButton

    ylabel_edit: QLineEdit
    ylabel_font_combo: QComboBox
    ylabel_size_spin: QSpinBox
    ylabel_color_btn: QPushButton

    ticks_font_combo: QComboBox
    ticks_size_spin: QSpinBox
    tick_rotation_spin: QSpinBox

    grid_checkbox: QCheckBox
    grid_style_combo: QComboBox

    legend_checkbox: QCheckBox
    legend_font_combo: QComboBox
    legend_size_spin: QSpinBox
    legend_location_combo: QComboBox
    legend_bg_color_btn: QPushButton

    aspect_checkbox: QCheckBox

    title_color: QColor
    xlabel_color: QColor
    ylabel_color: QColor
    legend_bg_color: QColor
    # endregion

    def __init__(self, parent: FieldPlotTabInterface):
        super().__init__()  # type: ignore

        self._parent = parent

        self.sections = {}
        fonts = self.get_available_fonts()

        # === Main layout with toolbox ===
        self._layout = QVBoxLayout(self)
        self.toolbox = QToolBox(self)
        self.toolbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout.addWidget(self.toolbox)

        self._init_title_section(fonts)
        self._init_xlabel_section(fonts)
        self._init_ylabel_section(fonts)
        self._init_tick_section(fonts)
        self._init_grid_section()
        self._init_legend_section(fonts)
        self._init_aspect_section()

        self._init_colors()
        self._connect_signals()

    # region Widget innit
    def _init_title_section(self, fonts: list[str]) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        self.title_edit = QLineEdit()
        self.title_font_combo = QComboBox()
        self.title_font_combo.addItems(fonts)
        self.title_font_combo.setCurrentIndex(self.title_font_combo.findText("Arial"))
        self.title_size_spin = QSpinBox()
        self.title_size_spin.setRange(6, 72)
        self.title_size_spin.setValue(24)
        self.title_color_btn = QPushButton("Choose Color")
        self.title_align_combo = QComboBox()
        self.title_align_combo.addItems(["center", "left", "right"])

        layout.addWidget(QLabel("Text:"))
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("Font:"))
        layout.addWidget(self.title_font_combo)
        layout.addWidget(QLabel("Size:"))
        layout.addWidget(self.title_size_spin)
        layout.addWidget(self.title_color_btn)
        layout.addWidget(QLabel("Alignment:"))
        layout.addWidget(self.title_align_combo)

        self._add_section(widget, "Title Settings")

    def _init_xlabel_section(self, fonts: list[str]) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        self.xlabel_edit = QLineEdit()
        self.xlabel_font_combo = QComboBox()
        self.xlabel_font_combo.addItems(fonts)
        self.xlabel_size_spin = QSpinBox()
        self.xlabel_size_spin.setRange(6, 72)
        self.xlabel_size_spin.setValue(12)
        self.xlabel_color_btn = QPushButton("Choose Color")

        layout.addWidget(QLabel("Text:"))
        layout.addWidget(self.xlabel_edit)
        layout.addWidget(QLabel("Font:"))
        layout.addWidget(self.xlabel_font_combo)
        layout.addWidget(QLabel("Size:"))
        layout.addWidget(self.xlabel_size_spin)
        layout.addWidget(self.xlabel_color_btn)

        self._add_section(widget, "X Label Settings")

    def _init_ylabel_section(self, fonts: list[str]) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        self.ylabel_edit = QLineEdit()
        self.ylabel_font_combo = QComboBox()
        self.ylabel_font_combo.addItems(fonts)
        self.ylabel_size_spin = QSpinBox()
        self.ylabel_size_spin.setRange(6, 72)
        self.ylabel_size_spin.setValue(12)
        self.ylabel_color_btn = QPushButton("Choose Color")

        layout.addWidget(QLabel("Text:"))
        layout.addWidget(self.ylabel_edit)
        layout.addWidget(QLabel("Font:"))
        layout.addWidget(self.ylabel_font_combo)
        layout.addWidget(QLabel("Size:"))
        layout.addWidget(self.ylabel_size_spin)
        layout.addWidget(self.ylabel_color_btn)

        self._add_section(widget, "Y Label Settings")

    def _init_tick_section(self, fonts: list[str]) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        self.ticks_font_combo = QComboBox()
        self.ticks_font_combo.addItems(fonts)
        self.ticks_size_spin = QSpinBox()
        self.ticks_size_spin.setRange(6, 72)
        self.ticks_size_spin.setValue(10)
        self.tick_rotation_spin = QSpinBox()
        self.tick_rotation_spin.setRange(0, 90)

        layout.addWidget(QLabel("Font:"))
        layout.addWidget(self.ticks_font_combo)
        layout.addWidget(QLabel("Size:"))
        layout.addWidget(self.ticks_size_spin)
        layout.addWidget(QLabel("Label Rotation:"))
        layout.addWidget(self.tick_rotation_spin)

        self._add_section(widget, "Tick Settings")

    def _init_grid_section(self) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_style_combo = QComboBox()
        self.grid_style_combo.addItems(["solid", "dashed", "dotted", "dashdot"])

        layout.addWidget(self.grid_checkbox)
        layout.addWidget(QLabel("Grid Style:"))
        layout.addWidget(self.grid_style_combo)

        self._add_section(widget, "Grid Settings")

    def _init_legend_section(self, fonts: list[str]) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        self.legend_checkbox = QCheckBox("Show Legend")
        self.legend_font_combo = QComboBox()
        self.legend_font_combo.addItems(fonts)
        self.legend_size_spin = QSpinBox()
        self.legend_size_spin.setRange(6, 72)
        self.legend_size_spin.setValue(10)
        self.legend_location_combo = QComboBox()
        self.legend_location_combo.addItems([
            "best", "upper right", "upper left", "lower left", "lower right",
            "right", "center left", "center right", "lower center", "upper center", "center"
        ])
        self.legend_bg_color_btn = QPushButton("Choose Background Color")

        layout.addWidget(self.legend_checkbox)
        layout.addWidget(QLabel("Font:"))
        layout.addWidget(self.legend_font_combo)
        layout.addWidget(QLabel("Size:"))
        layout.addWidget(self.legend_size_spin)
        layout.addWidget(QLabel("Location:"))
        layout.addWidget(self.legend_location_combo)
        layout.addWidget(self.legend_bg_color_btn)

        self._add_section(widget, "Legend Settings")

    def _init_aspect_section(self) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        self.aspect_checkbox = QCheckBox("Equal Aspect Ratio")
        self.aspect_checkbox.setCheckState(Qt.CheckState.Unchecked)

        layout.addWidget(self.aspect_checkbox)
        self._add_section(widget, "Aspect Ratio")

    def _init_colors(self) -> None:
        """Initialize the default colors and apply them to the corresponding buttons."""
        self.title_color = QColor(0, 0, 0)
        self.xlabel_color = QColor(0, 0, 0)
        self.ylabel_color = QColor(0, 0, 0)
        self.legend_bg_color = QColor(255, 255, 255)

        self.set_button_color(self.title_color_btn, self.title_color)
        self.set_button_color(self.xlabel_color_btn, self.xlabel_color)
        self.set_button_color(self.ylabel_color_btn, self.ylabel_color)
        self.set_button_color(self.legend_bg_color_btn, self.legend_bg_color)

    def _connect_signals(self) -> None:
        """Connect all interactive signals to appropriate handlers (to be implemented)."""

        self.title_edit.textChanged.connect(self.emit_title_settings)  # type: ignore
        self.title_font_combo.currentTextChanged.connect(self.emit_title_settings)  # type: ignore
        self.title_size_spin.valueChanged.connect(self.emit_title_settings)  # type: ignore
        self.title_color_btn.clicked.connect(self.pick_title_color)  # type: ignore
        self.title_align_combo.currentTextChanged.connect(self.emit_title_settings)  # type: ignore

        self.xlabel_edit.textChanged.connect(self.emit_xlabel_settings)  # type: ignore
        self.xlabel_font_combo.currentTextChanged.connect(self.emit_xlabel_settings)  # type: ignore
        self.xlabel_size_spin.valueChanged.connect(self.emit_xlabel_settings)  # type: ignore
        self.xlabel_color_btn.clicked.connect(self.pick_xlabel_color)  # type: ignore

        self.ylabel_edit.textChanged.connect(self.emit_ylabel_settings)  # type: ignore
        self.ylabel_font_combo.currentTextChanged.connect(self.emit_ylabel_settings)  # type: ignore
        self.ylabel_size_spin.valueChanged.connect(self.emit_ylabel_settings)  # type: ignore
        self.ylabel_color_btn.clicked.connect(self.pick_ylabel_color)  # type: ignore

        self.ticks_font_combo.currentTextChanged.connect(self.emit_tick_settings)  # type: ignore
        self.ticks_size_spin.valueChanged.connect(self.emit_tick_settings)  # type: ignore
        self.tick_rotation_spin.valueChanged.connect(self.emit_tick_settings)  # type: ignore

        self.grid_checkbox.toggled.connect(self.emit_grid_settings)  # type: ignore
        self.grid_style_combo.currentTextChanged.connect(self.emit_grid_settings)  # type: ignore

        self.legend_checkbox.toggled.connect(self.emit_legend_settings)  # type: ignore
        self.legend_font_combo.currentTextChanged.connect(self.emit_legend_settings)  # type: ignore
        self.legend_size_spin.valueChanged.connect(self.emit_legend_settings)  # type: ignore
        self.legend_location_combo.currentTextChanged.connect(self.emit_legend_settings)  # type: ignore
        self.legend_bg_color_btn.clicked.connect(self.pick_legend_bg_color)  # type: ignore

        self.aspect_checkbox.toggled.connect(self.on_aspect_ratio_changed)  # type: ignore
    # endregion

    # region Section management
    def _add_section(self, widget: QWidget, label: str) -> None:
        """Add a section to the toolbox and track it in the sections dictionary."""
        self.toolbox.addItem(widget, label)
        self.sections[label] = widget
    # endregion

    # region Color picking
    def pick_title_color(self):
        color = QColorDialog.getColor(self.title_color)
        if color.isValid():
            self.title_color = color
            self.set_button_color(self.title_color_btn, color)
            self.emit_title_settings()

    def pick_xlabel_color(self):
        color = QColorDialog.getColor(self.xlabel_color)
        if color.isValid():
            self.xlabel_color = color
            self.set_button_color(self.xlabel_color_btn, color)
            self.emit_xlabel_settings()

    def pick_ylabel_color(self):
        color = QColorDialog.getColor(self.ylabel_color)
        if color.isValid():
            self.ylabel_color = color
            self.set_button_color(self.ylabel_color_btn, color)
            self.emit_ylabel_settings()

    def pick_legend_bg_color(self):
        color = QColorDialog.getColor(self.legend_bg_color)
        if color.isValid():
            self.legend_bg_color = color
            self.set_button_color(self.legend_bg_color_btn, color)
            self.emit_legend_settings()

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

    # region Emissions
    def emit_title_settings(self):
        settings = {
            "text": self.title_edit.text(),
            "font": self.title_font_combo.currentText(),
            "size": self.title_size_spin.value(),
            "color": self.title_color,
            "align": self.title_align_combo.currentText()
        }
        self.on_title_changed(settings)

    def emit_xlabel_settings(self):
        settings = {  # type: ignore
            "text": self.xlabel_edit.text(),
            "font": self.xlabel_font_combo.currentText(),
            "size": self.xlabel_size_spin.value(),
            "color": self.xlabel_color
        }
        self.on_xlabel_changed(settings)

    def emit_ylabel_settings(self):
        settings = {
            "text": self.ylabel_edit.text(),
            "font": self.ylabel_font_combo.currentText(),
            "size": self.ylabel_size_spin.value(),
            "color": self.ylabel_color
        }
        self.on_ylabel_changed(settings)

    def emit_tick_settings(self):
        self.tick_settings_changed.emit({  # type: ignore
            "font": self.ticks_font_combo.currentText(),
            "size": self.ticks_size_spin.value(),
            "rotation": self.tick_rotation_spin.value()
        })

    def emit_grid_settings(self):
        self.grid_settings_changed.emit({  # type: ignore
            "shown": self.grid_checkbox.isChecked(),
            "style": self.grid_style_combo.currentText()
        })

    def emit_legend_settings(self):
        settings = {
            "shown": self.legend_checkbox.isChecked(),
            "font": self.legend_font_combo.currentText(),
            "size": self.legend_size_spin.value(),
            "location": self.legend_location_combo.currentText(),
            "background_color": self.qcolor_to_rgb(self.legend_bg_color)
        }
        self.on_legend_changed(settings)
    # endregion

    # region Callbacks
    def on_aspect_ratio_changed(self, val: bool) -> None:
        if val:
            self._parent.ax.set_aspect("equal")
        else:
            self._parent.ax.set_aspect("auto")
        self._parent.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)
        self._parent.canvas.draw_idle()

    def on_title_changed(self, settings: dict) -> None:
        """Update the plot title according to settings."""

        if self._parent.title is None:
            return

        self._parent.title.set_text(settings.get("text", ""))
        self._parent.title.set_fontfamily(settings.get("font", "Arial"))
        self._parent.title.set_fontsize(settings.get("size", 14))

        color = settings.get("color", QColor("black"))
        self._parent.title.set_color(color.name())  # Convert QColor to hex string

        align = settings.get("align", "center")
        if align == "center":
            self._parent.title.set_horizontalalignment("center")
        elif align == "left":
            self._parent.title.set_horizontalalignment("right")  # These are opposite for some wierd reason.
        elif align == "right":
            self._parent.title.set_horizontalalignment("left")

        # Force canvas redraw
        self._parent.canvas.draw_idle()

    def on_xlabel_changed(self, settings: dict) -> None:
        """Update the xlabel according to settings."""

        if self._parent.x_label is None:
            return

        self._parent.x_label.set_text(settings.get("text", ""))
        self._parent.x_label.set_fontfamily(settings.get("font", "Arial"))
        self._parent.x_label.set_fontsize(settings.get("size", 14))

        color = settings.get("color", QColor("black"))
        self._parent.x_label.set_color(color.name())  # Convert QColor to hex string

        # Force canvas redraw
        self._parent.canvas.draw_idle()

    def on_ylabel_changed(self, settings: dict) -> None:
        """Update the ylabel according to settings."""

        if self._parent.y_label is None:
            return

        self._parent.y_label.set_text(settings.get("text", ""))
        self._parent.y_label.set_fontfamily(settings.get("font", "Arial"))
        self._parent.y_label.set_fontsize(settings.get("size", 14))

        color = settings.get("color", QColor("black"))
        self._parent.y_label.set_color(color.name())  # Convert QColor to hex string

        # Force canvas redraw
        self._parent.canvas.draw_idle()

    def on_xticks_changed(self, settings: dict) -> None:
        ...

    def on_yticks_changed(self, settings: dict) -> None:
        ...

    def on_legend_changed(self, settings: dict):
        self._parent.legend = self._parent.ax.legend()
        legend = self._parent.legend

        # Show/hide legend
        legend.set_visible(settings.get("shown", True))

        legend.prop.set_name(settings.get("font", "Arial"))
        legend.prop.set_size(settings.get("size", 10))

        # Update location
        legend.set_loc(settings.get("location", "best"))

        # Update background color
        bg_color = settings.get("background_color")
        if bg_color:
            legend.get_frame().set_facecolor(bg_color)

        # Redraw canvas
        self._parent.canvas.draw_idle()

    def on_grid_changed(self, settings: dict) -> None:
        ...
    # endregion

    # region Methods
    @staticmethod
    def get_available_fonts() -> List[str]:
        # Get all available font file paths
        font_paths = fm.findSystemFonts(fontpaths=None, fontext='ttf')

        # Extract just the font names
        font_names = sorted({fm.FontProperties(fname=fp).get_name() for fp in font_paths})

        return font_names

    @staticmethod
    def qcolor_to_rgb(color: QColor) -> Tuple[float, float, float]:
        return color.redF(), color.greenF(), color.blueF()
    # endregion
