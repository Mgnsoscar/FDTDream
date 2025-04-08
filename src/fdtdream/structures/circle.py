from __future__ import annotations

from typing import TypedDict, Unpack, Union, Sequence, Self

import numpy as np
import trimesh
from numpy.typing import NDArray

from .structure import Structure
from .settings import StructureSettings
from .. import interfaces
from ..base_classes import BaseGeometry
from ..resources import validation, Materials
from ..resources.functions import convert_length
from ..resources.literals import AXES, LENGTH_UNITS


class CircleKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Circle structure type's constructor.
    """
    x: float
    y: float
    z: float
    radius: float
    radius_2: float
    z_span: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | interfaces.SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class CircleGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Circle structure type.
    """

    class _Dimensions(TypedDict, total=False):
        radius: float
        radius_2: float
        z_span: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        radius = kwargs.get("radius", None)
        radius_2 = kwargs.get("radius_2", None)
        if radius_2 is not None:
            if radius is None:
                radius = convert_length(self._get("radius", float), "m", self._units)

            ellipsoid = self._get("make ellipsoid", bool)
            if radius_2 == radius:
                kwargs.pop("radius_2")
            else:
                if not ellipsoid:
                    self._set("make ellipsoid", True)
        super().set_dimensions(**kwargs)


class CircleSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Circle structure type.
    """
    geometry: CircleGeometry


class Circle(Structure):

    settings: CircleSettings

    # region Dev Methods

    def __init__(self, name: str, sim: interfaces.SimulationInterface, **kwargs: Unpack[CircleKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign settings module
        self.settings = CircleSettings(self, CircleGeometry)

        # Filter and process kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Sphere structure type."""

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
            elif k in ["radius", "radius_2", "z_span"]:
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

        # Fetch the parameters for radius, radius_2, and z_span, and center position
        radius = self._get("radius", float)
        radius_2 = self._get("radius 2", float)
        z_span = self._get("z span", float)/2

        dimensions = np.array([radius, radius_2, z_span])
        position = self._get_position(absolute)
        min_pos = position - dimensions
        max_pos = position + dimensions

        corners = np.array([
            [min_pos[0], position[1], min_pos[2]], [min_pos[0], position[1], max_pos[2]],
            [max_pos[0], position[1], min_pos[2]], [max_pos[0], position[1], max_pos[2]],
            [position[0], min_pos[1], min_pos[2]], [position[0], min_pos[1], max_pos[2]],
            [position[0], max_pos[1], min_pos[2]], [position[0], max_pos[1], max_pos[2]]
        ], dtype=np.float64)

        return corners

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        # Validate units
        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        # Fetch position and dimensions
        position = convert_length(self._get_position(absolute), "m", units)
        radius = convert_length(self.radius, self._units, units)
        radius_2 = convert_length(self.radius_2, self._units, units)
        z_span = convert_length(self.z_span, self._units, units)

        # Create a base_classes cylinder with unit radius and height equal to z_span
        cylinder = trimesh.creation.cylinder(radius=1.0, height=z_span, sections=64)

        # Scale the cylinder to have the desired radii in x and y directions
        scale_matrix = np.diag([radius, radius_2, 1.0, 1.0])  # Scaling along x, y, and keep z unchanged
        cylinder.apply_transform(scale_matrix)

        # Translate the cylinder to the desired position
        cylinder.apply_translation(position)

        # Rotate the trimesh if neccessary.
        cylinder = self._rotate_trimesh(cylinder, position)

        return cylinder

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)

        if self._get("make ellipsoid", bool):
            radius_2 = (f"set('make ellipsoid', true);\n"
                        f"set('radius 2', {self._get("radius 2", float)});\n")
        else:
            radius_2 = ""

        script = (
            "addcircle();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('radius', {self._get("radius", float)});\n"
            f"{radius_2}"
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
    def radius(self) -> float:
        return convert_length(self._get("radius", float), "m", self._units)

    @radius.setter
    def radius(self, radius: float) -> None:
        validation.positive_number(radius, "radius")
        self._set("radius", convert_length(radius, self._units, "m"))

    @property
    def radius_2(self) -> float:
        if self._get("make ellipsoid", bool):
            return convert_length(self._get("radius 2", float), "m", self._units)
        else:
            return convert_length(self._get("radius", float), "m", self._units)

    @radius_2.setter
    def radius_2(self, radius: float) -> None:
        validation.positive_number(radius, "radius")
        if radius == self.radius:
            self._set("make ellipsoid", False)
        else:
            if not self._get("make ellipsoid", bool):
                self._set("make ellipsoid", True)
            self._set("radius 2", convert_length(radius, self._units, "m"))

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        validation.positive_number(span, "z_span")
        self._set("z span", convert_length(span, self._units, "m"))

    # endregion User Properties

    def copy(self, name, **kwargs: Unpack[CircleKwargs]) -> Self:
        return super().copy(name, **kwargs)

