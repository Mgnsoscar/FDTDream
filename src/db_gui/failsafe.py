import itertools
from typing import Union, List, Tuple, Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
from PyQt6.QtCore import QPoint
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QCheckBox, QHBoxLayout
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import QuadMesh, PolyCollection
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.quiver import Quiver
from numpy.typing import NDArray

from .field_plt_settings import FieldSettings
from .plt_settings import PlotSettings
from .top_level import TopLevel
from .vector_plt_settings import VectorSettings
from .widgets import LabeledSlider, LabeledDropdown
from ..fdtdream.database.db import FieldModel, MonitorModel, SimulationModel


class FieldPlotTab(QWidget):
    # region Settings and top level
    top: TopLevel
    field_settings: FieldSettings
    vector_settings: VectorSettings
    plot_settings: PlotSettings
    # endregion

    # region Default Values
    PLOT_TYPES = ["XY Plane", "XZ Plane", "YZ Plane", "X Linear", "Y Linear", "Z Linear", "Point"]
    # endregion

    # region Data
    selected_simulation: Optional[SimulationModel]
    selected_field: Optional[FieldModel]
    selected_quiver_field: Optional[FieldModel]
    field_data: Optional[NDArray]
    quiver_data: Optional[NDArray]

    component_idx: Optional[Tuple[int, ...]]
    coordinate_idx: Optional[List[Union[int, slice, Tuple, ...]]]
    component_2_magnitude_idx: Dict[str, int]
    component2idx: Dict
    available_quiver_fields: Dict
    # endregion

    # region Matplotlib
    fig: plt.Figure
    canvas: FigureCanvas

    title: plt.Text
    x_label: plt.Text
    y_label: plt.Text
    legend: Optional[Legend]

    field_ax: plt.Axes

    quadmesh: Optional[QuadMesh]
    colorbar: Optional[Colorbar]

    structure_outlines: Dict[int, Dict[str, Tuple[PolyCollection, bool]]]  # Bool shows active artist or not
    structure_fills: Dict[int, Dict[str, Tuple[PolyCollection, bool]]]
    structure_intersections: Dict[int, Dict[str, List[Tuple[PolyCollection, bool]]]]

    quiver: Optional[Quiver]

    linear_artist: Optional[plt.Line2D]
    # endregion

    # region Widgets
    _layout: QVBoxLayout
    wavelength_slider: LabeledSlider
    field_combo: LabeledDropdown
    plot_type_combo: LabeledDropdown

    quadmesh_dialog: Optional[QDialog]
    structure_dialog: Optional[QDialog]
    vector_dialog: Optional[QDialog]
    plot_dialog: Optional[QDialog]

    plot_fieldmap_checkbox: QCheckBox
    plot_vectors_checkbox: QCheckBox
    plot_structures_checkbox: QCheckBox
    # endregion

    # region Timers and callback delay
    update_data_timer: QTimer
    draw_idle_timer: QTimer
    cscale_timer: QTimer
    callback_delay: float = 10

    # endregion

    def __init__(self, parent: TopLevel):
        super().__init__(parent)

        # Store reference to app top level.
        self.top = parent

        # Create main layout
        self._layout = QVBoxLayout(self)

        # Initialize
        self._init_timers()
        self._init_quadmesh_settings()
        self._init_structure_settings()
        self._init_quiver_settings()
        self._init_plot_settings()
        self._init_dialogs()
        self._init_data()
        self._init_artists()
        self._init_figure()
        self._init_controls()

    # region INIT
    def _init_timers(self) -> None:
        self.update_data_timer = QTimer(self)
        self.update_data_timer.setSingleShot(True)
        self.update_data_timer.timeout.connect(self.update_data)  # type: ignore

        self.draw_idle_timer = QTimer(self)
        self.draw_idle_timer.setSingleShot(True)
        self.draw_idle_timer.timeout.connect(self.draw_idle)  # type: ignore

    def _init_quadmesh_settings(self) -> None:
        self.field_settings = FieldSettings(self, self.get_quadmesh_artist, self.draw_idle_timer)

    def _init_structure_settings(self) -> None:
        ...

    def _init_quiver_settings(self) -> None:
        self.quiver_settings = VectorSettings()
        self.quiver_settings.scalar_op_changed.connect(self._apply_scalar_operation_on_quiver_data)
        self.quiver_settings.normalized_changed.connect(self._on_quiver_normalize)
        self.quiver_settings.field_changed.connect(self._on_quiver_field_changed)
        self.quiver_settings.vector_settings_changed.connect(self._on_vector_settings_changed)

    def _init_plot_settings(self) -> None:
        self.plot_settings = PlotSettings()
        self.plot_settings.title_settings_changed.connect(self.on_title_changed)
        self.plot_settings.xlabel_settings_changed.connect(self.on_xlabel_changed)
        self.plot_settings.ylabel_settings_changed.connect(self.on_ylabel_changed)
        self.plot_settings.legend_settings_changed.connect(self.on_legend_changed)
        self.plot_settings.grid_settings_changed.connect(self.on_grid_changed)
        self.plot_settings.aspect_checkbox.toggled.connect(self.on_aspect_ratio_changed)  # type: ignore

    def _init_dialogs(self) -> None:
        self.quadmesh_dialog = None
        self.structure_dialog = None
        self.vector_dialog = None
        self.plot_dialog = None

    def _init_data(self) -> None:
        self.selected_simulation = None
        self.selected_field = None
        self.selected_quiver_field = None
        self.field_data = None
        self.quiver_data = None

        self.coordinate_idx = None
        self.component_idx = None
        self.component_2_magnitude_idx = {}
        self.component2idx = {}

    def _init_artists(self) -> None:
        self.quadmesh = None
        self.colorbar = None
        self.quiver = None
        self.linear_artist = None
        self.structure_outlines = {}
        self.structure_intersections = {}
        self.structure_fills = {}

    def _init_figure(self) -> None:

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self._layout.addWidget(self.canvas, stretch=1)

        self.ax = self.fig.add_subplot(111)

        # Store references to important artists
        self.title = self.ax.set_title("")
        self.x_label = self.ax.set_xlabel("")
        self.y_label = self.ax.set_ylabel("")
        self.legend = self.ax.legend([], [])  # Empty legend initially
        self.legend = None

    def _init_controls(self) -> None:

        # Create a new layout
        self._controls_layout = QVBoxLayout()
        self._layout.addLayout(self._controls_layout)

        self._init_plot_type_and_field_controls()
        self._init_wavelength_and_coordinate_sliders()
        self._init_settings_and_checkboxes()

    def _init_plot_type_and_field_controls(self) -> None:
        plot_type_and_field_layout = QHBoxLayout()

        self.field_combo = LabeledDropdown(self, "Field:", callback=self.on_field_changed)
        plot_type_and_field_layout.addWidget(self.field_combo)

        self.plot_type_combo = LabeledDropdown(self, "Plot type:", callback=self.on_plot_type_changed)
        plot_type_and_field_layout.addWidget(self.plot_type_combo)
        self._controls_layout.addLayout(plot_type_and_field_layout)

    def _init_wavelength_and_coordinate_sliders(self) -> None:

        # Create widget for wavelength and coordinate controls.
        wavelength_and_coordinate_controls = QWidget()
        layout = QVBoxLayout(wavelength_and_coordinate_controls)

        # Wavelength slider
        self.wavelength_slider = LabeledSlider(self, "Wavelength [nm]: ", 0, 0, self.on_wavelength_changed)
        self.wavelength_slider.slider.setEnabled(False)
        layout.addWidget(self.wavelength_slider)

        # Coordinate sliders
        coords_layout = QHBoxLayout()

        self.x_slider = LabeledSlider(self, "x [nm]: ", 0, 0, self.on_coordinate_change)
        self.x_slider.slider.setEnabled(False)
        coords_layout.addWidget(self.x_slider)

        self.y_slider = LabeledSlider(self, "y [nm]: ", 0, 0, self.on_coordinate_change)
        self.y_slider.slider.setEnabled(False)
        coords_layout.addWidget(self.y_slider)

        self.z_slider = LabeledSlider(self, "z [nm]: ", 0, 0, self.on_coordinate_change)
        self.z_slider.slider.setEnabled(False)
        coords_layout.addWidget(self.z_slider)

        layout.addLayout(coords_layout)

        self._controls_layout.addWidget(wavelength_and_coordinate_controls)

    def _init_settings_and_checkboxes(self) -> None:
        # Add checkboxes for toggling plot elements
        settings_layout = QHBoxLayout()

        # region Field settings button and checkbox
        field_plt_layout = QVBoxLayout()

        self.plot_fieldmap_checkbox = QCheckBox("Show Field")
        self.plot_fieldmap_checkbox.setChecked(True)
        self.plot_fieldmap_checkbox.setEnabled(False)
        self.plot_fieldmap_checkbox.toggled.connect(self._on_show_field_toggled)  # type: ignore
        field_plt_layout.addWidget(self.plot_fieldmap_checkbox)

        self.field_settings_btn = QPushButton("Field Settings")
        self.field_settings_btn.setEnabled(False)
        self.field_settings_btn.clicked.connect(self.show_quadmesh_settings)  # type: ignore
        field_plt_layout.addWidget(self.field_settings_btn)

        settings_layout.addLayout(field_plt_layout)
        # endregion

        # region Structure settings button and checkbox
        structure_plt_layout = QVBoxLayout()

        self.plot_structures_checkbox = QCheckBox("Show Structures")
        self.plot_structures_checkbox.setChecked(False)
        self.plot_structures_checkbox.setEnabled(False)
        self.plot_structures_checkbox.toggled.connect(self._on_show_structures_toggled)  # type: ignore
        structure_plt_layout.addWidget(self.plot_structures_checkbox)

        self.structure_btn = QPushButton("Structure Settings")
        self.structure_btn.setEnabled(False)
        self.structure_btn.clicked.connect(self.show_structure_settings)  # type: ignore
        structure_plt_layout.addWidget(self.structure_btn)

        settings_layout.addLayout(structure_plt_layout)
        # endregion

        # region Vector settings button and checkbox
        vector_plt_layout = QVBoxLayout()

        self.plot_vectors_checkbox = QCheckBox("Show Field Vectors")
        self.plot_vectors_checkbox.setChecked(False)
        self.plot_vectors_checkbox.setEnabled(False)
        self.plot_vectors_checkbox.toggled.connect(self._on_show_vectors_toggled)  # type: ignore
        vector_plt_layout.addWidget(self.plot_vectors_checkbox)

        self.vector_btn = QPushButton("Vector Plot Settings")
        self.vector_btn.setEnabled(False)
        self.vector_btn.clicked.connect(self.show_quiver_settings)  # type: ignore
        vector_plt_layout.addWidget(self.vector_btn)

        settings_layout.addLayout(vector_plt_layout)
        # endregion

        # region Plot settings button (aligned without checkbox)
        plt_settings_layout = QVBoxLayout()

        # Add spacer to vertically align with other buttons
        spacer_height = self.plot_vectors_checkbox.sizeHint().height()
        plt_settings_layout.addSpacing(spacer_height)

        self.plot_btn = QPushButton("Plot Settings")
        self.plot_btn.clicked.connect(self.show_plot_settings)  # type: ignore
        plt_settings_layout.addWidget(self.plot_btn)

        settings_layout.addLayout(plt_settings_layout)
        # endregion

        # Add the whole row to your layout
        self._layout.addLayout(settings_layout)

    # endregion

    # region Configuring new monitor

    def set_new_monitor(self) -> None:

        # If the selected simulation is None, update it. If it's not None, update it at the end of this method.
        # This is to keep track of if the newly selected monitor is a part of the same simulation as the previous one.
        if self.selected_simulation is None and self.monitor is not None:
            self.selected_simulation = self.monitor.simulation

        self._reinit_field_map_fields(keep_selection=True)
        self._reinit_components(keep_selection=True)
        self._reinit_component_idx()
        self._reinit_plot_types(keep_selection=True)
        self._reinit_wavelength_slider()
        self._reinit_coordinate_sliders()
        self._reinit_coordinate_idx()

        self._reinit_quiver_fields(keep_selection=True)
        self._reload_field_map_data()
        self._reload_quiver_data()
        self._apply_scalar_operation_on_quiver_data()
        self._apply_magnitude_operation_on_field_map_data()
        self._apply_scalar_operation_on_field_map_data(reload_temp_data=False)

        # Reset axes and plot controls while plotting the currently selected dataset
        self._reinit_axes()

        # Update the monitor's parent simulation
        self.selected_simulation = self.monitor.simulation if self.monitor else None

    def _reinit_field_map_fields(self, keep_selection: bool = False) -> None:
        """
        Loads available fields from the monitor.
        Sets the same field as previously if possible and keep_selection.
        If refill_combobox, the
        """

        # Fetch available field names
        field_names = [field.field_name for field in self._get_available_fields()]

        # Assign the new fields to the combo box.
        selected = self.field_combo.set_dropdown_items(field_names, keep_selection=keep_selection)

        # Store the selected field model.
        self._select_field(selected)

        # Disable field settings and checkbox if None is selected, else enable.
        enabled = self._select_field is not None
        self.plot_fieldmap_checkbox.setEnabled(enabled)
        self.field_settings_btn.setEnabled(enabled)

    def _reinit_components(self, keep_selection: bool = False):
        """Loads available field components and combinations into the combo box. Returns the selected component."""

        # Fetch component combinations. Returns empty list if no field is selected.
        combinations = self._get_component_combinations()

        # Assign the new items to the combo box.
        self.field_settings.component_combo.set_dropdown_items(combinations, keep_selection=keep_selection)

    def _reinit_component_idx(self) -> None:
        """Finds the correct indices for the components available in the dataset for the given field."""

        # Fetch available components.
        available_components = self._get_component_combinations()
        single_components = [c for c in available_components if len(c) == 1]
        composite_components = [c for c in available_components if len(c) > 1]

        # Create the mapping. Any combination of more than one component should be index 0,
        # since it will result in a magnitude, not a vector.
        self.component2idx = {
            **{label: i for i, label in enumerate(single_components)},
            **{label: 0 for label in composite_components},
            "": None  # In case no components are available.
        }

        # Assign the correct index for the the currently selected component.
        self.component_idx = self.component2idx[self.field_settings.component]

    def _reinit_plot_types(self, keep_selection: bool = False) -> Tuple[List[str], str]:

        # Fetch the data array from the field and check it's dimensions. If no data, return zero dim coordinate array.
        data = self.selected_field.data.copy() if self.selected_field else np.empty((0, 0, 0))

        x_dim, y_dim, z_dim = data.shape[:3]

        conditions = {
            "XY Plane": x_dim > 1 and y_dim > 1 and z_dim != 0,
            "XZ Plane": x_dim > 1 and z_dim > 1 and y_dim != 0,
            "YZ Plane": y_dim > 1 and z_dim > 1 and x_dim != 0,
            "X Linear": x_dim > 1 and y_dim != 0 and z_dim != 0,
            "Y Linear": y_dim > 1 and x_dim != 0 and z_dim != 0,
            "Z Linear": z_dim > 1 and x_dim != 0 and y_dim != 0,
            "Point": x_dim != 0 and y_dim != 0 and z_dim != 0
        }

        plot_types = []
        for t, c in conditions.items():
            if c:
                plot_types.append(t)

        selected = self.plot_type_combo.set_dropdown_items(plot_types, keep_selection=keep_selection)

        return plot_types, selected

    def _reinit_wavelength_slider(self) -> None:
        """Reloads wavelength slider range and updates the label above the slider."""

        # Set the range of the slider.
        wavelength_shape = self.monitor.wavelengths.shape[0] - 1 if self.monitor else 0
        self.wavelength_slider.set_range(0, wavelength_shape)

        # Fetch the wavelength corresponding to the slider's index value and update the label above the slider.
        if wavelength_shape != 0:
            wavelength = self.monitor.wavelengths[self.wavelength_slider.get_value()]
            self.wavelength_slider.set_label(f"Wavelength [nm]: {wavelength:.2f}")
        else:
            self.wavelength_slider.set_label(f"Wavelength [nm]:")

    def _reinit_coordinate_sliders(self) -> None:

        # Map enabled configurations to plot type.
        configuration_map = {
            "XY Plane": (False, False, True),
            "XZ Plane": (False, True, False),
            "YZ Plane": (True, False, False),
            "X Line": (False, True, True),
            "Y Line": (True, False, True),
            "Z Line": (True, True, False),
            "Point": (True, True, True),
            "": (False, False, False)  # In case no plot types are valid
        }

        # Fetch the data array from the field and check it's dimensions. If no data, return single dim coordinate array.
        data = self.selected_field.data.copy() if self.selected_field else np.empty((1, 1, 1))

        x_dim, y_dim, z_dim = data.shape[:3]

        # Reconfigure ranges
        self.x_slider.set_range(0, x_dim - 1)
        self.y_slider.set_range(0, y_dim - 1)
        self.z_slider.set_range(0, z_dim - 1)

        # Enable/disable correct sliders
        plot_type = self.plot_type_combo.get_selected()
        configuration = configuration_map[plot_type]
        for slider, enabled in zip([self.x_slider, self.y_slider, self.z_slider], configuration):
            slider.slider.setEnabled(enabled)

    def _reinit_coordinate_idx(self) -> None:
        """
        Creates a list of either slice objects or the get_value method of a slider corresponding to the
        index position of each axis coordinate. Calling each element of the list with None as an argument will
        produce the index for the currently selected coordinate.
        """

        plot_type_index_map = {
            "XY Plane": "slice,slice,slider",
            "XZ Plane": "slice,slider,slice",
            "YZ Plane": "slider,slice,slice",
            "X Linear": "slice,slider,slider",
            "Y Linear": "slider,slice,slider",
            "Z Linear": "slider,slider,slice",
            "Point": "slider,slider,slider",
            "": ""  # In case there are no available plot types.
        }

        plot_type = self.plot_type_combo.get_selected()
        index_configuration = plot_type_index_map[plot_type].split(",")
        idx = []
        for i, axis in zip(index_configuration, ["x", "y", "z"]):
            if i == "slice":
                idx.append(slice)
            elif i == "slider":
                # Append the method that fetches the idx from the given slider.
                slider: LabeledSlider = getattr(self, f"{axis}_slider")
                idx.append(slider.get_value)
            else:
                self.coordinate_idx = None
                return

        self.coordinate_idx = idx

    def _reinit_quiver_fields(self, keep_selection: bool = False):

        # Create dictionary with mappings to available fields based on the plot type.
        self.available_quiver_fields = {plot_type: [] for plot_type in self.PLOT_TYPES}

        # Check what fields have both in-plane components.
        for field in self._get_available_fields():

            # Iterate over the plane plot types.
            for plane in [plot_type for plot_type in self.available_quiver_fields.keys() if "Plane" in plot_type]:

                # If the sum is two, that means the field has both in-plane components
                if sum([int(component.capitalize() in plane) for component in field.components]) == 2:
                    self.available_quiver_fields[plane].append(field.field_name)

        # If no planes have both in-component vectors, disable vector plotting.
        if not any([self.available_quiver_fields[plane + " Plane"] for plane in ["XY", "XZ", "YZ"]]):
            self.plot_vectors_checkbox.setEnabled(False)
            self.vector_btn.setEnabled(False)
        else:
            self.plot_vectors_checkbox.setEnabled(True)
            self.vector_btn.setEnabled(True)

        # Assign the new fields to the combo box and store the selected field.
        plot_type = self.plot_type_combo.get_selected()
        selected = self.quiver_settings.field_combo.set_dropdown_items(
            self.available_quiver_fields[plot_type], keep_selection=keep_selection)

        # Fetch the corresponding field model.
        self._select_field(selected, quiver_field=True)

    def _reload_field_map_data(self) -> None:
        self.field_data = self.selected_field.data.copy() if self.selected_field else None

    def _reload_quiver_data(self) -> None:
        self.quiver_data = self.selected_quiver_field.data.copy() if self.selected_quiver_field else None

    def _apply_scalar_operation_on_quiver_data(self) -> None:
        if not self.selected_quiver_field:
            return

        scalar_operation = self.quiver_settings.scalar_operation
        if scalar_operation == "Re":
            self.quiver_data = self.quiver_data.real
        else:
            self.quiver_data = self.quiver_data.imag

    def _normalize_quiver_data(self) -> None:
        U, V = self._get_quiver_vectors()

    def _apply_magnitude_operation_on_field_map_data(self) -> None:
        """Sets the temp data array to the magnitude of the selected components."""
        component = self.field_settings.component
        if "magnitude" not in component:
            return
        component_idx = tuple([self.component2idx[char] for char in component.replace(" magnitude", "")])
        self.field_data = np.linalg.norm(self.field_data[:, :, :, :, component_idx], axis=-1, keepdims=True)

    def _apply_scalar_operation_on_field_map_data(self, reload_temp_data: bool = True) -> None:
        """
        Performs the selected scalar operation on the temp data array.

        If reload_temp_data, the array is reloaded from scratch, avoiding repeated scalar operations.
        """

        if reload_temp_data:
            self._reload_field_map_data()
            if self.field_data is None:
                return
            self._apply_magnitude_operation_on_field_map_data()  # Only does it if composite component is selected.

        # Fetch the scalar operation.
        scalar_operation = self.field_settings.scalar_op

        # Perform operations
        if scalar_operation == "Re":
            self.field_data = self.field_data.real
        elif scalar_operation == "-Re":
            self.field_data = -self.field_data.real
        elif scalar_operation == "Im":
            self.field_data = self.field_data.imag
        elif scalar_operation == "-Im":
            self.field_data = -self.field_data.imag
        elif scalar_operation == "|Abs|":
            self.field_data = np.abs(self.field_data)
        elif scalar_operation == "|Abs|^2":
            self.field_data = np.abs(self.field_data) ** 2

    def _reinit_axes(self) -> None:

        # Remove old quadmesh if it exists
        if self.quadmesh is not None:
            if self.colorbar is not None:
                self.colorbar.remove()
                self.colorbar = None
            self.quadmesh.remove()
            self.quadamesh = None

        # Remove old quiver if it exists
        if self.quiver:
            self.quiver.remove()
            self.quiver = None

        # Remove old structure artists if any.
        self._remove_structure_artists()

        # Remove linear artist if any.
        if self.linear_artist:
            self.linear_artist.remove()
            self.linear_artist = None

        plot_type = self.plot_type

        if "Plane" in plot_type:

            # Enable the wavelength slider
            self.wavelength_slider.slider.setEnabled(True)

            # Set the colormap and color scale combo boxes to visible
            self.field_settings.cmap_combo.setVisible(True)
            self.field_settings.color_scale_combo.setVisible(True)
            self.field_settings.update_custom_cscale_visibility()

            # Enable structure plots if there are structures in the simulation
            if self.simulation is None:
                plot_structures = False
            else:
                plot_structures = len(self.simulation.structures) > 0
            self.plot_structures_checkbox.setEnabled(plot_structures)
            self.structure_btn.setEnabled(plot_structures)

            # Enable field map plots if there are fields to plot
            plot_fieldmap = self.field != ""
            self.plot_fieldmap_checkbox.setEnabled(plot_fieldmap)
            self.field_settings_btn.setEnabled(plot_fieldmap)

            # Enable vector plots if there are vectors to plot
            plot_vectors = self._is_plottable_vector_fields()
            self.plot_vectors_checkbox.setEnabled(plot_vectors)
            self.vector_btn.setEnabled(plot_vectors)

            # Abort if no monitor is selected.
            if self.monitor is None:
                return

            # Fetch the coordinate arrays for the plane axes.
            coord1: NDArray = getattr(self.top.selected_monitor, plot_type[0].lower())
            coord2: NDArray = getattr(self.top.selected_monitor, plot_type[1].lower())

            # Create a mesh grid of the given coordinates.
            X, Y = np.meshgrid(coord1, coord2, indexing="ij")

            # Create a QuadMesh object with the current data and scale the color limits.
            if plot_fieldmap:
                field_idx = self._get_field_idx()
                field_map_array = self.field_data[field_idx]
                self.quadmesh = self.ax.pcolormesh(X, Y, field_map_array, cmap=self.field_settings.cmap)
                self._scale_color_limits(field_idx)
                if not self.plot_fieldmap_checkbox.isChecked():
                    self.quadamesh.set_visible(False)  # type: ignore

                # Create the colorbar and associate it with the mesh
                if not self.colorbar:
                    self.colorbar = self.fig.colorbar(self.quadmesh, ax=self.ax)

            # Create a new quiver object with zero data initially.
            if plot_vectors:
                U, V = self._get_quiver_vectors()
                self.quiver = self.ax.quiver(X, Y, U, V, scale_units="inches", )
                self._on_vector_settings_changed()
                if not self.plot_vectors_checkbox.isChecked():
                    self.quiver.set_visible(False)

            # Set the plot limits
            self.ax.set_xlim(coord1[0], coord1[-1])
            self.ax.set_ylim(coord2[0], coord2[-1])

            return

        else:
            # Enable/Disable The wavelength slider
            self.wavelength_slider.slider.setEnabled(self.plot_type != "Point")

            # Set the colormap and color scale combo boxes to invisible
            self.field_settings.cmap_combo.setVisible(False)
            self.field_settings.color_scale_combo.setVisible(False)
            self.field_settings.update_custom_cscale_visibility()

            # Enable field map plots if there are fields to plot
            plot_fieldmap = self.field != ""
            self.plot_fieldmap_checkbox.setEnabled(plot_fieldmap)
            self.field_settings_btn.setEnabled(plot_fieldmap)

            # Disable vector plots
            plot_vectors = False
            self.plot_vectors_checkbox.setEnabled(plot_vectors)
            self.vector_btn.setEnabled(plot_vectors)

            # Disable structure plots
            plot_structures = len(self.simulation.structures) > 0
            self.plot_structures_checkbox.setEnabled(plot_structures)
            self.structure_btn.setEnabled(plot_structures)

            # Abort if selected monitor is None
            if self.monitor is None:
                return

            coordinates = getattr(self.top.selected_monitor, plot_type[-1].lower())
            data = self.field_data[self._get_field_idx()]
            self.linear_artist = self.ax.plot(coordinates, data)[0]

    def _get_field_idx(self) -> tuple:
        # Fetch position index. self.coordinate_idx has either slice objects or the value getter of a slider.
        # Passing None will make empty slices or fetch the index of a slider.
        coordinate_idx = [i(None) for i in self.coordinate_idx]

        # Append index of the wavelength
        idx: List[Union[int, slice, Tuple]] = coordinate_idx.copy() + [self.wavelength_slider.get_value()]

        # Append index of the components
        idx.append(self.component_idx)

        idx_tuple = tuple(idx)

        return idx_tuple

    # endregion

    # region Helper methods
    def _get_available_fields(self) -> List[FieldModel]:
        """Returns the available fields of the currently selected monitor"""
        if self.monitor:
            return self.monitor.fields
        return []

    def _select_field(self, field_name: str, quiver_field: bool = False) -> None:
        """
        Updates the selected_field variable to the field of the currently selected monitor matching the field_name.
        """

        # Decide if it's the selected quiver field or the selected field map field that should be selected.
        if quiver_field:
            variable = "selected_quiver_field"
        else:
            variable = "selected_field"

        # Fetch the selected field
        selected_field: Optional[FieldModel] = next(
            (f for f in self._get_available_fields() if f.field_name == field_name), None
        )

        # Update the member variable
        setattr(self, variable, selected_field)

    def _get_component_combinations(self) -> List[str]:
        """Returns the possible combinations of the available components for the field."""

        # Fetch the available components.
        components = self.selected_field.components if self.selected_field else []

        # Generate the component combinations.
        combinations = []
        for r in range(1, len(components) + 1):
            for combo in itertools.combinations(components, r):
                if len(combo) == 1:
                    combinations.append(combo[0])
                else:
                    combinations.append(''.join(combo) + " magnitude")

        return combinations

    def _is_plottable_vector_fields(self) -> bool:
        if self.available_quiver_fields[self.plot_type]:
            return True
        return False

    def _remove_structure_artists(self) -> None:

        # Remove fill and outline.
        for struct_type in [self.structure_outlines, self.structure_fills]:
            for _, planes in struct_type.items():
                for _, artist in planes.items():
                    if artist[1]:  # boolean flag for wether the artist is currently active or not.
                        artist[0].remove()

        for _, planes in self.structure_intersections:
            for _, artists in planes.items():
                for artist, active in artists:
                    if active:
                        artist.remove()

    def _scale_color_limits(self, idx: tuple = None) -> None:

        scale = self.field_settings.cscale
        if type(idx) is not tuple:
            idx = self._get_field_idx()

        print(idx)
        # If current plot, the updatate_data method does this automatically
        if scale == "Current wavelength":
            pass

        # If current position, scale based on what's in the temp data.
        elif scale == "Current plane":
            idx = (*idx[:3], slice(None), idx[-1])

        # If all values, scale based on all positions.
        elif scale == "All planes":
            idx = (slice(None), slice(None), slice(None), slice(None), idx[-1])

        elif scale == "Custom limits":
            self.quadmesh.set_clim(self.field_settings.cscale_custom_min, self.field_settings.cscale_custom_max)
            self.canvas.draw_idle()
            return

        self.quadmesh.set_clim(np.min(self.field_data[idx]), np.max(self.field_data[idx]))
        self.canvas.draw_idle()

    def _get_quiver_vectors(self) -> Union[Tuple[NDArray, NDArray], Tuple[None, None]]:
        plane_components = self.plot_type.lower().replace(" plane", "")
        component_idx = tuple([i for i, component in enumerate(self.selected_quiver_field.components) if
                               component in plane_components])
        if len(component_idx) != 2:
            return None, None

        coordinate_idx = [i(None) for i in self.coordinate_idx]
        wavelength_idx = [self.wavelength_slider.get_value()]

        U = self.quiver_data[tuple(coordinate_idx + wavelength_idx + [component_idx[0]])]
        V = self.quiver_data[tuple(coordinate_idx + wavelength_idx + [component_idx[1]])]
        return U, V

    def _apply_quiver_cosmetics(self, settings: dict = None) -> None:
        ...

    @staticmethod
    def _normalize_vectors(U: NDArray, V: NDArray) -> Tuple[NDArray, NDArray]:
        magnitude = np.sqrt(U ** 2 + V ** 2)
        U_norm = np.divide(U, magnitude, out=np.zeros_like(U), where=magnitude != 0)
        V_norm = np.divide(V, magnitude, out=np.zeros_like(V), where=magnitude != 0)
        return U_norm, V_norm

    def get_quiver_artist(self) -> Quiver:
        """Returns the active quiver artist if any, else None."""
        return self.quiver

    def get_quadmesh_artist(self) -> QuadMesh:
        """Returns the active quadmesh artist if any, else None."""

    def update_data(self) -> None:

        # Fetch field map field index
        idx_tuple = self._get_field_idx()

        data = self.field_data[idx_tuple]

        # Update data for the quadmesh and quiver if plot type is
        if "Plane" in self.plot_type:
            if self.quadmesh is not None and self.plot_fieldmap_checkbox.isChecked():
                self.quadmesh.set_array(data)
            if self.quiver_data is not None and self.plot_vectors_checkbox.isChecked():
                U, V = self._get_quiver_vectors()
                if self.quiver_settings.normalized:
                    U, V = self._normalize_vectors(U, V)

                self.quiver.set_UVC(U, V)
        else:
            self.linear_artist.set_data(data)

        if self.field_settings.cscale == "Current wavelength":
            self.quadmesh.set_clim(np.min(data), np.max(data))

        self.canvas.draw_idle()

    # endregion

    # region Callbacks
    def on_aspect_ratio_changed(self, val: bool) -> None:
        if val:
            self.ax.set_aspect("equal")
        else:
            self.ax.set_aspect("auto")
        self.canvas.draw_idle()

    def on_title_changed(self, settings: dict) -> None:
        """Update the plot title according to settings."""

        if self.title is None:
            return

        self.title.set_text(settings.get("text", ""))
        self.title.set_fontfamily(settings.get("font", "Arial"))
        self.title.set_fontsize(settings.get("size", 14))

        color = settings.get("color", QColor("black"))
        self.title.set_color(color.name())  # Convert QColor to hex string

        align = settings.get("align", "center")
        if align == "center":
            self.title.set_horizontalalignment("center")
        elif align == "left":
            self.title.set_horizontalalignment("right")  # These are opposite for some wierd reason.
        elif align == "right":
            self.title.set_horizontalalignment("left")

        # Force canvas redraw
        self.canvas.draw_idle()

    def on_xlabel_changed(self, settings: dict) -> None:
        """Update the xlabel according to settings."""

        if self.x_label is None:
            return

        self.x_label.set_text(settings.get("text", ""))
        self.x_label.set_fontfamily(settings.get("font", "Arial"))
        self.x_label.set_fontsize(settings.get("size", 14))

        color = settings.get("color", QColor("black"))
        self.x_label.set_color(color.name())  # Convert QColor to hex string

        # Force canvas redraw
        self.canvas.draw_idle()

    def on_ylabel_changed(self, settings: dict) -> None:
        ...

    def on_xticks_changed(self, settings: dict) -> None:
        ...

    def on_yticks_changed(self, settings: dict) -> None:
        ...

    def on_legend_changed(self, settings: dict) -> None:
        ...

    def on_grid_changed(self, settings: dict) -> None:
        ...

    def toggle_field_plot(self, show_field: bool):
        if not show_field:
            self.quadmesh.set_visible(False)
            if self.colorbar:
                self.colorbar.remove()
                self.colorbar = None
        else:
            self.quadmesh.set_visible(True)
            if not self.colorbar:
                self.colorbar = self.fig.colorbar(self.quadmesh, ax=self.ax)

    def on_component_changed(self, component: str) -> None:
        self._reinit_component_idx()
        self._apply_scalar_operation_on_field_map_data(reload_temp_data=True)
        self._scale_color_limits()
        self.update_data_timer.start(self.callback_delay)

    def on_scalar_op_changed(self, op: str):
        self._apply_scalar_operation_on_field_map_data(reload_temp_data=True)
        self._scale_color_limits()
        self.update_data_timer.start(self.callback_delay)

    def on_cmap_changed(self, val: str):
        self.quadmesh.set_cmap(val)
        self.canvas.draw_idle()

    def on_field_changed(self, val: str) -> None:
        self._select_field(val)
        self._reload_field_map_data()
        self._apply_magnitude_operation_on_field_map_data()
        self._apply_scalar_operation_on_field_map_data()
        self._reinit_components(keep_selection=True)
        self._reinit_component_idx()
        self._scale_color_limits()
        self.update_data()

    def _on_quiver_field_changed(self, field: str) -> None:
        self._select_field(field, quiver_field=True)
        self._reload_quiver_data()
        self._apply_scalar_operation_on_quiver_data()
        self.update_data()

    def _on_quiver_scalar_operation_changed(self, scalar_op):
        self._reload_quiver_data()
        self._apply_scalar_operation_on_quiver_data()
        self.update_data()

    def _on_quiver_normalize(self):
        self.update_data()

    def _on_vector_settings_changed(self, settings: dict = None) -> None:
        """
        Apply the current vector plot settings from self.quiver_settings to the existing quiver artist.
        """
        if self.quiver is None:
            return

        self.quiver.scale_units = "width"
        self.quiver.scale = self.quiver_settings.scale
        self.quiver.pivot = self.quiver_settings.pivot
        self.quiver.set_color(self.quiver_settings.color)
        self.quiver.set_alpha(self.quiver_settings.alpha)
        self.quiver.width = self.quiver_settings.width
        self.quiver.headwidth = self.quiver_settings.headwidth
        self.quiver.headlength = self.quiver_settings.headlength
        self.quiver.headaxislength = self.quiver_settings.headaxislength

        # Redraw with delay
        self.draw_idle_timer.start(self.callback_delay)

    def on_wavelength_changed(self, val: int):
        self.wavelength_slider.set_label(f"Wavelength [nm]: {self.top.selected_monitor.wavelengths[val]:.2f}")
        self.update_data_timer.start(self.callback_delay)

    def on_coordinate_change(self):
        if self.field_settings.color_scale == "Current position":
            self._scale_color_limits()
        self.update_data()

    def on_plot_type_changed(self, plot_type: str):
        self._close_all_settings_panels()

    def _on_show_field_toggled(self, show_field: bool) -> None:
        if not show_field:
            self.quadmesh.set_visible(False)
            if self.colorbar:
                self.colorbar.remove()
                self.colorbar = None
        else:
            self.quadmesh.set_visible(True)
            if not self.colorbar:
                self.colorbar = self.fig.colorbar(self.quadmesh, ax=self.ax)
        self.update_data_timer.start(self.callback_delay)

    def _on_show_structures_toggled(self, val: bool) -> None:
        ...

    def _on_show_vectors_toggled(self, val: bool) -> None:
        if self.quiver:
            self.quiver.set_visible(val)
        self.update_data_timer.start(self.callback_delay)

    # endregion

    # region Properties
    @property
    def custom_intersection(self) -> Tuple[bool, int]:
        return False, 0

    @property
    def monitor(self) -> Optional[MonitorModel]:
        """Returns the currently selected monitor from the application's top level."""
        return self.top.selected_monitor

    @property
    def simulation(self) -> Optional[SimulationModel]:
        """Returns the simulation associated with the currently selected monitor."""
        if self.monitor is not None:
            return self.monitor.simulation
        return None

    @property
    def plot_type(self) -> str:
        return self.plot_type_combo.get_selected()

    @property
    def field(self) -> str:
        return self.field_combo.get_selected()

    @field.setter
    def field(self, val: str) -> None:
        self.field_combo.blockSignals(True)
        index = self.field_combo.dropdown.findText(val)
        if index != -1:
            self.field_combo.dropdown.setCurrentIndex(index)
        self.field_combo.blockSignals(False)

    # endregion

    # region TEMP
    def show_quadmesh_settings(self):
        if self.quadmesh_dialog and self.quadmesh_dialog.isVisible():
            self.quadmesh_dialog.close()
            return

        if self.quadmesh_dialog is None:
            self.quadmesh_dialog = QDialog(self)
            self.quadmesh_dialog.setWindowTitle("Quadmesh Settings")
            self.quadmesh_dialog.setMinimumWidth(300)
            self.quadmesh_dialog.setWindowFlags(self.quadmesh_dialog.windowFlags() | Qt.WindowType.Tool)

            layout = QVBoxLayout(self.quadmesh_dialog)
            layout.addWidget(self.field_settings)

        # Position dialog so its bottom aligns with button
        button_pos = self.field_settings_btn.mapToGlobal(self.field_settings_btn.rect().topRight())
        dialog_height = self.quadmesh_dialog.sizeHint().height()
        adjusted_pos = button_pos - QPoint(0, dialog_height)
        self.quadmesh_dialog.move(adjusted_pos)

        self.quadmesh_dialog.show()
        self.quadmesh_dialog.raise_()
        self.quadmesh_dialog.activateWindow()

    def show_quiver_settings(self):
        if self.vector_dialog and self.vector_dialog.isVisible():
            self.vector_dialog.close()
            return

        if self.vector_dialog is None:
            self.vector_dialog = QDialog(self)
            self.vector_dialog.setWindowTitle("Quadmesh Settings")
            self.vector_dialog.setMinimumWidth(300)
            self.vector_dialog.setWindowFlags(self.vector_dialog.windowFlags() | Qt.WindowType.Tool)

            layout = QVBoxLayout(self.vector_dialog)
            layout.addWidget(self.quiver_settings)

        # Position dialog so its bottom aligns with button
        button_pos = self.vector_btn.mapToGlobal(self.vector_btn.rect().topRight())
        dialog_height = self.vector_dialog.sizeHint().height()
        adjusted_pos = button_pos - QPoint(0, dialog_height)
        self.vector_dialog.move(adjusted_pos)

        self.vector_dialog.show()
        self.vector_dialog.raise_()
        self.vector_dialog.activateWindow()

    def show_plot_settings(self) -> None:
        if self.plot_dialog and self.plot_dialog.isVisible():
            self.plot_dialog.close()
            return

        if self.plot_dialog is None:
            self.plot_dialog = QDialog(self)
            self.plot_dialog.setWindowTitle("Quadmesh Settings")
            self.plot_dialog.setMinimumWidth(300)
            self.plot_dialog.setWindowFlags(self.plot_dialog.windowFlags() | Qt.WindowType.Tool)

            layout = QVBoxLayout(self.plot_dialog)
            layout.addWidget(self.plot_settings)

        # Position dialog so its bottom aligns with button
        button_pos = self.plot_btn.mapToGlobal(self.plot_btn.rect().topRight())
        dialog_height = self.plot_dialog.sizeHint().height()
        adjusted_pos = button_pos - QPoint(0, dialog_height)
        self.plot_dialog.move(adjusted_pos)

        self.plot_dialog.show()
        self.plot_dialog.raise_()
        self.plot_dialog.activateWindow()

    def _close_all_settings_panels(self):
        for dialog in [
            self.quadmesh_dialog,
            self.structure_dialog,
            self.vector_dialog,
            self.plot_dialog,
        ]:
            if dialog is not None and dialog.isVisible():
                dialog.close()

    @staticmethod
    def get_plot_modes(field: FieldModel) -> Tuple[List[str], List[str]]:

        array = field.data

        if array.ndim != 5:
            raise ValueError("Expected a 5D array of shape (x, y, z, lambda, components)")

        shape = array.shape
        x_len, y_len, z_len = shape[:3]

        modes2d = []
        modes1d = []

        # 2D planes
        if x_len > 1 and y_len > 1:
            modes2d.append("XY Plane")
        if x_len > 1 and z_len > 1:
            modes2d.append("XZ Plane")
        if y_len > 1 and z_len > 1:
            modes2d.append("YZ Plane")

        # 1D lines
        if x_len > 1 and y_len == 1 and z_len == 1:
            modes1d.append("X Line")
        if y_len > 1 and x_len == 1 and z_len == 1:
            modes1d.append("Y Line")
        if z_len > 1 and x_len == 1 and y_len == 1:
            modes1d.append("Z Line")

        return modes1d, modes2d

    def show_structure_settings(self) -> None:
        ...

    def draw_idle(self) -> None:
        self.canvas.draw_idle()
    # endregion
