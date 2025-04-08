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


class TriangleKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Triangle structure type's constructor.
    """
    x: float
    y: float
    z: float
    side_a: float
    side_b: float
    theta: float
    z_span: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class TriangleGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Triangle structure type.
    """

    class _Dimensions(TypedDict, total=False):
        side_a: float
        side_b: float
        theta: float
        z_span: float

    _get_nr_sides: Callable[[Optional[int]], int]
    _parent_object: Triangle

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:

        spans = {k: v for k, v in kwargs.items() if v is not None and k in ["side_a", "side_b"]}

        for k, v in spans.items():
            if v == 0:
                raise ValueError(f"A triangle cannot have side length = 0. Got {k} = 0.")

        if theta := kwargs.get("theta", None):
            if not isinstance(theta, (float, int)):
                raise TypeError(f"Expected float or int for parameter 'theta', got {type(theta)}.")
            elif theta % 180 == 0:
                raise ValueError(f"Parameter 'theta' should be an angle between 0 ang 180 degrees, not including "
                                 f"0 or 180. got {theta}.")
            spans["theta"] = theta

        # Create the vertices
        vertices = self._parent_object._create_vertices(**spans)

        # Set the vertices
        self._parent_object._set("vertices", vertices)

        # Set the z-span as regular
        super().set_dimensions(**{"z_span": kwargs.get("z_span", None)})


class TriangleSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the RegularPolygon structure type.
    """
    geometry: TriangleGeometry


class Triangle(Structure):

    settings: TriangleSettings

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[TriangleKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign the settings module
        self.settings = TriangleSettings(self, TriangleGeometry)

        # Set grid attribute name to Triangle to ease loading.
        self.settings.material._set_grid_attribute_name("Triangle")

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)

    def _get_dimension(self, axis: Literal["a", "b", "theta", "c"]) -> float:
        """Returns the length of the given side in meters or the angle theta in degrees."""

        # List of three vertices. The first vertex is at the end of side b,
        # the second is always at (0,0), and the third is at the end of side a.
        vertices = self._get("vertices", np.ndarray)

        if axis == "a":
            return float(np.linalg.norm(vertices[2] - vertices[1]))  # Distance from (0,0) to the third vertex
        elif axis == "b":
            return float(np.linalg.norm(vertices[0] - vertices[1]))  # Distance from (0,0) to the first vertex
        elif axis == "c":
            return float(np.round(np.linalg.norm(vertices[2] - vertices[0]), DECIMALS - 1))  # Distance between first and third vertex
        elif axis == "theta":
            # Compute the angle between sides a and b using dot product
            vector_a = vertices[2] - vertices[1]
            vector_b = vertices[0] - vertices[1]

            dot_product = np.dot(vector_a, vector_b)
            norm_a = np.linalg.norm(vector_a)
            norm_b = np.linalg.norm(vector_b)

            theta_rad = np.arccos(dot_product / (norm_a * norm_b))  # Angle in radians
            return float(np.round(np.degrees(theta_rad), DECIMALS - 2))  # Convert to degrees
        else:
            raise ValueError("Invalid axis. Must be 'a', 'b', 'c', or 'theta'.")

    def _create_vertices(self, side_a: float = None, side_b: float = None, theta: float = None):
        """
        Creates vertices for a triangle given any combination of side_a, side_b, and theta.
        """

        current_side_a = self._get_dimension("a")
        current_side_b = self._get_dimension("b")
        current_theta = self._get_dimension("theta")

        # Convert lengths to meters if needed
        side_a = convert_length(side_a, self._units, "m") if side_a is not None else current_side_a
        side_b = convert_length(side_b, self._units, "m") if side_b is not None else current_side_b
        theta = np.radians(theta) if theta is not None else np.radians(current_theta)  # Convert degrees to radians

        # Compute the third vertex based on side_a, side_b, and theta
        x = side_b * np.cos(theta)  # X-coordinate
        y = side_b * np.sin(theta)  # Y-coordinate

        vertices = np.array([[x, y], [0, 0], [side_a, 0]])

        return vertices

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
            elif k in ["side_a", "side_b", "theta", "z_span"]:
                dimensions[k] = v
            elif k in ["rot_vec", "rot_angle", "rot_point"]:
                rotation[k] = v
            elif k in ["material", "material_index"]:
                material[k] = v

        # Assure default dimensions if none are provided
        if not any([dimensions.get(key, None) for key in dimensions.keys()]) and not copied:
            dimensions["nr_sides"] = 6

        if not copied:
            if "x_span" not in dimensions:
                dimensions["x_span"] = 200
            if "y_span" not in dimensions:
                dimensions["y_span"] = 200
            if "theta" not in dimensions:
                dimensions["theta"] = 90

        # Apply kwargs
        if position:
            self.settings.geometry.set_position(**position)
        if dimensions:
            self.settings.geometry.set_dimensions(**dimensions)
        if rotation:
            self.settings.rotation.set_rotation(**rotation)
        if material:
            self.settings.material.set_material(**material)

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
            f"set('grid attribute name', 'Triangle');\n"
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
    def side_a(self) -> float:
        """Returns the lenght of the triangle's side along the x-axis."""
        return convert_length(self._get_dimension("a"), "m", self._units)

    @side_a.setter
    def side_a(self,  span: float) -> None:
        """Sets the lenght of the triangle's side along the x-axis."""
        self.settings.geometry.set_dimensions(side_a=span)

    @property
    def side_b(self) -> float:
        """Returns the lenght of the triangle's side along the y-axis."""
        return convert_length(self._get_dimension("b"), "m", self._units)

    @side_b.setter
    def side_b(self, span: float) -> None:
        """Sets the lenght of the triangle's side along the y-axis."""
        self.settings.geometry.set_dimensions(side_b=span)

    @property
    def side_c(self) -> float:
        """Returns the length of side c."""
        return convert_length(self._get_dimension("c"), "m", self._units)

    @property
    def theta(self) -> float:
        """Returns the angle between side a and b in degrees."""
        return self._get_dimension("theta")

    @theta.setter
    def theta(self, theta: float) -> None:
        """Sets the angle between side a and b in degrees."""
        self.settings.geometry.set_dimensions(theta=theta)

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        self.settings.geometry.set_dimensions(z_span=span)

    # endregion User Properties

    def copy(self, name, **kwargs: Unpack[TriangleKwargs]) -> Self:
        return super().copy(name, **kwargs)