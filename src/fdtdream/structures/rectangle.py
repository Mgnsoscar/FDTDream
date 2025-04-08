from __future__ import annotations

from typing import TypedDict, Unpack, Union, Sequence, Self

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


class RectangleKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Rectangle structure type's constructor.
    """
    x: float
    y: float
    z: float
    x_span: float
    y_span: float
    z_span: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class RectangleGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the rectangle structure type.
    """

    class _Dimensions(TypedDict, total=False):
        x_span: float
        y_span: float
        z_span: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        """
        Sets the dimensions of the object.

        Args:
            x_span (float): The rectangle's span along the x-axis (as if the rectangle was unrotated).
            y_span (float): The rectangle's span along the y-axis (as if the rectangle was unrotated).
            z_span (float): The rectangle's span along the z-axis (as if the rectangle was unrotated).

        Returns:
            None

        """
        super().set_dimensions(**kwargs)


class RectangleSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Rectangle structure type.
    """
    geometry: RectangleGeometry


class Rectangle(Structure):
    settings: RectangleSettings

    # region Dev. Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[RectangleKwargs]) -> None:
        super().__init__(name, sim)

        # Assign the settings module
        self.settings = RectangleSettings(self, RectangleGeometry)

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Rectangle structure type."""

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
            elif k in ["x_span", "y_span", "z_span"]:
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

    def _get_spans(self) -> NDArray[np.float64]:
        """
        Fetches the spans of the Rectangle.

        Returns:
            Three-element numpy vector with the x, y, and z spans. Units in meters.
        """
        return np.array([self._get("x span", float), self._get("y span", float), self._get("z span", float)],
                        dtype=np.float64)

    def _get_corners(self, absolute: bool = False) -> NDArray:

        # Fetch position and spans
        position = self._get_position(absolute)
        spans = self._get_spans()

        # Calculate half spans
        half_spans = spans / 2

        # Generate the 8 corners of the bounding box
        offsets = np.array([
            [-1, -1, -1], [1, -1, -1],
            [-1, 1, -1], [1, 1, -1],
            [-1, -1, 1], [1, -1, 1],
            [-1, 1, 1], [1, 1, 1],
        ], dtype=np.float64)

        # Factor in the position and spans
        corners = position + offsets * half_spans

        return corners

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        # Fetch absolute position
        position = convert_length(self._get_position(absolute), "m", units)
        spans = convert_length(self._get_spans(), "m", units)

        # Create a trimesh box
        polygon: trimesh.Trimesh = trimesh.creation.box(spans)
        polygon = polygon.apply_translation(position)

        # Rotate the trimesh if neccesary
        rectangle = self._rotate_trimesh(polygon, position)

        return rectangle

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)

        script = (
            "addrect();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('x span', {self._get("x span", float)});\n"
            f"set('y span', {self._get("y span", float)});\n"
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
    def x_span(self) -> float:
        return convert_length(self._get("x span", float), "m", self._units)

    @x_span.setter
    def x_span(self, span: float) -> None:
        validation.positive_number(span, "x_span")
        self._set("x span", convert_length(span, self._units, "m"))

    @property
    def y_span(self) -> float:
        return convert_length(self._get("y span", float), "m", self._units)

    @y_span.setter
    def y_span(self, span: float) -> None:
        validation.positive_number(span, "y_span")
        self._set("y span", convert_length(span, self._units, "m"))

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        validation.positive_number(span, "z_span")
        self._set("z span", convert_length(span, self._units, "m"))

    # endregion User Properties

    def copy(self, name, **kwargs: Unpack[RectangleKwargs]) -> Self:
        return super().copy(name, **kwargs)