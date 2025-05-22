from typing import TypedDict, Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from PyQt6.QtGui import QColor
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.axis import Axis, XAxis, YAxis
from matplotlib.text import Text
from matplotlib.figure import Figure
from .ScalableLine2D import ScalableLine2D


class Dataset:

    # region Defaults
    LEGEND_DEFAULTS = {
        'enabled': True,
        'loc': 'best',
        'frameon': True,
        'framealpha': 0.8,
        'fancybox': True,
        'edgecolor': 'black',
        'facecolor': 'white',
        'prop': {"family": 'cambria', "size": 18},
        'borderpad': 0.5,
    }
    AX_DEFAULTS = {"aspect_ratio": "1:1", "xlim": (None, None), "ylim": (None, None)}
    TITLE_DEFAULT = {"text": "", "fontsize": 40, "fontname": "cambria", "color": QColor("black")}
    AXIS_LABEL_DEFAULT = {"text": "", "fontsize": 30, "fontname": "cambria", "color": QColor("black")}
    TICK_LABELS_DEFAUL = {"labelsize": 20, "labelfontfamily": "cambria", "labelcolor": QColor("black"),
                          "labelrotation": 0, "labelbottom": True}
    GRID_DEFAULTS = {"gridOn": True, "grid_alpha": 0.3, "grid_color": QColor("black"),
                     "grid_linewidth": 0.5}
    # endregion

    # region Variables
    name: str
    fig: Figure
    ax: Axes
    xaxis: XAxis
    yaxis: YAxis
    xlabel: Text
    ylabel: Text
    title: Text
    legend_params: dict
    ylim: Tuple[Optional[float], Optional[float]]

    # endregion

    def __init__(self, name: str, fig: Figure, set_visible: bool = True) -> None:

        # Store the name and figure
        self.name = name
        self.fig = fig
        self.legend_params = self.LEGEND_DEFAULTS.copy()

        # Create new ax and set visibility
        self.ax = fig.add_subplot(111)
        self.ax.set_visible(set_visible)
        self.xlim = self.AX_DEFAULTS.get("xlim")
        self.ylim = self.AX_DEFAULTS.get("ylim")
        self.ax.set_xlim(left=self.xlim[0], right=self.xlim[1])
        self.ax.set_ylim(bottom=self.ylim[0], top=self.ylim[1])

        # Create title
        self.title = self.ax.set_title("")
        self.apply_defaults(self.title, self.TITLE_DEFAULT)

        # Create references to the x and y axis
        self.xaxis = self.ax.xaxis
        self.yaxis = self.ax.yaxis

        # Create X and Y Labels
        self.xlabel, self.ylabel = self.ax.xaxis.get_label(), self.ax.yaxis.get_label()
        self.apply_defaults(self.xlabel, self.AXIS_LABEL_DEFAULT)
        self.apply_defaults(self.ylabel, self.AXIS_LABEL_DEFAULT)

        # Set tick defaults
        self.apply_tick_defaults(self.ax.xaxis, self.TICK_LABELS_DEFAUL)
        self.apply_tick_defaults(self.ax.yaxis, self.TICK_LABELS_DEFAUL)

        # Apply grid defaults
        self.apply_grid_defaults(self.GRID_DEFAULTS)

        # Apply default aspect ratio
        self.set_aspect_ratio(self.AX_DEFAULTS.get("aspect_ratio"))

    @staticmethod
    def apply_defaults(artist, defaults: Dict[str, Any]) -> None:
        for param, value in defaults.items():
            setter = getattr(artist, f"set_{param}")
            if param == "color":
                value: QColor
                setter((value.redF(), value.greenF(), value.blueF()))
            else:
                setter(value)

    @staticmethod
    def apply_tick_defaults(axis: Axis, defaults: Dict[str, Any]) -> None:
        copied = defaults.copy()
        color: Optional[QColor] = copied.pop("labelcolor", None)
        if color:
            copied["labelcolor"] = (color.redF(), color.greenF(), color.blueF())
        axis.set_tick_params("both", **copied)

    def apply_grid_defaults(self, defaults: Dict[str, Any]) -> None:
        copied = defaults.copy()
        color: Optional[QColor] = copied.pop("grid_color", None)
        if color:
            copied["grid_color"] = (color.redF(), color.greenF(), color.blueF())
        self.ax.tick_params("both", **copied)

    def set_aspect_ratio(self, ratio: str) -> None:
        if ratio == "Auto":
            self.ax.set_box_aspect(None)  # Remove any fixed aspect
        else:
            try:
                w, h = map(float, ratio.split(":"))
                self.ax.set_box_aspect(h / w)  # Height relative to width!
            except Exception:
                self.ax.set_box_aspect(None)

    def detatch_artists_from_dataset(self) -> List[ScalableLine2D]:
        artists = [line for line in self.ax.lines]
        for artist in artists:
            artist.remove()
        return artists

    def clear_title_and_labels(self) -> None:
        self.title.set_text("")
        self.xlabel.set_text("")
        self.ylabel.set_text("")

    def set_ylim(self, bottom: Optional[float], top: Optional[float]) -> None:
        # Filter visible artists
        all_lines = list(self.ax.lines)
        visible_lines = [line for line in all_lines if line.get_visible()]

        # Temporarily remove all artists and add only visible ones
        for artist in self.ax.lines[:]:
            artist.remove()
        for artist in visible_lines:
            self.ax.add_artist(artist)

        self.ax.set_autoscaley_on(True)
        self.ylim = (bottom, top)

        # Force autoscale to get correct dynamic limit
        self.ax.relim()
        self.ax.autoscale_view()

        if bottom is not None and top is not None:
            self.ax.set_ylim(bottom, top)
        elif bottom is not None:
            # Use autoscaled top
            _, auto_top = self.ax.get_ylim()
            self.ax.set_ylim(bottom, auto_top)
        elif top is not None:
            # Use autoscaled bottom
            auto_bottom, _ = self.ax.get_ylim()
            self.ax.set_ylim(auto_bottom, top)
        # else: already autoscaled

        # Restore all original artists
        for artist in self.ax.lines[:]:
            artist.remove()
        for artist in all_lines:
            self.ax.add_artist(artist)

    def set_xlim(self, left: Optional[float], right: Optional[float]) -> None:
        # Filter visible artists
        all_lines = list(self.ax.lines)
        visible_lines = [line for line in all_lines if line.get_visible()]

        # Temporarily remove all artists and add only visible ones
        for artist in self.ax.lines[:]:
            artist.remove()
        for artist in visible_lines:
            self.ax.add_artist(artist)

        self.ax.set_autoscalex_on(True)
        self.xlim = (left, right)

        # Force autoscale to get correct dynamic limits
        self.ax.relim()
        self.ax.autoscale_view()

        if left is not None and right is not None:
            self.ax.set_xlim(left, right)
        elif left is not None:
            _, auto_right = self.ax.get_xlim()
            self.ax.set_xlim(left, auto_right)
        elif right is not None:
            auto_left, _ = self.ax.get_xlim()
            self.ax.set_xlim(auto_left, right)
        # else: already autoscaled

        # Restore all original artists
        for artist in self.ax.lines[:]:
            artist.remove()
        for artist in all_lines:
            self.ax.add_artist(artist)

    def relim(self) -> None:
        # Apply limits
        self.set_ylim(*self.ylim)
        self.set_xlim(*self.xlim)

    def add_artist(self, artist: Artist) -> None:
        artist.set_transform(self.ax.transData)
        self.ax.add_artist(artist)
        self.relim()
        self.update_legend()
        self.redraw()

    def redraw(self) -> None:
        # Anchor the current plot to the center and enforce tight layout.
        self.ax.set_anchor("C")
        self.fig.tight_layout()

        # Redraw contents
        self.fig.canvas.draw_idle()

    def update_legend(self) -> None:
        params = self.legend_params.copy()
        handles, _ = self.ax.get_legend_handles_labels()
        if params.pop("enabled", None) and handles:
            self.ax.legend(**params)
        elif self.ax.legend_:
            self.ax.legend_.set_visible(False)
