from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSlot
from matplotlib.figure import Figure

from ..models import SaveFigureState
from ...signal_busses import SAVE_FIGURE_SIGNAL_BUS
from ...shared import SETTINGS


class SaveFigureController(QObject):
    """Controller object that holds and manages the state of the SaveFigureDialog widget."""

    # region Namespaces for QSettings
    main_ns = "app/field_plot/save_figure_dialog/"
    dpi_ns = main_ns + "dpi"
    transparent_checkbox_ns = main_ns + "transparent_checkbox"
    bbox_ns = main_ns + "bbox"
    pad_visible_ns = main_ns + "pad_visible"
    pad_ns = main_ns + "pad"
    # endregion

    # region Attributes
    fig: Figure
    settings = SETTINGS
    # endregion

    def __init__(self):
        super().__init__()
        self.initialize_connections()

    def initialize_connections(self) -> None:
        """Connects the subscribed signals to their appropriate methods."""
        SAVE_FIGURE_SIGNAL_BUS.dpi_changed.connect(self.on_dpi_changed)
        SAVE_FIGURE_SIGNAL_BUS.transparent_checkbox_changed.connect(self.on_transparent_checkbox_changed)
        SAVE_FIGURE_SIGNAL_BUS.bbox_changed.connect(self.on_bbox_changed)
        SAVE_FIGURE_SIGNAL_BUS.pad_changed.connect(self.on_pad_changed)
        SAVE_FIGURE_SIGNAL_BUS.init_state_requested.connect(self.on_init_state_request)
        SAVE_FIGURE_SIGNAL_BUS.save_requested.connect(self.on_save_requested)

    def get_state(self) -> SaveFigureState:
        """Fetches the current state of the savefigure dialog settings."""
        return SaveFigureState(
            dpi=self.settings.value(self.dpi_ns, 300, type=int),
            transparent=self.settings.value(self.transparent_checkbox_ns, False, type=bool),
            bbox_inches=self.settings.value(self.bbox_ns, "tight", type=str),
            pad_inches_visible=self.settings.value(self.pad_visible_ns, True, type=bool),
            pad_inches=self.settings.value(self.pad_ns, 0.1, type=float)
        )

    @pyqtSlot()
    def on_init_state_request(self) -> None:
        """
        Reply to the init_state_request signal by fetching the current state of the class settings and replying with
        a dictionary of the current state.
        """
        SAVE_FIGURE_SIGNAL_BUS.init_state_reply.emit(self.get_state())

    @pyqtSlot(str, object)
    def on_save_requested(self, path: str, fig: Figure) -> None:
        """
        Saves the plot from the provided figure to the provided path emitted by the widget's save_request signal.
        """
        # Fetch the current state.
        state = self.get_state()

        # Set pad_inches to None if bbox_inches is not 'tight', and pop out the pad options' visibility
        if state["bbox_inches"] != "tight":
            state["pad_inches"] = None
        state.pop("pad_inches_visible")

        # Save the figure
        fig.savefig(path, **state)

    @pyqtSlot(int)
    def on_dpi_changed(self, dpi: int) -> None:
        """Updates the dpi settings."""
        self.settings.setValue(self.dpi_ns, dpi)

    @pyqtSlot(bool)
    def on_transparent_checkbox_changed(self, enabled: bool) -> None:
        """Updates the transparent checkbox enabled flag in the settings."""
        self.settings.setValue(self.transparent_checkbox_ns, enabled)

    @pyqtSlot(str)
    def on_bbox_changed(self, bbox_inches: str) -> None:
        """Updates the bbox settings and emits a signal updating the visibility of the padding options."""
        # Set visibility of the pas options.
        SAVE_FIGURE_SIGNAL_BUS.set_pad_visible.emit(bbox_inches == "tight")

        # Set the value
        self.settings.setValue(self.bbox_ns, bbox_inches)

    @pyqtSlot(float)
    def on_pad_changed(self, pad_inches: float) -> None:
        """Updates the pad settings."""
        self.settings.setValue(self.pad_ns, pad_inches)

