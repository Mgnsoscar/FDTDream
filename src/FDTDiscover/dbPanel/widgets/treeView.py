from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, QModelIndex, QPoint, QItemSelectionModel, pyqtSlot, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QTreeView, QAbstractItemView, QMenu
)

from ..signals import dbPanelSignalBus, dbRightClickMenuSignalBus
from ...shared import SignalProtocol


class TreeView(QTreeView):

    customContextMenuRequested: SignalProtocol[QPoint]
    """Existing signal type hinted with the SignalProtocol1."""

    def __init__(self) -> None:
        super().__init__()
        self.setHeaderHidden(True)

        # Enable multiple object selection
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Enable context menu on right click and connect the rightclick event.
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._onRightClick)

        self._connectSignals()

    def _connectSignals(self):
        dbPanelSignalBus.populateTree.connect(self._onSetModel)
        dbRightClickMenuSignalBus.requestContextMenu.connect(self._onContextMenuRequested)

    @pyqtSlot(object)
    def _onSetModel(self, model):
        expanded_ids = self._get_expanded_identifiers()
        self.setModel(model)
        self._connectModelSelectionChanged()
        self._restore_expanded_identifiers(expanded_ids)

    def _get_expanded_identifiers(self, index: QModelIndex = QModelIndex()) -> list[tuple]:
        """Recursively collect stable identifiers for expanded items."""
        identifiers = []
        model = self.model()
        if not model:
            return identifiers

        row_count = model.rowCount(index)
        for row in range(row_count):
            child_index = model.index(row, 0, index)
            if not child_index.isValid():
                continue

            if self.isExpanded(child_index):
                item = model.itemFromIndex(child_index)
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    depth = self._depth(child_index)

                    if depth == 0:
                        key = (data.get("name", ""),)
                    elif depth == 1:
                        key = (data.get("name", ""), id(data.get("dbHandler")))
                    else:
                        key = (data.get("type", ""), data.get("id", None), id(data.get("dbHandler")))

                    identifiers.append(key)

                # Recurse into children
                identifiers.extend(self._get_expanded_identifiers(child_index))

        return identifiers

    def mouseReleaseEvent(self, event):
        """Prevent Qt from selecting the item under the cursor on mouse release after drag."""
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and not self.selectionModel().isSelected(index):
            # Prevent Qt from auto-selecting the hovered item
            event.ignore()
            return
        super().mouseReleaseEvent(event)

    def _restore_expanded_identifiers(self, identifiers: list[tuple], index: QModelIndex = QModelIndex()):
        """Recursively expand rows that match previously stored identifiers."""
        model = self.model()
        if not model:
            return

        row_count = model.rowCount(index)
        for row in range(row_count):
            child_index = model.index(row, 0, index)
            if not child_index.isValid():
                continue

            item = model.itemFromIndex(child_index)
            data = item.data(Qt.ItemDataRole.UserRole)
            if not data:
                continue

            depth = self._depth(child_index)

            if depth == 0:
                key = (data.get("name", ""),)
            elif depth == 1:
                key = (data.get("name", ""), id(data.get("dbHandler")))
            else:
                key = (data.get("type", ""), data.get("id", None), id(data.get("dbHandler")))

            if key in identifiers:
                self.setExpanded(child_index, True)
                self._restore_expanded_identifiers(identifiers, child_index)

    def selectionCommand(self, index: QModelIndex, event=None):
        """Allow selection, but block additive selection across hierarchy levels."""
        if not index.isValid():
            return super().selectionCommand(index, event)

        selected_indexes = self.selectionModel().selectedIndexes()
        selected_row_indexes = [i for i in selected_indexes if i.column() == 0]

        if not selected_row_indexes:
            return super().selectionCommand(index, event)

        # Only restrict if the user is trying to *add* to the current selection
        if event and event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            ref_index = selected_row_indexes[0]
            if self._depth(index) != self._depth(ref_index):
                return QItemSelectionModel.SelectionFlag.NoUpdate  # Block the additive selection

        return super().selectionCommand(index, event)

    @pyqtSlot()
    def _connectModelSelectionChanged(self) -> None:
        """Assigns the selection changed signal from the current model to the selection changed method of this class."""
        try:
            self.selectionModel().selectionChanged.disconnect()  # type: ignore
        except TypeError:
            pass  # Not connected yet
        self.selectionModel().selectionChanged.connect(self._onSelectionChanged)  # type: ignore

    @pyqtSlot()
    def _onSelectionChanged(self):
        QTimer.singleShot(0, self._sanitizeSelection)

    def _sanitizeSelection(self):
        indexes = self.selectionModel().selectedIndexes()
        row_indexes = [idx for idx in indexes if idx.column() == 0]

        if not row_indexes:
            dbPanelSignalBus.nothingSelected.emit()
            return

        row_indexes.sort(key=lambda i: self._depth(i))
        ref_index = row_indexes[0]
        target_depth = self._depth(ref_index)

        valid_indexes = [i for i in row_indexes if self._depth(i) == target_depth]

        if len(valid_indexes) != len(row_indexes):
            self.blockSignals(True)
            self.selectionModel().clearSelection()
            for index in valid_indexes:
                self.selectionModel().select(
                    index,
                    QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
                )
            if valid_indexes:
                self.setCurrentIndex(valid_indexes[0])
            self.blockSignals(False)

        selected_data = []
        for index in valid_indexes:
            item = self.model().itemFromIndex(index)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                selected_data.append(data)

        if selected_data:
            dbPanelSignalBus.objectsSelected.emit(selected_data)
        else:
            dbPanelSignalBus.nothingSelected.emit()

        self.viewport().update()  # <-- Force visual refresh to clear lingering selection

    @pyqtSlot(list, object)
    def _onContextMenuRequested(self, actions: List[QAction], pos: QPoint):
        """Displays a context menu with the provided actions at the provided position."""
        contextMenu = QMenu("Options:", self)
        contextMenu.addActions(actions)
        contextMenu.exec(self.viewport().mapToGlobal(pos))

    @staticmethod
    def _depth(index: QModelIndex) -> int:
        """Returns the depth (level) of the index in the tree."""
        depth = 0
        while index.parent().isValid():
            index = index.parent()
            depth += 1
        return depth

    def _onRightClick(self, pos: QPoint) -> None:
        """Handles the right-click context menu and emits selected items with position."""
        index = self.indexAt(pos)
        if not index.isValid():
            return

        # Check if clicked item is already part of the selection
        selected_indexes = self.selectionModel().selectedIndexes()
        selected_row_indexes = [i for i in selected_indexes if i.column() == 0]

        clicked_row = index.row()
        clicked_parent = index.parent()

        # If clicked item is not in selection, update selection to that row only
        matching_selected = [
            i for i in selected_row_indexes
            if i.row() == clicked_row and i.parent() == clicked_parent
        ]

        if not matching_selected:
            self.blockSignals(True)
            self.selectionModel().clearSelection()
            self.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
            )
            self.setCurrentIndex(index)
            self.blockSignals(False)

            selected_row_indexes = [index]

        # Gather data from all selected row items
        selected_data = []
        for i in selected_row_indexes:
            item = self.model().itemFromIndex(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                selected_data.append(data)

        dbPanelSignalBus.objectsRightClicked.emit(selected_data, pos)
