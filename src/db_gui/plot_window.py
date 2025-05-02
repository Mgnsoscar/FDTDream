from __future__ import annotations

import sys
from typing import List, Literal, Tuple, Union, cast, get_args

import matplotlib.pyplot as plt
import numpy as np
from PyQt6.QtCore import QTimer, Qt, QPoint, QEvent
from PyQt6.QtWidgets import (
    QApplication, QSizePolicy, QWidget, QListWidget, QCheckBox, QLabel, QVBoxLayout,
    QColorDialog, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, QFrame, QHBoxLayout
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import QuadMesh
from matplotlib.colorbar import Colorbar

from .widgets import LabeledSlider, LabeledDropdown
from ..fdtdream.results import FieldAndPower
from ..fdtdream.results.field_and_power_monitor import Field, Coordinates
from ..fdtdream.results.plotted_structure import PlottedStructure

PLANE_NORMALS = Literal["x-normal", "y-normal", "z-normal"]
RESULTS = Literal["power", "T", "E", "H", "P"]
LINESTYLES = Literal["solid", "dotted", "dashed", "dashdot"]
COMPONENTS = Literal["x", "y", "z", "xy", "xz", "yz", "xyz"]
PLANES = Literal["xy", "xz", "yz"]
FIELDS = Literal["E", "H", "P"]
AXES = Literal["x", "y", "z"]


class FieldPlot(QWidget):

    # region Class Body

    # Some stuff
    callback_delay: float = 10  # Has to be 10 ms uninterupted after a change before the callbacks are triggered.
    temp_data: Union[np.ndarray, None]
    main_level: PlotWindow

    # Artists
    quadmesh: Union[QuadMesh, None]
    cbar: Union[Colorbar, None]

    # Data objects
    current_monitor: Union[FieldAndPower, None]
    structures: List[PlottedStructure]

    # Canvas objects
    ax: plt.Axes
    fig: plt.Figure

    # Widgets
    wavelength_slider: LabeledSlider
    normal_idx_slider: LabeledSlider
    plane_dropdown: LabeledDropdown
    field_dropdown: LabeledDropdown
    component_dropdown: LabeledDropdown
    scale_dropdown: LabeledDropdown
    structure_options: StructureOptions

    # PyQT6 objects
    slider_timer: QTimer
    cb_scale_timer: QTimer

    # endregion

    def __init__(self, parent: PlotWindow, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # region Init some variables:
        self.current_monitor = None
        self.quadmesh = None
        self.cbar = None
        self.temp_data = None
        self.main_level = parent
        # endregion

        # region Canvas setup
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # endregion

        # region Sliders, Dropdowns and other widgets
        self.wavelength_slider = LabeledSlider(self, "Wavelength", 0, 0, self.on_wavelength_change)
        self.wavelength_slider.enabled = False

        self.normal_idx_slider = LabeledSlider(self, "Fixed axis", 0, 0, self.on_fixed_idx_change)
        self.normal_idx_slider.enabled = False

        self.plane_dropdown = LabeledDropdown(self, "Plane", self.on_plane_change)
        self.plane_dropdown.enabled = False

        self.field_dropdown = LabeledDropdown(self, "Field", self.on_field_change)
        self.field_dropdown.enabled = False

        self.component_dropdown = LabeledDropdown(self, "Field Components", self.on_component_change)
        self.component_dropdown.enabled = False

        self.scale_dropdown = LabeledDropdown(self, "Colorbar Scaling", self.on_cbar_scale_change)
        self.scale_dropdown.blockSignals(True)  # Avoid triggering the callback
        self.scale_dropdown.set_dropdown_items(
            ["Current position", "Current plot", "All values"]
        )
        self.scale_dropdown.blockSignals(False)
        self.component_dropdown.enabled = False
        # endregion

        # region Layouts
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.wavelength_slider)
        layout.addWidget(self.normal_idx_slider)
        layout.addWidget(self.plane_dropdown)
        layout.addWidget(self.field_dropdown)
        layout.addWidget(self.component_dropdown)
        layout.addWidget(self.scale_dropdown)
        self.setLayout(layout)
        # endregion

        # region Timers
        self.slider_timer = QTimer(self)
        self.slider_timer.setSingleShot(True)  # Run once
        self.slider_timer.timeout.connect(self.update_data)  # type: ignore

        self.cb_scale_timer = QTimer(self)
        self.cb_scale_timer.setSingleShot(True)  # Run once
        self.cb_scale_timer.timeout.connect(self.on_cbar_scale_change)  # type: ignore
        # endregion

    # region Properties
    @property
    def current_data(self) -> Field:
        if hasattr(self.current_monitor, self.current_field):
            return getattr(self.current_monitor, self.current_field)
        else:
            raise ValueError(f"Current monitor has not recorded the {self.current_field}-field.")

    @property
    def normal_axis(self) -> AXES:
        plane = self.current_plane
        for axis in get_args(AXES):
            if axis not in plane:
                return axis

    @property
    def current_field(self) -> FIELDS:
        return self.field_dropdown.get_selected()  # type: ignore

    @property
    def current_plane(self) -> PLANES:
        return self.plane_dropdown.get_selected()  # type: ignore

    @property
    def normal_idx(self) -> int:
        return self.normal_idx_slider.get_value()

    @property
    def normal_coordinate(self) -> float:
        return getattr(self.current_monitor, self.normal_axis)[self.normal_idx]

    @property
    def current_components(self) -> COMPONENTS:
        return self.component_dropdown.get_selected()  # type: ignore

    @property
    def wavelength_idx(self) -> int:
        return self.wavelength_slider.get_value()

    @property
    def wavelength(self) -> float:
        if self.current_monitor is None:
            raise RuntimeError("Cannot access wavelength: current_monitor is not set.")
        return self.current_monitor.idx_to_wavelength(self.wavelength_idx)

    # endregion

    # region Callbacks
    def on_cbar_scale_change(self) -> None:
        if self.current_monitor:
            mapping = {
                "Current position": self.scale_cbar_to_current_position,
                "Current plot": self.scale_cbar_to_current_plot,
                "All values": self.scale_cbar_to_entire_dataset
            }
            mapping[self.scale_dropdown.get_selected()]()
            self.redraw()

    def on_wavelength_change(self) -> None:

        self.wavelength_slider.set_label(f"{self.wavelength:.2f} nm")

        # Update colorbar if it's scaled to the current plot.
        if self.scale_dropdown.get_selected() == "Current plot":
            self.cb_scale_timer.start(self.callback_delay)
        self.slider_timer.start(self.callback_delay)

    def on_fixed_idx_change(self) -> None:

        if self.scale_dropdown.get_selected() == "Current position":
            self.cb_scale_timer.start(self.callback_delay)

        self.slider_timer.start(self.callback_delay)

    def on_field_change(self) -> None:

        # Update plottable field components.
        if self.current_monitor:
            components = self.current_monitor.get_field_components(self.current_field)
            self.component_dropdown.blockSignals(True)
            self.component_dropdown.set_dropdown_items(components, keep_selection=True)
            self.component_dropdown.blockSignals(False)
            if not components:
                self.component_dropdown.enabled = False
                self.temp_data = None
            else:
                self.component_dropdown.enabled = True
                self.temp_data = self.get_data(())
                self.cb_scale_timer.start(self.callback_delay)
                self.update_data()
        else:
            self.component_dropdown.enabled = False

    def on_plane_change(self) -> None:
        if self.current_monitor:
            self.replace_quad_mesh()
            self.cb_scale_timer.start(self.callback_delay)
            self.update_data()

            for structure in self.main_level.structures:
                if structure.projection_outline or structure.intersection_outline or structure.fill_projection:
                    mapping = {
                        "x": (self.normal_coordinate, 0, 0),
                        "y": (0, self.normal_coordinate, 0),
                        "z": (0, 0, self.normal_coordinate)
                    }
                    structure.ax = self.ax
                    structure.recreate(self.current_plane, mapping[self.normal_axis])
            self.redraw()

    def on_component_change(self) -> None:
        if self.current_monitor:
            self.cb_scale_timer.start(self.callback_delay)
            self.temp_data = self.get_data(())
            self.update_data()

    # endregion

    # region Method overrides
    def parent(self) -> PlotWindow:
        return cast(super().parent(), PlotWindow)
    # endregion

    # region Methods

    def reset_widgets(self) -> None:

        self.fig.clear()

        self.temp_data = None

        self.field_dropdown.blockSignals(True)
        self.field_dropdown.set_dropdown_items([])
        self.field_dropdown.enabled = False
        self.field_dropdown.blockSignals(False)

        self.plane_dropdown.blockSignals(True)
        self.plane_dropdown.set_dropdown_items([])
        self.plane_dropdown.enabled = False
        self.plane_dropdown.blockSignals(False)

        self.component_dropdown.blockSignals(True)
        self.component_dropdown.set_dropdown_items([])
        self.component_dropdown.enabled = False
        self.component_dropdown.blockSignals(False)

        self.wavelength_slider.blockSignals(True)
        self.wavelength_slider.set_range(0, 0)
        self.wavelength_slider.enabled = False
        self.wavelength_slider.blockSignals(False)

        self.normal_idx_slider.blockSignals(True)
        self.normal_idx_slider.set_range(0, 0)
        self.normal_idx_slider.enabled = False
        self.normal_idx_slider.blockSignals(False)

        self.scale_dropdown.enabled = False

    def set_new_monitor(self, new_monitor: FieldAndPower) -> None:

        # Reset if there is no monitor.
        if new_monitor is None:
            self.current_monitor = None
            self.reset_widgets()
            self.temp_data = None
            return

        # Flag whether to enable or disable sliders and dropdowns.
        all_enabled = True

        # Update plottable planes.
        prev_plane = self.plane_dropdown.get_selected()
        planes = new_monitor.get_planes()
        self.plane_dropdown.blockSignals(True)
        self.plane_dropdown.set_dropdown_items(planes, keep_selection=True)
        if not planes:
            all_enabled = False
        if prev_plane != self.plane_dropdown.get_selected() and self.current_monitor is not None:
            for structure in self.main_level.structures:
                if structure.projection_outline or structure.intersection_outline or structure.fill_projection:
                    mapping = {
                        "x": (self.normal_coordinate, 0, 0),
                        "y": (0, self.normal_coordinate, 0),
                        "z": (0, 0, self.normal_coordinate)
                    }
                    structure.ax = self.ax
                    structure.recreate(self.current_plane, mapping[self.normal_axis])
            self.redraw()
        self.plane_dropdown.blockSignals(False)

        # Update plottable fields.
        fields = new_monitor.get_fields()
        self.field_dropdown.blockSignals(True)
        self.field_dropdown.set_dropdown_items(fields, keep_selection=True)
        if not fields:
            all_enabled = False
        self.field_dropdown.blockSignals(False)

        # Update plottable field components.
        components = new_monitor.get_field_components(self.current_field)
        self.component_dropdown.blockSignals(True)
        self.component_dropdown.set_dropdown_items(components, keep_selection=True)
        if not components:
            all_enabled = False
        self.component_dropdown.blockSignals(False)

        if all_enabled:
            self.plane_dropdown.enabled = True
            self.field_dropdown.enabled = True
            self.component_dropdown.enabled = True

        # Fetch the previous wavelength and normal axis coordinate if there was one.
        if self.current_monitor:
            prev_wavelength = self.wavelength
            prev_normal_coord = self.normal_coordinate
        else:
            prev_wavelength = 0
            prev_normal_coord = -float('inf')

        # Set the new monitor
        self.current_monitor = new_monitor

        # Update plottable wavelengths. Keep new wavelength as close to previous as possible.
        wavelength_shape = new_monitor.wavelengths.shape[0]
        self.wavelength_slider.blockSignals(True)
        self.wavelength_slider.set_range(0, wavelength_shape - 1)
        if wavelength_shape == 1:
            self.wavelength_slider.enabled = False
        else:
            closest_idx = new_monitor.wavelength_to_idx(prev_wavelength)
            self.wavelength_slider.set_index(closest_idx)
            self.wavelength_slider.enabled = True
        self.wavelength_slider.blockSignals(False)

        # Update the slider label.
        self.wavelength_slider.set_label(f"{self.wavelength:.2f} nm")

        # Update plottable normal axis coordinates.
        normal_axis: Coordinates = getattr(new_monitor, self.normal_axis)
        normal_axis_shape = normal_axis.shape[0]
        self.normal_idx_slider.blockSignals(True)
        self.normal_idx_slider.set_range(0, normal_axis_shape - 1)
        if normal_axis_shape == 1:
            self.normal_idx_slider.enabled = False
        else:
            closest_idx = np.argmin(np.abs(normal_axis - prev_normal_coord))
            self.normal_idx_slider.set_index(closest_idx)
            self.normal_idx_slider.enabled = True
        self.normal_idx_slider.blockSignals(False)

        # Update the slider label.
        self.normal_idx_slider.set_label(f"{self.normal_axis}: {self.normal_coordinate:.2f} nm")

        # Replace the quadmesh with a new empty one.
        self.replace_quad_mesh()

        # Fill the temp array of data for quicker access.
        self.temp_data = self.get_data(())

        # Update the plot data using the slider timer.
        self.slider_timer.start(self.callback_delay)

        # Finallypdate cbar limits
        self.on_cbar_scale_change()

    def replace_quad_mesh(self) -> None:
        # Remove old quadmesh if it exists
        if hasattr(self, "quadmesh") and self.quadmesh:
            if self.quadmesh.colorbar is not None:
                self.quadmesh.colorbar.remove()
            self.quadmesh.remove()

        # Assign new quadmesh and colorbar
        if self.current_monitor:
            self.quadmesh, self.cbar = self.current_monitor.get_empty_quadmesh(self.ax, self.current_plane)
            data = self.quadmesh.get_coordinates()
            self.ax.set_xlim(data[0, 0, 0], data[-1, 0, 0])  # type: ignore
            self.ax.set_ylim(data[0, 0, 1], data[0, -1, 1])  # type: ignore

    def get_data(self, idx) -> Union[np.ndarray, None]:

        # Abort if no monitor is selected.
        if self.current_monitor is None:
            return None

        # Fetch the components. Do the magnitude if more than one component.
        if len(self.current_components) > 1:
            data = self.current_data.__getattribute__(self.current_components + "_magnitude")[idx]
        else:
            data = self.current_data.__getattribute__(self.current_components)[idx].real

        return data

    def update_data(self,) -> None:

        # Fetch the correct coordinate and wavelength index
        idx = self.get_position_and_wavelength_index()
        data = self.temp_data[idx]

        # Update the quadmesh array.
        self.quadmesh.set_array(data)

        # Redraw plot
        self.redraw()

    def scale_cbar_to_current_plot(self) -> None:
        """Sets min and max of the colorbar based on the min and max values in the current plot image."""
        current_data = self.quadmesh.get_array()
        self.quadmesh.set_clim(current_data.min(), current_data.max())

    def set_cbar_limits(self, vmin: float, vmax: float) -> None:
        """Manually sets the limits of the colorbar."""
        self.quadmesh.set_clim(vmin, vmax)

    def scale_cbar_to_current_position(self) -> None:
        """Sets min and max of the colorbar for the given position and plane. Min and max is based on all plots for all
        wavelengths for that position."""
        idx = {
            "xy": (slice(None, None), slice(None, None), self.normal_idx),
            "xz": (slice(None, None), self.normal_idx, slice(None, None)),
            "yz": (self.normal_idx, slice(None, None), slice(None, None))
        }

        data = self.get_data(idx[self.current_plane])
        vmin = data.min()
        vmax = data.max()
        self.quadmesh.set_clim(vmin, vmax)

    def scale_cbar_to_entire_dataset(self) -> None:
        """Sets the colorbar min and max based on all recorded values of the dataset."""
        idx = {
            "xy": (slice(None, None), slice(None, None), slice(None, None)),
            "xz": (slice(None, None), slice(None, None), slice(None, None)),
            "yz": (slice(None, None), slice(None, None), slice(None, None))
        }

        data = self.get_data(idx[self.current_plane])
        vmin = data.min()
        vmax = data.max()
        self.quadmesh.set_clim(vmin, vmax)

    def get_position_index(self) -> Tuple[Union[slice, int], ...]:
        idx = {
            "xy": (slice(None, None), slice(None, None), self.normal_idx),
            "xz": (slice(None, None), self.normal_idx, slice(None, None)),
            "yz": (self.normal_idx, slice(None, None), slice(None, None))
        }
        return idx[self.current_plane]

    def get_position_and_wavelength_index(self) -> Tuple[Union[slice, int], ...]:
        """Return the indices that retrieves given indexes along the axis normal to the plotted plane."""
        idx = {
            "xy": (slice(None, None), slice(None, None), self.normal_idx, self.wavelength_idx),
            "xz": (slice(None, None), self.normal_idx, slice(None, None), self.wavelength_idx),
            "yz": (self.normal_idx, slice(None, None), slice(None, None), self.wavelength_idx)
        }
        return idx[self.current_plane]

    def redraw(self):
        """Updates the plot."""
        self.fig.canvas.draw_idle()
    # endregion


class PlotWindow(QWidget):
    plotter: FieldPlot
    monitors: List[FieldAndPower]
    structures: List[PlottedStructure]
    current_monitor_idx: int
    structure_options: StructureOptions

    def __init__(self, monitors: List[FieldAndPower], structures: List[PlottedStructure]):
        super().__init__()

        self.structures = structures
        self.monitors = monitors
        self.current_monitor_idx = 0

        self.setWindowTitle("Wavelength Slider")
        self.resize(800, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.plotter = FieldPlot(self)
        self.plotter.set_new_monitor(self.monitors[self.current_monitor_idx])
        self.structure_options = StructureOptions(self, self)
        self.structure_options.add_structures()

        layout.addWidget(self.plotter)
        layout.addWidget(self.structure_options)

        # Add cycle button
        self.cycle_button = QPushButton("Next Monitor")
        self.cycle_button.clicked.connect(self.cycle_monitor)  # type: ignore
        layout.addWidget(self.cycle_button)

    def cycle_monitor(self):
        self.current_monitor_idx = (self.current_monitor_idx + 1) % len(self.monitors)
        next_monitor = self.monitors[self.current_monitor_idx]
        self.plotter.set_new_monitor(next_monitor)

    @classmethod
    def launch(cls, monitors: List[FieldAndPower], structures: List[PlottedStructure]) -> QApplication:

        app = QApplication(sys.argv)
        window = cls(monitors, structures)
        window.show()
        app.exec()
        return app


class StructureOptions(QWidget):
    def __init__(self, parent, main_level: PlotWindow):
        super().__init__(parent)
        self.main_level = main_level
        self.current_structure = None

        self.structure_list = QListWidget()
        self.structure_list.currentItemChanged.connect(self.on_structure_selected)

        # --- Checkboxes and config buttons ---
        self.checkbox_proj_outline = QCheckBox("Projection Outline")
        self.checkbox_proj_outline.toggled.connect(self.on_proj_outline_toggled)
        self.button_proj_outline = QPushButton("⚙")
        self.button_proj_outline.setFixedWidth(25)
        self.button_proj_outline.clicked.connect(self.toggle_proj_outline_config)

        self.checkbox_proj_fill = QCheckBox("Projection Fill")
        self.checkbox_proj_fill.toggled.connect(self.on_proj_fill_toggled)
        self.button_proj_fill = QPushButton("⚙")
        self.button_proj_fill.setFixedWidth(25)
        self.button_proj_fill.clicked.connect(self.toggle_proj_fill_config)

        self.checkbox_intersect = QCheckBox("Intersection Outline")
        self.checkbox_intersect.toggled.connect(self.on_intersect_toggled)
        self.button_intersect = QPushButton("⚙")
        self.button_intersect.setFixedWidth(25)
        self.button_intersect.clicked.connect(self.toggle_intersect_config)

        # --- Settings Panels ---
        self.proj_outline_config = self.create_outline_config_panel()
        self.proj_fill_config = self.create_fill_config_panel()
        self.intersect_config = self.create_intersect_config_panel()

        # --- Layouts ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Structures"))
        left_layout.addWidget(self.structure_list)

        right_layout = QVBoxLayout()
        right_layout.addLayout(self._option_row(self.checkbox_proj_outline, self.button_proj_outline))
        right_layout.addLayout(self._option_row(self.checkbox_proj_fill, self.button_proj_fill))
        right_layout.addLayout(self._option_row(self.checkbox_intersect, self.button_intersect))

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)

    def _option_row(self, checkbox, button):
        layout = QHBoxLayout()
        layout.addWidget(checkbox)
        layout.addStretch()
        layout.addWidget(button)
        return layout

    def parent(self) -> FieldPlot:
        return cast(super().parent(), FieldPlot)

    def add_structures(self):
        self.structure_list.clear()
        for struct in self.main_level.structures:
            self.structure_list.addItem(struct._name)

    def on_structure_selected(self):
        item = self.structure_list.currentItem()
        if item:
            name = item.text()
            self.current_structure = next((s for s in self.main_level.structures if s._name == name), None)
            if self.current_structure:
                if self.current_structure.ax is None:
                    self.current_structure.ax = self.main_level.plotter.ax
                self.load_settings()

    def load_settings(self):
        s = self.current_structure
        self.checkbox_proj_outline.setChecked(s.projection_outline)
        self.checkbox_proj_fill.setChecked(s.fill_projection)
        self.checkbox_intersect.setChecked(s.intersection_outline)

        # Load config panel values
        self.outline_alpha.setValue(s.outline_alpha)
        self.outline_width.setValue(s.outline_width)
        self.outline_style.setCurrentText(s.outline_linestyle)
        self.outline_color.setStyleSheet(f"background-color: {s.outline_color}")

        self.fill_alpha.setValue(s.fill_alpha)
        self.fill_color.setStyleSheet(f"background-color: {s.fill_color}")

        self.intersect_alpha.setValue(s.intersection_alpha)
        self.intersect_width.setValue(s.intersection_width)
        self.intersect_style.setCurrentText(s.intersection_linestyle)
        self.intersect_color.setStyleSheet(f"background-color: {s.intersection_color}")

    def toggle_proj_outline_config(self):
        self.show_panel(self.button_proj_outline, self.proj_outline_config)

    def toggle_proj_fill_config(self):
        self.show_panel(self.button_proj_fill, self.proj_fill_config)

    def toggle_intersect_config(self):
        self.show_panel(self.button_intersect, self.intersect_config)

    def show_panel(self, button, panel):
        panel.move(button.mapToGlobal(QPoint(0, button.height())))
        panel.setVisible(not panel.isVisible())

    def on_proj_outline_toggled(self, state):
        if self.current_structure and self.main_level.plotter.current_monitor:
            mapping = {
                "x": (self.main_level.plotter.normal_coordinate, 0, 0),
                "y": (0, self.main_level.plotter.normal_coordinate, 0),
                "z": (0, 0, self.main_level.plotter.normal_coordinate)
            }

            self.current_structure.projection_outline = state
            self.current_structure.recreate(self.main_level.plotter.current_plane,
                                            mapping[self.main_level.plotter.normal_axis])
            self.main_level.plotter.redraw()

    def on_proj_fill_toggled(self, state):
        if self.current_structure:
            mapping = {
                "x": (self.main_level.plotter.normal_coordinate, 0, 0),
                "y": (0, self.main_level.plotter.normal_coordinate, 0),
                "z": (0, 0, self.main_level.plotter.normal_coordinate)
            }
            self.current_structure.fill_projection = state
            self.current_structure.recreate(self.main_level.plotter.current_plane,
                                            mapping[self.main_level.plotter.normal_axis])
            self.main_level.plotter.redraw()

    def on_intersect_toggled(self, state):
        if self.current_structure:
            mapping = {
                "x": (self.main_level.plotter.normal_coordinate, 0, 0),
                "y": (0, self.main_level.plotter.normal_coordinate, 0),
                "z": (0, 0, self.main_level.plotter.normal_coordinate)
            }
            self.current_structure.intersection_outline = state
            self.current_structure.recreate(self.main_level.plotter.current_plane,
                                            mapping[self.main_level.plotter.normal_axis])
            self.main_level.plotter.redraw()

    def create_outline_config_panel(self):
        panel = QFrame(self, flags=Qt.WindowType.Popup)
        panel.setMinimumWidth(250)
        layout = QVBoxLayout(panel)

        self.outline_width = QSpinBox()
        self.outline_width.setRange(1, 10)
        self.outline_width.valueChanged.connect(lambda v: setattr(self.current_structure, "outline_width", v))
        self.outline_width.valueChanged.connect(self.main_level.plotter.redraw)

        self.outline_style = QComboBox()
        self.outline_style.addItems(["-", "--", "-.", ":"])
        self.outline_style.currentTextChanged.connect(lambda t: setattr(self.current_structure, "outline_linestyle", t))
        self.outline_style.currentTextChanged.connect(self.main_level.plotter.redraw)

        self.outline_color = QPushButton("Color")
        self.outline_color.clicked.connect(self.set_outline_color)
        self.outline_color.clicked.connect(self.main_level.plotter.redraw)

        self.outline_alpha = QDoubleSpinBox()
        self.outline_alpha.setRange(0, 1)
        self.outline_alpha.setSingleStep(0.1)
        self.outline_alpha.valueChanged.connect(lambda a: setattr(self.current_structure, "outline_alpha", a))
        self.outline_alpha.valueChanged.connect(self.main_level.plotter.redraw)

        layout.addWidget(QLabel("Line Width"))
        layout.addWidget(self.outline_width)
        layout.addWidget(QLabel("Line Style"))
        layout.addWidget(self.outline_style)
        layout.addWidget(self.outline_color)
        layout.addWidget(QLabel("Alpha"))
        layout.addWidget(self.outline_alpha)
        return panel

    def create_fill_config_panel(self):
        panel = QFrame(self, flags=Qt.WindowType.Popup)
        panel.setMinimumWidth(250)
        layout = QVBoxLayout(panel)

        self.fill_color = QPushButton("Color")
        self.fill_color.clicked.connect(self.set_fill_color)
        self.fill_alpha = QDoubleSpinBox()
        self.fill_alpha.setRange(0, 1)
        self.fill_alpha.setSingleStep(0.1)
        self.fill_alpha.valueChanged.connect(lambda a: setattr(self.current_structure, "fill_alpha", a))

        layout.addWidget(self.fill_color)
        layout.addWidget(QLabel("Alpha"))
        layout.addWidget(self.fill_alpha)
        return panel

    def create_intersect_config_panel(self):
        panel = QFrame(self, flags=Qt.WindowType.Popup)
        panel.setMinimumWidth(250)
        layout = QVBoxLayout(panel)

        self.intersect_width = QSpinBox()
        self.intersect_width.setRange(1, 10)
        self.intersect_width.valueChanged.connect(lambda v: setattr(self.current_structure,
                                                                    "intersection_width", v))

        self.intersect_style = QComboBox()
        self.intersect_style.addItems(["-", "--", "-.", ":"])
        self.intersect_style.currentTextChanged.connect(lambda t: setattr(self.current_structure,
                                                                          "intersection_linestyle", t))

        self.intersect_color = QPushButton("Color")
        self.intersect_color.clicked.connect(self.set_intersect_color)

        self.intersect_alpha = QDoubleSpinBox()
        self.intersect_alpha.setRange(0, 1)
        self.intersect_alpha.setSingleStep(0.1)
        self.intersect_alpha.valueChanged.connect(lambda a: setattr(self.current_structure,
                                                                    "intersection_alpha", a))

        layout.addWidget(QLabel("Line Width"))
        layout.addWidget(self.intersect_width)
        layout.addWidget(QLabel("Line Style"))
        layout.addWidget(self.intersect_style)
        layout.addWidget(self.intersect_color)
        layout.addWidget(QLabel("Alpha"))
        layout.addWidget(self.intersect_alpha)
        return panel

    def set_outline_color(self):
        if self.current_structure:
            color = QColorDialog.getColor()
            if color.isValid():
                self.current_structure.outline_color = color.name()
                self.outline_color.setStyleSheet(f"background-color: {color.name()}")
                self.main_level.plotter.redraw()

    def set_fill_color(self):
        if self.current_structure:
            color = QColorDialog.getColor()
            if color.isValid():
                self.current_structure.fill_color = color.name()
                self.fill_color.setStyleSheet(f"background-color: {color.name()}")
                self.main_level.plotter.redraw()

    def set_intersect_color(self):
        if self.current_structure:
            color = QColorDialog.getColor()
            if color.isValid():
                self.current_structure.intersection_color = color.name()
                self.intersect_color.setStyleSheet(f"background-color: {color.name()}")
                self.main_level.plotter.redraw()