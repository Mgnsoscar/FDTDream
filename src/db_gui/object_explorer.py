from PyQt6.QtWidgets import (
    QWidget, QTreeView, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QSplitter, QLabel, QFrame
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal
from .top_level import TopLevel
from typing import Tuple


class ObjectExplorer(QWidget):

    # region Class Body
    top: TopLevel
    monitor_selected = pyqtSignal(int, int)
    simulation_selected = pyqtSignal(int)
    splitter: QSplitter
    tree: QTreeView
    sim_param_viewer: QTableWidget
    monitor_param_viewer: QTableWidget
    # endregion

    def __init__(self, parent: TopLevel):
        super().__init__(parent)

        self.top = parent

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0)

        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self.splitter)

        # Tree view (hierarchical object list)
        tree_wrapper = QWidget(self)
        tree_wrapper_layout = QVBoxLayout()
        tree_wrapper_layout.setContentsMargins(0, 0, 0, 5)
        tree_wrapper.setLayout(tree_wrapper_layout)
        self.tree = QTreeView()
        self.tree.setHeaderHidden(True)
        tree_wrapper_layout.addWidget(self.tree)
        self.splitter.addWidget(tree_wrapper)

        # Simulation Parameters Group
        sim_param_group = QFrame()
        sim_param_layout = QVBoxLayout(sim_param_group)
        sim_param_layout.setContentsMargins(0, 0, 0, 5)
        sim_param_label = QLabel("Simulation Parameters")
        sim_param_label.setStyleSheet("color: white; font-weight: bold; padding: 4px;")
        sim_param_layout.addWidget(sim_param_label)

        self.sim_param_viewer = QTableWidget()
        self.sim_param_viewer.setColumnCount(2)
        self.sim_param_viewer.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.sim_param_viewer.verticalHeader().setVisible(False)
        self.sim_param_viewer.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        sim_param_layout.addWidget(self.sim_param_viewer)

        self.splitter.addWidget(sim_param_group)

        # Monitor Parameters Group
        monitor_param_group = QFrame()
        monitor_param_layout = QVBoxLayout(monitor_param_group)
        monitor_param_layout.setContentsMargins(0, 0, 0, 5)
        monitor_param_label = QLabel("Monitor Parameters")
        monitor_param_label.setStyleSheet("color: white; font-weight: bold; padding: 4px;")
        monitor_param_layout.addWidget(monitor_param_label)

        self.monitor_param_viewer = QTableWidget()
        self.monitor_param_viewer.setColumnCount(2)
        self.monitor_param_viewer.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.monitor_param_viewer.verticalHeader().setVisible(False)
        self.monitor_param_viewer.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        monitor_param_layout.addWidget(self.monitor_param_viewer)

        self.splitter.addWidget(monitor_param_group)

        # Size preferences

        self._populate_model()
        self.tree.selectionModel().selectionChanged.connect(self._on_selection_changed)

        header = self.sim_param_viewer.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)

        header = self.monitor_param_viewer.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)

    def _populate_model(self):
        model = QStandardItemModel()
        root = model.invisibleRootItem()

        # Fetch all categories
        categories = self.top.db_handler.get_all_categories()
        for category in categories:

            # Create item for the category and make it non-editable.
            cat_item = QStandardItem(category)
            cat_item.setEditable(False)
            cat_item.setData(("category", category), Qt.ItemDataRole.UserRole)

            # Create item for each simulation. Map the simulation id to each item.
            simulations = self.top.db_handler.get_simulations_by_category(category)
            for sim_id, sim_name in simulations:
                sim_item = QStandardItem(sim_name)
                sim_item.setEditable(False)
                sim_item.setData(("simulation", sim_id), Qt.ItemDataRole.UserRole)

                # Create item for each monitor in the simulation. Map monitor id to each item.
                monitors = self.top.db_handler.get_monitors_for_simulation(sim_id)
                for mon_id, mon_name in monitors:
                    monitor_item = QStandardItem(mon_name)
                    monitor_item.setEditable(False)
                    monitor_item.setData(("monitor", mon_id), Qt.ItemDataRole.UserRole)

                    # Add monitor to the simulation branch.
                    sim_item.appendRow(monitor_item)

                # Add simulation item to category branch.
                cat_item.appendRow(sim_item)

            # Add the category branch to the root and assign the model to the tree.
            root.appendRow(cat_item)
            self.tree.setModel(model)

    def _on_selection_changed(self, selected, deselected):
        index = self.tree.currentIndex()
        if not index.isValid():
            return

        item = self.tree.model().itemFromIndex(index)
        data = item.data(Qt.ItemDataRole.UserRole)

        if not isinstance(data, tuple) or len(data) != 2:
            return

        dtype, val = data

        if dtype == "monitor":

            # Fetch the id of the parent simulation:
            sim_index = index.parent()
            sim_item = self.tree.model().itemFromIndex(sim_index)
            sim_data = sim_item.data(Qt.ItemDataRole.UserRole)
            _, sim_id = sim_data

            # Mark the monitor and simulation as selected in the top level.
            self.top.selected_monitor = val
            self.top.selected_simulation = sim_id

            # Fetch the monitor and simulation parameters and update the tables.
            simulation_parameters = self.top.db_handler.get_simulation_parameters(sim_id)
            monitor_parameters = self.top.db_handler.get_monitor_parameters(val)
            self._populate_sim_params(simulation_parameters)
            self._populate_monitor_params(monitor_parameters)

            # Make the widget emit a signal with the selected simulation and monitor id's
            self.monitor_selected.emit(sim_id, val)  # type: ignore

        elif dtype == "simulation":

            simulation_parameters = self.top.db_handler.get_simulation_parameters(val)

            # Update the selected simulation and monitor.
            if self.top.selected_simulation != val:
                self.top.selected_monitor = None

            #  Clear the monitor parameter table and populate the simulation parameter table
            self._populate_monitor_params({})
            self._populate_sim_params(simulation_parameters)

            self.simulation_selected.emit(val)  # type: ignore

        elif dtype == "category":
            # Clear both parameter views
            self._populate_sim_params({})
            self._populate_monitor_params({})

    def _populate_sim_params(self, params: dict):
        self.sim_param_viewer.setRowCount(len(params))
        for row, (key, value) in enumerate(params.items()):
            self.sim_param_viewer.setItem(row, 0, QTableWidgetItem(str(key)))
            self.sim_param_viewer.setItem(row, 1, QTableWidgetItem(str(value)))

    def _populate_monitor_params(self, params: dict):
        self.monitor_param_viewer.setRowCount(len(params))
        for row, (key, value) in enumerate(params.items()):
            self.monitor_param_viewer.setItem(row, 0, QTableWidgetItem(str(key)))
            self.monitor_param_viewer.setItem(row, 1, QTableWidgetItem(str(value)))
