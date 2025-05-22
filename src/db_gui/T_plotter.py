import os
from typing import Tuple, Optional, Dict, TypedDict

import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton
)
from PyQt6.QtWidgets import (
    QWidget, QFileDialog, QMessageBox, QInputDialog
)
from matplotlib.axes import Axes
from matplotlib.axis import XAxis, YAxis
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.text import Text

from .linear_plot_settings import TPlotSettings
from .top_level import TopLevel
from .widgets import TightNavigationToolbar


class AxisDict(TypedDict, total=False):
    ax: Axes
    title: Text
    x_label: Text
    y_label: Text
    xticks: XAxis
    yticks: YAxis
    legend: Optional[Legend]
    artists: Dict[str, Line2D]
    settings: TPlotSettings


class TPlotTab(QWidget):

    # region Top level
    top: TopLevel
    # endregion

    # region Default Values
    CALLBACK_DELAY: float = 10
    # endregion

    current_ax: AxisDict

    # region Matplotlib
    fig: Figure
    canvas: FigureCanvas
    toolbar: TightNavigationToolbar
    axes: Dict[str, AxisDict]
    # endregion

    draw_idle_timer: QTimer

    def _init_timers(self) -> None:
        self.draw_idle_timer = QTimer(self)
        self.draw_idle_timer.setSingleShot(True)
        self.draw_idle_timer.timeout.connect(self._draw_idle)  # type: ignore

    def _init_attributes(self) -> None:
        self.axes = {}

    def _init_figure(self) -> None:
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = TightNavigationToolbar(self.canvas, self)
        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.canvas, stretch=1)

        ax = self.fig.add_subplot(111)
        self.axes["main"] = AxisDict(
            ax=ax,
            title=ax.set_title(""),
            x_label=ax.set_xlabel(""),
            y_label=ax.set_ylabel(""),
            xticks=ax.xaxis,
            yticks=ax.yaxis,
            legend=None,
            artists={}
        )
        self.current_ax = self.axes["main"]
        self.fig.tight_layout()
        self.axes["main"]["settings"] = TPlotSettings(self)

    def __init__(self, top: TopLevel) -> None:
        super().__init__(top)

        # Store reference to app top level.
        self.top = top

        # Create main layout
        self._layout = QVBoxLayout(self)

        # Initialize
        self._init_timers()
        self._init_attributes()
        self._init_figure()
        self._add_import_dataset_settings()

        # --- Settings button ---
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self._layout.addWidget(self.settings_button)



    def _init_attributes(self) -> None:
        self.axes = {}

    def _init_figure(self) -> None:
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = TightNavigationToolbar(self.canvas, self)
        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.canvas, stretch=1)

        ax = self.fig.add_subplot(111)
        self.axes["main"] = AxisDict(
            ax=ax,
            title=ax.set_title(""),
            x_label=ax.set_xlabel(""),
            y_label=ax.set_ylabel(""),
            xticks=ax.xaxis,
            yticks=ax.yaxis,
            legend=None,
            artists={}
        )
        self.current_ax = self.axes["main"]
        self.fig.tight_layout()
        self.axes["main"]["settings"] = TPlotSettings(self)

    # region Import data and add to dataset
    def _add_import_dataset_settings(self) -> None:
        self.import_sampled_data_button = QPushButton("Import Sampled Data")
        self.edit_units_button = QPushButton("Edit Units")
        self.add_to_dataset_button = QPushButton("Add to Dataset")
        self.add_to_dataset_button.setEnabled(False)
        self.open_dataset_button = QPushButton("Open Dataset")

        self.import_sampled_data_button.clicked.connect(self.on_import_sampled_data_clicked)
        self.add_to_dataset_button.clicked.connect(self.on_add_to_dataset_clicked)
        # self.open_dataset_button.clicked.connect(self.on_open_dataset_clicked)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.import_sampled_data_button)
        button_layout.addWidget(self.add_to_dataset_button)
        button_layout.addWidget(self.open_dataset_button)
        self._layout.addLayout(button_layout)

    def on_import_sampled_data_clicked(self) -> None:
        # --- Open file dialog (multiple files allowed) ---
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select one or more CSV or TXT files",
            "",
            "Data Files (*.csv *.txt);;All Files (*)"
        )

        if not file_paths:
            return  # User canceled

        all_data = []
        all_column_names = []
        all_x_values = []

        # --- Load all files ---
        for file_path in file_paths:
            try:
                data, column_names = load_two_column_data(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to load file:\n{file_path}\n\n{str(e)}")
                return

            if data.size == 0:
                QMessageBox.warning(self, "Import Warning", f"No valid data found in file:\n{file_path}")
                return

            all_data.append(data)
            all_column_names.append(column_names)
            all_x_values.append(data[:, 0])

        # --- Check x-values are identical across all files ---
        reference_x = all_x_values[0]
        for x in all_x_values[1:]:
            if not np.allclose(x, reference_x, rtol=1e-5, atol=1e-8):
                QMessageBox.critical(self, "Import Error",
                                     "Selected files do not have matching x-axis (wavelength) values.")
                return

        # --- Handle axes switching ---
        self.open_dataset("main")

        # --- Check column names consistency ---
        reference_x_label, reference_y_label = all_column_names[0]
        x_label_mismatch = False
        y_label_mismatch = False

        for x_label, y_label in all_column_names[1:]:
            if x_label != reference_x_label:
                x_label_mismatch = True
            if y_label != reference_y_label:
                y_label_mismatch = True

        if x_label_mismatch:
            QMessageBox.warning(self, "Import Warning",
                                "X-axis labels differ across files. Using label from first file.")
        if y_label_mismatch:
            QMessageBox.warning(self, "Import Warning",
                                "Y-axis labels differ across files. Using label from first file.")

        # --- Compute average ---
        all_y_values = [data[:, 1] for data in all_data]
        mean_y = np.mean(np.stack(all_y_values, axis=0), axis=0)

        # --- Determine combined label ---
        if len(file_paths) == 1:
            filename_without_suffix = os.path.splitext(os.path.basename(file_paths[0]))[0]
        else:
            filename_without_suffix = "Averaged Data"

        # --- Clear previous artists ---
        for artist in self.current_ax["ax"].lines:
            artist.remove()

        # Clear artists
        self.current_ax["settings"].clear_artists()

        # --- Plot averaged data ---
        artist = self.current_ax["ax"].plot(reference_x, mean_y, label=filename_without_suffix)

        # --- Update axis labels from column names ---
        self.current_ax["settings"].xlabel_group.checkbox.setChecked(True)
        self.current_ax["settings"].ylabel_group.checkbox.setChecked(True)
        self.current_ax["settings"].xlabel_text.setText(reference_x_label)
        self.current_ax["settings"].ylabel_text.setText(reference_y_label)
        self.current_ax["settings"].on_xlabel_visibility_change(True)
        self.current_ax["settings"].on_ylabel_visibility_change(True)

        # --- Add artist widget ---
        x_label, y_label = all_column_names[0] if not (x_label_mismatch or y_label_mismatch) else (None, None)
        self.current_ax["settings"].add_artist(filename_without_suffix, filename_without_suffix, artist,
                                               xlabel=x_label, ylabel=y_label)
        self.add_to_dataset_button.setEnabled(True)

    def create_and_open_new_dataset(self, name: str, x_label: str = None, y_label: str = None) -> None:

        # --- Handle axes switching ---
        selected_ax = self.current_ax
        selected_ax["ax"].set_visible(False)
        if selected_ax["settings"].isVisible():
            was_open = True
            selected_ax["settings"].close()
        else:
            was_open = False

        x_label = x_label if x_label else ""
        y_label = y_label if y_label else ""

        ax = self.fig.add_subplot(111)
        self.axes[name] = AxisDict(
            ax=ax,
            title=ax.set_title(""),
            x_label=ax.set_xlabel(x_label),
            y_label=ax.set_ylabel(y_label),
            xticks=ax.xaxis,
            yticks=ax.yaxis,
            legend=None,
            artists={}
        )
        self.current_ax = self.axes[name]
        self.axes[name]["settings"] = TPlotSettings(self)
        self.current_ax["ax"].set_visible(True)
        self.current_ax["settings"].xlabel_group.checkbox.setChecked(True)
        self.current_ax["settings"].ylabel_group.checkbox.setChecked(True)
        self.current_ax["settings"].xlabel_text.setText(x_label)
        self.current_ax["settings"].ylabel_text.setText(y_label)
        self.current_ax["settings"].on_xlabel_visibility_change(True)
        self.current_ax["settings"].on_ylabel_visibility_change(True)
        self._draw_idle()
        if was_open:
            self.current_ax["settings"].show()

    def open_dataset(self, name: str) -> None:

        self.add_to_dataset_button.setEnabled(name == "main")

        if self.axes[name] is self.current_ax:
            return

        # --- Handle axes switching ---
        selected_ax = self.current_ax
        selected_ax["ax"].set_visible(False)
        if selected_ax["settings"].isVisible():
            was_open = True
            selected_ax["settings"].close()
        else:
            was_open = False

        self.current_ax = self.axes[name]
        self.current_ax["ax"].set_visible(True)

        if was_open:
            self.current_ax["settings"].show()

    def on_add_to_dataset_clicked(self) -> None:

        if not any([line.get_visible() for line in self.current_ax["ax"].lines]):
            return

        # Ask user for a dataset name
        dataset_names = list(self.axes.keys())
        try:
            dataset_names.remove("main")
        except:
            pass

        options = dataset_names + ["<Create New Dataset>"]
        if len(options) == 1:
            dataset_name = "<Create New Dataset>"
        else:
            dataset_name, ok = QInputDialog.getItem(
                self,
                "Select Dataset",
                "Select an existing dataset or create a new one:",
                options,
                editable=False
            )

            if not ok:
                return

        if dataset_name == "<Create New Dataset>":
            new_dataset = True
            dataset_name, ok = QInputDialog.getText(
                self,
                "New Dataset",
                "Enter name for new dataset:"
            )

            if not ok or not dataset_name:
                return
        else:
            new_dataset = False

        artist = self.current_ax["settings"].artists[0]
        if new_dataset:
            x_label = self.current_ax["settings"].xlabel_text.text()
            y_label = self.current_ax["settings"].ylabel_text.text()
            self.create_and_open_new_dataset(dataset_name, x_label, y_label)
        else:
            self.open_dataset(dataset_name)

        self.current_ax["settings"].add_existing_artist(artist)
        self.add_to_dataset_button.setEnabled(False)

    def update_add_to_dataset_button_state(self) -> None:
        has_artists = bool(self.get_current_ax()["ax"].lines)
        self.add_to_dataset_button.setEnabled(has_artists)

    # endregion

    def get_current_ax(self) -> AxisDict:
        return self.current_ax

    def open_settings(self):
        self.current_ax["settings"].setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.current_ax["settings"].show()

    def _draw_idle(self) -> None:
        self.current_ax["ax"].set_anchor("C")
        self.current_ax["settings"].apply_limits(update=False)
        self.fig.tight_layout()
        self.canvas.draw_idle()


def load_two_column_data(file_path: str) -> Tuple[np.ndarray, Tuple[str, str]]:
    data = []
    column_names = ("", "")  # Default names if no header is found
    found_column_names = False

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            if "," in line:
                parts = [p.strip() for p in line.split(",")]
            else:
                parts = [p.strip() for p in line.split()]

            if len(parts) != 2:
                continue  # Not two columns, skip

            if not found_column_names:
                try:
                    float(parts[0])
                    float(parts[1])
                    # Both parts are numbers, real data starts here
                except ValueError:
                    # First non-numeric two-column line = column names
                    column_names = (parts[0], parts[1])
                    found_column_names = True
                    continue  # Go to next line

            try:
                wavelength = float(parts[0])
                value = float(parts[1])
                data.append((wavelength, value))
            except ValueError:
                continue  # Skip if still bad row

    return np.array(data), column_names