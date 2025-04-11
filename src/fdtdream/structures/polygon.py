from __future__ import annotations

# Std library imports
from functools import partial
# Std imports
from typing import TypedDict, Unpack, Union, Sequence, Literal, Iterable, Tuple, Self

# 3rd party imports
import numpy as np
import trimesh
from numpy.typing import NDArray

# Local imports
from .settings import StructureSettings
from .structure import Structure
from ..base_classes import BaseGeometry
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..resources import validation, Materials
from ..resources.functions import convert_length
from ..resources.literals import AXES, LENGTH_UNITS


class PolygonKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Polygon structure type's constructor.
    """
    x: float
    y: float
    z: float
    vertices: Iterable
    z_span: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class PolygonGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Polygon structure type.
    """
    class _Dimensions(TypedDict, total=False):
        vertices: Iterable

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        vertices = kwargs.pop("vertices", None)
        if vertices is not None:
            vertices = np.array(vertices)
            if vertices.shape[1] > 2:
                raise ValueError(f"Vertices must be an Iterable containing xy- coordinates, no z-coordinates")
            self._set("vertices", convert_length(vertices, self._units, "m"))
        if z_span := kwargs.get("z_span", None):
            self._set("z span", convert_length(z_span, self._units, "m"))




class PolygonSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Polygon structure type.
    """
    geometry: PolygonGeometry


class Polygon(Structure):
    settings: PolygonSettings

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[PolygonKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign the settings module
        self.settings = PolygonSettings(self, PolygonGeometry)

        # Filter and process kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Polygon structure type."""

        # Abort if the kwargs are empty
        if not kwargs:
            return

        # Initialize dicts
        position = {}
        dimensions = {}
        rotation = {}
        material = {}

        # Filter kwargs
        for k, v in kwargs.items():
            if k in ["x", "y", "z"]:
                position[k] = v
            elif k in ["vertices", "z_span"]:
                dimensions[k] = v
            elif k in ["rot_vec", "rot_angle", "rot_point"]:
                rotation[k] = v
            elif k in ["material", "material_index"]:
                material[k] = v

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
        vertices = self._get("vertices", np.ndarray) + self._get_position(absolute)
        z_span_half = self._get("z span", float)/2

        min_corners = vertices - z_span_half
        max_corners = vertices + z_span_half

        return np.stack((min_corners, max_corners))

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        # Fetch position, z span, and vertices
        position = convert_length(self._get_position(absolute), "m", units)
        vertices = convert_length(self.vertices, self._units, units)
        z_span = convert_length(self.z_span, self._units, units)

        # Create a 2D polygon from the vertices
        polygon_2d = trimesh.path.polygons.Polygon(vertices)

        # Extrude the polygon along the z-axis to create a 3D mesh
        polygon_mesh = trimesh.creation.extrude_polygon(polygon_2d, height=z_span)

        # Translate the mesh to the correct position. Adjust z-coordinate to acount for only positive extrusion.
        polygon_mesh.apply_translation(position - np.array([0, 0, z_span / 2]))

        # Rotate the trimesh if neccesary
        polygon_mesh = self._rotate_trimesh(polygon_mesh, position)

        return polygon_mesh

    def copy(self, name, **kwargs: Unpack[PolygonKwargs]) -> Self:
        return super().copy(name, **kwargs)

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)
        vertices = self._get("vertices", np.ndarray).tolist()

        script = (
            "addpoly();\n"
            f"set('detail', 0);\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('vertices', [{';'.join([','.join(map(str, row)) for row in vertices])}]);\n"
            f"set('z span', {self._get('z span', float)});\n"
            f"set('material', '{material}');\n"
        )
        if material == "<Object defined dielectric>":
            script += f"set('index', '{self._get('index', str)}');\n"
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
    def vertices(self) -> NDArray[Tuple[any, NDArray[2, float]]]:
        return convert_length(self._get("vertices", np.ndarray), "m", self._units)

    @vertices.setter
    def vertices(self, vertices: Iterable) -> None:
        self.settings.geometry.set_dimensions(vertices=np.array(vertices))

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        validation.positive_number(span, "z_span")
        self._set("z span", convert_length(span, self._units, "m"))

    # endregion User Properties

