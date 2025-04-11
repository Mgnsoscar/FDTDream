from __future__ import annotations

import math
from typing import TypedDict, Unpack, Union, Sequence, Self
from collections.abc import Sequence as Sqn

import numpy as np
import trimesh
from numpy.typing import NDArray
from shapely import Polygon

from .structure import Structure
from .settings import StructureSettings
from ..base_classes import BaseGeometry
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..resources import validation, Materials
from ..resources.functions import convert_length, bezier_curve
from ..resources.literals import AXES, LENGTH_UNITS

raise NotImplementedError("Waveguides are yet to be implemented in FDTDream v2.0.0.")


class WaveguideKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Waveguide structure type's constructor.
    """
    x: float
    y: float
    z: float
    poles: Sequence[Sequence[float, float]]
    base_width: float
    base_height: float
    base_angle: float
    top_width: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class WaveguideGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Waveguide structure type.
    """

    class _Dimensions(TypedDict, total=False):
        poles: Sequence[Sequence[float, float]]
        base_width: float
        base_height: float
        base_angle: float
        top_width: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        poles = kwargs.get("poles", None)
        base_width = kwargs.get("base_width", None)
        base_height = kwargs.get("base_height", None)
        base_angle = kwargs.get("base_angle", None)
        top_width = kwargs.get("top_width", None)

        if poles:
            if not (isinstance(poles, Sqn) and all(
                    isinstance(pt, Sqn) and len(pt) == 2 and
                    all(isinstance(coord, (int, float)) for coord in pt)
                    for pt in poles
            )):
                raise ValueError("`poles` must be a sequence of (x, y) float/int coordinate pairs.")

            poles = convert_length(np.array(poles), self._units, "m")

            self._set("poles", poles)

        if base_width is not None:
            if not isinstance(base_width, (int, float)):
                raise TypeError("`base_width` must be a number.")
            base_width = convert_length(base_width, self._units, "m")

        if base_height is not None:
            if not isinstance(base_height, (int, float)):
                raise TypeError("`base_height` must be a number.")
            base_height = convert_length(base_height, self._units, "m")

        if base_angle is not None:
            if not isinstance(base_angle, (int, float)):
                raise TypeError("`base_angle` must be a number.")
            if not (10 <= base_angle <= 90):
                raise ValueError("`base_angle` must be between 10 and 90 degrees.")
            base_angle = float(base_angle)

        if top_width is not None:
            if not isinstance(top_width, (int, float)):
                raise TypeError("`top_width` must be a number.")
            top_width = convert_length(top_width, self._units, "m")



class WaveguideSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Ring structure type.
    """
    geometry: WaveguideGeometry


class Waveguide(Structure):

    settings: WaveguideSettings

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[WaveguideKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign the settings module
        self.settings = WaveguideSettings(self, WaveguideGeometry)

        # Filter and apply kwargs
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Ring structure type."""

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
            elif k in ["base_width", "base_height", "base_angle", "top_width", "poles"]:
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

        theta_start = self._get("theta start", float)
        theta_stop = self._get("theta stop", float)
        outer_radius_x = self._get("outer radius", float)
        outer_radius_y = self._get("outer radius 2", float)
        inner_radius_x = self._get("inner radius", float)
        inner_radius_y = self._get("inner radius 2", float)
        x_center, y_center, z_center = self._get_position(absolute)
        z_span = self._get("z span", float)
        z_min = z_center - z_span / 2
        z_max = z_center + z_span / 2

        # Normalize angles to [0, 360)
        theta_start = theta_start % 360
        theta_stop = theta_stop % 360

        # Determine angles based on the start and stop
        if theta_start < theta_stop:
            # For normal ranges
            angles = [theta_start, theta_stop]
            # Add cardinal angles if they fall within the range
            for cardinal_angle in [0, 90, 180, 270]:
                if theta_start <= cardinal_angle <= theta_stop:
                    angles.append(cardinal_angle)
        else:
            # For wrap-around ranges (e.g., theta_start = 350, theta_stop = 10)
            angles = [theta_start, theta_stop]
            for cardinal_angle in [0, 90, 180, 270]:
                if cardinal_angle >= theta_start or cardinal_angle <= theta_stop:
                    angles.append(cardinal_angle)

        def polar_to_cartesian(radius_x, radius_y, theta, x_c, y_c):
            # Convert theta to radians for trigonometric calculations
            theta_rad = math.radians(theta)

            x = x_c + (math.cos(theta_rad) / np.sqrt((np.square(math.cos(theta_rad)) / np.square(radius_x))
                                                     + (np.square(math.sin(theta_rad)) / np.square(radius_y))))
            y = y_c + (math.sin(theta_rad) / np.sqrt((np.square(math.cos(theta_rad)) / np.square(radius_x))
                                                     + (np.square(math.sin(theta_rad)) / np.square(radius_y))))

            return x, y

        # Calculate points for the outer and inner edges
        outer_points = [polar_to_cartesian(outer_radius_x, outer_radius_y, angle, x_center, y_center) for angle in
                        angles]
        inner_points = [polar_to_cartesian(inner_radius_x, inner_radius_y, angle, x_center, y_center) for angle in
                        angles]

        # Collect all points and find min/max
        all_points = outer_points + inner_points
        min_y = max_y = min_x = max_x = all_points[0]

        for point in all_points:
            if point[0] < min_x[0]:
                min_x = point
            if point[0] > max_x[0]:
                max_x = point
            if point[1] > max_y[1]:
                max_y = point
            if point[1] < min_y[1]:
                max_y = point
        # Return corners at extremes
        return np.array([
            (*min_x, z_min), (*min_x, z_max), (*max_x, z_min), (*max_x, z_max),
            (*min_y, z_min), (*min_y, z_max), (*max_y, z_min), (*max_y, z_max)
            ])

    @staticmethod
    def _create_trapezoid(width_bottom, height, width_top=None, base_angle=None) -> Polygon:
        """
        Creates a 2D isosceles trapezoid or triangle centered at the origin.

        You can specify either:
        - width_top
        - or base_angle (in degrees), which overrides width_top

        If width_top becomes zero or less, returns a triangle instead.

        Returns:
            np.array of shape (3, 2) or (4, 2) defining the vertices
        """
        if base_angle is not None:
            # Convert angle to radians
            angle_rad = np.radians(90 - base_angle)
            offset = height * np.tan(angle_rad)
            width_top = width_bottom - 2 * offset

        if width_top is None:
            raise ValueError("You must specify either width_top or base_angle")

        half_wb = width_bottom / 2

        if width_top <= 0:
            # Triangle mode: apex at the center top
            return Polygon(np.array([
                [-half_wb, 0],
                [half_wb, 0],
                [0.0, -height]  # negative height
            ]))
        else:
            half_wt = width_top / 2
            # Trapezoid
            return Polygon(np.array([
                [-half_wb, 0],
                [half_wb, 0],
                [half_wt, -height],
                [-half_wt, -height]
            ]))

        # Loft mesh

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        poles = convert_length(self._get("poles", np.ndarray), "um", units)
        base_width = convert_length(self._get("Base Width", float), "um", units)
        base_height = convert_length(self._get("Base Height", float), "um", units)
        base_angle = self._get("Base Angle", float)

        trapezoid = self._create_trapezoid(base_width, base_height, base_angle)

        curve = bezier_curve(poles, num_points=100)
        mesh = trimesh.creation.sweep_polygon(trapezoid, np.array([[c[0], c[1], 0] for c in curve.coords]))

        # Translate the ring to its final position
        position = convert_length(self._get_position(absolute), "m", units)
        mesh = mesh.apply_translation(position)

        # Apply rotation if neccessary.
        mesh = self._rotate_trimesh(mesh, position)

        return mesh

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)

        script = (
            "addwaveguide();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('Base Width', {self._get('Base Width', float)});\n"
            f"set('Base Height', {self._get('Base Height', float)});\n"
            f"set('Base Angle', {self._get('Base Angle', float)});\n"
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
    def inner_radius(self) -> float:
        return convert_length(self._get("inner radius", float), "m", self._units)

    @inner_radius.setter
    def inner_radius(self, radius: float) -> None:
        validation.positive_number(radius, "inner radius")
        self._set("inner radius", convert_length(radius, self._units, "m"))

    @property
    def inner_radius_2(self) -> float:
        if self._get("make ellipsoid", bool):
            return convert_length(self._get("inner radius 2", float), "m", self._units)
        else:
            return convert_length(self._get("inner radius", float), "m", self._units)

    @inner_radius_2.setter
    def inner_radius_2(self, radius: float) -> None:
        validation.positive_number(radius, "radius")
        if not self._get("make ellipsoid", bool):
            self._set("make ellipsoid", True)
        self._set("inner radius 2", convert_length(radius, self._units, "m"))

    @property
    def outer_radius(self) -> float:
        return convert_length(self._get("outer radius", float), "m", self._units)

    @outer_radius.setter
    def outer_radius(self, radius: float) -> None:
        validation.positive_number(radius, "outer radius")
        self._set("outer radius", convert_length(radius, self._units, "m"))

    @property
    def outer_radius_2(self) -> float:
        if self._get("make ellipsoid", bool):
            return convert_length(self._get("outer radius 2", float), "m", self._units)
        else:
            return convert_length(self._get("outer radius", float), "m", self._units)

    @outer_radius_2.setter
    def outer_radius_2(self, radius: float) -> None:
        validation.positive_number(radius, "radius")
        if not self._get("make ellipsoid", bool):
            self._set("make ellipsoid", True)
        self._set("outer radius 2", convert_length(radius, self._units, "m"))

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        validation.positive_number(span, "z_span")
        self._set("z span", convert_length(span, self._units, "m"))

    @property
    def theta_start(self) -> float:
        return self._get("theta start", float)

    @theta_start.setter
    def theta_start(self, angle: float) -> None:
        validation.number(angle, "theta_start")
        self._set("theta start", angle % 360)

    @property
    def theta_stop(self) -> float:
        return self._get("theta stop", float)

    @theta_stop.setter
    def theta_stop(self, angle: float) -> None:
        validation.number(angle, "theta_stop")
        self._set("theta stop", angle % 360)

    # endregion User Properties

    def copy(self, name, **kwargs: Unpack[WaveguideKwargs]) -> Self:
        return super().copy(name, **kwargs)