from PyQt6.QtCore import QObject, pyqtSlot
from matplotlib.axes import Axes
from matplotlib.axis import XAxis, YAxis
from matplotlib.collections import QuadMesh
from matplotlib.colorbar import Colorbar
from matplotlib.quiver import Quiver
from matplotlib.patches import PathPatch
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.text import Text
from numpy.typing import NDArray
import numpy as np
from typing import List, Optional, Dict, Tuple

from ...shared import SETTINGS
from ...signal_busses import CANVAS_SIGNAL_BUS
from ..models import OriginalFieldData, FieldData, FieldSliderConfig
from ....fdtdream.database.db import MonitorModel


class CanvasController(QObject):

    fig: Figure
    ax: Axes
    xaxis: XAxis
    yaxis: YAxis
    xlabel: Text
    ylabel: Text
    title: Text

    original_field_data: Optional[OriginalFieldData]
    """
    The original and unprocessed field data belonging to the currently loaded monitor.
    """

    processed_quadmesh_data: Optional[OriginalFieldData]
    """The field map data-post processing."""

    processed_quiver_data: Optional[OriginalFieldData]
    """The quiver data post-processing."""

    quadmesh: Optional[QuadMesh]
    """The artist responsible for displaying the field map."""

    colorbar: Optional[Colorbar]
    """The colorbar artist displayed next to the quadmesh artist."""

    quiver: Optional[Quiver]
    """The artist responsible for displaying the vector field."""

    structure_projections: Optional[Dict[int, Dict[str, PathPatch]]]
    """
    A nested dictionary with integer keys being the database id of the structures belonging to the simulation of the 
    currently loaded monitor. Each nested dictionary has keys "XY Plane", "XZ Plane", and "YZ Plane", where each key
    contains a PathPatch artist responsible for drawing the projection of the given structure onto the given plane.
    """

    structure_intersections: Optional[Dict[int, Dict[str, List[Optional[PathPatch]]]]]
    """
    A nested dictionary with integer keys being the database id of the structures belonging to the simulation of the 
    currently loaded monitor. Each nested dictionary has keys "XY Plane", "XZ Plane", and "YZ Plane", where each key
    contains a list of PathPatch artists responsible for drawing the intersection of the structure with the plane 
    at the coordinate of the monitor. The indices of each intersection relates to the coordinate at the same index
    in the database MonitorModel's coordinate array.
    """

    # region QSettings Namespaces
    field_plotter_ns = "app/field_plotter/"
    x_slider_val_ns = field_plotter_ns + "x_slider_val/"
    y_slider_val_ns = field_plotter_ns + "y_slider_val/"
    z_slider_val_ns = field_plotter_ns + "z_slider_val/"
    lambda_slider_val_ns = field_plotter_ns + "lambda_slider_val/"
    fieldmap_settings_ns = field_plotter_ns + "fieldmap/"
    quadmesh_settings_ns = field_plotter_ns + "quadmesh/"
    fieldmap_field_ns = fieldmap_settings_ns + "field/"
    fieldmap_component_ns = fieldmap_settings_ns + "component/"
    quadmesh_field_ns = quadmesh_settings_ns + "field/"
    plot_type_ns = field_plotter_ns + "plot_type/"
    quiver_settings_ns = field_plotter_ns + "quiver/"
    quiver_field_ns = quiver_settings_ns + "field/"
    # endregion

    def __init__(self):
        super().__init__()

        # Create the figure and ax.
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)

        # Create references to the x and y axis
        self.xaxis = self.ax.xaxis
        self.yaxis = self.ax.yaxis

        # Fetch references to the title, x and y labels.
        self.title = self.ax.set_title("")
        self.xlabel = self.ax.set_xlabel("")
        self.ylabel = self.ax.set_ylabel("")

        #

        self.initialize_connections()

    def initialize_connections(self) -> None:
        """Connects signals from the CanvasSignalBus."""
        CANVAS_SIGNAL_BUS.connection_requested.connect(self.on_connection_requested)
        CANVAS_SIGNAL_BUS.load_new_field_monitor_requested.connect(self.on_load_new_field_monitor_requested)

    @pyqtSlot(object)
    def on_connection_requested(self, canvas: FigureCanvasQTAgg) -> None:
        """Assigns the figure to the canvas widget and requests it to redraw."""
        canvas.figure = self.fig
        canvas.ax = self.ax
        CANVAS_SIGNAL_BUS.redraw_requested.emit()

    @pyqtSlot(object)
    def on_load_new_field_monitor_requested(self, monitor: MonitorModel) -> None:
        """
        Initializes the loading of a new monitor for the field plot.
        """
        self.clear_current_monitor()
        self.analyze_fields(monitor)

    def clear_current_monitor(self) -> None:
        """
        Clear all data related to the currently loaded monitor, if any.
        Finish by requesting a redraw of the canvas.
        """
        self.original_field_data = None

        self.quadmesh.remove()
        self.quadmesh = None
        self.processed_quadmesh_data = None

        self.colorbar.remove()
        self.colorbar = None

        self.quiver.remove()
        self.quiver = None
        self.processed_quiver_data = None

        self.structure_projections = None
        self.structure_intersections = None

        CANVAS_SIGNAL_BUS.redraw_requested.emit()
        CANVAS_SIGNAL_BUS.disable_all_field_settings_requested.emit()

    def analyze_fields(self, monitor: MonitorModel) -> None:
        """Check what fields are available for plotting for the quadmesh and quiver artists."""

        COMPONENT_COMBINATIONS_MAP = {
            "x": ["x"],
            "y": ["y"],
            "z": ["z"],
            "xy": ["x", "y", "xy"],
            "xz": ["x", "z", "xz"],
            "yz": ["y", "z", "yz"],
            "xyz": ["x", "y", "z", "xy", "xz", "yz", "xyz"],
        }

        # Fetch the fields available for field map plots.
        fields: List[Tuple[str, str, List[str]]] = []
        for field in monitor.fields:
            field_name = field.field_name
            components = field.components
            combonent_combinations = COMPONENT_COMBINATIONS_MAP[components]
            fields.append((field_name, components, combonent_combinations))

        # Fetch available plot types
        shape = monitor.fields[0].data.shape[:5]
        plot_types = self.analyze_shape(shape)

        # Get available quadmesh fields pr. plot type.
        quadmesh_fields = self.get_fields_with_inplane_components(plot_types, fields)

        # Decide the plot type to display and send a request.
        plot_type = SETTINGS.value(self.plot_type_ns, plot_types[0], type=str)
        if plot_type not in plot_types:
            plot_type = plot_types[0]
            SETTINGS.setValue(self.plot_type_ns, plot_type)
        CANVAS_SIGNAL_BUS.populate_plot_types_combobox_requested.emit(plot_types, plot_type)

        # Decide the quiver field to display and send a request
        quiver_fields = self.get_fields_with_inplane_components(plot_types, fields)
        quiver_field = quiver_fields[plot_type][0] if quiver_fields[plot_type] else None
        quiver_field = SETTINGS.value(self.quiver_field_ns, quiver_field)
        if quiver_field not in quiver_fields[plot_type]:
            quiver_field = quiver_fields[plot_type][0] if quiver_fields[plot_type] else None
            SETTINGS.setValue(self.quiver_field_ns, quiver_field)
        # TODO


        # Decide the fieldmap field to display and send a request.
        field_map_field_names = [field[0] for field in fields]
        fieldmap_field = SETTINGS.value(self.fieldmap_field_ns, fields[0][0], type=str)
        if fieldmap_field not in field_map_field_names:
            fieldmap_field = field_map_field_names[0]
            SETTINGS.setValue(self.fieldmap_field_ns, fieldmap_field)
        CANVAS_SIGNAL_BUS.populate_fieldmap_field_combobox_requested.emit(field_map_field_names, fieldmap_field)

        # Decide the field components of the field map to display
        fieldmap_components = [field[2] for field in fields if field[0] == fieldmap_field][0]
        fieldmap_component = SETTINGS.value(self.fieldmap_component_ns, fieldmap_components[0], type=str)
        if fieldmap_component not in fieldmap_components:
            fieldmap_component = fieldmap_components[0]
            SETTINGS.setValue(self.fieldmap_component_ns, fieldmap_component)
        CANVAS_SIGNAL_BUS.populate_quadmesh_components_combobox_requested.emit(fieldmap_components, fieldmap_component)

        # Decide the quadmesh field and send a request.
        quadmesh_field_names = quadmesh_fields[plot_type]
        quadmesh_field = SETTINGS.value(self.quadmesh_field_ns, quadmesh_field_names[0], type=str)
        if quadmesh_field not in quadmesh_field_names:
            quadmesh_field = quadmesh_field_names[0]
            SETTINGS.setValue(self.quadmesh_field_ns, quadmesh_field)
        CANVAS_SIGNAL_BUS.populate_quadmesh_field_combobox_requested.emit(quadmesh_field_names, quadmesh_field)

        # Fetch the configuration of the sliders and emit a request to reset ranges.
        raw_slider_config = self.get_plot_slider_configs(shape, plot_type)
        slider_config = FieldSliderConfig()
        for k, (enabled, range_) in raw_slider_config.items():
            coordinate = SETTINGS.value(getattr(self, f"{k}_slider_val_ns"), 0, type=int)
            if coordinate > range_:
                coordinate = 0
                SETTINGS.setValue(getattr(self, f"{k}_slider_val_ns"), coordinate)
            slider_config[k] = (enabled, range, coordinate)  # type: ignore
        CANVAS_SIGNAL_BUS.set_slider_configurations_requested.emit(slider_config)

    @staticmethod
    def get_fields_with_inplane_components(
            plot_types: List[str],
            fields: List[Tuple[str, str, List[str]]],
    ) -> Dict[str, List[str]]:
        """
        For each 2D plot type, return the list of fields that have both in-plane components.
        Input:
            - plot_types: list of valid plot types from `analyze_shape`
            - fields: list of (field_name, component_string) tuples, e.g. ("E", "xy")
        Output:
            - Dict mapping each 2D plot type to a list of field names with in-plane components
        """
        component_map = {
            "XY Plane": ("x", "y"),
            "YZ Plane": ("y", "z"),
            "XZ Plane": ("x", "z"),
        }

        result = {}

        for plot_type in plot_types:
            if plot_type not in component_map:
                continue

            c1, c2 = component_map[plot_type]
            valid_fields = [
                name for name, comps in fields
                if c1 in comps and c2 in comps
            ]

            result[plot_type] = valid_fields

        return result

    @staticmethod
    def analyze_shape(shape: Tuple[int, ...]) -> List[str]:
        if len(shape) < 4:
            raise ValueError(f"Expected shape: (Nx, Ny, Nz, Nwavelengths), got {shape}.")

        Nx, Ny, Nz = shape[0], shape[1], shape[2]

        # Fast pre-allocated result list (at most 4 matches)
        plot_types = []

        if Nx > 1 and Ny > 1:
            plot_types.append("XY Plane")
        if Ny > 1 and Nz > 1:
            plot_types.append("YZ Plane")
        if Nx > 1 and Nz > 1:
            plot_types.append("XZ Plane")
        if Nx > 1 and Ny == 1 and Nz == 1:
            plot_types.append("X Linear")
        if Ny > 1 and Nx == 1 and Nz == 1:
            plot_types.append("Y Linear")
        if Nz > 1 and Nx == 1 and Ny == 1:
            plot_types.append("Z Linear")
        if Nx == 1 and Ny == 1 and Nz == 1:
            plot_types.append("Point")

        return plot_types

    @staticmethod
    def get_component_to_idx_map(components: str) -> Dict[str, int]:
        component_map = {}
        for idx in range(len(components)):
            component_map[components[idx]] = idx
        return component_map

    @staticmethod
    def get_plot_slider_configs(shape: Tuple[int, int, int, int], plot_type: str) -> Dict[str, Tuple[bool, int]]:
        """
        Returns which slider are variable and which are fixed, along with the slider ranges.

        Returns:
            A dictionary like:
            {
                "x": (True, 100),     # axis is used in plot, size = 100
                "y": (False, 1),      # axis is fixed (slider), size = 1
                "z": (False, 50)      # axis is fixed (slider), size = 50
                "wavelength": (True, 1000)
            }
        """
        Nx, Ny, Nz, Nlambda = shape[0] - 1, shape[1] - 1, shape[2] - 1, shape[3] - 1

        # Default all as fixed, except for the wavelengths.
        axes = {
            "x": (False, Nx),
            "y": (False, Ny),
            "z": (False, Nz),
            "wavelength": (True, Nlambda)
        }

        if plot_type == "XY Plane":
            axes["x"] = (True, Nx)
            axes["y"] = (True, Ny)
        elif plot_type == "YZ Plane":
            axes["y"] = (True, Ny)
            axes["z"] = (True, Nz)
        elif plot_type == "XZ Plane":
            axes["x"] = (True, Nx)
            axes["z"] = (True, Nz)
        elif plot_type == "X Linear":
            axes["x"] = (True, Nx)
        elif plot_type == "Y Linear":
            axes["y"] = (True, Ny)
        elif plot_type == "Z Linear":
            axes["z"] = (True, Nz)
        elif plot_type == "Point":
            pass
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")

        return axes

