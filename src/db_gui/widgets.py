from typing import Callable, List, Literal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QCheckBox, QFrame
)
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtCore import Qt
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QObject
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QComboBox, QFormLayout, QToolButton,
                             QLineEdit)
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PyQt6.QtWidgets import QFileDialog


class WheelEventBlocker(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True  # Block wheel event
        return super().eventFilter(obj, event)


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
        self.slider.wheelEvent = lambda event: None
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
        self.dropdown.wheelEvent = lambda event: None
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


class CollapsibleWidget(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.clicked.connect(self.toggle_content)

        self.content_area = QWidget()
        self.content_area.setVisible(False)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.toggle_button)
        self.layout.addWidget(self.content_area)

        self.content_layout = QVBoxLayout(self.content_area)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def toggle_content(self):
        is_expanded = self.toggle_button.isChecked()
        self.content_area.setVisible(is_expanded)
        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow if is_expanded else Qt.ArrowType.RightArrow
        )

    def addRow(self, widget: QWidget):
        """Helper to add rows easily"""
        self.content_layout.addWidget(widget)


class CollapsibleGroupBox(QWidget):
    title_label: QLabel

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header
        self.header = QHBoxLayout()
        self.header.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.checkbox = QCheckBox()
        self.title_label = QLabel(title)
        self.toggle_button = QToolButton()
        self.toggle_button.setText(">")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.clicked.connect(self.toggle_content)

        self.header.addWidget(self.checkbox)
        self.header.addWidget(self.title_label)
        self.header.addStretch()
        self.header.addWidget(self.toggle_button)

        self.layout().addLayout(self.header)

        # Content
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_area.setLayout(QVBoxLayout())
        self.layout().addWidget(self.content_area)
        self.content_area.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.toggle_content()

    def toggle_content(self):
        if self.toggle_button.isChecked():
            self.toggle_button.setText("˅")
            self.content_area.show()
        else:
            self.toggle_button.setText(">")
            self.content_area.hide()

    def addRow(self, label, widget):
        """Adds a row to the internal form."""
        widg = QWidget()
        row = QHBoxLayout()
        widg.setLayout(row)
        row.addWidget(QLabel(label))
        row.addWidget(widget)
        self.content_area.layout().addWidget(widg)

    def insert_row(self, idx: int, label: str, widget: QWidget) -> None:
        widg = QWidget()
        row = QHBoxLayout()
        widg.setLayout(row)
        row.addWidget(QLabel(label))
        row.addWidget(widget)
        layout: QVBoxLayout = self.content_area.layout()
        layout.insertWidget(idx, widget)

    def remove_row(self, row: QWidget):
        self.content_area.layout().removeWidget(row)

    def remove_rows(self):
        for i in range(self.content_area.layout().count())[::-1]:
            widget = self.content_area.layout().takeAt(i).widget()
            widget.setParent(None)
            widget.deleteLater()
            del widget

    def setContentLayout(self, layout):
        """Replace default layout inside the content area."""
        QWidget().setLayout(self.content_area.layout())  # clear old
        self.content_area.setLayout(layout)


class TightNavigationToolbar(NavigationToolbar):
    def save_figure(self, *args):
        """Override save behavior to include bbox_inches='tight' automatically."""
        dialog = QFileDialog(self)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter("PNG files (*.png);;JPEG files (*.jpg);;All Files (*)")
        dialog.setDefaultSuffix("png")

        if dialog.exec():
            filename = dialog.selectedFiles()[0]
            if filename:
                self.canvas.figure.savefig(filename, bbox_inches="tight")


class ClickableLabel(QLabel):
    doubleClicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        parent = kwargs.pop("_parent", None)
        super().__init__(*args, **kwargs)
        if parent:
            self._parent = parent

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        self._on_edit_name()
        super().mouseDoubleClickEvent(event)

    def _on_edit_name(self) -> None:
        self.edit_name_lineedit = QLineEdit(self.text())
        self.edit_name_lineedit.returnPressed.connect(self._on_name_edit_done)  # Enter key
        self.edit_name_lineedit.editingFinished.connect(self._on_name_edit_done)  # Focus out

        # Replace label with line edit in layout
        layout: QHBoxLayout = self.parentWidget().layout()  # type: ignore
        index = layout.indexOf(self)

        self.hide()
        layout.insertWidget(index, self.edit_name_lineedit)
        self.edit_name_lineedit.setFocus()
        self.edit_name_lineedit.selectAll()

    def _on_name_edit_done(self) -> None:
        new_name = self.edit_name_lineedit.text()
        if new_name != "":
            self.setText(new_name)
        self.show()

        layout = self.edit_name_lineedit.parentWidget().layout()
        layout.removeWidget(self.edit_name_lineedit)
        self.edit_name_lineedit.deleteLater()

        if self._parent:
            self._parent.name = new_name
