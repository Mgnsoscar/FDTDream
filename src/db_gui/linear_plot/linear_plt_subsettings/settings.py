from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel
from ...widgets import CollapsibleGroupBox
from .artists_settings import LinearArtistSettings
from .text_settings import EditableTextSettings, TextSetting, TicksSetting, GridSetting
from ..dataset import Dataset
from .legend_settings import LegendSettings
from .plot_limits import PlotLimitsSettings
from typing import List


class LinearPlotSettings(QWidget):

    def __init__(self, parent: QWidget, dataset: Dataset) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        self.dataset = dataset
        self.setLayout(layout)

        self.title = EditableTextSettings("Title:", dataset, dataset.title)
        self.xlabel = EditableTextSettings("X Label:", dataset, dataset.xlabel)
        self.ylabel = EditableTextSettings("Y Label:", dataset, dataset.ylabel)
        self.xticks = TicksSetting("X Ticks:", dataset, dataset.xaxis)
        self.yticks = TicksSetting("Y Ticks:", dataset, dataset.yaxis)
        self.plot_limits = PlotLimitsSettings("Plot limits:", dataset, dataset.ax)
        self.legend = LegendSettings("Legend:", dataset, dataset.ax)
        self.grid = GridSetting("Grid:", dataset, dataset.ax)
        self.artist = CollapsibleGroupBox("Artists:")
        self.artist.checkbox.setVisible(False)
        self._init_aspect_ratio_selector()

        for artist in dataset.ax.lines:
            artist_settings = LinearArtistSettings(artist.get_label(), dataset, artist)  # type: ignore
            artist_settings.moved_up.connect(self.on_move_artist_up)
            artist_settings.moved_down.connect(self.on_move_artist_down)
            artist_settings.remove_artist.connect(self.on_artist_removed)
            self.artist.addRow("", artist_settings)

        # Add widgets to layout
        layout.addWidget(self.title)
        layout.addWidget(self.xlabel)
        layout.addWidget(self.ylabel)
        layout.addWidget(self.xticks)
        layout.addWidget(self.yticks)
        layout.addWidget(self.legend)
        layout.addWidget(self.grid)
        layout.addWidget(self.plot_limits)
        layout.addWidget(QLabel("Aspect ratio:"))
        layout.addWidget(self.aspect_box)

        layout.addWidget(self.artist)
        layout.addStretch()

    def on_move_artist_up(self, current_idx: int):
        if current_idx <= 0:
            return

        artists = [line for line in self.dataset.ax.lines]
        artists[current_idx - 1], artists[current_idx] = (
            artists[current_idx],
            artists[current_idx - 1],
        )
        for artist in artists:
            artist.remove()
        for artist in artists:
            self.dataset.ax.add_line(artist)

        layout = self.artist.content_area.layout()
        all_widgets = [layout.itemAt(i).widget() for i in range(layout.count())]

        all_widgets[current_idx - 1], all_widgets[current_idx] = (
            all_widgets[current_idx],
            all_widgets[current_idx - 1],
        )

        self.rebuild_artist_widgets(all_widgets)
        self.dataset.update_legend()
        self.dataset.redraw()

    def on_move_artist_down(self, current_idx: int):
        artists = [line for line in self.dataset.ax.lines]
        if current_idx >= len(artists) - 1:
            return

        # --- 1. Swap artist order in Axes
        artists[current_idx], artists[current_idx + 1] = (
            artists[current_idx + 1],
            artists[current_idx],
        )
        for artist in artists:
            artist.remove()
        for artist in artists:
            self.dataset.ax.add_line(artist)

        # --- 2. Swap widgets
        layout = self.artist.content_area.layout()
        all_widgets = [layout.itemAt(i).widget() for i in range(layout.count())]
        all_widgets[current_idx], all_widgets[current_idx + 1] = (
            all_widgets[current_idx + 1],
            all_widgets[current_idx],
        )

        # --- 3. Rebuild layout
        self.rebuild_artist_widgets(all_widgets)
        self.dataset.update_legend()
        self.dataset.redraw()

    def rebuild_artist_widgets(self, new_order: List[LinearArtistSettings]) -> None:
        layout = self.artist.content_area.layout()

        # Remove all widgets from layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if isinstance(widget, LinearArtistSettings):
                widget.setParent(None)  # Detach safely

        # Re-add all widgets in new order
        for widget in new_order:
            layout.addWidget(widget)

    def on_artist_removed(self):
        # Get the sender widget (the LinearArtistSettings instance)
        artist_settings = self.sender()
        if not isinstance(artist_settings, LinearArtistSettings):
            return

        artist = artist_settings.artist

        # 1. Remove artist from Axes
        if artist in self.dataset.ax.lines:
            artist.remove()

        # 3. Remove the settings row from the CollapsibleGroupBox
        self.artist.remove_row(artist_settings)
        self.reset_after_artist_removal()

        # 4. Redraw
        self.dataset.update_legend()
        self.dataset.relim()
        self.dataset.redraw()

    def reset_after_artist_removal(self) -> None:
        layout = self.artist.content_area.layout()

        # Update the normalization boxes of all artists.
        for idx in range(layout.count()):
            item = layout.itemAt(idx)
            widget = item.widget()
            if isinstance(widget, LinearArtistSettings):
                widget.populate_normalize_box()

    def _init_aspect_ratio_selector(self) -> None:
        self.aspect_box = QComboBox()
        self.aspect_box.wheelEvent = lambda event: None

        # Supported options in display format
        self.aspect_options = [
            "Auto",
            "1:1",
            "16:9",
            "4:3",
            "3:2",
            "2:1",
            "3:1",
        ]
        self.aspect_box.addItems(self.aspect_options)

        # Determine current box aspect ratio
        current_box_aspect = self.dataset.ax.get_box_aspect()  # Returns float or None
        if current_box_aspect is None:
            self.aspect_box.setCurrentText("Auto")
        else:
            # Try to find the closest ratio match
            def ratio_value(text: str) -> float:
                w, h = map(float, text.split(":"))
                return h / w

            best_match = min(
                self.aspect_options[1:],  # Skip 'Auto'
                key=lambda opt: abs(ratio_value(opt) - current_box_aspect),
            )
            self.aspect_box.setCurrentText(best_match)

        self.aspect_box.currentTextChanged.connect(self.on_aspect_ratio_change)  # type: ignore

    def on_aspect_ratio_change(self, text: str) -> None:
        self.dataset.set_aspect_ratio(text)
        self.dataset.redraw()