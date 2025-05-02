from typing import Optional, Callable, cast

import numpy as np

import matplotlib.pyplot as plt
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QDoubleSpinBox, QWidget, QVBoxLayout, QHBoxLayout
from matplotlib.collections import QuadMesh

from .widgets import LabeledDropdown
from .fieldplot_tab_interface import FieldPlotTabInterface


class FieldSettings(QWidget):
    """
    A widget for selecting field visualization settings like component, scalar operation, color map, and color scale.
    """

    # region Default Values
    COLORMAPS = ["viridis"] + sorted(c for c in plt.colormaps() if not (c.endswith("_r") or c == "viridis"))
    """List of available color maps, with 'viridis' placed first."""

    SCALAR_OPERATIONS = ["Re", "-Re", "Im", "-Im", "|Abs|", "|Abs|^2"]
    """List of available scalar operations for field visualization."""

    COLOR_SCALE_MODES = ["Current wavelength", "Current plane", "All planes", "Custom limits"]
    """List of color scale modes controlling the value range of the color map."""

    LIMIT_SCALE_MODES = []
    # endregion

    # region Variable declarations
    _layout: QVBoxLayout
    _parent: FieldPlotTabInterface
    _cscale_limits_layout: QHBoxLayout
    component_combo: LabeledDropdown
    scalar_op_combo: LabeledDropdown
    cmap_combo: LabeledDropdown
    color_scale_combo: LabeledDropdown
    cscale_min: QDoubleSpinBox
    cscale_max: QDoubleSpinBox
    # endregion

    def __init__(self, parent: FieldPlotTabInterface) -> None:
        """
        Initialize the FieldSettings widget.

        Args:
            parent (QWidget): The parent widget.
        """
        super().__init__(parent)  # type: ignore

        # Set reference to FieldPlotTab
        self._parent = parent

        # Create the main layout
        self._layout = QVBoxLayout(self)

        # Combo boxes
        self._create_combos()

        # Custom limits input
        self._create_custom_limits_boxes()

    # region Widget initialization
    def _create_combos(self) -> None:
        """Create and initialize the labeled combo boxes for the field settings."""

        # Components
        self.component_combo = LabeledDropdown(self, "Components:", self.on_component_change)
        self._layout.addWidget(self.component_combo)

        # Scalar operation
        self.scalar_op_combo = LabeledDropdown(self, "Scalar operation:", self.on_scalar_op_change)
        self.scalar_op_combo.set_dropdown_items(self.SCALAR_OPERATIONS)
        self._layout.addWidget(self.scalar_op_combo)

        # Color map (make sure viridis is the first one).
        self.cmap_combo = LabeledDropdown(self, "Color map:", self.on_cmap_change)
        self.cmap_combo.set_dropdown_items(self.COLORMAPS)
        self._layout.addWidget(self.cmap_combo)

        # Color scale
        self.color_scale_combo = LabeledDropdown(self, "Color scale:", self.on_cscale_change)
        self.color_scale_combo.set_dropdown_items(self.COLOR_SCALE_MODES)
        self._layout.addWidget(self.color_scale_combo)

        # Linear scale
        self.linear_scale_combo = LabeledDropdown(self, "Limit scale:", self.on_limit_scale_change)
        self.linear_scale_combo.set_dropdown_items(self.LIMIT_SCALE_MODES)
        self.linear_scale_combo.setVisible(False)
        self._layout.addWidget(self.linear_scale_combo)

    def _create_custom_limits_boxes(self) -> None:
        """Create and initialize the spin boxes for setting custom color scale limits."""

        # Create the layout.
        self._cscale_limits_layout = QHBoxLayout()

        # Create the min value spinbox.
        self.cscale_min = QDoubleSpinBox(self)
        self.cscale_min.setRange(-1e9, 1e9)
        self.cscale_min.setDecimals(2)
        self.cscale_min.setValue(-10)
        self.cscale_min.setPrefix("Min: ")
        self.cscale_min.setVisible(False)
        self.cscale_min.valueChanged.connect(self.on_cscale_change)  # type: ignore

        # Create the max value spinbox.
        self.cscale_max = QDoubleSpinBox(self)
        self.cscale_max.setRange(-1e9, 1e9)
        self.cscale_max.setDecimals(2)
        self.cscale_max.setValue(10)
        self.cscale_max.setPrefix("Max: ")
        self.cscale_max.setVisible(False)
        self.cscale_max.valueChanged.connect(self.on_cscale_change)  # type: ignore

        # Add layouts
        self._cscale_limits_layout.addWidget(self.cscale_min)
        self._cscale_limits_layout.addWidget(self.cscale_max)
        self._layout.addLayout(self._cscale_limits_layout)
    # endregion

    # region Callbacks
    def on_component_change(self) -> None:
        self._parent.reinit_component_idx()
        self._parent.apply_scalar_operation_on_field_map_data(reload_temp_data=True)
        self.scale_color_limits()
        self._update_data()

    def on_scalar_op_change(self) -> None:
        self._parent.apply_scalar_operation_on_field_map_data(reload_temp_data=True)
        self.scale_color_limits()
        self._update_data()

    def on_cmap_change(self, val: str) -> None:
        self._parent.quadmesh.set_cmap(val)
        self._draw_idle()

    def on_cscale_change(self) -> None:
        self.update_custom_cscale_visibility()
        self.scale_color_limits()

    def on_limit_scale_change(self, val: str) -> None:
        ...
    # endregion

    # region Methods
    def update_custom_cscale_visibility(self) -> None:
        # Toggle the custom limits widgets.
        is_custom = self.cscale == "Custom limits"
        self.cscale_min.setVisible(is_custom)
        self.cscale_max.setVisible(is_custom)

    def scale_color_limits(self, idx: tuple = None) -> None:

        scale = self.cscale
        if not idx:
            idx = self._parent.get_field_idx()

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
            self._parent.quadmesh.set_clim(self.cscale_custom_min, self.cscale_custom_max)
            self._draw_idle()
            return

        if "Plane" in self._parent.plot_type:
            self._parent.quadmesh.set_clim(np.min(self._parent.field_data[idx]), np.max(self._parent.field_data[idx]))
        else:
            self._parent.ax.relim()
            self._parent.ax.autoscale()
        self._draw_idle()

    def _draw_idle(self) -> None:
        """Triggers the FieldPlotTab's draw_idle_timer, promting redrawing of the canvas."""
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _update_data(self) -> None:
        """Triggers the FieldPlotTab's update_data_timer, promting data update and redrawing of the canvas."""
        self._parent.update_data_timer.start(self._parent.CALLBACK_DELAY)
    # endregion

    # region Properties
    @property
    def component(self) -> str:
        return self.component_combo.get_selected()

    @property
    def scalar_op(self) -> str:
        return self.scalar_op_combo.get_selected()

    @property
    def cmap(self) -> str:
        return self.cmap_combo.get_selected()

    @property
    def cscale(self) -> str:
        return self.color_scale_combo.get_selected()

    @property
    def cscale_custom_min(self) -> Optional[float]:
        if self.cscale == "Custom limits":
            return self.cscale_min.value()
        return None

    @property
    def cscale_custom_max(self) -> Optional[float]:
        if self.cscale == "Custom limits":
            return self.cscale_max.value()
        return None
    # endregion
