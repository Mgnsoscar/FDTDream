import numpy as np

from .subsettings import Subsetting
from PyQt6.QtWidgets import QPushButton, QLineEdit, QCheckBox, QSlider, QComboBox, QHBoxLayout
from PyQt6.QtGui import QColor, QDoubleValidator
from PyQt6.QtCore import Qt, pyqtSignal, QLocale
from matplotlib.lines import Line2D
from ..ScalableLine2D import ScalableLine2D
from ..dataset import Dataset


class LinearArtistSettings(Subsetting):

    moved_up = pyqtSignal(int)
    moved_down = pyqtSignal(int)
    remove_artist = pyqtSignal(int)
    artist: ScalableLine2D
    include_in_legend: QCheckBox
    dataset: Dataset

    def __init__(self, name: str, dataset, artist: Line2D):
        super().__init__(name, dataset, artist)

        self._init_label_input()
        self._init_linestyle_selector()
        self._init_linewidth_slider()
        self._init_alpha_slider()
        self._init_color_selection()
        self._init_include_in_legend_checkbox()

        lay = QHBoxLayout()
        upbutton = QPushButton("↑")
        upbutton.clicked.connect(self.on_moveup_clicked)
        downbutton = QPushButton("↓")
        downbutton.clicked.connect(self.on_moveddown_clicked)
        lay.addWidget(upbutton)
        lay.addWidget(downbutton)

        self.header.insertLayout(2, lay)
        self._init_scaling_controls()

        self.remove = QPushButton("Remove Artist")
        self.remove.clicked.connect(self.on_remove_artist_clicked)
        self.addRow("", self.remove)

    def on_moveup_clicked(self) -> None:
        self.moved_up.emit([artist for artist in self.dataset.ax.lines].index(self.artist))

    def on_moveddown_clicked(self) -> None:
        self.moved_down.emit([artist for artist in self.dataset.ax.lines].index(self.artist))

    def _init_color_selection(self) -> None:
        self.color_button = QPushButton("Select Color")
        self.color_button.clicked.connect(self.on_color_change)  # type: ignore
        try:
            self.selected_color = QColor(self.artist.get_color())
        except Exception:
            self.selected_color = QColor(*[int(color) for color in self.artist.get_color()])
        self.set_button_color(self.color_button, self.selected_color)
        self.addRow("Color:", self.color_button)

    def _init_linestyle_selector(self) -> None:
        self.linestyle_box = QComboBox()
        self.linestyle_box.wheelEvent = lambda event: None
        self.linestyle_options = {
            "Solid": "-",
            "Dashed": "--",
            "Dotted": ":",
            "Dash-dot": "-.",
        }

        # Populate combo box
        self.linestyle_box.addItems(self.linestyle_options.keys())

        # Set current value
        current_style = self.artist.get_linestyle()
        for name, style in self.linestyle_options.items():
            if style == current_style:
                self.linestyle_box.setCurrentText(name)
                break

        self.linestyle_box.currentTextChanged.connect(self.on_linestyle_change)  # type: ignore
        self.addRow("Line style:", self.linestyle_box)

    def _init_include_in_legend_checkbox(self) -> None:
        self.include_in_legend = QCheckBox()
        self.include_in_legend.setChecked(not str(self.artist.get_label()).startswith("_"))
        self.include_in_legend.clicked.connect(self.on_include_in_legend_change)  # type: ignore
        self.addRow("Include in legend:", self.include_in_legend)

    def _init_label_input(self) -> None:
        self.input = QLineEdit()
        label = str(self.artist.get_label()).lstrip("_")
        self.input.setMinimumWidth(200)
        self.input.setText(label)
        self.input.textChanged.connect(self.on_label_change)  # type: ignore
        self.title_label.setVisible(False)
        self.header.insertWidget(1, self.input)

    def _init_alpha_slider(self) -> None:
        self.alpha = QSlider()
        self.alpha.setOrientation(Qt.Orientation.Horizontal)
        self.alpha.setRange(0, 100)
        self.alpha.setValue(int(self.artist.get_alpha() * 100) if self.artist.get_alpha() else 100)
        self.alpha.wheelEvent = lambda event: None
        self.alpha.valueChanged.connect(self.on_alpha_change)  # type: ignore
        self.addRow("Alpha:", self.alpha)

    def _init_linewidth_slider(self) -> None:
        self.linewidth = QSlider()
        self.linewidth.setOrientation(Qt.Orientation.Horizontal)
        self.linewidth.setRange(0, 100)
        self.linewidth.setValue(int(self.artist.get_linewidth() * 10))
        self.linewidth.wheelEvent = lambda event: None
        self.linewidth.valueChanged.connect(self.on_linewidth_change)  # type: ignore
        self.addRow("Linewidth:", self.linewidth)

    def _init_scaling_controls(self) -> None:
        validator = QDoubleValidator()
        validator.setBottom(-float("inf"))
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        validator.setLocale(QLocale("C"))  # Force '.' as decimal separator

        # Scale input
        self.scale_input = QLineEdit()
        if self.artist.yscalar is not None:
            self.scale_input.setText(str(self.artist.yscalar))
        self.scale_input.setValidator(validator)
        self.scale_input.textChanged.connect(self.apply_scalar_update)

        # Subtract combobox
        self.subtract_box = QComboBox()
        if self.artist.subtract_from is None:
            self.subtract_box.addItem("None", userData="None")
        else:
            for line in self.dataset.ax.lines:
                if line is self.artist.subtract_from:
                    label = str(line.get_label()).lstrip("_") or f"Line {id(line)}"
                    self.subtract_box.addItem(label, userData=line)
                    break

        self.subtract_box.currentIndexChanged.connect(self.apply_scalar_update)

        # Normalize combobox
        self.normalize_box = QComboBox()
        if self.artist.normalized_to is None:
            self.normalize_box.addItem("None", userData="None")
        else:
            for line in self.dataset.ax.lines:
                if line is self.artist.normalized_to:
                    label = str(line.get_label()).lstrip("_") or f"Line {id(line)}"
                    self.normalize_box.addItem(label, userData=line)
                    break
        self.populate_normalize_box()
        self.normalize_box.currentIndexChanged.connect(self.apply_scalar_update)

        # Post-normalization scale input
        self.post_scale_input = QLineEdit()
        if self.artist.post_scalar is not None:
            self.post_scale_input.setText(str(self.artist.post_scalar))
        self.post_scale_input.setValidator(validator)
        self.post_scale_input.textChanged.connect(self.apply_scalar_update)

        self.addRow("Pre-scale Y by:", self.scale_input)
        self.addRow("Subtract by dataset:", self.subtract_box)
        self.addRow("Normalize to dataset:", self.normalize_box)
        self.addRow("Post-scale Y by:", self.post_scale_input)

    def populate_normalize_box(self) -> None:
        current_x = self.artist.true_xdata if isinstance(self.artist, ScalableLine2D) else None
        norm_to: ScalableLine2D = self.artist.normalized_to
        subtr_from: ScalableLine2D = self.artist.subtract_from

        new_data = [("None", None)]
        for line in self.dataset.ax.lines:
            if line is not self.artist and isinstance(line, ScalableLine2D):
                if current_x is not None:
                    try:
                        if not np.allclose(current_x, line.true_xdata, rtol=1e-9, atol=1e-12):
                            continue  # Skip lines with mismatched x values
                    except ValueError:
                        continue  # Skip lines with incompatible shapes
                label = str(line.get_label()).lstrip("_") or f"Line {id(line)}"
                new_data.append((label, line))

        self.normalize_box.blockSignals(True)
        self.subtract_box.blockSignals(True)

        self.normalize_box.clear()
        self.subtract_box.clear()

        normalize_index = 0
        subtract_index = 0

        for i, (label, line) in enumerate(new_data):
            self.normalize_box.addItem(label, userData=line)
            self.subtract_box.addItem(label, userData=line)
            if line is norm_to:
                normalize_index = i
            if line is subtr_from:
                subtract_index = i

        self.normalize_box.setCurrentIndex(normalize_index)
        self.subtract_box.setCurrentIndex(subtract_index)

        self.normalize_box.blockSignals(False)
        self.subtract_box.blockSignals(False)
    # region Callbacks

    def on_linewidth_change(self, width: int) -> None:
        self.artist.set_linewidth(width/10)
        self.dataset.update_legend()
        self.draw_idle()

    def on_alpha_change(self, alpha: int) -> None:
        self.artist.set_alpha(alpha/100)
        self.dataset.update_legend()
        self.draw_idle()

    def on_label_change(self, text: str) -> None:
        if text == "":
            text = "_"
        self.artist.set_label(text)
        self.title_label.setText(text)

        # Update the legend
        self.dataset.update_legend()
        self.draw_idle()

    def on_enabled_change(self, checked: bool) -> None:
        super().on_enabled_change(checked)
        self.on_include_in_legend_change(self.include_in_legend.isChecked())
        self.dataset.relim()

    def on_include_in_legend_change(self, checked: bool) -> None:
        label = str(self.artist.get_label())
        checked = checked and self.checkbox.isChecked()
        if checked:
            # Should be visible → remove leading underscores
            label = label.lstrip("_")
        else:
            # Should be hidden → ensure it starts with an underscore
            if not label.startswith("_"):
                label = "_" + label
        self.artist.set_label(label)
        self.dataset.update_legend()
        self.draw_idle()

    def on_linestyle_change(self, text: str) -> None:
        style = self.linestyle_options.get(text, "-")
        self.artist.set_linestyle(style)
        self.draw_idle()

    def update_color(self) -> None:
        color = self.selected_color
        self.set_button_color(self.color_button, self.selected_color)
        rgb_color = (color.redF(), color.greenF(), color.blueF())
        self.artist.set_color(rgb_color)
        self.dataset.update_legend()
        self.draw_idle()

    def on_remove_artist_clicked(self) -> None:
        self.artist.on_removed()
        self.remove_artist.emit([artist for artist in self.dataset.ax.lines].index(self.artist))

    def apply_scalar_update(self) -> None:
        if not isinstance(self.artist, ScalableLine2D):
            return

        try:
            scalar = float(self.scale_input.text()) if self.scale_input.text() else 1
        except ValueError:
            scalar = 1

        try:
            post_scalar = float(self.post_scale_input.text()) if self.post_scale_input.text() else 1
        except ValueError:
            post_scalar = 1

        normalized_line = self.normalize_box.currentData()
        if normalized_line == "None":
            normalized_line = None

        subtract_line = self.subtract_box.currentData()
        if subtract_line == "None":
            subtract_line = None

        self.artist.apply_scalar_operation(
            yscalar=scalar,
            post_scalar=post_scalar,
            subtract_from=subtract_line,
            normalized_to=normalized_line,
        )
        self.dataset.update_legend()
        self.dataset.relim()
        self.draw_idle()