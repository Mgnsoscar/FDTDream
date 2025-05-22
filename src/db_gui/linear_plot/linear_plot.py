from typing import Dict, Tuple, List, Optional, Any
import os

import numpy as np
from PyQt6.QtWidgets import (
    QVBoxLayout, QFrame, QSizePolicy, QComboBox, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout, QMessageBox, QFileDialog, QInputDialog
)
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axis import Axis
from matplotlib.lines import Line2D
from ...FDTDiscover.dbPanel import signals
from ...FDTDiscover.dbPanel.models import DBObjects

from src.db_gui.top_level import TopLevel
from src.db_gui.widgets import TightNavigationToolbar
from .dataset import Dataset
from .linear_plt_subsettings.settings import LinearPlotSettings
from .ScalableLine2D import ScalableLine2D


class LinearPlotTab(QWidget):

    top: TopLevel

    # region PyQt6
    import_sampled_data: QPushButton
    settings: Optional[QWidget]
    # endregion

    # region Matplotlib
    fig: Figure
    canvas: FigureCanvas
    toolbar: TightNavigationToolbar
    datasets: Dict[str, Dataset]
    current_dataset: Dataset
    # endregion

    def _init_dataset(self, name: str, set_visible: bool = True) -> Optional[Dataset]:

        if name in self.datasets:
            QMessageBox.critical(self, "Name Error",
                                 f"Another dataset named '{name}' already exist. Please choose another name.")
            return None

        dataset = Dataset(name, self.fig, set_visible)

        # Add it to the dictionary of datasets
        self.datasets[name] = dataset

        # ✅ Update combo box
        self.dataset_selector.addItem(name)
        self.dataset_selector.blockSignals(True)
        self.dataset_selector.setCurrentText(name)
        self.dataset_selector.blockSignals(False)

        return dataset

    def _init_figure(self) -> None:

        # Init the figure, canvas and toolbar
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = TightNavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas, stretch=1)

        # Set up the main dataset
        self.datasets = {}
        self._init_dataset("__main__", set_visible=True)
        self.current_dataset = self.datasets["__main__"]
        self.redraw_plot()

    def _init_buttons(self) -> None:
        self.import_sampled_data = QPushButton("Import Sampled Data")
        self.add_to_dataset = QPushButton("Add to Dataset")
        self.add_to_dataset.setEnabled(False)
        self.settings_btn = QPushButton("Plot settings")
        self.settings_btn.clicked.connect(self.on_settings_clicked)

        self.import_sampled_data.clicked.connect(self.on_import_sampled_data_clicked)  # type: ignore
        self.add_to_dataset.clicked.connect(self.on_add_to_dataset_clicked)  # type: ignore

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.import_sampled_data)
        button_layout.addWidget(self.add_to_dataset)
        self.layout().addLayout(button_layout)

        self.layout().addWidget(QLabel("Select dataset"))
        self.layout().addWidget(self.dataset_selector)

        self.layout().addWidget(self.settings_btn)

    def _init_signals(self) -> None:
        # Prompt redraw of the canvas when tab is changed to the linear plot tab.
        self.top.tabs.currentChanged.connect(self.on_linear_tab_selected)  # type: ignore

    def _init_dataset_selector(self) -> None:
        self.dataset_selector = QComboBox()
        self.dataset_selector.wheelEvent = lambda event: None
        self.dataset_selector.setPlaceholderText("Select dataset")
        self.dataset_selector.currentTextChanged.connect(self.on_dataset_selected)  # type: ignore

    def __init__(self, top: TopLevel):
        super().__init__()

        # Assign the layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Assign the settings window variable
        self.settings = None

        # Assign reference to the top level
        self.top = top

        # Connect the monitor selected signal
        signals.dbRightClickMenuSignalBus.plotPower.connect(self.on_monitor_selected)

        # Init the dataset selector
        self._init_dataset_selector()

        # Init the figure
        self._init_figure()

        # Init buttons
        self._init_buttons()

        # Init signals
        self._init_signals()

    # region Callbacks
    def on_dataset_selected(self, name: str) -> None:
        if name and name in self.datasets:
            self.display_dataset(name)

    def on_settings_clicked(self) -> None:
        if not self.settings:
            self.settings = QWidget()
            self.settings.setWindowTitle("Plot Settings")
            self.settings.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)
            self.settings.setMaximumHeight(500)

            layout = QVBoxLayout()
            layout.addWidget(LinearPlotSettings(self, self.current_dataset))
            self.settings.setLayout(layout)

            self.settings.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.settings.destroyed.connect(lambda: setattr(self, "settings", None))

            self.settings.show()
        else:
            self.settings.close()
            self.settings.deleteLater()
            self.settings = None

    def change_settings_dataset(self) -> None:
        if self.settings:
            prev_layout = self.settings.layout()
            new_layout = QVBoxLayout()
            self.settings.setLayout(new_layout)
            prev_layout.deleteLater()
            new_layout.addWidget(LinearPlotSettings(self, self.current_dataset))

    def on_linear_tab_selected(self, index: int) -> None:
        if index == 1:
            self.redraw_plot()

    def on_import_sampled_data_clicked(self) -> None:

        # Fetch the files
        file_paths = open_file_dialog(self)
        if not file_paths:
            return  # No paths selected

        # Load all data and axis labels.
        all_data, all_column_names = load_files(self, file_paths)
        if not (all_data and all_column_names):
            return  # Didn't load any data

        # Fetch labels and if it was mismatch of labels across the loaded files.
        x_mismatch, y_mismatch, x_label, y_label = check_label_mismatch_and_get_labels(self, all_column_names)

        # Compute average of all y-values
        all_y_values = [data[:, 1] for data in all_data]
        mean_y = np.mean(np.stack(all_y_values, axis=0), axis=0)

        # Determine label
        if len(file_paths) == 1:
            label = os.path.splitext(os.path.basename(file_paths[0]))[0]
        else:
            label = "Averaged Data"

        # Detatch the artists from the main dataset and clear titles and labels
        dataset = self.datasets["__main__"]
        dataset.detatch_artists_from_dataset()
        dataset.clear_title_and_labels()

        # Plot the data and store the artists in the artist dictionary
        line2d_artists = dataset.ax.plot(all_data[0][:, 0], mean_y, label=label)
        artists = [ScalableLine2D.from_Line2D(artist) for artist in line2d_artists]
        dataset.relim()

        # Update the plot's labels if given
        if x_label:
            x_axis_label = dataset.ax.xaxis.get_label()
            x_axis_label.set_text(x_label)
            x_axis_label.set_visible(True)
        if y_label:
            y_axis_label = dataset.ax.yaxis.get_label()
            y_axis_label.set_text(y_label)
            y_axis_label.set_visible(True)

        # Enable the add_to_dataset_button
        self.add_to_dataset.setEnabled(True)

        # Switch to the __main__ dataset:
        self.display_dataset("__main__")

    def on_monitor_selected(self, monitors: DBObjects) -> None:
        monitorData: List[Tuple[str, np.ndarray, np.ndarray]] = []
        for monitor in monitors:
            result: Tuple[np.ndarray, np.ndarray] = monitor["dbHandler"].get_T_data(monitor["id"])
            if result is not None:
                monitorData.append((monitor["name"], *result))

        # Detatch the artists from the main dataset and clear titles and labels
        dataset = self.datasets["__main__"]
        dataset.detatch_artists_from_dataset()
        dataset.clear_title_and_labels()

        # Plot all curves
        all_artists = []
        for name, wavelengths, power in monitorData:
            line2d_artists = dataset.ax.plot(wavelengths, power, label=name)
            scaled_artists = [ScalableLine2D.from_Line2D(artist) for artist in line2d_artists]
            all_artists.extend(scaled_artists)

        dataset.xlabel.set_text("Wavelength [nm]")
        dataset.ylabel.set_text("T")
        dataset.relim()

        self.display_dataset("__main__")
        dataset.update_legend()

        # Enable the add_to_dataset_button
        self.add_to_dataset.setEnabled(True)

    def on_add_to_dataset_clicked(self) -> None:

        if not any([line.get_visible() for line in self.current_dataset.ax.lines]):
            return

        # Ask user for a dataset name
        dataset_names = list(self.datasets.keys())
        if "__main__" in dataset_names:
            dataset_names.remove("__main__")

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

        # Fetch reference to the main dataset
        main = self.datasets["__main__"]

        # Fetch the artists that will be transferred to the new dataset, while clearing the main dataset.
        main_artists = main.detatch_artists_from_dataset()

        # Update the x and y labels if it's a new dataset.
        if new_dataset:
            dataset = self._init_dataset(dataset_name, set_visible=True)
            if not dataset:
                return
            dataset.xlabel.set_text(self.current_dataset.xlabel.get_text())
            dataset.ylabel.set_text(self.current_dataset.ylabel.get_text())
        else:
            dataset = self.datasets[dataset_name]

        # Clear titles and labels from the main dataset.
        main.clear_title_and_labels()

        # Fetch the existing artists in the dataset
        existing_artists = dataset.ax.lines
        for artist in main_artists:
            dataset.add_artist(artist)

        # Display new dataset
        self.display_dataset(dataset_name)

        # Disable the add to dataset button.
        self.add_to_dataset.setEnabled(False)

    # endregion

    # region Events
    def resizeEvent(self, a0) -> None:
        self.redraw_plot()
        super().resizeEvent(a0)
    # endregion

    # region Plotting methods
    def update_plot(self) -> None:
        ...

    def redraw_plot(self) -> None:
        # Anchor the current plot to the center and enforce tight layout.
        self.current_dataset.ax.set_anchor("C")
        self.fig.tight_layout()

        # Redraw contents
        self.canvas.draw_idle()

    def detach_artists_from_main_dataset(self, redraw: bool = True) -> List[Line2D]:
        artists = []
        for _, artist in self.datasets["__main__"].ax.lines:
            artists.append(artist)
            artist.remove()
        if redraw:
            self.redraw_plot()
        return artists

    def clear_titles_and_labels_from_main_dataset(self, redraw: bool = True) -> None:
        main = self.datasets["__main__"]
        main.xlabel.set_text("")
        main.ylabel.set_text("")
        main.title.set_text("")
        if redraw:
            self.redraw_plot()

    def display_dataset(self, dataset_name: str) -> None:

        if self.settings:
            self.settings.close()
            self.on_settings_clicked()

        if self.current_dataset.name == dataset_name:
            self.current_dataset.update_legend()
            self.redraw_plot()
            return
        else:
            self.dataset_selector.blockSignals(True)
            self.dataset_selector.setCurrentText(dataset_name)
            self.dataset_selector.blockSignals(False)
            self.current_dataset.ax.set_visible(False)
            self.current_dataset = self.datasets[dataset_name]
            self.current_dataset.ax.set_visible(True)
            self.current_dataset.update_legend()
            self.redraw_plot()



    # endregion

    # region Overrides
    def layout(self) -> QVBoxLayout:
        return super().layout()  # type: ignore
    # endregion


# region Functions
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


def open_file_dialog(parent_widget: LinearPlotTab) -> List[str]:
    file_paths, _ = QFileDialog.getOpenFileNames(
        parent_widget,
        "Select one or more CSV or TXT files",
        "",
        "Data Files (*.csv *.txt);;All Files (*)"
    )
    return file_paths


def load_files(parent_widget: LinearPlotTab,
               file_paths: List[str]) -> Optional[Tuple[List[np.ndarray], List[Tuple[str, str]]]]:
    # Init lists
    all_data = []
    all_column_names = []
    all_x_values = []

    # Load all files
    for file_path in file_paths:
        try:
            data, column_names = load_two_column_data(file_path)
        except Exception as e:
            QMessageBox.critical(parent_widget, "Import Error",
                                 f"Failed to load file:\n{file_path}\n\n{str(e)}")
            return [], []

        if data.size == 0:
            QMessageBox.warning(parent_widget,
                                "Import Warning", f"No valid data found in file:\n{file_path}")
            return [], []

        all_data.append(data)
        all_column_names.append(column_names)
        all_x_values.append(data[:, 0])

    # --- Check x-values are identical across all files ---
    reference_x = all_x_values[0]
    for x in all_x_values[1:]:
        if not np.allclose(x, reference_x, rtol=1e-5, atol=1e-8):
            QMessageBox.critical(parent_widget, "Import Error",
                                 "Selected files do not have matching x-axis (wavelength) values.")
            return [], []

    return all_data, all_column_names


def check_label_mismatch_and_get_labels(parent_widget: LinearPlotTab,
                                        all_column_names: List[Tuple[str, str]]) -> Tuple[bool, bool, str, str]:
    ...

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
        QMessageBox.warning(parent_widget, "Import Warning",
                            "X-axis labels differ across files. Using label from first file.")
    if y_label_mismatch:
        QMessageBox.warning(parent_widget, "Import Warning",
                            "Y-axis labels differ across files. Using label from first file.")

    return x_label_mismatch, y_label_mismatch, reference_x_label, reference_y_label
# endregion
