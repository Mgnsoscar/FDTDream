from __future__ import annotations

from functools import partial
from typing import TypedDict, Unpack, Union, Sequence, Literal, Tuple, Callable, Optional, Self

import numpy as np
import trimesh
from numpy.typing import NDArray

from .settings import StructureSettings
from .structure import Structure
from ..base_classes import BaseGeometry
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..resources import validation, Materials
from ..resources.functions import convert_length
from ..resources.literals import AXES, LENGTH_UNITS
from ..resources.local_resources import DECIMALS


class RegularPolygonKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the RegularPolygon structure type's constructor.
    """
    x: float
    y: float
    z: float
    nr_sides: int
    inner_radius: float
    outer_radius: float
    side_length: float
    z_span: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class RegularPolygonGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the RegularPolygon structure type.
    """

    class _Dimensions(TypedDict, total=False):
        nr_sides: float
        inner_radius: float
        outer_radius: float
        side_length: float
        z_span: float

    _get_nr_sides: Callable[[Optional[int]], int]

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        dims = [(dim, kwargs.get(dim, None)) for dim in ["inner_radius", "outer_radius", "side_length"]]  # type: ignore
        dims = [dim for dim in dims if dim[1] is not None]
        if len(dims) > 1:
            raise ValueError(f"Regular Polygons can be defined by it's outer radius, it's inner radius, or by "
                             f"it's side length. Only one of these can be defined at a time, not '{dims}'.")
        elif len(dims) == 1:
            vertices = self._create_regular_polygon(
                self._get_nr_sides(kwargs.pop("nr_sides", None)),
                **{dims[0][0]: dims[0][1]}
            )
            self._set("vertices", convert_length(vertices, self._units, "m"))

        else:
            if kwargs.get("nr_sides", None) is not None:
                outer_radius = convert_length(self._get_side_length_and_radius()[2], self._units, "m")
                vertices = self._create_regular_polygon(self._get_nr_sides(kwargs.get("nr_sides")),
                                                        outer_radius=outer_radius)
                self._set("vertices", vertices)

        super().set_dimensions(**{"z_span": kwargs.get("z_span", None)})

    @staticmethod
    def _is_equilateral(vertices: NDArray) -> bool:
        """
        Determines whether the polygon is equilateral by checking if all side lengths are equal.

        Returns:
        --------
        bool
            `True` if the polygon is equilateral, `False` otherwise.
        """

        # Calculate the side lengths
        side_lengths = []
        num_vertices = len(vertices)

        for i in range(num_vertices):
            # Get consecutive vertices (wraps around to the first vertex at the end)
            x1, y1 = vertices[i][0], vertices[i][1]
            x2, y2 = vertices[(i + 1) % num_vertices][0], vertices[(i + 1) % num_vertices][1]

            # Calculate the Euclidean distance between the two vertices
            side_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            side_lengths.append(side_length)

        # Check if all side lengths are approximately equal
        return np.allclose(side_lengths, side_lengths[0], atol=DECIMALS)

    @staticmethod
    def _create_regular_polygon(nr_sides: int, side_length=None, outer_radius=None, inner_radius=None):
        """
        Creates vertices for an N-sided equilateral polygon.
        The user can input either the side length, the outer radius, or the inner radius.
        """

        if not any([side_length, outer_radius, inner_radius]):
            raise ValueError("Either side_length, radius, or inner_radius must be provided.")

        if outer_radius is None:
            if side_length is not None:
                # Calculate radius from side length
                outer_radius = side_length / (2 * np.sin(np.pi / nr_sides))
            elif inner_radius is not None:
                # Calculate radius from inner radius
                outer_radius = inner_radius / np.cos(np.pi / nr_sides)

        vertices = []
        for i in range(nr_sides):
            angle = i * 2 * np.pi / nr_sides  # Rotate around the center
            x = outer_radius * np.cos(angle)
            y = outer_radius * np.sin(angle)
            vertices.append((x, y))

        return np.array(vertices)

    def _get_side_length_and_radius(self) -> Optional[Tuple[float, float, float]]:
        """
        Returns the side length, inner radius (inradius), and circumradius (outer radius) of the polygon
        if it is equilateral; otherwise, returns `None`.

        This method first checks if the polygon is equilateral by calling `_is_equilateral`. If the polygon
        is equilateral, it calculates:
        - Side length: Euclidean distance between the first two vertices.
        - Circumradius (outer radius): Distance from the polygon's center to any vertex.
        - Inradius (inner radius): Distance from the polygon's center to the midpoint of any side.

        Returns:
        --------
        Optional[Tuple[float, float, float]]
            A tuple containing:
            - The length of a side of the equilateral polygon.
            - The inner radius (distance from center to the midpoint of a side).
            - The circumradius (distance from center to a vertex).
            Returns `None` if the polygon is not equilateral.
        """

        vertices = self._get("vertices", np.ndarray)

        # Check if the polygon is equilateral
        if not self._is_equilateral(vertices):
            return None

        # Get the first two vertices to calculate side length
        x1, y1 = vertices[0][0], vertices[0][1]
        x2, y2 = vertices[1][0], vertices[1][1]

        # Calculate the Euclidean distance as the side length
        side_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Calculate the number of vertices (N-sided polygon)
        num_vertices = len(vertices)

        # Calculate the circumradius (outer radius)
        circumradius = side_length / (2 * np.sin(np.pi / num_vertices))

        # Calculate the inradius (inner radius)
        inradius = convert_length(circumradius * np.cos(np.pi / num_vertices), "m", self._units)
        circumradius = convert_length(circumradius, "m", self._units)
        side_length = convert_length(side_length, "m", self._units)

        return side_length, inradius, circumradius


class RegularPolygonSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the RegularPolygon structure type.
    """
    geometry: RegularPolygonGeometry


class RegularPolygon(Structure):

    settings: RegularPolygonSettings
    _sides: int

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[RegularPolygonKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign the settings module
        self.settings = RegularPolygonSettings(self, RegularPolygonGeometry)

        # Assign variables and references
        self._sides = 6
        self.settings.geometry._get_nr_sides = self._get_nr_sides

        # Set grid attribute name to RegularPolygon to ease loading.
        self.settings.material._set_grid_attribute_name("RegularPolygon")

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the RegularPolygon structure type."""

        # Initialize dicts
        position = {}
        dimensions = {}
        rotation = {}
        material = {}

        # Filter kwargs
        for k, v in kwargs.items():
            if k in ["x", "y", "z"]:
                position[k] = v
            elif k in ["nr_sides", "inner_radius", "outer_radius", "side_length"]:
                dimensions[k] = v
            elif k in ["rot_vec", "rot_angle", "rot_point"]:
                rotation[k] = v
            elif k in ["material", "material_index"]:
                material[k] = v

        # Assure default dimensions if none are provided
        if not any([dimensions.get(key, None) for key in dimensions.keys()]) and not copied:
            dimensions["nr_sides"] = 6

        # Apply kwargs
        if position:
            self.settings.geometry.set_position(**position)
        if dimensions:
            self.settings.geometry.set_dimensions(**dimensions)
        if rotation:
            self.settings.rotation.set_rotation(**rotation)
        if material:
            self.settings.material.set_material(**material)

    def _get_nr_sides(self, sides: int = None) -> int:
        """Fetches and returns the number of sides in the regular polygon."""
        if sides is not None:
            self._sides = sides
        return self._sides

    def _get_corners(self, absolute: bool = False) -> NDArray:

        # Fetch the position of the object, and it's vertices relative to the position.
        position = self._get_position(absolute)
        vertices = self._get("vertices", np.ndarray)  # 2D coordinates relative to object center

        # Create 3D vectors by appending the z-position
        z_values = np.full((vertices.shape[0], 1), position[2])
        vertices_3d = np.hstack((vertices, z_values))

        # Now find the top and bottom set of vertices
        z_span_half = self._get("z span", float)/2
        min_corners = vertices_3d - z_span_half
        max_corners = vertices_3d + z_span_half

        return np.stack((min_corners, max_corners))

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        # Fetch dimensions in the correct units
        vertices = convert_length(self._get("vertices", np.ndarray), "m", units)
        z_span = convert_length(self.z_span, self._units, units)

        # Create a 2D polygon from the vertices
        polygon_2d = trimesh.path.polygons.Polygon(vertices)

        # Extrude the polygon along the z-axis to create a 3D mesh
        polygon_mesh = trimesh.creation.extrude_polygon(polygon_2d, height=z_span)

        # Translate the mesh to the correct position. Adjust z-coordinate to acount for only positive extrusion.
        position = convert_length(self._get_position(absolute), "m", units) - np.array([0, 0, z_span / 2])
        polygon_mesh = polygon_mesh.apply_translation(position)

        # Rotate the trimesh
        rotated_trimesh = self._rotate_trimesh(polygon_mesh, position)

        return rotated_trimesh

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)
        vertices = self._get("vertices", np.ndarray).tolist()

        script = (
            "addpoly();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('vertices', [{";".join([",".join(map(str, row)) for row in vertices])}]);\n"
            f"set('material', '{material}');\n"
        )
        if material == "<Object defined dielectric>":
            script += f"set('index', '{self._get("index", str)}');\n"
        if self.settings.rotation.__getattribute__("_is_rotated"):
            axes, rotations = self.settings.rotation._get_rotation_euler()
            for axis, rotation, que, nr in zip(axes, rotations, ["first", "second", "third"], ["1", "2", "3"]):
                if rotation == 0:
                    continue
                else:
                    script += (
                        f"set('{que} axis', '{axis}');\n"
                        f"set('rotation {nr}', {rotation});\n"
                    )
        return script

    # endregion Dev Methods

    # region User Properties

    @property
    def outer_radius(self) -> float:
        return convert_length(self.settings.geometry._get_side_length_and_radius()[2], "m", self._units)

    @outer_radius.setter
    def outer_radius(self, radius: float) -> None:
        self.settings.geometry.set_dimensions(outer_radius=radius)

    @property
    def inner_radius(self) -> float:
        return convert_length(self.settings.geometry._get_side_length_and_radius()[1], "m", self._units)

    @inner_radius.setter
    def inner_radius(self, radius: float) -> None:
        self.settings.geometry.set_dimensions(inner_radius=radius)

    @property
    def side_length(self) -> float:
        return convert_length(self.settings.geometry._get_side_length_and_radius()[0], "m", self._units)

    @side_length.setter
    def side_length(self, length: float) -> None:
        self.settings.geometry.set_dimensions(side_length=length)

    @property
    def nr_sides(self) -> int:
        return self._sides

    @nr_sides.setter
    def nr_sides(self, nr: int) -> None:
        self._get_nr_sides(nr)

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        validation.positive_number(span, "z_span")
        self._set("z span", convert_length(span, self._units, "m"))

    # endregion User Properties

    def copy(self, name, **kwargs: Unpack[RegularPolygonKwargs]) -> Self:
        return super().copy(name, **kwargs)