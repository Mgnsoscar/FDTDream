from __future__ import annotations

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QSpinBox, QLabel, QComboBox, QCheckBox, QDoubleSpinBox,
                             QDialogButtonBox, QWidget, QFileDialog)
from matplotlib.figure import Figure

from ..models import SaveFigureState
from ...signal_busses import SAVE_FIGURE_SIGNAL_BUS


class SaveFigureWidget(QDialog):
    """Widget opened when the user tries to save the current plot contents. Is managed by the SaveFigureController."""

    # region Attributes
    dpi_input: QSpinBox
    transparent_checkbox: QCheckBox
    bbox_combo: QComboBox
    pad_label: QLabel
    pad_input: QDoubleSpinBox
    figure: Figure
    # endregion

    def __init__(self, parent: QWidget, figure: Figure):
        super().__init__(parent)

        # Store the signal bus as an attribute and request the initial state.
        self.figure = figure
        self._initialize_connections()

        # Request the initial state
        SAVE_FIGURE_SIGNAL_BUS.init_state_requested.emit()

    def _initialize_connections(self) -> None:
        """Connects the appropriate signals from the signal bus."""
        SAVE_FIGURE_SIGNAL_BUS.init_state_reply.connect(self._init_UI)
        SAVE_FIGURE_SIGNAL_BUS.set_pad_visible.connect(self.on_pad_visible_change)

    def _init_UI(self, state: SaveFigureState) -> None:
        """Initializes the widget when the init_state_reply signal is detected."""

        # Set window options
        self.setWindowTitle("Save Figure Options")
        self.setMinimumWidth(300)

        # Create the layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # DPI input
        dpi_label = QLabel("DPI:")
        dpi_label.setToolTip("Dots per inch (image resolution). Higher values give better quality.")
        self.dpi_input = QSpinBox()
        self.dpi_input.setRange(50, 1000)
        self.dpi_input.setValue(state["dpi"])
        self.dpi_input.setToolTip("Image resolution in dots per inch.")
        layout.addWidget(dpi_label)
        layout.addWidget(self.dpi_input)

        # Transparent background
        self.transparent_checkbox = QCheckBox("Transparent Background")
        self.transparent_checkbox.setChecked(state["transparent"])
        self.transparent_checkbox.setToolTip(
            "Save figure with a transparent background (only for formats that support it).")
        layout.addWidget(self.transparent_checkbox)

        # bbox_inches option
        bbox_label = QLabel("Bounding Box:")
        bbox_label.setToolTip("Controls layout tightness. 'tight' removes extra whitespace.")
        self.bbox_combo = QComboBox()
        self.bbox_combo.addItems(["tight", "standard", "None"])
        value = state["bbox_inches"]
        self.bbox_combo.setCurrentText(value if value is not None else "None")
        self.bbox_combo.setToolTip("Determines how much of the surrounding whitespace is included.")
        layout.addWidget(bbox_label)
        layout.addWidget(self.bbox_combo)

        # pad_inches
        self.pad_label = QLabel("Padding (inches):")
        self.pad_label.setVisible(state["pad_inches_visible"])
        self.pad_label.setToolTip("Extra padding around the figure (only used when bounding box is 'tight').")

        self.pad_input = QDoubleSpinBox()
        self.pad_input.setVisible(state["pad_inches_visible"])
        self.pad_input.setDecimals(2)
        self.pad_input.setRange(0.0, 5.0)
        self.pad_input.setValue(state["pad_inches"])
        self.pad_input.setToolTip("Extra space (in inches) to pad around the tight bounding box.")
        layout.addWidget(self.pad_label)
        layout.addWidget(self.pad_input)

        # Buttons.
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(  # type: ignore
            self.accept)
        buttons.rejected.connect(  # type: ignore
            self.reject)
        layout.addWidget(buttons)

        # Connect callbacks
        self.connect_widgets()

        # Execute the dialog
        self.setVisible(True)

    @pyqtSlot()
    def accept(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Figure",
            "",  # Default directory
            "PNG Image (*.png);;PDF Document (*.pdf);;All Files (*)"
        )

        if filename:
            SAVE_FIGURE_SIGNAL_BUS.save_requested.emit(filename, self.figure)
            super().accept()  # closes the dialog
        else:
            pass

    def connect_widgets(self) -> None:
        """Connects the widget signals to the signal bus' signals."""
        self.dpi_input.valueChanged.connect(  # type: ignore
            SAVE_FIGURE_SIGNAL_BUS.dpi_changed
         )
        self.transparent_checkbox.clicked.connect(  # type: ignore
            SAVE_FIGURE_SIGNAL_BUS.transparent_checkbox_changed
        )
        self.bbox_combo.currentTextChanged.connect(  # type: ignore
            SAVE_FIGURE_SIGNAL_BUS.bbox_changed
        )
        self.pad_input.valueChanged.connect(  # type: ignore
            SAVE_FIGURE_SIGNAL_BUS.pad_changed
        )

    @pyqtSlot(bool)
    def on_pad_visible_change(self, visible: bool) -> None:
        """Toggles the visibility of the pad_inches options based on the reciev signal from the controller."""
        self.pad_input.setVisible(visible)
        self.pad_label.setVisible(visible)
