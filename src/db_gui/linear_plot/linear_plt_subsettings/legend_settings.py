from PyQt6.QtWidgets import QComboBox, QSlider, QCheckBox, QPushButton, QColorDialog, QSpinBox, QFontComboBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from matplotlib.axes import Axes
from .subsettings import Subsetting
from ..dataset import Dataset


class LegendSettings(Subsetting):

    def __init__(self, name: str, dataset: Dataset, ax: Axes):
        super().__init__(name, dataset, ax)
        self.ax = ax

        self._init_location_selector()
        self._init_font_selector()
        self._init_fontsize_spinbox()
        self._init_alpha_slider()
        self._init_frame_checkbox()
        self._init_fancybox_checkbox()
        self._init_edgecolor_button()
        self._init_facecolor_button()
        self._init_borderpad_slider()
        self._init_color_timers()

    def _init_font_selector(self) -> None:
        self.font_combo = QFontComboBox()
        current_font = self.dataset.legend_params.get("prop", {}).get("family", "")
        if current_font:
            self.font_combo.setCurrentFont(QFont(current_font))  # fallback: string works too
        self.font_combo.currentFontChanged.connect(self.on_font_family_change)  # type: ignore
        self.addRow("Font family:", self.font_combo)

    def _init_color_timers(self) -> None:
        self.edgecolor_timer = QTimer()
        self.edgecolor_timer.setSingleShot(True)
        self.edgecolor_timer.timeout.connect(self.update_edgecolor)  # type: ignore

        self.facecolor_timer = QTimer()
        self.facecolor_timer.setSingleShot(True)
        self.facecolor_timer.timeout.connect(self.update_facecolor)  # type: ignore

    def _init_location_selector(self) -> None:
        self.location_box = QComboBox()
        self.location_box.wheelEvent = lambda event: None

        self.location_options = [
            'best', 'upper right', 'upper left', 'lower left', 'lower right',
            'right', 'center left', 'center right', 'lower center', 'upper center', 'center'
        ]
        self.location_box.addItems(self.location_options)

        loc = self.dataset.legend_params.get("loc")
        if loc in self.location_options:
            self.location_box.setCurrentText(loc)

        self.location_box.currentTextChanged.connect(self.on_location_change)  # type: ignore
        self.addRow("Location:", self.location_box)

    def _init_fontsize_spinbox(self) -> None:
        self.fontsize_spinbox = QSpinBox()
        self.fontsize_spinbox.setRange(6, 100)
        self.fontsize_spinbox.setValue(self.dataset.legend_params.get("prop").get("size"))
        self.fontsize_spinbox.valueChanged.connect(self.on_fontsize_change)  # type: ignore
        self.addRow("Font size:", self.fontsize_spinbox)

    def _init_alpha_slider(self) -> None:
        self.alpha_slider = QSlider()
        self.alpha_slider.setOrientation(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(int(self.dataset.legend_params.get("framealpha", 0.8) * 100))
        self.alpha_slider.wheelEvent = lambda event: None
        self.alpha_slider.valueChanged.connect(self.on_alpha_change)  # type: ignore
        self.addRow("Frame alpha:", self.alpha_slider)

    def _init_frame_checkbox(self) -> None:
        self.frame_checkbox = QCheckBox()
        self.frame_checkbox.setChecked(self.dataset.legend_params.get("frameon"))
        self.frame_checkbox.stateChanged.connect(self.on_frame_toggle)  # type: ignore
        self.addRow("Frame on:", self.frame_checkbox)

    def _init_fancybox_checkbox(self) -> None:
        self.fancybox_checkbox = QCheckBox()
        self.fancybox_checkbox.setChecked(self.dataset.legend_params.get("fancybox"))
        self.fancybox_checkbox.stateChanged.connect(self.on_fancybox_toggle)  # type: ignore
        self.addRow("Fancy box:", self.fancybox_checkbox)

    def _init_edgecolor_button(self) -> None:
        self.edgecolor_button = QPushButton("Edge Color")
        color = QColor(self.dataset.legend_params.get("edgecolor", "black"))
        self.set_button_color(self.edgecolor_button, color)
        self.edgecolor_button.clicked.connect(lambda: self.on_color_change("edgecolor"))  # type: ignore
        self.addRow("Edge color:", self.edgecolor_button)

    def _init_facecolor_button(self) -> None:
        self.facecolor_button = QPushButton("Face Color")
        color = QColor(self.dataset.legend_params.get("facecolor", "white"))
        self.set_button_color(self.facecolor_button, color)
        self.facecolor_button.clicked.connect(lambda: self.on_color_change("facecolor"))  # type: ignore
        self.addRow("Face color:", self.facecolor_button)

    def _init_borderpad_slider(self) -> None:
        self.borderpad_slider = QSlider()
        self.borderpad_slider.setOrientation(Qt.Orientation.Horizontal)
        self.borderpad_slider.setRange(0, 100)
        pad = self.dataset.legend_params.get("borderpad", 0.5)
        self.borderpad_slider.setValue(int(pad * 100))
        self.borderpad_slider.wheelEvent = lambda event: None
        self.borderpad_slider.valueChanged.connect(self.on_borderpad_change)  # type: ignore
        self.addRow("Border padding:", self.borderpad_slider)

    # region Callbacks
    def on_location_change(self, text: str) -> None:
        self.dataset.legend_params["loc"] = text
        self.dataset.update_legend()
        self.draw_idle()

    def on_fontsize_change(self, size: int) -> None:
        self.dataset.legend_params["prop"]["size"] = size
        self.dataset.update_legend()
        self.draw_idle()

    def on_alpha_change(self, value: int) -> None:
        self.dataset.legend_params["framealpha"] = value / 100
        self.dataset.update_legend()
        self.draw_idle()

    def on_frame_toggle(self, state: int) -> None:
        self.dataset.legend_params["frameon"] = bool(state)
        self.dataset.update_legend()
        self.draw_idle()

    def on_fancybox_toggle(self, state: int) -> None:
        self.dataset.legend_params["fancybox"] = bool(state)
        self.dataset.update_legend()
        self.draw_idle()

    def on_borderpad_change(self, value: int) -> None:
        self.dataset.legend_params["borderpad"] = value / 100
        self.dataset.update_legend()
        self.draw_idle()

    def on_color_change(self, key: str) -> None:
        dialog = QColorDialog(self)
        dialog.currentColorChanged.connect(
            lambda color: self.update_color_delayed(key, color)
        )  # type: ignore
        dialog.open()

    def update_color_delayed(self, key: str, color: QColor) -> None:
        if color.isValid():
            if key == "edgecolor":
                self.edge_selected_color = color
                self.edgecolor_timer.start(10)
            elif key == "facecolor":
                self.face_selected_color = color
                self.facecolor_timer.start(10)

    def update_facecolor(self) -> None:
        self.dataset.legend_params["facecolor"] = self.face_selected_color.name()
        self.set_button_color(self.facecolor_button, self.face_selected_color)
        self.dataset.update_legend()
        self.draw_idle()

    def update_edgecolor(self) -> None:
        self.dataset.legend_params["edgecolor"] = self.edge_selected_color.name()
        self.set_button_color(self.edgecolor_button, self.edge_selected_color)
        self.dataset.update_legend()
        self.draw_idle()

    def on_enabled_change(self, checked: bool) -> None:
        self.dataset.legend_params["enabled"] = checked
        self.dataset.update_legend()
        self.draw_idle()

    def on_font_family_change(self, font) -> None:
        family = font.family()
        self.dataset.legend_params["prop"]["family"] = family
        self.dataset.update_legend()
        self.draw_idle()

    def on_font_hover(self, index) -> None:
        font_name = self.font_combo.itemText(index.row())
        self.dataset.legend_params["prop"]["family"] = font_name
        self.dataset.update_legend()
        self.draw_idle()
    # endregion