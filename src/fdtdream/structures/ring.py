from __future__ import annotations

import math
from typing import TypedDict, Unpack, Union, Sequence, Self

import numpy as np
import trimesh
from numpy.typing import NDArray
from shapely import Polygon

from .structure import Structure
from .settings import StructureSettings
from ..base_classes import BaseGeometry
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..resources import validation, Materials
from ..resources.functions import convert_length
from ..resources.literals import AXES, LENGTH_UNITS


class RingKwargs(TypedDict, total=False):
    """
    Key-value pairs that can be used in the Ring structure type's constructor.
    """
    x: float
    y: float
    z: float
    inner_radius: float
    outer_radius: float
    inner_radius_2: float
    outer_radius_2: float
    theta_start: float
    theta_stop: float
    z_span: float
    rot_vec: AXES | Sequence[float]
    rot_angle: float
    rot_point: Sequence[float] | SimulationObjectInterface
    material: Materials
    material_index: Union[str, float]


class RingGeometry(BaseGeometry):
    """
    Setting module for geometry specific to the Ring structure type.
    """

    class _Dimensions(TypedDict, total=False):
        inner_radius: float
        outer_radius: float
        inner_radius_2: float
        outer_radius_2: float
        theta_start: float
        theta_stop: float
        z_span: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        ellipsoid = self._get("make ellipsoid", bool)
        if not ellipsoid:
            if any([k is not None for k in [kwargs.get("inner_radius_2", None), kwargs.get("outer_radius_2", None)]]):
                self._set("make ellipsoid", True)
        for degree in ["theta_start", "theta_stop"]:
            deg = kwargs.pop(degree, None)
            if deg is not None:
                self._set(degree.replace("_", " "), deg)

        super().set_dimensions(**kwargs)


class RingSettings(StructureSettings):
    """
    A module containing submodules for settings specific to the Ring structure type.
    """
    geometry: RingGeometry


class Ring(Structure):

    settings: RingSettings

    # region Dev Methods

    def __init__(self, name: str, sim: SimulationInterface, **kwargs: Unpack[RingKwargs]) -> None:
        super().__init__(name, sim, **kwargs)

        # Assign the settings module
        self.settings = RingSettings(self, RingGeometry)

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
            elif k in ["inner_radius", "outer_radius", "inner_radius_2", "outer_radius_2", "theta_start", "theta_stop",
                       "z_span"]:
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

    def _get_trimesh(self, absolute: bool = False, units: LENGTH_UNITS = None) -> trimesh.Trimesh:

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        # Fetch dimensions in correct units
        outer_radius = convert_length(self.outer_radius, self._units, units)
        inner_radius = convert_length(self.inner_radius, self._units, units)
        outer_radius_2 = convert_length(self.outer_radius_2, self._units, units)
        inner_radius_2 = convert_length(self.inner_radius_2, self._units, units)
        z_span = convert_length(self.z_span, self._units, units)
        theta_start = np.deg2rad(self.theta_start) % (2 * np.pi)
        theta_stop = np.deg2rad(self.theta_stop) % (2 * np.pi)

        # Create the outer and inner cylinders
        outer_cylinder = trimesh.creation.cylinder(radius=outer_radius, height=z_span, sections=128)
        inner_cylinder = trimesh.creation.cylinder(radius=inner_radius, height=z_span, sections=128)

        # Apply scaling for the second set of radii in the y-direction
        scale_matrix_outer = np.diag([1.0, outer_radius_2 / outer_radius, 1.0, 1.0])
        scale_matrix_inner = np.diag([1.0, inner_radius_2 / inner_radius, 1.0, 1.0])
        outer_cylinder.apply_transform(scale_matrix_outer)
        inner_cylinder.apply_transform(scale_matrix_inner)

        # Subtract the inner cylinder from the outer cylinder to create the ring
        ring = outer_cylinder.difference(inner_cylinder)

        # Create a 2D mask polygon using Shapely
        if theta_start != theta_stop:
            num_vertices = 64  # Number of vertices to approximate the curved edge

            angles = np.linspace(theta_start, theta_stop, num_vertices)
            outer_vertices = np.column_stack((np.cos(angles) * max(outer_radius, outer_radius_2) * 1.5,
                                              np.sin(angles) * max(outer_radius, outer_radius_2) * 1.5))
            mask_polygon = trimesh.path.polygons.Polygon(np.vstack(([0, 0], outer_vertices, [0, 0])))

            # Extrude the 2D polygon into a 3D mask volume
            mask_volume = trimesh.creation.extrude_polygon(mask_polygon, height=z_span * 2)

            # Translate the mask to align with the ring
            mask_volume.apply_translation([0, 0, -z_span])

            # Subtract the mask from the ring
            ring = ring.intersection(mask_volume)

        # Translate the ring to its final position
        position = convert_length(self._get_position(absolute), "m", units)
        ring = ring.apply_translation(position)

        # Apply rotation if neccessary.
        ring = self._rotate_trimesh(ring, position)

        return ring

    def _get_scripted(self, position: Sequence[float, float, float]) -> str:
        material = self._get("material", str)

        if self._get("make ellipsoid", bool):
            radius_2 = (f"set('make ellipsoid', true);\n"
                        f"set('outer radius 2', {self._get("outer radius 2", float)});\n"
                        f"set('inner radius 2', {self._get("inner radius 2", float)});\n")
        else:
            radius_2 = ""

        script = (
            "addring();\n"
            f"set('name', '{self._name}');\n"
            f"set('x', {position[0]});\n"
            f"set('y', {position[1]});\n"
            f"set('z', {position[2]});\n"
            f"set('outer radius', {self._get("outer radius", float)});\n"
            f"set('inner radius', {self._get("inner radius", float)});\n"
            f"{radius_2}"
            f"set('theta start', {self._get("theta start", float)});\n"
            f"set('theta stop', {self._get("theta stop", float)});\n"
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

    def copy(self, name, **kwargs: Unpack[RingKwargs]) -> Self:
        return super().copy(name, **kwargs)