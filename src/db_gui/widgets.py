from typing import Callable, List, Literal

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QComboBox


class LabeledSlider(QWidget):
    """Slider object with included label."""

    label: QLabel
    slider: QSlider

    def __init__(self, parent: QWidget, name: str, min_val: int, max_val: int, callback: Callable = None,
                 orientation: Qt.Orientation = Qt.Orientation.Horizontal,
                 label_pos: Literal["top", "left"] = "top", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Create label
        self.label = QLabel(f"{name}:", self)

        # Create slider - set min and max values
        self.slider = QSlider(orientation)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setSingleStep(1)
        if callback:
            self.slider.valueChanged.connect(callback)  # type: ignore

        # Create a layout and add the slider to it.
        if label_pos == "left":
            layout = QHBoxLayout(self)
        else:
            layout = QVBoxLayout(self)

        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        self.setLayout(layout)

    def setVisible(self, visible):
        self.slider.setVisible(visible)
        self.label.setVisible(visible)

    def get_value(self, ignore=None) -> int:
        """The ignore parameter is jsut to be able to pass a None value,
        so you can create slices and call this method the same way."""
        return self.slider.value()

    def set_range(self, min_val: int, max_val: int) -> None:
        self.blockSignals(True)
        self.slider.setRange(min_val, max_val)
        self.blockSignals(False)

    def set_index(self, idx: int) -> None:
        self.blockSignals(True)
        self.slider.setValue(idx)
        self.blockSignals(False)

    def set_label(self, text: str) -> None:
        self.label.setText(text)

    def set_slider_callback(self, function: Callable) -> None:
        self.slider.valueChanged.connect(function)  # type: ignore

    def blockSignals(self, b):
        self.slider.blockSignals(b)

    @property
    def enabled(self) -> bool:
        return self.slider.isEnabled()

    @enabled.setter
    def enabled(self, enable: bool) -> None:
        self.slider.setEnabled(enable)


class LabeledDropdown(QWidget):
    """Slider object with included label."""

    label: QLabel
    dropdown: QComboBox

    def __init__(self, parent: QWidget, label: str, callback: Callable = None,
                 label_pos: Literal["top", "left"] = "left", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Create label
        self.label = QLabel(f"{label}:", self)

        # Create the dropdown and set callback function
        self.dropdown = QComboBox(self)
        if callback:
            self.dropdown.currentTextChanged.connect(callback)  # type: ignore

        # Create layout and add the dropdown menu to it
        if label_pos == "left":
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.dropdown)
        self.setLayout(layout)

    def setVisible(self, visible):
        self.dropdown.setVisible(visible)
        self.label.setVisible(visible)

    def get_items(self) -> List[str]:
        return [self.dropdown.itemText(i) for i in range(self.dropdown.count())]

    def get_selected(self) -> str:
        return self.dropdown.currentText()

    def set_item(self, val: str):
        self.dropdown.blockSignals(True)
        index = self.dropdown.findText(val)
        if index != -1:
            self.dropdown.setCurrentIndex(index)
        self.dropdown.blockSignals(False)

    def set_dropdown_items(self, items: List[str], keep_selection: bool = True) -> str:

        # Store the currently selected
        self.blockSignals(True)
        selected = self.get_selected()

        # Clear and add new items
        self.dropdown.clear()
        self.dropdown.addItems(items)

        # Try to restore the selection if the old item is still there
        if keep_selection:
            index = self.dropdown.findText(selected)
            if index >= 0:
                self.dropdown.setCurrentIndex(index)
            else:
                selected = self.get_selected()
        else:
            selected = self.get_selected()

        self.blockSignals(False)
        return selected

    def set_label(self, text: str) -> None:
        self.label.setText(text)

    def set_dropdown_callback(self, function: Callable) -> None:
        self.dropdown.currentTextChanged.connect(function)  # type: ignore

    def blockSignals(self, b):
        self.dropdown.blockSignals(b)

    @property
    def enabled(self) -> bool:
        return self.dropdown.isEnabled()

    @enabled.setter
    def enabled(self, enable: bool) -> None:
        self.dropdown.setEnabled(enable)


