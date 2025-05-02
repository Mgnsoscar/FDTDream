import numpy as np
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QPushButton, QVBoxLayout, QWidget
)

from .fieldplot_tab_interface import FieldPlotTabInterface
from .widgets import LabeledSlider, LabeledDropdown


class VectorSettings(QWidget):
    """
    A widget for configuring vector (quiver) plot visualization,
    including field selection, scaling, pivot, color with alpha,
    arrow width, and head shape parameters.
    """

    # region Constants
    SCALE_MIN = 0.01
    SCALE_MAX = 500
    ALPHA_SLIDER_SCALING_FACTOR = 100
    WIDTH_SLIDER_SCALING_FACTOR = 10000
    HEADWIDTH_SLIDER_SCALING_FACTOR = 100
    HEADLENGTH_SLIDER_SCALING_FACTOR = 100
    HEADAXISLENGTH_SLIDER_SCALING_FACTOR = 100
    SCALAR_OPERATIONS = ["Re", "Im"]
    PIVOT_OPTIONS = ["tail", "middle", "tip"]
    QUIVER_CONFIG = {
        "scale_units": "width",
        "scale": 50.,
        "pivot": "tail",
        "color": (0, 0, 0),
        "alpha": 1.,
        "width": 0.005,
        "headwidth": 3.,
        "headlength": 5.,
        "headaxislength": 4.5
    }
    # endregion

    # region Variables
    _parent: FieldPlotTabInterface
    # endregion

    def __init__(self, parent: FieldPlotTabInterface) -> None:
        super().__init__(parent)  # type: ignore

        # Create reference to FieldPlotTab
        self._parent = parent

        # Create layout
        self._layout = QVBoxLayout(self)

        # Create widgets
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Initialize the widgets for vector settings."""

        # Field
        self.field_combo = LabeledDropdown(self, "Field:", self.on_field_change)
        self._layout.addWidget(self.field_combo)

        # Scalar operation
        self.scalar_op_combo = LabeledDropdown(self, "Scalar operation:", self.on_scalar_operation_change)
        self.scalar_op_combo.set_dropdown_items(self.SCALAR_OPERATIONS)
        self._layout.addWidget(self.scalar_op_combo)

        # Scale
        self.scale_slider = LabeledSlider(self, "Scale", -20_000, 20_000)
        self.scale_slider.slider.setSingleStep(1)
        self.scale_slider.slider.setValue(self.scale_to_slider(self.QUIVER_CONFIG["scale"]))
        self.scale_slider.slider.setInvertedAppearance(True)
        self.scale_slider.set_slider_callback(self.on_scale_change)
        self._layout.addWidget(self.scale_slider)

        # Pivot
        self.pivot_combo = LabeledDropdown(self, "Pivot:")
        self.pivot_combo.set_dropdown_items(self.PIVOT_OPTIONS)
        self.pivot_combo.set_dropdown_callback(self.on_pivot_change)
        self._layout.addWidget(self.pivot_combo)

        # Color and alpha
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self.on_color_change)  # type: ignore
        self._layout.addWidget(self.color_button)

        # Alpha
        self.alpha_slider = LabeledSlider(self, "Alpha", 1, 100)
        self.alpha_slider.slider.setValue(int(self.QUIVER_CONFIG["alpha"] * self.ALPHA_SLIDER_SCALING_FACTOR))
        self.alpha_slider.set_slider_callback(self.on_alpha_change)
        self._layout.addWidget(self.alpha_slider)

        # Width
        self.width_slider = LabeledSlider(self, "Arrow Width", 1, 200)
        self.width_slider.slider.setValue(int(self.QUIVER_CONFIG["width"] * self.WIDTH_SLIDER_SCALING_FACTOR))
        self.width_slider.set_slider_callback(self.on_width_change)
        self._layout.addWidget(self.width_slider)

        # Head width
        self.headwidth_slider = LabeledSlider(self, "Head Width", 1, 1000)
        self.headwidth_slider.slider.setValue(
            int(self.QUIVER_CONFIG["headwidth"] * self.HEADWIDTH_SLIDER_SCALING_FACTOR))
        self.headwidth_slider.set_slider_callback(self.on_headwidth_change)
        self._layout.addWidget(self.headwidth_slider)

        # Head length
        self.headlength_slider = LabeledSlider(self, "Head Length", 1, 1000)
        self.headlength_slider.slider.setValue(
            int(self.QUIVER_CONFIG["headlength"] * self.HEADLENGTH_SLIDER_SCALING_FACTOR))
        self.headlength_slider.set_slider_callback(self.on_headlength_change)
        self._layout.addWidget(self.headlength_slider)

        # Head axis length
        self.headaxislength_slider = LabeledSlider(self, "Head Axis Length", 1, 1000)
        self.headaxislength_slider.slider.setValue(
            int(self.QUIVER_CONFIG["headaxislength"] * self.HEADAXISLENGTH_SLIDER_SCALING_FACTOR))
        self.headaxislength_slider.set_slider_callback(self.on_headaxislength_change)
        self._layout.addWidget(self.headaxislength_slider)

        # Normalization checkbox
        self.normalized_checkbox = QCheckBox("Normalized")
        self.normalized_checkbox.setChecked(False)
        self.normalized_checkbox.stateChanged.connect(self.on_normalize_change)  # type: ignore
        self._layout.addWidget(self.normalized_checkbox)

    # region Callbacks
    def on_field_change(self, field: str) -> None:
        self._parent.select_field(field, quiver_field=True)
        self._parent.reload_quiver_data()
        self._update_data()

    def on_scalar_operation_change(self) -> None:
        self._parent.reload_quiver_data()
        self._update_data()

    def on_normalize_change(self) -> None:
        self._parent.reload_quiver_data()
        self._update_data()

    def on_scale_change(self, scale: int) -> None:
        scale = self.slider_to_scale(scale + 20_001)
        self.QUIVER_CONFIG["scale"] = scale
        if self._parent.quiver is not None:
            self._parent.quiver.scale = scale
            self._draw_idle()

    def on_pivot_change(self, pivot: str) -> None:
        self.QUIVER_CONFIG["pivot"] = pivot
        if self._parent.quiver is not None:
            self._parent.quiver.pivot = pivot
            self._draw_idle()

    def on_color_change(self) -> None:
        color = QColorDialog.getColor()
        if not color.isValid():
            return

        # Update the button color.
        self.color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: {'black' if color.lightness() > 128 else 'white'};
                }}
            """)

        # Fetch the rgb value and update.
        rgb_color = color.redF(), color.greenF(), color.blueF()
        self.QUIVER_CONFIG["color"] = rgb_color
        if self._parent.quiver:
            self._parent.quiver.set_color(rgb_color)
            self._draw_idle()

    def on_alpha_change(self, alpha: float) -> None:
        alpha /= self.ALPHA_SLIDER_SCALING_FACTOR
        self.QUIVER_CONFIG["alpha"] = alpha
        if self._parent.quiver is not None:
            self._parent.quiver.set_alpha(alpha)
            self._draw_idle()

    def on_width_change(self, width: float) -> None:
        width /= self.WIDTH_SLIDER_SCALING_FACTOR
        self.QUIVER_CONFIG["width"] = width
        if self._parent.quiver is not None:
            self._parent.quiver.width = width
            self._draw_idle()

    def on_headwidth_change(self, headwidth: float) -> None:
        headwidth /= self.HEADWIDTH_SLIDER_SCALING_FACTOR

        self.QUIVER_CONFIG["headwidth"] = headwidth
        if self._parent.quiver is not None:
            self._parent.quiver.headwidth = headwidth
            self._draw_idle()

    def on_headlength_change(self, headlength: float) -> None:
        headlength /= self.HEADLENGTH_SLIDER_SCALING_FACTOR
        self.QUIVER_CONFIG["headlength"] = headlength
        if self._parent.quiver is not None:
            self._parent.quiver.headlength = headlength
            self._draw_idle()

    def on_headaxislength_change(self, headaxislength: float) -> None:
        headaxislength /= self.HEADAXISLENGTH_SLIDER_SCALING_FACTOR
        self.QUIVER_CONFIG["headaxislength"] = headaxislength
        if self._parent.quiver is not None:
            self._parent.quiver.headaxislength = headaxislength
            self._draw_idle()
    # endregion

    # region Properties
    @property
    def field(self) -> str:
        return self.field_combo.get_selected()

    @property
    def scalar_operation(self) -> str:
        return self.scalar_op_combo.get_selected()

    @property
    def scale(self) -> float:
        return self.slider_to_scale(self.scale_slider.get_value() + 20_000)

    @property
    def pivot(self) -> str:
        return self.pivot_combo.get_selected()

    @property
    def width(self) -> float:
        return self.width_slider.get_value() / self.WIDTH_SLIDER_SCALING_FACTOR

    @property
    def headwidth(self) -> float:
        return self.headwidth_slider.get_value() / self.HEADWIDTH_SLIDER_SCALING_FACTOR

    @property
    def headlength(self) -> float:
        return self.headlength_slider.get_value() / self.HEADLENGTH_SLIDER_SCALING_FACTOR

    @property
    def headaxislength(self) -> float:
        return self.headaxislength_slider.get_value() / self.HEADAXISLENGTH_SLIDER_SCALING_FACTOR

    @property
    def alpha(self) -> float:
        return self.alpha_slider.get_value() / self.ALPHA_SLIDER_SCALING_FACTOR

    @property
    def color(self) -> tuple:
        color = self.color_button.palette().button().color()
        return color.redF(), color.greenF(), color.blueF()

    @property
    def normalized(self) -> bool:
        return self.normalized_checkbox.isChecked()
    # endregion

    # region Methods
    def reapply_quiver_config(self) -> None:
        """Reapply the quiver configuration."""
        if not self._parent.quiver:
            return

        quiver = self._parent.quiver
        for k, v in self.QUIVER_CONFIG.items():
            if hasattr(quiver, k):
                setattr(quiver, k, v)
            else:
                getattr(quiver, "set_" + k)(v)

    def slider_to_scale(self, slider_val: int) -> float:
        slider_min = 1
        slider_max = 40_001

        # Convert slider to a normalized 0-1 value
        normalized = (slider_val - slider_min) / (slider_max - slider_min)
        # Map normalized value to log scale
        log_min = np.log10(self.SCALE_MIN)
        log_max = np.log10(self.SCALE_MAX)
        log_val = log_min + normalized * (log_max - log_min)
        return 10 ** log_val

    def scale_to_slider(self, scale_val: float) -> int:
        slider_min = 1
        slider_max = 40_001

        log_min = np.log10(self.SCALE_MIN)
        log_max = np.log10(self.SCALE_MAX)
        log_val = np.log10(scale_val)
        normalized = (log_val - log_min) / (log_max - log_min)
        return int(round(slider_min + normalized * (slider_max - slider_min))) - 20_001

    def _draw_idle(self) -> None:
        """Triggers the FieldPlotTab's draw_idle_timer, promting redrawing of the canvas."""
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _update_data(self) -> None:
        """Triggers the FieldPlotTab's update_data_timer, promting data update and redrawing of the canvas."""
        self._parent.update_data_timer.start(self._parent.CALLBACK_DELAY)
    # endregion
