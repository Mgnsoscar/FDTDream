from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QPushButton, QGroupBox, QLabel,
    QHBoxLayout, QCheckBox, QScrollArea, QFrame, QFormLayout, QSizePolicy,
    QComboBox, QSpinBox, QColorDialog, QSlider, QToolBox
)
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from .fieldplot_tab_interface import FieldPlotTabInterface
from trimesh import Trimesh
from typing import Dict, List
from ..fdtdream.database.db import StructureModel
from .widgets import CollapsibleWidget, LabeledSlider, LabeledDropdown, CollapsibleGroupBox
import numpy as np


class Structure(CollapsibleGroupBox):

    name: str
    id_int: int


class StructureSettings(QWidget):
    def __init__(self, parent: FieldPlotTabInterface):
        super().__init__()
        self._parent = parent

        self.section_widgets: List[StructureSection] = []
        self.name_to_struct: Dict[str, StructureModel] = {}  # Map name -> structure object
        self.id_to_strcut: Dict[int, StructureModel] = {}

        self.init_ui()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding))

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
                self.id_to_strcut[struct.id] = struct
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

        # Compute projections and intersections
        if struct.id not in self._parent.structure_outlines or struct.id not in self._parent.structure_intersections:
            projections, intersections = struct.get_projections_and_intersections(self._parent.monitor.x,
                                                                                  self._parent.monitor.y,
                                                                                  self._parent.monitor.z)
            if struct.id not in self._parent.structure_outlines:
                self._parent.structure_outlines[struct.id] = projections
            if struct.id not in self._parent.structure_intersections:
                self._parent.structure_intersections[struct.id] = intersections

        section = StructureSection(self._parent, struct)
        section.remove_requested.connect(lambda: self._remove_section(section, name))
        self.section_layout.addWidget(section)
        self.section_widgets.append(section)

    def _remove_section(self, section_widget, name: str = "", noadd: bool = False):
        self.section_layout.removeWidget(section_widget)
        section_widget.deleteLater()
        self.section_widgets.remove(section_widget)

        if not noadd:
            self.list_widget.addItem(name)


class StructureSection(CollapsibleGroupBox):

    struct: StructureModel
    _parent: FieldPlotTabInterface

    # region Constants
    ALPHA_SCALE = 100
    LINEWIDTH_SCALE = 100
    # endregion

    def __init__(self, top: FieldPlotTabInterface, struct: StructureModel) -> None:
        super().__init__(f"{struct.name} (ID: {struct.id})")

        self.struct = struct
        self._parent = top

        self.struct = struct

        self.layout = QVBoxLayout(self)

        # Inner collapsible settings
        self.projection_box = self._create_projection_group()
        self.intersection_box = self._create_intersection_group()

        self.layout.addWidget(self.projection_box)
        self.layout.addWidget(self.intersection_box)

        self._on_structure_checkbox_clicked()

        # Update the visuals on all artists:
        self._reapply_visuals()

        self._parent.plot_structures_checkbox.clicked.connect(self._on_structure_checkbox_clicked)
        self._parent.plot_type_combo.dropdown.currentTextChanged.connect(self._on_plot_type_changed)
        self._parent.x_slider.slider.valueChanged.connect(self._on_coordinate_change)
        self._parent.y_slider.slider.valueChanged.connect(self._on_coordinate_change)
        self._parent.z_slider.slider.valueChanged.connect(self._on_coordinate_change)

    def _create_projection_group(self) -> QGroupBox:
        projection_box = CollapsibleGroupBox("Projection")
        projection_box.layout().setSpacing(0)
        projection_box.checkbox.clicked.connect(self._on_projection_checked)
        form = QFormLayout(projection_box)
        form.addWidget(self._create_projection_settings())

        return projection_box

    def _create_intersection_group(self) -> QGroupBox:
        box = QGroupBox("Intersection")
        box.layout().setSpacing(0)
        box.setCheckable(True)
        box.setChecked(False)
        box.clicked.connect(self._on_intersection_checked)
        form = QFormLayout(box)

        form.addWidget(self._create_intersection_settings())

        return box

    def _create_projection_settings(self) -> QWidget:

        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # region Outline subsection
        outline_box = CollapsibleGroupBox("Outline Settings")
        outline_box.layout().setSpacing(0)

        self.projection_outline_linewidth_slider = LabeledSlider(self, "Linewidth", 1, 1000)
        self.projection_outline_linewidth_slider.slider.setValue(100)
        self.projection_outline_linewidth_slider.set_slider_callback(self._on_prjctn_linewidth_change)

        self.projection_outline_linestyle_dropdown = LabeledDropdown(self, "Linestyle")
        self.projection_outline_linestyle_dropdown.set_dropdown_items(["solid", "dashed", "dotted", "dashdot"])
        self.projection_outline_linestyle_dropdown.set_dropdown_callback(self._on_prjctn_linestyle_change)

        self.projection_outline_color_btn = QPushButton("Pick Outline Color")
        self.projection_outline_color_val = QColor(0, 0, 0)
        self.projection_outline_color_btn.clicked.connect(self._get_prjctn_outline_color)

        self.projection_outline_alpha_slider = LabeledSlider(self, "Alpha", 0, 100)
        self.projection_outline_alpha_slider.slider.setValue(30)
        self.projection_outline_alpha_slider.set_slider_callback(self._on_prjctn_outline_color_change)

        outline_box.addRow("", self.projection_outline_linewidth_slider)
        outline_box.addRow("", self.projection_outline_linestyle_dropdown)
        outline_box.addRow("", self.projection_outline_color_btn)
        outline_box.addRow("", self.projection_outline_alpha_slider)
        # endregion

        # --- Fill Subsection ---
        fill_box = CollapsibleGroupBox("Fill Settings")
        fill_box.layout().setSpacing(0)

        self.projection_fill_color_btn = QPushButton("Pick Fill Color")
        self.projection_fill_color_val = QColor(255, 0, 0)
        self.projection_fill_color_btn.clicked.connect(self._get_prjctn_fill_color)

        self.projection_fill_alpha_slider = LabeledSlider(self, "Alpha", 0, 100)
        self.projection_fill_alpha_slider.slider.setValue(30)
        self.projection_fill_alpha_slider.set_slider_callback(self._on_prjctn_fill_color_change)

        fill_box.addRow("", self.projection_fill_color_btn)
        fill_box.addRow("", self.projection_fill_alpha_slider)

        # --- Add both to outer_box ---
        layout.addWidget(outline_box)
        layout.addWidget(fill_box)

        return widget

    def _create_intersection_settings(self) -> QWidget:

        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # region Outline subsection
        outline_box = CollapsibleGroupBox("Outline Settings")
        outline_box.layout().setSpacing(0)

        self.intersection_outline_linewidth_slider = LabeledSlider(self, "Linewidth", 1, 1000)
        self.intersection_outline_linewidth_slider.slider.setValue(100)
        self.intersection_outline_linewidth_slider.set_slider_callback(self._on_intrsctn_linewidth_change)

        self.intersection_outline_linestyle_dropdown = LabeledDropdown(self, "Linestyle")
        self.intersection_outline_linestyle_dropdown.set_dropdown_items(["solid", "dashed", "dotted", "dashdot"])
        self.intersection_outline_linestyle_dropdown.dropdown.setCurrentIndex(
            self.intersection_outline_linestyle_dropdown.dropdown.findText("dashed")
        )
        self.intersection_outline_linestyle_dropdown.set_dropdown_callback(self._on_intrsctn_linestyle_change)

        self.intersection_outline_color_btn = QPushButton("Pick Outline Color")
        self.intersection_outline_color_val = QColor(0, 0, 0)
        self.intersection_outline_color_btn.clicked.connect(self._get_intrsctn_outline_color)

        self.intersection_outline_alpha_slider = LabeledSlider(self, "Alpha", 0, 100)
        self.intersection_outline_alpha_slider.slider.setValue(30)
        self.intersection_outline_alpha_slider.set_slider_callback(self._on_intrsctn_outline_color_change)

        outline_box.addRow("", self.intersection_outline_linewidth_slider)
        outline_box.addRow("", self.intersection_outline_linestyle_dropdown)
        outline_box.addRow("", self.intersection_outline_color_btn)
        outline_box.addRow("", self.intersection_outline_alpha_slider)
        # endregion

        # --- Fill Subsection ---
        fill_box = CollapsibleGroupBox("Fill Settings")
        fill_box.layout().setSpacing(0)

        self.intersection_fill_color_btn = QPushButton("Pick Fill Color")
        self.intersection_fill_color_val = QColor(0, 0, 0)
        self.intersection_fill_color_btn.clicked.connect(self._get_intrsctn_fill_color)

        self.intersection_fill_alpha_slider = LabeledSlider(self, "Alpha", 0, 100)
        self.intersection_fill_alpha_slider.slider.setValue(30)
        self.intersection_fill_alpha_slider.set_slider_callback(self._on_intrsctn_fill_color_change)

        fill_box.addRow("", self.intersection_fill_color_btn)
        fill_box.addRow("", self.intersection_fill_alpha_slider)

        layout.addWidget(outline_box)
        layout.addWidget(fill_box)

        return widget

    # region Properties
    @property
    def intersection_outline_alpha(self) -> float:
        return self.intersection_outline_alpha_slider.get_value() / self.ALPHA_SCALE

    @property
    def intersection_fill_alpha(self) -> float:
        return self.intersection_fill_alpha_slider.get_value() / self.ALPHA_SCALE

    @property
    def intersection_outline_width(self) -> float:
        return self.intersection_outline_linewidth_slider.get_value() / self.LINEWIDTH_SCALE

    @property
    def intersection_outline_style(self) -> str:
        return self.intersection_outline_linestyle_dropdown.get_selected()

    @property
    def intersection_outline_color(self) -> tuple:
        color = self.intersection_outline_color_btn.palette().button().color()
        return color.redF(), color.greenF(), color.blueF()

    @property
    def intersection_fill_color(self) -> tuple:
        color = self.intersection_fill_color_btn.palette().button().color()
        return color.redF(), color.greenF(), color.blueF()

    @property
    def projection_outline_alpha(self) -> float:
        return self.projection_outline_alpha_slider.get_value() / self.ALPHA_SCALE

    @property
    def projection_fill_alpha(self) -> float:
        return self.projection_fill_alpha_slider.get_value() / self.ALPHA_SCALE

    @property
    def projection_outline_width(self) -> float:
        return self.projection_outline_linewidth_slider.get_value() / self.LINEWIDTH_SCALE

    @property
    def projection_outline_style(self) -> str:
        return self.projection_outline_linestyle_dropdown.get_selected()

    @property
    def projection_outline_color(self) -> tuple:
        color = self.projection_outline_color_btn.palette().button().color()
        return color.redF(), color.greenF(), color.blueF()

    @property
    def projection_fill_color(self) -> tuple:
        color = self.projection_fill_color_btn.palette().button().color()
        return color.redF(), color.greenF(), color.blueF()
    # endregion

    # region Callbacks
    def _on_prjctn_outline_color_change(self) -> None:
        color = self.projection_outline_color
        alpha = self.projection_outline_alpha
        for _, artist in self._parent.structure_outlines[self.struct.id].items():
            artist.set_edgecolor((*color[:3], alpha))
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_prjctn_fill_color_change(self) -> None:
        color = self.projection_fill_color
        alpha = self.projection_fill_alpha
        for _, artist in self._parent.structure_outlines[self.struct.id].items():
            artist.set_facecolor((*color[:3], alpha))
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_intrsctn_outline_color_change(self) -> None:
        color = self.intersection_outline_color
        alpha = self.intersection_outline_alpha
        for plane, artists in self._parent.structure_intersections[self.struct.id].items():
            for artist in artists:
                if artist:
                    artist.set_edgecolor((*color[:3], alpha))
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_intrsctn_fill_color_change(self) -> None:
        color = self.intersection_fill_color
        alpha = self.intersection_fill_alpha
        for plane, artists in self._parent.structure_intersections[self.struct.id].items():
            for artist in artists:
                if artist:
                    artist.set_facecolor((*color[:3], alpha))
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_prjctn_linewidth_change(self) -> None:
        width = self.projection_outline_width
        for plane, artist in self._parent.structure_outlines[self.struct.id].items():
            artist.set_linewidth(width)
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_prjctn_linestyle_change(self) -> None:
        style = self.projection_outline_style
        for plane, artist in self._parent.structure_outlines[self.struct.id].items():
            artist.set_linestyle(style)
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_intrsctn_linewidth_change(self) -> None:
        width = self.intersection_outline_width
        for _, artists in self._parent.structure_intersections[self.struct.id].items():
            for artist in artists:
                if artist:
                    artist.set_linewidth(width)
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_intrsctn_linestyle_change(self) -> None:
        style = self.intersection_outline_style
        for _, artists in self._parent.structure_intersections[self.struct.id].items():
            for artist in artists:
                if artist:
                    artist.set_linestyle(style)
        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_structure_checkbox_clicked(self) -> None:
        self._on_projection_checked(
            self.projection_box.isChecked()
            and self.checkbox.isChecked()
            and self._parent.plot_structures_checkbox.isChecked())
        self._on_intersection_checked(
            self.intersection_box.isChecked()
            and self.checkbox.isChecked()
            and self._parent.plot_structures_checkbox.isChecked())

    def _on_projection_checked(self, active: bool) -> None:

        plot_type = self._parent.plot_type
        if "Plane" not in plot_type:
            return

        # Remove the artist from the ax if non active
        if not active:
            if self._parent.structure_outlines[self.struct.id][plot_type].axes:
                self._parent.structure_outlines[self.struct.id][plot_type].remove()
        else:
            self._parent.ax.add_artist(self._parent.structure_outlines[self.struct.id][plot_type])

        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _on_intersection_checked(self, active: bool) -> None:

        plot_type = self._parent.plot_type
        if "Plane" not in plot_type:
            return

        # Remove the artist from the ax if non active
        if not active:
            for artist in self._parent.structure_intersections[self.struct.id][plot_type]:
                if artist and artist.axes:
                    artist.remove()
            return None

        coordinate_indices = [idx for idx in self._parent.get_field_idx()[:3] if type(idx) is int]
        if len(coordinate_indices) > 1:
            raise ValueError(f"Something wierd has happened here. Expected single idx, got multiple.")
        idx = coordinate_indices[0]

        artist = self._parent.structure_intersections[self.struct.id][plot_type][idx]
        if artist:
            self._parent.ax.add_artist(artist)

        self._parent.draw_idle_timer.start(self._parent.CALLBACK_DELAY)

    def _get_intrsctn_fill_color(self) -> None:
        self._on_color_change(self.intersection_fill_color_btn)
        self._on_intrsctn_fill_color_change()

    def _get_intrsctn_outline_color(self) -> None:
        self._on_color_change(self.intersection_outline_color_btn)
        self._on_intrsctn_outline_color_change()

    def _get_prjctn_fill_color(self) -> None:
        self._on_color_change(self.projection_fill_color_btn)
        self._on_intrsctn_fill_color_change()

    def _get_prjctn_outline_color(self) -> None:
        self._on_color_change(self.projection_outline_color_btn)
        self._on_prjctn_outline_color_change()

    def _on_plot_type_changed(self) -> None:
        self._on_structure_checkbox_clicked()

    def _on_coordinate_change(self) -> None:
        plot_type = self._parent.plot_type
        if "Plane" not in plot_type:
            return

        active = (self.checkbox.isChecked() and self.intersection_box.isChecked()
                  and self._parent.plot_structures_checkbox.isChecked())

        for artist in self._parent.structure_intersections[self.struct.id][plot_type]:
            if artist and artist.axes:
                artist.remove()

        self._on_intersection_checked(active)

    def on_monitor_changed(self) -> None:

        struct = self.struct
        # Compute projections and intersections
        projections, intersections = struct.get_projections_and_intersections(self._parent.monitor.x,
                                                                              self._parent.monitor.y,
                                                                              self._parent.monitor.z)
        self._parent.structure_outlines[struct.id] = projections
        self._parent.structure_intersections[struct.id] = intersections
        self._reapply_visuals()
        self._on_structure_checkbox_clicked()

    @staticmethod
    def _on_color_change(button: QPushButton) -> None:
        color = QColorDialog.getColor()
        if not color.isValid():
            return

        # Update the button color.
        button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: {'black' if color.lightness() > 128 else 'white'};
                }}
            """)
    # endregion

    def _reapply_visuals(self):
        self._on_prjctn_fill_color_change()
        self._on_prjctn_outline_color_change()
        self._on_prjctn_linewidth_change()
        self._on_prjctn_linestyle_change()
        self._on_intrsctn_fill_color_change()
        self._on_intrsctn_outline_color_change()
        self._on_intrsctn_linewidth_change()
        self._on_intrsctn_linestyle_change()