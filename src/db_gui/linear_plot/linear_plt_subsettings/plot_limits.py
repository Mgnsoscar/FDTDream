from PyQt6.QtWidgets import QLineEdit, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from matplotlib.axes import Axes
from .subsettings import Subsetting
from ..dataset import Dataset


class PlotLimitsSettings(Subsetting):

    dataset: Dataset
    ax: Axes

    def __init__(self, name: str, dataset: Dataset, ax: Axes):
        super().__init__(name, dataset, ax)
        self.checkbox.setVisible(False)
        self.dataset = dataset
        self.ax = ax

        self._init_xlim_inputs()
        self._init_ylim_inputs()

    def _init_xlim_inputs(self) -> None:
        self.xmin_input = QLineEdit()
        self.xmax_input = QLineEdit()
        xmin, xmax = self.dataset.xlim
        self._setup_input(self.xmin_input, self.on_limits_changed, xmin)
        self._setup_input(self.xmax_input, self.on_limits_changed, xmax)

        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.xmin_input)
        layout.addWidget(self.xmax_input)
        widget.setLayout(layout)
        self.addRow("X limits:", widget)

    def _init_ylim_inputs(self) -> None:
        self.ymin_input = QLineEdit()
        self.ymax_input = QLineEdit()
        ymin, ymax = self.dataset.ylim
        self._setup_input(self.ymin_input, self.on_limits_changed, ymin)
        self._setup_input(self.ymax_input, self.on_limits_changed, ymax)

        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ymin_input)
        layout.addWidget(self.ymax_input)
        widget.setLayout(layout)
        self.addRow("Y limits:", widget)

    def _setup_input(self, line_edit: QLineEdit, callback, text: float) -> None:
        line_edit.setPlaceholderText("None")
        if text is not None:
            line_edit.setText(str(text))
        line_edit.setMaximumWidth(80)
        line_edit.textChanged.connect(callback)  # type: ignore

    def on_limits_changed(self) -> None:
        x_min = self._parse_float(self.xmin_input.text())
        x_max = self._parse_float(self.xmax_input.text())
        y_min = self._parse_float(self.ymin_input.text())
        y_max = self._parse_float(self.ymax_input.text())

        self.dataset.set_xlim(x_min, x_max)
        self.dataset.set_ylim(y_min, y_max)
        self.draw_idle()

    @staticmethod
    def _parse_float(text: str) -> float | None:
        text = text.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
