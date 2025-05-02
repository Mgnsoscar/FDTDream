from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QPushButton, QGroupBox, QLabel,
    QHBoxLayout, QCheckBox, QScrollArea, QFrame, QFormLayout, QSizePolicy,
    QComboBox, QSpinBox, QColorDialog, QSlider, QToolBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from .fieldplot_tab_interface import FieldPlotTabInterface
from trimesh import Trimesh
from typing import Dict, List
from ..fdtdream.database.db import StructureModel
import numpy as np


class StructureSettings(QWidget):
    def __init__(self, parent: FieldPlotTabInterface):
        super().__init__()
        self._parent = parent

        self.section_widgets: List[StructureSection] = []
        self.name_to_struct: Dict[str, StructureModel] = {}  # Map name -> structure object

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Structure selector
        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(100)
        self.list_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        self.list_widget.currentRowChanged.connect(self._on_selection_changed)

        self.plot_button = QPushButton("Plot")
        self.plot_button.setEnabled(False)
        self.plot_button.clicked.connect(self._on_plot_clicked)

        layout.addWidget(QLabel("Available Structures:"))
        layout.addWidget(self.list_widget)
        layout.addWidget(self.plot_button)

        # Scrollable area for plotted structures
        self.section_container = QWidget()
        self.section_layout = QVBoxLayout(self.section_container)
        self.section_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.section_container)
        layout.addWidget(scroll)

    def populate_structures(self) -> None:
        """Populate available structures AFTER the parent simulation is ready."""
        self.list_widget.clear()
        self.name_to_struct.clear()

        if self._parent.simulation is not None:
            for struct in self._parent.simulation.structures:
                self.name_to_struct[struct.name] = struct
                self.list_widget.addItem(struct.name)

    def _on_selection_changed(self, row: int):
        self.plot_button.setEnabled(row >= 0)

    def _on_plot_clicked(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return

        item = self.list_widget.takeItem(row)
        if item is None:
            return

        name = item.text()
        struct = self.name_to_struct[name]

        if struct.id not in self._parent.structure_outlines:
            projection, outlines = struct.get_projection_and_intersection(self._parent.monitor.x,
                                                                          self._parent.monitor.y,
                                                                          self._parent.monitor.z)
            self._parent.structure_outlines[struct.id] = projection
            self._parent.structure_intersections[struct.id] = outlines

        plot_type = self._parent.plot_type
        if "Plane" in plot_type:
            self._parent.ax.add_artist(self._parent.structure_outlines[struct.id][plot_type[:2].lower()])
            self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY
)
        section = StructureSection(self._parent, struct.name, struct.id)
        section.remove_requested.connect(lambda: self._remove_section(section, name))
        self.section_layout.addWidget(section)
        self.section_widgets.append(section)

    def _remove_section(self, section_widget, name: str):
        self.section_layout.removeWidget(section_widget)
        section_widget.deleteLater()
        self.section_widgets.remove(section_widget)

        self.list_widget.addItem(name)


class StructureSection(QGroupBox):
    remove_requested = pyqtSignal()
    struct_id: int
    _parent: FieldPlotTabInterface

    def __init__(self, parent: FieldPlotTabInterface, name: str, struct_id: int):
        super().__init__(f"{name} (ID: {struct_id})")
        self._parent = parent
        self.struct_id = struct_id
        self.setCheckable(True)
        self.setChecked(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        main_layout = QVBoxLayout(self)

        # Remove Button
        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(80)
        remove_btn.clicked.connect(self.remove_requested.emit)
        top_row = QHBoxLayout()
        top_row.addStretch()
        top_row.addWidget(remove_btn)
        main_layout.addLayout(top_row)

        # Inner collapsible settings
        self.outline_box = self._create_outline_group()
        self.fill_box = self._create_fill_group()
        self.intersection_box = self._create_intersection_group()

        main_layout.addWidget(self.outline_box)
        main_layout.addWidget(self.fill_box)
        main_layout.addWidget(self.intersection_box)

        main_layout.addStretch()

    def _create_outline_group(self) -> QGroupBox:
        box = QGroupBox("Projection Outline")
        box.setCheckable(True)
        box.setChecked(False)
        form = QFormLayout(box)

        self.outline_cb = QCheckBox("Enable Outline")
        self.outline_linewidth = QSpinBox()
        self.outline_linewidth.setRange(1, 10)
        self.outline_linestyle = QComboBox()
        self.outline_linestyle.addItems(["solid", "dashed", "dotted", "dashdot"])
        self.outline_alpha = QSlider(Qt.Orientation.Horizontal)
        self.outline_alpha.setRange(0, 100)
        self.outline_alpha.setValue(100)
        self.outline_color_btn = QPushButton("Pick Color")
        self.outline_color_val = QColor(0, 0, 0)
        self.outline_color_btn.clicked.connect(self._pick_outline_color)
        self.outline_alpha.valueChanged.connect(self._on_outline_alpha_change)

        form.addRow(self.outline_cb)
        form.addRow("Linewidth:", self.outline_linewidth)
        form.addRow("Linestyle:", self.outline_linestyle)
        form.addRow("Alpha:", self.outline_alpha)
        form.addRow(self.outline_color_btn)

        return box

    def _create_fill_group(self) -> QGroupBox:
        box = QGroupBox("Projection Fill")
        box.setCheckable(True)
        box.setChecked(False)
        form = QFormLayout(box)

        self.fill_cb = QCheckBox("Enable Fill")
        self.fill_alpha = QSlider(Qt.Orientation.Horizontal)
        self.fill_alpha.setRange(0, 100)
        self.fill_alpha.setValue(50)
        self.fill_color_btn = QPushButton("Pick Fill Color")
        self.fill_color_val = QColor(100, 100, 255)
        self.fill_color_btn.clicked.connect(self._pick_fill_color)
        self.fill_alpha.valueChanged.connect(self._on_outline_fill_alpha_change)

        form.addRow(self.fill_cb)
        form.addRow("Alpha:", self.fill_alpha)
        form.addRow(self.fill_color_btn)

        return box

    def _create_intersection_group(self) -> QGroupBox:
        box = QGroupBox("Intersection Outline")
        box.setCheckable(True)
        box.setChecked(False)
        form = QFormLayout(box)

        self.intersection_cb = QCheckBox("Enable Intersection")
        self.intersection_linewidth = QSpinBox()
        self.intersection_linewidth.setRange(1, 10)
        self.intersection_linestyle = QComboBox()
        self.intersection_linestyle.addItems(["solid", "dashed", "dotted", "dashdot"])
        self.intersection_alpha = QSlider(Qt.Orientation.Horizontal)
        self.intersection_alpha.setRange(0, 100)
        self.intersection_alpha.setValue(100)
        self.intersection_color_btn = QPushButton("Pick Intersection Color")
        self.intersection_color_val = QColor(0, 255, 0)
        self.intersection_color_btn.clicked.connect(self._pick_intersection_color)

        self.use_custom_coord_cb = QCheckBox("Use custom coordinate")
        self.custom_coord_slider = QSlider(Qt.Orientation.Horizontal)
        self.custom_coord_slider.setRange(0, 100)
        self.custom_coord_slider.setVisible(False)
        self.use_custom_coord_cb.toggled.connect(self.custom_coord_slider.setVisible)

        form.addRow(self.intersection_cb)
        form.addRow("Linewidth:", self.intersection_linewidth)
        form.addRow("Linestyle:", self.intersection_linestyle)
        form.addRow("Alpha:", self.intersection_alpha)
        form.addRow(self.intersection_color_btn)
        form.addRow(self.use_custom_coord_cb)
        form.addRow(self.custom_coord_slider)

        return box

    def _on_outline_alpha_change(self, alpha) -> None:
        alpha /= 100
        for plane, artist in self._parent.structure_outlines[self.struct_id].items():
            color = artist.get_edgecolor()
            artist.set_edgecolor((*color[:3], alpha))
        self.alpha = alpha
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_outline_fill_alpha_change(self, alpha) -> None:
        alpha /= 100
        for plane, artist in self._parent.structure_outlines[self.struct_id].items():
            color = artist.get_facecolor()
            artist.set_facecolor((*color[:3], alpha))
        self.alpha = alpha
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _pick_outline_color(self):
        color = QColorDialog.getColor(self.outline_color_val)
        if color.isValid():
            self.outline_color_val = color
            self.outline_color_btn.setStyleSheet(f"background-color: {color.name()}")
            for plane, artist in self._parent.structure_outlines[self.struct_id].items():
                artist.set_edgecolor((color.redF(), color.greenF(), color.blueF()))
            self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _pick_fill_color(self):
        color = QColorDialog.getColor(self.fill_color_val)
        if color.isValid():
            self.fill_color_val = color
            self.fill_color_btn.setStyleSheet(f"background-color: {color.name()}")
            for plane, artist in self._parent.structure_outlines[self.struct_id].items():
                artist.set_facecolor((color.redF(), color.greenF(), color.blueF()))
            self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _pick_intersection_color(self):
        color = QColorDialog.getColor(self.intersection_color_val)
        if color.isValid():
            self.intersection_color_val = color
            self.intersection_color_btn.setStyleSheet(f"background-color: {color.name()}")
            for _, planes in self._parent.structure_intersections[self.struct_id].items():
                ...