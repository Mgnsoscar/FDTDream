from typing import List, Tuple, Union, Optional, Dict, Protocol

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QWidget
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import QuadMesh, PolyCollection
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.quiver import Quiver
from matplotlib.text import Text
from matplotlib.patches import PathPatch
from numpy.typing import NDArray

from .top_level import TopLevel
from .widgets import LabeledSlider, LabeledDropdown
from ..fdtdream.database.db import FieldModel, MonitorModel, SimulationModel


class FieldPlotTabInterface(Protocol):

    # region Top level
    top: TopLevel
    # endregion

    # region Default Values
    PLOT_TYPES = ["XY Plane", "XZ Plane", "YZ Plane", "X Linear", "Y Linear", "Z Linear", "Point"]
    CALLBACK_DELAY: float = 10
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

    def set_new_monitor(self) -> None: ...
    def reinit_field_map_fields(self, keep_selection: bool = False) -> None: ...
    def reinit_components(self, keep_selection: bool = False) -> None: ...
    def reinit_component_idx(self) -> None: ...
    def reinit_plot_types(self, keep_selection: bool = False) -> Tuple[List[str], str]: ...
    def reinit_wavelength_slider(self) -> None: ...
    def reinit_coordinate_sliders(self) -> None: ...
    def reinit_coordinate_idx(self) -> None: ...
    def reinit_quiver_fields(self, keep_selection: bool = False) -> None: ...
    def reload_field_map_data(self) -> None: ...
    def reload_quiver_data(self) -> None: ...
    def normalize_quiver_data(self) -> None: ...
    def apply_magnitude_operation_on_field_map_data(self) -> None: ...
    def apply_scalar_operation_on_field_map_data(self, reload_temp_data: bool = True) -> None: ...
    def reinit_axes(self) -> None: ...
    def get_field_idx(self) -> tuple: ...
    def get_available_fields(self) -> List[FieldModel]: ...
    def select_field(self, field_name: str, quiver_field: bool = False) -> None: ...
    def get_component_combinations(self) -> List[str]: ...
    def is_plottable_vector_fields(self) -> bool: ...
    def remove_structure_artists(self) -> None: ...
    def get_quiver_artist(self) -> Optional[Quiver]: ...
    def get_quadmesh_artist(self) -> Optional[QuadMesh]: ...
    def update_data(self) -> None: ...
    def _draw_idle(self) -> None: ...

    @property
    def monitor(self) -> Optional[MonitorModel]: ...

    @property
    def simulation(self) -> Optional[SimulationModel]: ...

    @property
    def plot_type(self) -> str: ...

    @property
    def field(self) -> str: ...