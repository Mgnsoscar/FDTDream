from __future__ import annotations
from typing import Literal, Unpack, TypedDict, Tuple, List, Union

import matplotlib.pyplot as plt
import numpy as np
import shapely
import trimesh

LINESTYLES = Literal["solid", "dotted", "dashed", "dashdot"]


class ProjectionKwargs(TypedDict, total=False):
    intersection_outline: bool
    intersection_linestyle: LINESTYLES
    intersection_alpha: float
    intersection_width: bool
    intersection_color: str

    fill_projection: bool
    fill_alpha: float
    fill_color: str

    projection_outline: bool
    outline_linestyle: LINESTYLES
    outline_alpha: float
    outline_color: str
    outline_width: float


class PlottedStructure:

    _outline_artists: List[plt.Line2D]
    _fill_artists: List[plt.Polygon]
    _intersection_artists: List[plt.Line2D]  # List for storing intersection artists
    _parent_structure: PlottedStructure

    def __init__(self, name: str, mesh: trimesh.Trimesh, parent_structure: PlottedStructure = None,
                 **kwargs: Unpack[ProjectionKwargs]):
        """
        Initializes the PlottedStructure object.

        Args:
        - ax: The Matplotlib Axes object where the structure will be plotted.
        - name: Name of the structure.
        - mesh: A trimesh object representing the structure's mesh.
        - **kwargs: Additional optional keyword arguments for customizing the plot.
        """
        self._name = name
        self._mesh = mesh
        self._parent_structure = parent_structure
        self._last_plane = None
        self._last_plane_origin = None

        # Optional plotting attributes (Intersection)
        self._intersection_alpha = kwargs.get("intersection_alpha", 1)
        self._intersection_color = kwargs.get("intersection_color", "black")
        self._intersection_linestyle = kwargs.get("intersection_linestyle", "dashed")  # Dashed line by default
        self._intersection_width = kwargs.get("intersection_width", 2)
        self._intersection_outline = kwargs.get("intersection_outline", True)

        # Fill and outline options
        self._fill_projection = kwargs.get("fill_projection", False)
        self._fill_alpha = kwargs.get("fill_alpha", 0.5)
        self._fill_color = kwargs.get("fill_color", "black")

        self._projection_outline = kwargs.get("projection_outline", False)
        self._outline_linestyle = kwargs.get("outline_linestyle", "solid")
        self._outline_alpha = kwargs.get("outline_alpha", 1)
        self._outline_color = kwargs.get("outline_color", "black")
        self._outline_width = kwargs.get("outline_width", 2)

        # Internal lists to store artists for fill, outline, and intersection
        self._fill_artists = []
        self._outline_artists = []
        self._intersection_artists = []

        # Axes for plotting
        self._ax = None

    @property
    def ax(self) -> plt.Axes:
        return self._ax

    @ax.setter
    def ax(self, ax: Union[plt.Axes, None]) -> None:
        if ax is not None:
            if not isinstance(ax, plt.Axes):
                raise TypeError(f"Expected type Axes, got {type(ax)}.")
        self.remove()
        self._ax = ax

    # Intersection properties
    @property
    def intersection_alpha(self) -> float:
        return self._intersection_alpha

    @intersection_alpha.setter
    def intersection_alpha(self, alpha: float) -> None:
        if not (0 <= alpha <= 1):
            raise ValueError("intersection_alpha must be between 0 and 1")
        self._intersection_alpha = alpha
        for artist in self._intersection_artists:
            artist.set_alpha(alpha)

    @property
    def intersection_color(self) -> str:
        return self._intersection_color

    @intersection_color.setter
    def intersection_color(self, color: str) -> None:
        self._intersection_color = color
        for artist in self._intersection_artists:
            artist.set_color(color)

    @property
    def intersection_linestyle(self) -> str:
        return self._intersection_linestyle

    @intersection_linestyle.setter
    def intersection_linestyle(self, linestyle: LINESTYLES) -> None:
        self._intersection_linestyle = linestyle
        for artist in self._intersection_artists:
            artist.set_linestyle(linestyle)

    @property
    def intersection_width(self) -> float:
        return self._intersection_width

    @intersection_width.setter
    def intersection_width(self, width: float) -> None:
        if width <= 0:
            raise ValueError("intersection_width must be a positive number")
        self._intersection_width = width
        for artist in self._intersection_artists:
            artist.set_linewidth(width)

    @property
    def intersection_outline(self) -> bool:
        return self._intersection_outline

    @intersection_outline.setter
    def intersection_outline(self, truth: bool) -> None:
        if not isinstance(truth, bool):
            raise ValueError("intersection_outline must be a boolean")
        if not truth:
            for artist in self._intersection_artists:
                artist.remove()
            self._intersection_artists.clear()
        else:
            if not self._intersection_outline:
                self.recreate(self._last_plane, self._last_plane_origin)
        self._intersection_outline = truth

    # Properties for the fill projection
    @property
    def fill_projection(self) -> bool:
        return self._fill_projection

    @fill_projection.setter
    def fill_projection(self, truth: bool) -> None:
        if not isinstance(truth, bool):
            raise ValueError("fill_projection must be a boolean")
        if not isinstance(truth, bool):
            raise ValueError("projection_outline must be a boolean")
        if not truth:
            for artist in self._fill_artists:
                artist.remove()
        else:
            if not self._fill_projection:
                self.recreate(self._last_plane, self._last_plane_origin)

        self._fill_projection = truth

    # Properties for the fill alpha (transparency)
    @property
    def fill_alpha(self) -> float:
        return self._fill_alpha

    @fill_alpha.setter
    def fill_alpha(self, alpha: float) -> None:
        if not (0 <= alpha <= 1):
            raise ValueError("fill_alpha must be between 0 and 1")
        self._fill_alpha = alpha
        for artist in self._fill_artists:
            artist.set_alpha(alpha)

    # Properties for the fill color
    @property
    def fill_color(self) -> str:
        return self._fill_color

    @fill_color.setter
    def fill_color(self, color: str) -> None:
        self._fill_color = color
        for artist in self._fill_artists:
            artist.set_facecolor(color)

    # Properties for the outline projection
    @property
    def projection_outline(self) -> bool:
        return self._projection_outline

    @projection_outline.setter
    def projection_outline(self, truth: bool) -> None:
        if not isinstance(truth, bool):
            raise ValueError("projection_outline must be a boolean")
        if not truth:
            for artist in self._outline_artists:
                artist.remove()
        else:
            if not self._projection_outline:
                self.recreate(self._last_plane, self._last_plane_origin)

        self._projection_outline = truth

    # Properties for the outline alpha (transparency)
    @property
    def outline_alpha(self) -> float:
        return self._outline_alpha

    @outline_alpha.setter
    def outline_alpha(self, alpha: float) -> None:
        if not (0 <= alpha <= 1):
            raise ValueError("outline_alpha must be between 0 and 1")
        self._outline_alpha = alpha
        for outline in self._outline_artists:
            outline.set_alpha(alpha)

    @property
    def outline_linestyle(self) -> str:
        return self._outline_linestyle

    @outline_linestyle.setter
    def outline_linestyle(self, linestyle: LINESTYLES) -> None:
        self._intersection_linestyle = linestyle
        for artist in self._intersection_artists:
            artist.set_linestyle(linestyle)

    # Properties for the outline color
    @property
    def outline_color(self) -> str:
        return self._outline_color

    @outline_color.setter
    def outline_color(self, color: str) -> None:
        self._outline_color = color
        for artist in self._outline_artists:
            artist.set_color(color)

    # Properties for the outline width
    @property
    def outline_width(self) -> float:
        return self._outline_width

    @outline_width.setter
    def outline_width(self, width: float) -> None:
        if width <= 0:
            raise ValueError("outline_width must be a positive number")
        self._outline_width = width
        for artist in self._outline_artists:
            artist.set_linewidth(width)

    def recreate(self, plane: Literal["xy", "xz", "yz"], plane_origin: Tuple[Union[float, int], ...] = None,
                 custom_intersection_coordinate: float = None) -> None:

        # Clear all artists from this structure.
        self.remove()

        # Return if nothing is plotted.
        if not (self._fill_projection or self._projection_outline or self._intersection_outline):
            return None

        custom_intersection = plane_origin

        # Get the 2D projection by taking only X and Y of each vertex
        if plane == "xy":
            vtx_idx = (0, 1)
            vertices_2d = self._mesh.vertices[:, vtx_idx]  # Take only x and y
            plane_normal = (0, 0, 1)
            if custom_intersection_coordinate is not None:
                custom_intersection = (*plane_origin[:2], custom_intersection_coordinate)
        elif plane == "xz":
            vtx_idx = (0, 2)
            vertices_2d = self._mesh.vertices[:, vtx_idx]  # Take only x and z
            plane_normal = (0, 1, 0)
            if custom_intersection_coordinate is not None:
                custom_intersection = (plane_origin[1], custom_intersection_coordinate, plane_origin[2])
        elif plane == "yz":
            vtx_idx = (1, 2)
            vertices_2d = self._mesh.vertices[:, vtx_idx]  # Take only y and z
            plane_normal = (1, 0, 0)
            if custom_intersection_coordinate:
                custom_intersection = (custom_intersection_coordinate, *plane_origin[1:])
        else:
            raise ValueError(f"Expected 'xy', 'xz', 'yz', got {plane}.")

        self._last_plane = plane
        self._last_plane_origin = plane_origin

        polys = []
        for face in self._mesh.faces:

            if self._projection_outline:
                polys.append(shapely.Polygon([self._mesh.vertices[vtx, vtx_idx] for vtx in face]))

            if self._fill_projection:
                self._fill_artists.extend(self._ax.fill(*zip(*vertices_2d[face]),
                                                        color=self._fill_color,
                                                        edgecolor="none",
                                                        alpha=self._fill_alpha)
                                          )

        if polys:
            # Combine all polygons into one shape
            total_shape: shapely.Polygon = shapely.unary_union(polys)

            # Plot the outline of the combined shape
            if total_shape.geom_type == "Polygon":
                x_outline, y_outline = total_shape.exterior.coords.xy
                self._outline_artists.extend(self._ax.plot(x_outline, y_outline, color=self._outline_color,
                                                           linewidth=self._outline_width, alpha=self._outline_alpha,
                                                           linestyle=self._outline_linestyle)
                                             )

                for inner in total_shape.interiors:
                    inner: shapely.LinearRing
                    if inner.minimum_clearance < 1e-3:
                        continue
                    x_outline, y_outline = inner.coords.xy
                    self._outline_artists.extend(self._ax.plot(x_outline, y_outline,
                                                               color=self._outline_color,
                                                               linewidth=self._outline_width,
                                                               alpha=self._outline_alpha,
                                                               linestyle=self._outline_linestyle)
                                                 )
            else:
                for shape in total_shape.geoms:
                    x_outline, y_outline = shape.exterior.coords.xy
                    self._outline_artists.extend(self._ax.plot(x_outline, y_outline,
                                                               color=self._outline_color,
                                                               linewidth=self._outline_width,
                                                               alpha=self._outline_alpha,
                                                               linestyle=self._outline_linestyle)
                                                 )
                    for inner in shape.interiors:
                        inner: shapely.LinearRing
                        if inner.minimum_clearance < 1e-3:
                            continue
                        x_outline, y_outline = inner.coords.xy
                        self._outline_artists.extend(self._ax.plot(x_outline, y_outline,
                                                                   color=self._outline_color,
                                                                   linewidth=self._outline_width,
                                                                   alpha=self._outline_alpha,
                                                                   linestyle=self._outline_linestyle)
                                                     )
        if self._intersection_outline:
            intersection = self._mesh.section(plane_normal, custom_intersection)
            if intersection is not None:
                # This was a real hassle since the to_planar() method recenters the cross section.
                # Honestly, I'm not 100% certain how I got this to work, but I had to apply a plane transform and
                # then rotate the planar cross section depending on the plane normal. Now it should work like a charm.
                try:
                    to_2D = trimesh.geometry.plane_transform(origin=(0, 0, 0), normal=plane_normal)
                    intersection, _ = intersection.to_planar(to_2D=to_2D)
                    # Fix 2D orientation if needed
                    if plane == "xz":
                        # First, mirror the intersection across the Y-axis (invert X-axis)
                        reflection = np.array([
                            [-1, 0, 0],  # Mirror X-axis
                            [0, 1, 0],  # Keep Y-axis
                            [0, 0, 1]  # Keep Z-axis
                        ])

                        intersection.apply_transform(reflection)  # Apply reflection first
                        # Rotate 90 degrees counter-clockwise to swap axes for XZ view
                        angle = np.deg2rad(90)
                        rotation = np.array([
                            [np.cos(angle), -np.sin(angle), 0],
                            [np.sin(angle), np.cos(angle), 0],
                            [0, 0, 1]
                        ])

                        # Apply transform to Path2D (trimesh.path.Path2D expects 3x3 for 2D)
                        intersection.apply_transform(rotation)

                    elif plane == "yz":

                        # Rotate 180 degrees around origin
                        angle = np.deg2rad(-90)
                        rotation = np.array([
                            [np.cos(angle), -np.sin(angle), 0],
                            [np.sin(angle), np.cos(angle), 0],
                            [0, 0, 1]
                        ])
                        intersection.apply_transform(rotation)

                except ValueError as e:
                    print("to_planar failed:", e)
                    intersection = None

                if not intersection.is_empty:
                    for entity in intersection.entities:
                        discrete = entity.discrete(intersection.vertices)
                        self._intersection_artists.extend(self._ax.plot(*discrete.T, alpha=self._intersection_alpha,
                                                                        linewidth=self._intersection_width,
                                                                        color=self._intersection_color,
                                                                        linestyle=self._intersection_linestyle))
        return None

# Method to remove the structure from the plot
    def remove_outline(self):
        """
        Removes the plotted structure from the plot.
        """
        for artist in self._outline_artists:
            artist.remove()
        self._outline_artists.clear()

# Method to remove the structure from the plot
    def remove_fill(self):
        """
        Removes the plotted structure from the plot.
        """
        for artist in self._fill_artists:
            artist.remove()
        self._fill_artists.clear()

    def remove_intersection(self):
        """
        Removes the intersection artists from the plot.
        """
        for artist in self._intersection_artists:
            artist.remove()
        self._intersection_artists.clear()

# Method to remove the structure from the plot
    def remove(self):
        """
        Removes the plotted structure from the plot.
        """
        for artist in self._fill_artists:
            if artist.axes:
                artist.remove()
        for artist in self._outline_artists:
            if artist.axes:
                artist.remove()
        for artist in self._intersection_artists:
            if artist.axes:
                artist.remove()
        self._fill_artists.clear()
        self._outline_artists.clear()
        self._intersection_artists.clear()