from __future__ import annotations

from functools import partial
from typing import TypedDict, Unpack, Union, Sequence, Literal, Self

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


class SphereKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Sphere structure type's constructor.
    """
    x: float
    y: float
    z: float
    radius: float
    radius_2: float
    radius_3: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class SphereGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Sphere structure type.
    """

    class _Dimensions(TypedDict, total=False):
        radius: float
        radius_2: float
        radius_3: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        radius = kwargs.get("radius", None)
        radius_2 = kwargs.get("radius_2", None)
        radius_3 = kwargs.get("radius_3", None)
        ellipsoid = self._get("make ellipsoid", bool)

        if any([rad is not None for rad in [radius_2, radius_3]]) and radius is None:
            radius = convert_length(self._get("radius", float), "m", self._units)

        if radius_2 == radius and radius_2 is not None:
            kwargs.pop("radius_2")
        elif radius_2 is not None and not ellipsoid:
            self._set("make ellipsoid", True)
            ellipsoid = True

        if radius_3 == radius and radius_3 is not None:
            kwargs.pop("radius_3")
        elif radius_3 is not None and not ellipsoid:
            self._set("make ellipsoid", True)

        super().set_dimensions(**kwargs)


class SphereSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Rectangle structure type.
    """
    geometry: SphereGeometry


class Sphere(Structure):
    settings: SphereSettings

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[SphereKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign settings module.
        self.settings = SphereSettings(self, SphereGeometry)

        # Filter an apply kwargs
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
            elif k in ["radius", "radius_2", "radius_2"]:
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

        # Fetch the parameters for radius, radius_2, and z_span, and center position
        radius = self._get("radius", float)
        radius_2 = self._get("radius 2", float)
        z_span = self._get("z span", float)/2

        dimensions = np.array([radius, radius_2, z_span])
        position = self._get_position(absolute)
        min_pos = position - dimensions
        max_pos = position + dimensions

        corners = np.array([
            [min_pos[0], position[1], position[2]], [max_pos[0], position[1], position[2]],
            [position[0], min_pos[1], position[2]], [position[0], max_pos[1], position[2]],
            [position[0], position[1], min_pos[2]], [position[0], position[1], max_pos[2]],
        ])

        return corners

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        # Fetch position and spans and convert to simulation units
        position = convert_length(self._get_position(absolute), "m", units)
        spans_non_converted = np.array([self.radius, self.radius_2, self.radius_3], dtype=np.float64)
        spans = convert_length(spans_non_converted, self._units, units)

        # Create a base_classes sphere with unit radius (this is a unit sphere)
        sphere = trimesh.creation.icosphere(radius=1.0)

        # Scale the sphere to have the desired radii in x, y, and z directions
        scale_matrix = np.diag([*spans, 1.0])  # Scaling along x, y, and z axes
        sphere.apply_transform(scale_matrix)

        # Translate the sphere to the desired position
        sphere.apply_translation(position)

        # Rotate the sphere
        sphere = self._rotate_trimesh(sphere, position)

        return sphere

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)

        if self._get("make ellipsoid", bool):
            radius_2 = (f"set('make ellipsoid', true);\n"
                        f"set('radius 2', {self._get("radius 2", float)});\n"
                        f"set('radius 3', {self._get("radius 3", float)});\n")
        else:
            radius_2 = ""

        script = (
            "addsphere();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('radius', {self._get("radius", float)});\n"
            f"{radius_2}"
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
        if radius == self.radius == self.radius_3:
            self._set("make ellipsoid", False)
        else:
            if not self._get("make ellipsoid", bool):
                self._set("make ellipsoid", True)
            self._set("radius 2", convert_length(radius, self._units, "m"))

    @property
    def radius_3(self) -> float:
        if self._get("make ellipsoid", bool):
            return convert_length(self._get("radius 3", float), "m", self._units)
        else:
            return convert_length(self._get("radius", float), "m", self._units)

    @radius_3.setter
    def radius_3(self, radius: float) -> None:
        validation.positive_number(radius, "radius")
        if radius == self.radius == self.radius_2:
            self._set("make ellipsoid", False)
        else:
            if not self._get("make ellipsoid", bool):
                self._set("make ellipsoid", True)
            self._set("radius 3", convert_length(radius, self._units, "m"))

    # endregion User Properties

    def copy(self, name, **kwargs: Unpack[SphereKwargs]) -> Self:
        return super().copy(name, **kwargs)