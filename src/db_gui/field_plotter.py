import itertools
from typing import Union, List, Tuple, Optional, Dict

import numpy as np
from PyQt6.QtCore import QPoint
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QCheckBox, QHBoxLayout
)
from matplotlib.axes import Axes
from .widgets import TightNavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import QuadMesh
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch
from matplotlib.quiver import Quiver
from matplotlib.text import Text
from numpy.typing import NDArray
from mpl_toolkits.axes_grid1 import make_axes_locatable

from .field_plt_settings import FieldSettings
from .plt_settings import PlotSettings
from .structure_plt_settings import StructureSettings
from .top_level import TopLevel
from .vector_plt_settings import VectorSettings
from .widgets import LabeledSlider, LabeledDropdown
from ..fdtdream.database.db import FieldModel, MonitorModel, SimulationModel


class FieldPlotTab(QWidget):
    # region Top level
    top: TopLevel
    # endregion

    # region Default Values
    PLOT_TYPES = ["XY Plane", "XZ Plane", "YZ Plane", "X Linear", "Y Linear", "Z Linear", "Point"]
    CALLBACK_DELAY: float = 10
    # endregion

    # region Data
    selected_simulation: Optional[int]
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
    fig: Figure
    canvas: FigureCanvas

    title: Text
    x_label: Text
    y_label: Text
    legend: Optional[Legend]

    ax: Axes

    quadmesh: Optional[QuadMesh]
    colorbar: Optional[Colorbar]

    structure_outlines: Dict[int, Dict[str, PathPatch]]  # Bool shows active artist or not
    structure_intersections: Dict[int, Dict[str, List[PathPatch]]]

    quiver: Optional[Quiver]

    linear_artist: Optional[Line2D]
    # endregion

    # region Widgets
    _layout: QVBoxLayout
    wavelength_slider: LabeledSlider
    field_combo: LabeledDropdown
    plot_type_combo: LabeledDropdown

    field_settings_dialog: Optional[QDialog]
    structure_settings_dialog: Optional[QDialog]
    quiver_settings_dialog: Optional[QDialog]
    plot_settings_dialog: Optional[QDialog]

    plot_fieldmap_checkbox: QCheckBox
    plot_vectors_checkbox: QCheckBox
    plot_structures_checkbox: QCheckBox
    # endregion

    # region Timers
    update_data_timer: QTimer
    draw_idle_timer: QTimer
    cscale_timer: QTimer

    # endregion
    def __init__(self, parent: TopLevel):
        super().__init__(parent)

        # Store reference to app top level.
        self.top = parent

        # Create main layout
        self._layout = QVBoxLayout(self)

        # Initialize
        self._init_timers()
        self._init_data()
        self._init_artists()
        self._init_figure()
        self._init_setting_modules()
        self._init_controls()

    # region INIT
    def _init_timers(self) -> None:
        self.update_data_timer = QTimer(self)
        self.update_data_timer.setSingleShot(True)
        self.update_data_timer.timeout.connect(self.update_data)  # type: ignore

        self.draw_idle_timer = QTimer(self)
        self.draw_idle_timer.setSingleShot(True)
        self.draw_idle_timer.timeout.connect(self._draw_idle)  # type: ignore

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
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)
        self.canvas = FigureCanvas(self.fig)

        # Create the toolbar
        self.toolbar = TightNavigationToolbar(self.canvas, self)

        # Add the toolbar and canvas to the layout
        self._layout.addWidget(self.toolbar)
        self._layout.addWidget(self.canvas, stretch=1)

        self.ax = self.fig.add_subplot(111)

        # Store references to important artists
        self.title = self.ax.set_title("")
        self.x_label = self.ax.set_xlabel("")
        self.y_label = self.ax.set_ylabel("")
        self.legend = self.ax.legend([], [])  # Empty legend initially
        self.legend.set_visible(False)

    def _init_setting_modules(self) -> None:
        self.field_settings = FieldSettings(self)  # type: ignore
        self.quiver_settings = VectorSettings(self)  # type: ignore
        self.plot_settings = PlotSettings(self)  # type: ignore
        self.structure_settings = StructureSettings(self)  # type: ignore

        self.field_settings_dialog = None
        self.structure_settings_dialog = None
        self.quiver_settings_dialog = None
        self.plot_settings_dialog = None

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

        self.x_slider = LabeledSlider(self, "x [nm]: ", 0, 0, self.on_x_coord_change)
        self.x_slider.slider.setEnabled(False)
        coords_layout.addWidget(self.x_slider)

        self.y_slider = LabeledSlider(self, "y [nm]: ", 0, 0, self.on_y_coord_change)
        self.y_slider.slider.setEnabled(False)
        coords_layout.addWidget(self.y_slider)

        self.z_slider = LabeledSlider(self, "z [nm]: ", 0, 0, self.on_z_coord_change)
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
        self.plot_fieldmap_checkbox.toggled.connect(self.on_show_field_toggled)  # type: ignore
        field_plt_layout.addWidget(self.plot_fieldmap_checkbox)

        self.field_settings_btn = QPushButton("Field Settings")
        self.field_settings_btn.setEnabled(False)
        self.field_settings_btn.clicked.connect(self.on_field_settings_clicked)  # type: ignore
        field_plt_layout.addWidget(self.field_settings_btn)

        settings_layout.addLayout(field_plt_layout)
        # endregion

        # region Structure settings button and checkbox
        structure_plt_layout = QVBoxLayout()

        self.plot_structures_checkbox = QCheckBox("Show Structures")
        self.plot_structures_checkbox.setChecked(True)
        self.plot_structures_checkbox.setEnabled(False)
        self.plot_structures_checkbox.toggled.connect(self.on_show_structures_toggled)  # type: ignore
        structure_plt_layout.addWidget(self.plot_structures_checkbox)

        self.structure_btn = QPushButton("Structure Settings")
        self.structure_btn.setEnabled(False)
        self.structure_btn.clicked.connect(self.on_structure_settings_clicked)  # type: ignore
        structure_plt_layout.addWidget(self.structure_btn)

        settings_layout.addLayout(structure_plt_layout)
        # endregion

        # region Vector settings button and checkbox
        vector_plt_layout = QVBoxLayout()

        self.plot_vectors_checkbox = QCheckBox("Show Field Vectors")
        self.plot_vectors_checkbox.setChecked(False)
        self.plot_vectors_checkbox.setEnabled(False)
        self.plot_vectors_checkbox.toggled.connect(self.on_show_vectors_toggled)  # type: ignore
        vector_plt_layout.addWidget(self.plot_vectors_checkbox)

        self.vector_btn = QPushButton("Vector Plot Settings")
        self.vector_btn.setEnabled(False)
        self.vector_btn.clicked.connect(self.on_quiver_settings_clicked)  # type: ignore
        vector_plt_layout.addWidget(self.vector_btn)

        settings_layout.addLayout(vector_plt_layout)
        # endregion

        # region Plot settings button (aligned without checkbox)
        plt_settings_layout = QVBoxLayout()

        # Add spacer to vertically align with other buttons
        spacer_height = self.plot_vectors_checkbox.sizeHint().height()
        plt_settings_layout.addSpacing(spacer_height)

        self.plot_btn = QPushButton("Plot Settings")
        self.plot_btn.clicked.connect(self.on_plot_settings_clicked)  # type: ignore
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
        was_none = self.selected_simulation is None
        if self.selected_simulation is None and self.monitor is not None:
            self.selected_simulation = self.monitor.simulation.id

        self.reinit_field_map_fields(keep_selection=True)
        self.reinit_components(keep_selection=True)
        self.reinit_component_idx()
        self.reinit_plot_types(keep_selection=True)
        self.reinit_wavelength_slider()
        self.reinit_coordinate_idx()
        self.reinit_coordinate_sliders()

        self.reinit_quiver_fields(keep_selection=True)
        self.reload_field_map_data()
        self.reload_quiver_data()
        self.apply_magnitude_operation_on_field_map_data()
        self.apply_scalar_operation_on_field_map_data(reload_temp_data=False)

        # Reset axes and plot controls while plotting the currently selected dataset
        self.reinit_axes()

        self.reinit_structures(was_none)

        # Update the monitor's parent simulation
        self.selected_simulation = self.monitor.simulation.id if self.monitor else None

    def reinit_field_map_fields(self, keep_selection: bool = False) -> None:
        """
        Loads available fields from the monitor.
        Sets the same field as previously if possible and keep_selection.
        If refill_combobox, the
        """

        # Fetch available field names
        field_names = [field.field_name for field in self.get_available_fields()]

        # Assign the new fields to the combo box.
        selected = self.field_combo.set_dropdown_items(field_names, keep_selection=keep_selection)

        # Store the selected field model.
        self.select_field(selected)

        # Disable field settings and checkbox if None is selected, else enable.
        enabled = self.select_field is not None
        self.plot_fieldmap_checkbox.setEnabled(enabled)
        self.field_settings_btn.setEnabled(enabled)

    def reinit_components(self, keep_selection: bool = False):
        """Loads available field components and combinations into the combo box. Returns the selected component."""

        # Fetch component combinations. Returns empty list if no field is selected.
        combinations = self.get_component_combinations()

        # Assign the new items to the combo box.
        self.field_settings.component_combo.set_dropdown_items(combinations, keep_selection=keep_selection)

    def reinit_component_idx(self) -> None:
        """Finds the correct indices for the components available in the dataset for the given field."""

        # Fetch available components.
        available_components = self.get_component_combinations()
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

    def reinit_plot_types(self, keep_selection: bool = False) -> None:

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

        self.plot_type_combo.set_dropdown_items(plot_types, keep_selection=keep_selection)

    def reinit_wavelength_slider(self) -> None:
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

    def reinit_coordinate_idx(self) -> None:
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

    def reinit_coordinate_sliders(self) -> None:

        # Map enabled configurations to plot type.
        configuration_map = {
            "XY Plane": (False, False, True),
            "XZ Plane": (False, True, False),
            "YZ Plane": (True, False, False),
            "X Linear": (False, True, True),
            "Y Linear": (True, False, True),
            "Z Linear": (True, True, False),
            "Point": (True, True, True),
            "": (False, False, False)  # In case no plot types are valid
        }

        # Fetch the data array from the field and check it's dimensions. If no data, return single dim coordinate array.
        data = self.selected_field.data.copy() if self.selected_field else np.empty((1, 1, 1))

        x_dim, y_dim, z_dim = data.shape[:3]

        # Reconfigure ranges
        self.x_slider.set_range(0, x_dim-1), self.on_x_coord_change(update_data=False)
        self.y_slider.set_range(0, y_dim-1), self.on_y_coord_change(update_data=False)
        self.z_slider.set_range(0, z_dim-1), self.on_z_coord_change(update_data=False)

        # Enable/disable correct sliders
        plot_type = self.plot_type_combo.get_selected()
        configuration = configuration_map[plot_type]
        for slider, enabled in zip([self.x_slider, self.y_slider, self.z_slider], configuration):
            slider.slider.setEnabled(enabled)

    def reinit_quiver_fields(self, keep_selection: bool = False):

        # Create dictionary with mappings to available fields based on the plot type.
        self.available_quiver_fields = {plot_type: [] for plot_type in self.PLOT_TYPES}

        # Check what fields have both in-plane components.
        for field in self.get_available_fields():

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
        self.select_field(selected, quiver_field=True)

    def reload_field_map_data(self) -> None:
        self.field_data = self.selected_field.data.copy() if self.selected_field else None

    def reload_quiver_data(self) -> None:

        # Fetch the raw field data
        data = self.selected_quiver_field.data.copy() if self.selected_quiver_field else None
        if data is None:
            return

        # Fetch the in-plane field components indices.
        plane_components = self.plot_type.lower().replace(" plane", "")
        component_idx = tuple([i for i, component in enumerate(self.selected_quiver_field.components) if
                               component in plane_components])

        # Filter data
        data = data[:, :, :, :, component_idx]

        # Apply scalar operation
        scalar_operation = self.quiver_settings.scalar_operation
        if scalar_operation == "Re":
            data = data.real
        else:
            data = data.imag

        # Normalize if normalization is enabled.
        if self.quiver_settings.normalized:
            norm = np.linalg.norm(data, axis=-1, keepdims=True)  # shape (X, Y, Z, Lambda, 1)

            # Avoid division by zero
            with np.errstate(divide='ignore', invalid='ignore'):
                data = np.divide(data, norm, where=norm != 0)

        # Assign quiver data
        self.quiver_data = data

    def apply_magnitude_operation_on_field_map_data(self) -> None:
        """Sets the temp data array to the magnitude of the selected components."""
        component = self.field_settings.component
        if "magnitude" not in component:
            return
        component_idx = tuple([self.component2idx[char] for char in component.replace(" magnitude", "")])
        self.field_data = np.linalg.norm(self.field_data[:, :, :, :, component_idx], axis=-1, keepdims=True)

    def apply_scalar_operation_on_field_map_data(self, reload_temp_data: bool = True) -> None:
        """
        Performs the selected scalar operation on the temp data array.

        If reload_temp_data, the array is reloaded from scratch, avoiding repeated scalar operations.
        """

        if reload_temp_data:
            self.reload_field_map_data()
            if self.field_data is None:
                return
            self.apply_magnitude_operation_on_field_map_data()  # Only does it if composite component is selected.

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

    def reinit_axes(self) -> None:

        # Remove old quadmesh if it exists
        if self.quadmesh is not None:
            if self.colorbar is not None:
                self.colorbar.remove()
                self.colorbar = None
            self.quadmesh.remove()
            self.quadmesh = None

        # Remove old quiver if it exists
        if self.quiver:
            self.quiver.remove()
            self.quiver = None

        # Remove old structure artists if any.
        self.remove_structure_artists()

        # Remove linear artist if any.
        if self.linear_artist:
            self.linear_artist.remove()
            self.linear_artist = None

        plot_type = self.plot_type

        if "Plane" in plot_type:

            # Enable the wavelength slider
            self.wavelength_slider.slider.setEnabled(True)

            # Reconfigure coordinate sliders
            self.reinit_coordinate_sliders()

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
            plot_vectors = self.is_plottable_vector_fields()
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
            idx = field_idx = self.get_field_idx()
            if plot_fieldmap:
                field_map_array = self.field_data[idx]
                self.quadmesh = self.ax.pcolormesh(X, Y, field_map_array, cmap=self.field_settings.cmap)
                self.field_settings.scale_color_limits(idx)
                self.quadmesh.set_visible(self.plot_fieldmap_checkbox.isChecked())

                # Create the colorbar and associate it with the mesh
                if not self.colorbar and self.plot_fieldmap_checkbox.isChecked():
                    divider = make_axes_locatable(self.ax)

                    # 5% of main plot width, 5% padding
                    self.cax = divider.append_axes("right", size="5%", pad=0.1)
                    self.cax.xaxis.set_visible(False)
                    self.cax.yaxis.set_ticks_position('right')
                    self.cax.yaxis.set_label_position('right')
                    self.colorbar = self.fig.colorbar(self.quadmesh, cax=self.cax)

            # Create a new quiver object with zero data initially.
            if plot_vectors:
                vector_idx = idx[:-1]
                U, V = np.moveaxis(self.quiver_data[vector_idx], -1, 0)
                self.quiver = self.ax.quiver(X, Y, U, V)
                self.quiver_settings.reapply_quiver_config()
                self.quiver.set_visible(self.plot_vectors_checkbox.isChecked())

            # Set the plot limits
            self.ax.set_xlim(coord1[0], coord1[-1])
            self.ax.set_ylim(coord2[0], coord2[-1])

            return

        else:
            # Enable/Disable The wavelength slider
            self.wavelength_slider.slider.setEnabled(self.plot_type != "Point")

            # Reinit coordinate sliders.
            self.reinit_coordinate_sliders()

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

            coordinates = getattr(self.top.selected_monitor, plot_type[0].lower())
            data = self.field_data[self.get_field_idx()]
            self.linear_artist = self.ax.plot(coordinates, data)[0]
            self.ax.relim()
            self.ax.autoscale()

    def reinit_structures(self, execute_anyways: bool = False) -> None:

        if self.monitor is None:
            return
        elif execute_anyways:
            self.remove_structure_artists()
            self.structure_outlines = {}
            self.structure_intersections = {}
            for section in self.structure_settings.section_widgets:
                self.structure_settings._remove_section(section)
            self.structure_settings.populate_structures()

        elif self.selected_simulation == self.monitor.simulation.id:
            for section in self.structure_settings.section_widgets:
                section.on_monitor_changed()
        else:
            self.remove_structure_artists()
            self.structure_outlines = {}
            self.structure_intersections = {}
            for section in self.structure_settings.section_widgets:
                self.structure_settings._remove_section(section)
            self.structure_settings.populate_structures()

    # endregion

    # region Helper methods
    def get_field_idx(self) -> tuple:
        # Fetch position index. self.coordinate_idx has either slice objects or the value getter of a slider.
        # Passing None will make empty slices or fetch the index of a slider.
        coordinate_idx = [i(None) for i in self.coordinate_idx]

        # Append index of the wavelength
        idx: List[Union[int, slice, Tuple]] = coordinate_idx.copy() + [self.wavelength_slider.get_value()]

        # Append index of the components
        idx.append(self.component_idx)

        idx_tuple = tuple(idx)

        return idx_tuple

    def get_available_fields(self) -> List[FieldModel]:
        """Returns the available fields of the currently selected monitor"""
        if self.monitor:
            return self.monitor.fields
        return []

    def select_field(self, field_name: str, quiver_field: bool = False) -> None:
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
            (f for f in self.get_available_fields() if f.field_name == field_name), None
        )

        # Update the member variable
        setattr(self, variable, selected_field)

    def get_component_combinations(self) -> List[str]:
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

    def is_plottable_vector_fields(self) -> bool:
        if self.available_quiver_fields[self.plot_type]:
            return True
        return False

    def remove_structure_artists(self) -> None:
        # Remove outline.
        for _, structures in self.structure_outlines.items():
            for _, artist in structures.items():
                if artist.axes:
                    artist.remove()

        # Remove intersection
        for _, planes in self.structure_intersections.items():
            for _, artists in planes.items():
                for artist in artists:
                    if artist and artist.axes:
                        artist.remove()

    def _on_coordinate_change(self, coordinate_idx: int, update_data: bool = True):
        mapping = {0: "x", 1: "y", 2: "z"}
        coordinate = mapping[coordinate_idx]
        coordinates = getattr(self.monitor, coordinate)
        idx = self.coordinate_idx[coordinate_idx](None)

        if type(idx) is slice:
            label = f"{coordinate} [nm]: {coordinates[0]:.2f} → {coordinates[-1]:.2f}"
        else:
            label = f"{coordinate} [nm]: {coordinates[idx]:.2f}"

        slider: LabeledSlider = getattr(self, f"{coordinate}_slider")
        slider.set_label(label)

        if update_data:
            if self.field_settings.cscale in ["Current wavelength", "Current plane"]:
                if "Plane" in self.plot_type:
                    self.field_settings.scale_color_limits()
            self.update_data_timer.start(self.CALLBACK_DELAY)

    def update_data(self) -> None:

        # Fetch field map field index
        idx_tuple = self.get_field_idx()
        data = self.field_data[idx_tuple]

        # Update data for the quadmesh and quiver if plot type is
        if "Plane" in self.plot_type:
            if self.quadmesh is not None and self.plot_fieldmap_checkbox.isChecked():
                self.quadmesh.set_array(data)
            if self.quiver_data is not None and self.plot_vectors_checkbox.isChecked():
                U, V = np.moveaxis(self.quiver_data[idx_tuple[:-1]], -1, 0)
                self.quiver.set_UVC(U, V)
            if self.field_settings.cscale == "Current wavelength":
                self.quadmesh.set_clim(np.min(data), np.max(data))
        else:
            self.linear_artist.set_ydata(data)
            self.ax.relim()
            self.ax.autoscale()

        self.canvas.draw_idle()
    # endregion

    # region Callbacks
    def on_show_field_toggled(self, show_field: bool) -> None:
        if not show_field:
            self.quadmesh.set_visible(False)
            if self.colorbar:
                self.cax.set_visible(False)
                self.colorbar.remove()
                self.colorbar = None
        else:
            divider = make_axes_locatable(self.ax)

            # 5% of main plot width, 5% padding
            self.cax = divider.append_axes("right", size="5%", pad=0.1)
            self.cax.xaxis.set_visible(False)
            self.cax.yaxis.set_ticks_position('right')
            self.cax.yaxis.set_label_position('right')

            self.quadmesh.set_visible(True)
            self.cax.set_visible(True)
            if not self.colorbar:
                self.colorbar = self.fig.colorbar(self.quadmesh, cax=self.cax)
        self.draw_idle_timer.start(self.CALLBACK_DELAY)

    def on_show_structures_toggled(self, val: bool) -> None:
        ...

    def on_show_vectors_toggled(self, val: bool) -> None:
        if self.quiver:
            self.quiver.set_visible(val)
        self.draw_idle_timer.start(self.CALLBACK_DELAY)

    def on_field_changed(self, val: str) -> None:
        self.select_field(val)
        self.reload_field_map_data()
        self.apply_magnitude_operation_on_field_map_data()
        self.apply_scalar_operation_on_field_map_data()
        self.reinit_components(keep_selection=True)
        self.reinit_component_idx()
        self.field_settings.scale_color_limits()
        self.update_data()

    def on_wavelength_changed(self, val: int):
        self.wavelength_slider.set_label(f"Wavelength [nm]: {self.top.selected_monitor.wavelengths[val]:.2f}")
        self.update_data_timer.start(self.CALLBACK_DELAY)

    def on_x_coord_change(self, val: int = None, update_data: bool = True) -> None:
        self._on_coordinate_change(0, update_data=update_data)

    def on_y_coord_change(self, val: int = None, update_data: bool = True) -> None:
        self._on_coordinate_change(1, update_data=update_data)

    def on_z_coord_change(self, val: int = None, update_data: bool = True) -> None:
        self._on_coordinate_change(2, update_data=update_data)

    def on_plot_type_changed(self, plot_type: str):
        self.reinit_coordinate_idx()
        self.reinit_quiver_fields(keep_selection=True)
        self.reload_quiver_data()
        self.reinit_axes()  # Also updates data and creates new artists.
        self.draw_idle_timer.start(self.CALLBACK_DELAY)
        if "Plane" in plot_type:
            self.plot_fieldmap_checkbox.setEnabled(True)
        else:
            self.plot_fieldmap_checkbox.setEnabled(False)

    def on_field_settings_clicked(self):
        if self.field_settings_dialog and self.field_settings_dialog.isVisible():
            self.field_settings_dialog.close()
            return

        if self.field_settings_dialog is None:
            self.field_settings_dialog = QDialog(self)
            self.field_settings_dialog.setWindowTitle("Quadmesh Settings")
            self.field_settings_dialog.setMinimumWidth(300)
            self.field_settings_dialog.setWindowFlags(self.field_settings_dialog.windowFlags() | Qt.WindowType.Tool)

            layout = QVBoxLayout(self.field_settings_dialog)
            layout.addWidget(self.field_settings)

        # Position dialog so its bottom aligns with button
        button_pos = self.field_settings_btn.mapToGlobal(self.field_settings_btn.rect().topRight())
        dialog_height = self.field_settings_dialog.sizeHint().height()
        adjusted_pos = button_pos - QPoint(0, dialog_height)
        self.field_settings_dialog.move(adjusted_pos)

        self.field_settings_dialog.show()
        self.field_settings_dialog.raise_()
        self.field_settings_dialog.activateWindow()

    def on_structure_settings_clicked(self) -> None:
        if self.structure_settings_dialog and self.structure_settings_dialog.isVisible():
            self.structure_settings_dialog.close()
            return

        if self.structure_settings_dialog is None:
            self.structure_settings_dialog = QDialog(self)
            self.structure_settings_dialog.setWindowTitle("Quadmesh Settings")
            self.structure_settings_dialog.setMinimumWidth(300)
            self.structure_settings_dialog.setWindowFlags(
                self.structure_settings_dialog.windowFlags() | Qt.WindowType.Tool)

            layout = QVBoxLayout(self.structure_settings_dialog)
            layout.addWidget(self.structure_settings)

        # Position dialog so its bottom aligns with button
        button_pos = self.structure_btn.mapToGlobal(self.structure_btn.rect().topRight())
        dialog_height = self.structure_settings_dialog.sizeHint().height()
        adjusted_pos = button_pos - QPoint(0, dialog_height)
        self.structure_settings_dialog.move(adjusted_pos)

        self.structure_settings_dialog.show()
        self.structure_settings_dialog.raise_()
        self.structure_settings_dialog.activateWindow()

    def on_quiver_settings_clicked(self):
        if self.quiver_settings_dialog and self.quiver_settings_dialog.isVisible():
            self.quiver_settings_dialog.close()
            return

        if self.quiver_settings_dialog is None:
            self.quiver_settings_dialog = QDialog(self)
            self.quiver_settings_dialog.setWindowTitle("Quadmesh Settings")
            self.quiver_settings_dialog.setMinimumWidth(300)
            self.quiver_settings_dialog.setWindowFlags(self.quiver_settings_dialog.windowFlags() | Qt.WindowType.Tool)

            layout = QVBoxLayout(self.quiver_settings_dialog)
            layout.addWidget(self.quiver_settings)

        # Position dialog so its bottom aligns with button
        button_pos = self.vector_btn.mapToGlobal(self.vector_btn.rect().topRight())
        dialog_height = self.quiver_settings_dialog.sizeHint().height()
        adjusted_pos = button_pos - QPoint(0, dialog_height)
        self.quiver_settings_dialog.move(adjusted_pos)

        self.quiver_settings_dialog.show()
        self.quiver_settings_dialog.raise_()
        self.quiver_settings_dialog.activateWindow()

    def on_plot_settings_clicked(self) -> None:
        if self.plot_settings.isVisible():
            self.plot_settings.close()
            return

        else:
            self.plot_settings.show()
    # endregion

    # region Methods
    def close_all_settings_panels(self):
        for dialog in [
            self.field_settings_dialog,
            self.structure_settings_dialog,
            self.quiver_settings_dialog,
            self.plot_settings_dialog,
        ]:
            if dialog is not None and dialog.isVisible():
                dialog.close()

    def _draw_idle(self) -> None:
        self.ax.set_anchor('C')
        self.fig.tight_layout()
        self.canvas.draw_idle()
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
    # endregion

    def resizeEvent(self, a0):
        self.ax.set_anchor('C')
        self.fig.tight_layout()
        self.canvas.draw_idle()
