from __future__ import annotations

from typing import TypedDict, Unpack, Union, Sequence, Self

import numpy as np
import trimesh
from numpy.typing import NDArray

from .structure import Structure
from .settings import StructureSettings
from ..base_classes import BaseGeometry
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..resources import validation, Materials
from ..resources.functions import convert_length
from ..resources.literals import AXES, LENGTH_UNITS


class PyramidKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Pyramid structure type's constructor.
    """
    x: float
    y: float
    z: float
    x_span_top: float
    x_span_bottom: float
    y_span_top: float
    y_span_bottom: float
    z_span: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class PyramidGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Pyramid structure type.
    """

    class _Dimensions(TypedDict, total=False):
        x_span_top: float
        x_span_bottom: float
        y_span_top: float
        y_span_bottom: float
        z_span: float
        z_span: float


class PyramidSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Circle structure type.
    """
    geometry: PyramidGeometry


class Pyramid(Structure):

    settings: PyramidSettings

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[PyramidKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign the settings module
        self.settings = PyramidSettings(self, PyramidGeometry)

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Pyramid structure type."""

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
            elif k in ["x_span_bottom", "x_span_top", "y_span_bottom", "y_span_top", "z_span"]:
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

    def _get_corners(self, absolute: bool = False) -> NDArray[np.float64]:

        z_center = self._get_position(absolute)
        z_span = self._get("z span", float)
        z_min = z_center - z_span / 2
        z_max = z_center + z_span / 2
        x_span_bottom = self._get("x span bottom", float)
        y_span_bottom = self._get("y span bottom", float)
        x_span_top = self._get("x span top", float)
        y_span_top = self._get("y span top", float)
        x_center = self._get("x", float)
        y_center = self._get("y", float)

        return np.unique(np.array([
            (x_center - x_span_bottom / 2, y_center - y_span_bottom / 2, z_min),
            (x_center - x_span_top / 2, y_center - y_span_top / 2, z_max),
            (x_center - x_span_bottom / 2, y_center + y_span_bottom / 2, z_min),
            (x_center - x_span_top / 2, y_center + y_span_top / 2, z_max),
            (x_center + x_span_bottom / 2, y_center - y_span_bottom / 2, z_min),
            (x_center + x_span_top / 2, y_center - y_span_top / 2, z_max),
            (x_center + x_span_bottom / 2, y_center + y_span_bottom / 2, z_min),
            (x_center + x_span_top / 2, y_center + y_span_top / 2, z_max)
        ]))

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        # Fetch dimension in correct units
        x_span_bottom = convert_length(self.x_span_bottom, self._units, units)
        x_span_top = convert_length(self.x_span_top, self._units, units)
        y_span_bottom = convert_length(self.y_span_bottom, self._units, units)
        y_span_top = convert_length(self.y_span_top, self._units, units)
        z_span = convert_length(self.z_span, self._units, units)

        # Start with a box mesh with spans matching the bottom dimensions
        box_mesh = trimesh.creation.box(extents=[x_span_bottom, y_span_bottom, z_span])

        # Get the vertices of the box
        vertices = box_mesh.vertices.copy()

        # The z position of the top and bottom faces
        z_bottom = -z_span / 2
        z_top = z_span / 2

        # Taper the top vertices (those with z = z_top) based on the top spans
        for i, vertex in enumerate(vertices):
            if np.isclose(vertex[2], z_top):  # If vertex belongs to the top face
                # Scale the x and y coordinates towards the center
                vertices[i, 0] *= x_span_top / x_span_bottom
                vertices[i, 1] *= y_span_top / y_span_bottom

        # Replace the box's vertices with the modified ones
        box_mesh.vertices = vertices

        # Translate the pyramid to it's correct position
        position = convert_length(self._get_position(absolute), "m", units)
        box_mesh = box_mesh.apply_translation(position)

        # Rotate the trimesh if neccessary.
        box_mesh = self._rotate_trimesh(box_mesh, position)

        return box_mesh

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)

        script = (
            "addpyramid();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('x span top', {self._get("x span top", float)});\n"
            f"set('x span bottom', {self._get("x span bottom", float)});\n"
            f"set('y span top', {self._get("y span top", float)});\n"
            f"set('y span bottom', {self._get("y span bottom", float)});\n"
            f"set('z span', {self._get("z span", float)});\n"
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
    def x_span_top(self) -> float:
        return convert_length(self._get("x span top", float), "m", self._units)

    @x_span_top.setter
    def x_span_top(self, span: float) -> None:
        validation.positive_number(span, "x_span_top")
        self._set("x span top", convert_length(span, self._units, "m"))

    @property
    def x_span_bottom(self) -> float:
        return convert_length(self._get("x span bottom", float), "m", self._units)

    @x_span_bottom.setter
    def x_span_bottom(self, span: float) -> None:
        validation.positive_number(span, "x_span_bottom")
        self._set("x span bottom", convert_length(span, self._units, "m"))

    @property
    def y_span_top(self) -> float:
        return convert_length(self._get("y span top", float), "m", self._units)

    @y_span_top.setter
    def y_span_top(self, span: float) -> None:
        validation.positive_number(span, "y_span_top")
        self._set("y span top", convert_length(span, self._units, "m"))

    @property
    def y_span_bottom(self) -> float:
        return convert_length(self._get("y span bottom", float), "m", self._units)

    @y_span_bottom.setter
    def y_span_bottom(self, span: float) -> None:
        validation.positive_number(span, "y_span_bottom")
        self._set("y span bottom", convert_length(span, self._units, "m"))

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        validation.positive_number(span, "z_span")
        self._set("z span", convert_length(span, self._units, "m"))

    # endregion User Properties

    def copy(self, name, **kwargs: Unpack[PyramidKwargs]) -> Self:
        return super().copy(name, **kwargs)
