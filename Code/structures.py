from __future__ import annotations

# Standard library imports
from typing import (Unpack, List, Tuple, Any, Callable, cast, TypeVar, TypedDict, ClassVar, Literal, Optional, Union,
                    Dict)
import re
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Third-party library imports
import numpy as np


# Local library imports
from Code.Resources.literals import MATERIALS, PARAMETER_TYPES, AXES
from Code.Resources.local_resources import convert_length, Validate, generate_random_hash
from base_classes import TSimulation, TSimulationObject, TStructure
from base_classes import Structure, Rotation, Group, Settings, RotateableSimulationObject
from geometry import (CircularGeometry, PolygonGeometryBase, TrippleSpannableGeometryRelative,
                      CircleGeometry, SphereGeometry, TrippleSpansKwargs, RingGeometry, PolygonGeometry,
                      EquilateralPolygonGeometry, PyramidGeometry, TrippleSpansProperties)
from base_classes import MeshBase as Mesh
from materials import MaterialSettings


########################################################################################################################
#                                             DATACLASSES
########################################################################################################################
@dataclass
class UserProperty(Settings):
    name: str
    value: Any


########################################################################################################################
#                                           CONSTANTS AND LITERALS
########################################################################################################################
class CircularStructureBase(Structure, ABC):
    class _SettingsCollection(Structure._SettingsCollection):
        geometry: CircularGeometry
        __slots__ = Structure._SettingsCollection.__slots__

    settings: _SettingsCollection
    __slots__ = Structure.__slots__

    @property
    def radius(self) -> float:
        return convert_length(self._get_parameter("radius", "float"),
                              from_unit="m", to_unit=self._simulation.__getattribute__("_global_units"))

    @radius.setter
    def radius(self, radius: float) -> None:
        self.settings.geometry.set_radius(radius=radius)

    @property
    def make_ellipsoid(self) -> None:
        return self._get_parameter("make ellipsoid", "bool")

    @make_ellipsoid.setter
    def make_ellipsoid(self, true_or_false: bool) -> None:
        self.settings.geometry.make_ellipsoid(true_or_false)

    @property
    def radius_2(self) -> float:
        return convert_length(self._get_parameter("radius 2", "float"),
                              from_unit="m", to_unit=self._simulation.__getattribute__("_global_units"))

    @radius_2.setter
    def radius_2(self, radius_2: float) -> None:
        self.settings.geometry.set_radius(radius_2=radius_2)


TPolygon = TypeVar("TPolygon", bound="PolygonStructureBase")


class PolygonStructureBase(Structure, ABC):
    class _SettingsCollection(Structure._SettingsCollection):
        geometry: PolygonGeometryBase
        __slots__ = Structure._SettingsCollection.__slots__

    settings: _SettingsCollection
    _nr_sides: int
    __slots__ = Structure.__slots__ + ["_n_sides"]

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter("z span", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.settings.geometry.set_z_span(z_span)

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        # Retrieve vertices and z_span
        vertices = self._get_parameter("vertices", "list")
        z_span = self._get_parameter("z span", "float")

        # Initialize variables to track min/max x and y
        x_min = y_min = float("inf")
        x_max = y_max = float("-inf")

        # Find the extremal vertices in the x and y directions
        for x, y in vertices:
            if x < x_min:
                x_min = x
            if x > x_max:
                x_max = x
            if y < y_min:
                y_min = y
            if y > y_max:
                y_max = y

        # Calculate z_min and z_max based on z_span
        z_center = self._get_parameter("z", "float")  # Assuming center z-coordinate is provided
        z_min = z_center - (z_span / 2)
        z_max = z_center + (z_span / 2)

        # Create list of the extreme corners in each direction
        return [
            (x_min, y_min, z_min), (x_min, y_min, z_max),
            (x_min, y_max, z_min), (x_min, y_max, z_max),
            (x_max, y_min, z_min), (x_max, y_min, z_max),
            (x_max, y_max, z_min), (x_max, y_max, z_max)
        ]


########################################################################################################################
#                                             CLASSES FOR STRUCTURE OBJECTS
########################################################################################################################


class Rectangle(Structure, TrippleSpansProperties):
    class _SettingsCollection(Structure._SettingsCollection):
        _settings = [TrippleSpannableGeometryRelative, MaterialSettings, Rotation]
        _settings_names = ["geometry", "material", "rotations"]

        geometry: TrippleSpannableGeometryRelative
        material: MaterialSettings
        __slots__ = Structure._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        x_span: float
        y_span: float
        z_span: float
        material: MATERIALS
        index: Optional[Union[str, float]]

    @dataclass
    class _Settings(Structure._Settings):
        geometry_settings: TrippleSpannableGeometryRelative._Settings

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = Structure.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[_Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    def _get_corners(self) -> List[np.ndarray]:
        x_min = self._get_parameter("x min", "float")
        x_max = self._get_parameter("x max", "float")
        y_min = self._get_parameter("y min", "float")
        y_max = self._get_parameter("y max", "float")
        z_min = self._get_parameter("z min", "float")
        z_max = self._get_parameter("z max", "float")

        return [np.array([x_min, y_min, z_min]), np.array([x_min, y_min, z_max]),
                np.array([x_min, y_max, z_min]), np.array([x_min, y_max, z_max]),
                np.array([x_max, y_min, z_min]), np.array([x_max, y_min, z_max]),
                np.array([x_max, y_max, z_min]), np.array([x_max, y_max, z_max])]

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


class Circle(CircularStructureBase):
    class _SettingsCollection(CircularStructureBase._SettingsCollection):
        _settings = [CircleGeometry, MaterialSettings, Rotation]
        _settings_names = ["geometry", "material", "rotations"]

        geometry: CircleGeometry
        __slots__ = CircularStructureBase._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        radius: float
        radius_2: float
        z_span: float
        material: MATERIALS
        index: Optional[Union[str, float]]

    @dataclass
    class _Settings(CircularStructureBase._Settings):
        geometry_settings: CircleGeometry

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = CircularStructureBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[Circle._Kwargs]) -> None:
        kwargs = dict(**kwargs)
        if kwargs.get("radius_2"):
            kwargs["make_ellipsoid"] = True
        else:
            kwargs["make_ellipsoid"] = False
        super().__init__(name, simulation, **kwargs)

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        # Fetch the parameters for radius, radius_2, and z_span, and center position
        radius = self._get_parameter("radius", "float")
        radius_2 = self._get_parameter("radius 2", "float")
        z_span = self._get_parameter("z span", "float")

        # Fetch center coordinates
        x_center = self._get_parameter("x", "float")
        y_center = self._get_parameter("y", "float")
        z_center = self._get_parameter("z", "float")

        # Calculate min and max coordinates based on radius, radius_2, and z_span
        x_min, x_max = x_center - radius, x_center + radius
        y_min, y_max = y_center - radius_2, y_center + radius_2
        z_min, z_max = z_center - (z_span / 2), z_center + (z_span / 2)

        # Return list of corners
        return [
            (x_min, y_center, z_min), (x_min, y_center, z_max),
            (x_max, y_center, z_min), (x_max, y_center, z_max),
            (x_center, y_min, z_min), (x_center, y_min, z_max),
            (x_center, y_max, z_min), (x_center, y_max, z_max)
        ]

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter("z span", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.settings.geometry.set_z_span(z_span)

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


class Sphere(CircularStructureBase):
    class _SettingsCollection(CircularStructureBase._SettingsCollection):
        _settings = [SphereGeometry, MaterialSettings, Rotation]
        _settings_names = ["geometry", "material", "rotations"]

        geometry: SphereGeometry
        __slots__ = CircularStructureBase._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        radius: float
        radius_2: float
        radius_3: float
        material: MATERIALS
        index: Optional[Union[str, float]]

    @dataclass
    class _Settings(CircularStructureBase._Settings):
        geometry_settings: SphereGeometry

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = CircularStructureBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[Sphere._Kwargs]):
        kwargs = dict(**kwargs)
        if kwargs.get("radius_2") or kwargs.get("radius_3"):
            kwargs["make_ellipsoid"] = True
        else:
            kwargs["make_ellipsoid"] = False
        super().__init__(name, simulation, **kwargs)

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        # Retrieve radii for the ellipsoid (or sphere if all are equal)
        radius_x = self._get_parameter("radius", "float")
        radius_y = self._get_parameter("radius 2", "float")
        radius_z = self._get_parameter("radius 3", "float")

        # Get the center position of the sphere/ellipsoid
        x_center = self._get_parameter("x", "float")
        y_center = self._get_parameter("y", "float")
        z_center = self._get_parameter("z", "float")

        # Calculate min/max for each axis based on center and radii
        x_min = x_center - radius_x
        x_max = x_center + radius_x
        y_min = y_center - radius_y
        y_max = y_center + radius_y
        z_min = z_center - radius_z
        z_max = z_center + radius_z

        # Return the extreme corners in each direction
        return [
            (x_min, y_center, z_center), (x_max, y_center, z_center),
            (x_center, y_min, z_center), (x_center, y_max, z_center),
            (x_center, y_center, z_min), (x_center, y_center, z_max)
        ]

    @property
    def radius_3(self) -> float:
        return convert_length(self._get_parameter("radius 3", "float"),
                              from_unit="m", to_unit=self._simulation.__getattribute__("_global_units"))

    @radius_3.setter
    def radius_3(self, radius_3: float) -> None:
        self.settings.geometry.set_radius(radius_3=radius_3)

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


class Ring(Structure):
    class _SettingsCollection(Structure._SettingsCollection):
        _settings = [RingGeometry, MaterialSettings, Rotation]
        _settings_names = ["geometry", "material", "rotations"]

        geometry: RingGeometry
        __slots__ = Structure._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        outer_radius: float
        inner_radius: float
        outer_radius_2: float
        inner_radius_2: float
        theta_start: float
        theta_stop: float
        z_span: float
        material: MATERIALS
        index: float | str

    @dataclass
    class _Settings(Structure._Settings):
        geometry_settings: RingGeometry

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = Structure.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[Ring._Kwargs]) -> None:
        kwargs = dict(**kwargs)
        if kwargs.get("inner_radius_2") or kwargs.get("outer_radius_2"):
            kwargs["make_ellipsoid"] = True
        else:
            kwargs["make_ellipsoid"] = False
        super().__init__(name, simulation, **kwargs)

    def _get_corners(self) -> List[Tuple[float, float]]:
        theta_start = self._get_parameter("theta start", "float")
        theta_stop = self._get_parameter("theta stop", "float")
        outer_radius_x = self._get_parameter("outer radius", "float")
        outer_radius_y = self._get_parameter("outer radius 2", "float")
        inner_radius_x = self._get_parameter("inner radius", "float")
        inner_radius_y = self._get_parameter("inner radius 2", "float")
        x_center = self._get_parameter("x", "float")
        y_center = self._get_parameter("y", "float")
        z_center = self._get_parameter("z", "float")
        z_span = self._get_parameter("z span", "float")
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

        def polar_to_cartesian(radius_x, radius_y, theta, x_center, y_center):
            # Convert theta to radians for trigonometric calculations
            theta_rad = math.radians(theta)

            x = x_center + (math.cos(theta_rad) / np.sqrt((np.square(math.cos(theta_rad)) / np.square(radius_x))
                                                          + (np.square(math.sin(theta_rad)) / np.square(radius_y))))
            y = y_center + (math.sin(theta_rad) / np.sqrt((np.square(math.cos(theta_rad)) / np.square(radius_x))
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
            # print(point)
            # point = [float(point[0]), float(point[1])]
            if point[0] < min_x[0]:
                min_x = point

            if point[0] > max_x[0]:
                max_x = point

            if point[1] > max_y[1]:
                max_y = point

            if point[1] < min_y[1]:
                max_y = point

        # Return corners at extremes
        return [
            (*min_x, z_min), (*min_x, z_max), (*max_x, z_min), (*max_x, z_max),
            (*min_y, z_min), (*min_y, z_max), (*max_y, z_min), (*max_y, z_max)
        ]

    @property
    def outer_radius(self) -> float:
        return convert_length(self._get_parameter("outer radius", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @outer_radius.setter
    def outer_radius(self, outer_radius: float) -> None:
        self.settings.geometry.set_radius(outer_radius=outer_radius)

    @property
    def inner_radius(self) -> float:
        return convert_length(self._get_parameter("inner radius", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @inner_radius.setter
    def inner_radius(self, inner_radius: float) -> None:
        self.settings.geometry.set_radius(inner_radius=inner_radius)

    @property
    def outer_radius_2(self) -> float:
        return convert_length(self._get_parameter("outer radius 2", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @outer_radius_2.setter
    def outer_radius_2(self, outer_radius_2: float) -> None:
        self.settings.geometry.set_radius(outer_radius_2=outer_radius_2)

    @property
    def inner_radius_2(self) -> float:
        return convert_length(self._get_parameter("inner radius 2", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @inner_radius_2.setter
    def inner_radius_2(self, inner_radius_2: float) -> None:
        self.settings.geometry.set_radius(inner_radius_2= inner_radius_2)

    @property
    def theta_start(self) -> float:
        return self._get_parameter("theta start", "float")

    @theta_start.setter
    def theta_start(self, theta_start: float) -> None:
        self.settings.geometry.set_theta_start(theta_start)

    @property
    def theta_stop(self) -> float:
        return self._get_parameter("theta stop", "float")

    @theta_stop.setter
    def theta_stop(self, theta_stop: float) -> None:
        self.settings.geometry.set_theta_stop(theta_stop)

    @property
    def make_ellipsoid(self) -> bool:
        return self._get_parameter("make ellipsoid", "bool")

    @make_ellipsoid.setter
    def make_ellipsoid(self, true_or_false: bool) -> None:
        self.settings.geometry.make_ellipsoid(true_or_false)

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


class Polygon(PolygonStructureBase):
    class _SettingsCollection(PolygonStructureBase._SettingsCollection):
        _settings = [PolygonGeometry, MaterialSettings, Rotation]
        _settings_names = ["geometry", "material", "rotations"]

        geometry: PolygonGeometry
        __slots__ = PolygonStructureBase._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        vertices: List[Tuple[float, float]]
        z_span: float
        material: MATERIALS
        index: float | str

    @dataclass
    class _Settings(PolygonStructureBase._Settings):
        geometry_settings: PolygonGeometry

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = PolygonStructureBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[Polygon._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    @property
    def vertices(self) -> List[Tuple[float, float]]:
        return self._get_parameter("vertices", "list")

    @vertices.setter
    def vertices(self, vertices: List[Tuple[float, float]]) -> None:
        self.settings.geometry.set_vertices(vertices)

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


class EquilateralPolygon(PolygonStructureBase):
    class _SettingsCollection(PolygonStructureBase._SettingsCollection):
        _settings = [EquilateralPolygonGeometry, MaterialSettings, Rotation]
        _settings_names = ["geometry", "material", "rotations"]

        geometry: EquilateralPolygonGeometry
        __slots__ = PolygonStructureBase._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        z_span: float
        radius: float
        side_length: float
        material: MATERIALS
        index: float | str

    @dataclass
    class _Settings(PolygonStructureBase._Settings):
        geometry_settings: EquilateralPolygonGeometry

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = PolygonStructureBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, nr_sides: int,
                 **kwargs: Unpack[EquilateralPolygon._Kwargs]) -> None:
        self._nr_sides = nr_sides
        if kwargs.get("radius", None) is None and kwargs.get("side_length", None) is None:
            kwargs["radius"] = 100
        super().__init__(name, simulation, **kwargs)

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter("z span", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.settings.geometry.set_z_span(z_span)

    @property
    def side_length(self) -> float:
        vertices = self._get_parameter("vertices", "list")
        return self.settings.geometry.__getattribute__("_get_side_length_and_radius")(vertices)[0]

    @side_length.setter
    def side_length(self, side_length: float) -> None:
        self.settings.geometry.set_side_length(side_length)

    @property
    def radius(self) -> float:
        vertices = self._get_parameter("vertices", "list")
        return self.settings.geometry.__getattribute__("_get_side_length_and_radius")(vertices)[1]

    @radius.setter
    def radius(self, radius: float) -> None:
        self.settings.geometry.set_radius(radius)

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


class Pyramid(Structure):
    class _SettingsCollection(Structure._SettingsCollection):
        _settings = [PyramidGeometry, MaterialSettings, Rotation]
        _settings_names = ["geometry", "material", "rotations"]

        geometry: PyramidGeometry
        __slots__ = Structure._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        x_span_top: float
        x_span_bottom: float
        y_span_top: float
        y_span_bottom: float
        z_span: float
        material: MATERIALS
        index: float | str

    @dataclass
    class _Settings(Structure._Settings):
        geometry_settings: PyramidGeometry

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = Structure.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[Pyramid._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        z_center = self._get_parameter("z", "float")
        z_span = self._get_parameter("z span", "float")
        z_min = z_center - z_span / 2
        z_max = z_center + z_span / 2
        x_span_bottom = self._get_parameter("x span bottom", "float")
        y_span_bottom = self._get_parameter("y span bottom", "float")
        x_span_top = self._get_parameter("x span top", "float")
        y_span_top = self._get_parameter("y span top", "float")
        x_center = self._get_parameter("x", "float")
        y_center = self._get_parameter("y", "float")

        return [
            (x_center - x_span_bottom / 2, y_center - y_span_bottom / 2, z_min),
            (x_center - x_span_top / 2, y_center - y_span_top / 2, z_max),
            (x_center - x_span_bottom / 2, y_center + y_span_bottom / 2, z_min),
            (x_center - x_span_top / 2, y_center + y_span_top / 2, z_max),
            (x_center + x_span_bottom / 2, y_center - y_span_bottom / 2, z_min),
            (x_center + x_span_top / 2, y_center - y_span_top / 2, z_max),
            (x_center + x_span_bottom / 2, y_center + y_span_bottom / 2, z_min),
            (x_center + x_span_top / 2, y_center + y_span_top / 2, z_max)
        ]

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter("z span", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.settings.geometry.set_spans(z_span=z_span)

    @property
    def x_span_bottom(self) -> float:
        return convert_length(self._get_parameter("x span bottom", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @x_span_bottom.setter
    def x_span_bottom(self, x_span_bottom: float) -> None:
        self.settings.geometry.set_spans(x_span_bottom=x_span_bottom)

    @property
    def x_span_top(self) -> float:
        return convert_length(self._get_parameter("x span top", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @x_span_top.setter
    def x_span_top(self, x_span_top: float) -> None:
        self.settings.geometry.set_spans(x_span_top=x_span_top)

    @property
    def y_span_bottom(self) -> float:
        return convert_length(self._get_parameter("y span bottom", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @y_span_bottom.setter
    def y_span_bottom(self, y_span_bottom: float) -> None:
        self.settings.geometry.set_spans(y_span_bottom=y_span_bottom)

    @property
    def y_span_top(self) -> float:
        return convert_length(self._get_parameter("y span top", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @y_span_top.setter
    def y_span_top(self, y_span_top: float) -> None:
        self.settings.geometry.set_spans(y_span_top=y_span_top)

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())

########################################################################################################################
#                                              CLASSES FOR STRUCTURE GROUPS
########################################################################################################################


class LayoutGroup(Group):
    class _SettingsCollection(Group._SettingsCollection):
        _settings = [TrippleSpannableGeometryRelative]
        _settings_names = ["geometry"]

        geometry: TrippleSpannableGeometryRelative
        __slots__ = Group._SettingsCollection.__slots__ + _settings_names

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = Group.__slots__ + _settings_names

    @property
    def grouped_objects(self) -> List[TSimulationObject]:
        return self._grouped_objects

    def _get_active_parameters(self) -> None:
        return None


class StructureGroup(Group):

    class _SettingsCollection(Group._SettingsCollection):
        _settings = [TrippleSpannableGeometryRelative, Rotation]
        _settings_names = ["geometry", "rotations"]

        rotations: Rotation
        geometry: TrippleSpannableGeometryRelative
        __slots__ = Group._SettingsCollection.__slots__ + _settings_names

    @dataclass
    class _SettingsDict(Settings):
        user_properties: List[UserProperty]
        grouped_objects: List[TSimulationObject]

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    _grouped_objects: List[TStructure | StructureGroup]
    settings: _SettingsCollection
    __slots__ = Group.__slots__ + _settings_names

    @property
    def grouped_objects(self) -> List[TStructure | StructureGroup]:
        return self._grouped_objects

    def set_as_construction_group(self, true_or_false: bool) -> None:
        Validate.boolean(true_or_false, "true_or_false")
        self._simulation.__getattribute__("_lumapi").setnamed(self.name, "construction group", true_or_false)
        script = self._get_parameter("script", "str")
        if not true_or_false:
            if script.startswith("deleteall;\n"):
                script = script[len("deleteall;\n"):]
            self._set_parameter("script", "", "str")

    def add(self, simulation_object: TSimulationObject | StructureGroup,
            use_relative_coordinates: bool = None) -> None:

        if self._get_parameter("construction group", "bool"):
            raise ValueError(
                f"The structure group '{self.name}' has the 'construction group' flag enabled, meaning structures "
                f"can only be added and modified through the script parameter. Use 'set_as_construction_group(False)' "
                f"to disable this flag."
            )
        super().add(simulation_object, use_relative_coordinates)

    def set_script(self, script: str):
        is_construction_group = self._get_parameter("construction group", "bool")
        if is_construction_group:
            script = "deleteall;\n" + script
        else:
            raise ValueError(
                f"You should not set a script for a structure group that is not set as a construction group."
                f"This can lead to all kinds of unintended behaviour. Use the 'set_as_construction_group()' method."
            )
        self._set_parameter("script", script, "str")

    def get_script(self) -> str:
        """Returns the current scipt """
        is_construction_group = self._get_parameter("construction_group", "bool")
        if is_construction_group:
            return self._get_parameter("script", "str")
        return ""

    def get_user_properties(self) -> List[UserProperty]:
        properties = self._simulation.__getattribute__("_lumapi").getnamed(self.name).splitlines()
        non_user_properties = ["enabled", "first axis", "name", "rotation 1", "rotation 2", "rotation 3",
                               "script", "second axis", "third axis", "type", "use relative coordinates",
                               "x", "y", "z"]
        user_properties = [property_ for property_ in properties if property_ not in non_user_properties]
        properties_list = []
        for user_property in user_properties:
            prop = UserProperty(hash=None, name=user_property, value=self._get_parameter(user_property, "str"))
            prop.fill_hash_fields()
            properties_list.append(prop)
        return properties_list

    def set_property(self, property_name: str, value: Any) -> None:
        self._simulation.__getattribute__("_lumapi").setnamed(self.name, property_name, value)

    def _get_active_parameters(self) -> _SettingsDict:

        # Save temporary file to make sure all script come active
        save_temp: Callable[[], None] = getattr(self._simulation, "_save_temp")
        save_temp()

        typed_dict = StructureGroup._SettingsDict
        settings = typed_dict(**{param: None for param in typed_dict.__annotations__})

        settings.grouped_objects = []

        was_construction_group = self._get_parameter("construction group", "bool")
        prev_script = self._get_parameter("script", "str")

        # Set as not a construction group to allow changes to structures within group
        self.set_as_construction_group(False)

        def iterate_though_objects() -> None:

            sim = self._simulation.__getattribute__("_lumapi")

            # Select the provided group as the groupscope and select all objects in it
            sim.groupscope(self.name)
            sim.selectall()
            num_objects = int(sim.getnumber())

            # Iterate through all the objects in the group
            for i in range(num_objects):

                prev_name = sim.get("name", i + 1)
                type_ = sim.get("type", i + 1)
                name = generate_random_hash(16)  # Name very unlikely allready in the sim
                i = 0
                while name in self._simulation.__getattribute__("_active_objects").used_names:
                    name = generate_random_hash(16)
                sim.set("name", name, i + 1)

                if type_ in ["Layout Group", "Structure Group"]:
                    group_object = TYPE_TO_STRUCTURE_MAP[type_](name, sim)
                    setattr(group_object, "_group", self)
                    sim.groupscope(self.name)
                    sim.selectall()
                    settings.grouped_objects.extend(group_object)
                    sim.set("name", prev_name, i + 1)  # Reset the name

                else:
                    simulation_object = TYPE_TO_STRUCTURE_MAP[type_](name, sim)
                    simulation_object._group = self
                    settings.grouped_objects.append(simulation_object)
                    sim.groupscope(self.name)
                    sim.selectall()
                    sim.set("name", prev_name, i + 1)  # Reset the name

        iterate_though_objects()

        self_scope = self.name.split("::")
        self_scope = self_scope[:-1]
        parent_scope = "::" + "::".join(self_scope)
        if parent_scope.endswith("::"):
            parent_scope = parent_scope[:-2]
        self._simulation.__getattribute__("_lumapi").groupscope(parent_scope)

        # Reset construction group to previous settings
        self.set_as_construction_group(was_construction_group)
        if was_construction_group:
            self.set_script(prev_script)

        return settings


########################################################################################################################
#                                              PHOTONIC CRYSTALS
########################################################################################################################
class CrystalBaseStructure:

    class _RectangleKwargs(TypedDict, total=False):
        x_span: float
        y_span: float
        z_span: float
        material: MATERIALS
        index: float | str

    class _CircleKwargs(TypedDict, total=False):
        radius: float
        radius_2: float
        z_span: float
        material: MATERIALS
        index: float | str

    class _SphereKwargs(TypedDict, total=False):
        radius: float
        radius_2: float
        radius_3: float
        material: MATERIALS
        index: float | str

    class _RingKwargs(TypedDict, total=False):
        outer_radius: float
        inner_radius: float
        outer_radius_2: float
        inner_radius_2: float
        z_span: float
        material: MATERIALS
        index: float | str

    class _PyramidKwargs(TypedDict, total=False):
        x_span_bottom: float
        y_span_bottom: float
        x_span_top: float
        y_span_top: float
        z_span: float
        material: MATERIALS
        index: float | str

    __slots__ = ["_crystal", "_simulation", "_current_settings", "_clear_base_structure", "_insert_command",
                 "_create_grid", "_creation"]

    def __init__(self, crystal: PhotonicCrystal):
        self._crystal = crystal
        self._simulation: TSimulation = crystal.__getattribute__("_simulation")
        self._current_settings = {"type": "Rectangle",
                                  "x_span": 200,
                                  "y_span": 200,
                                  "z_span": 200,
                                  "material": "<Object defined dielectric>",
                                  "index": None,
                                  "convertable": ["x_span", "y_span", "z_span"]}
        self._clear_base_structure: Callable = crystal.__getattribute__("_clear_base_structure")
        self._insert_command: Callable[[str, str, str], None] = crystal.__getattribute__("_insert_command")
        self._create_grid: Callable = crystal.__getattribute__("_create_grid")
        self._creation = True

    def _apply_kwargs(self, typed_dict, defaults, **kwargs):

        kwargs = {**kwargs}
        convertable = defaults.pop("convertable")
        for k in typed_dict.__annotations__.keys():
            value = kwargs.get(k, None)
            if value is None:
                value = defaults.get(k)
                if value is None:
                    continue

            if k in convertable:
                value = convert_length(value, self._simulation._global_units, "m")
            elif isinstance(value, str):
                if not value.startswith("'") and not value.endswith("'"):
                    value = f"'{value}'"

            command = f"set('{k.replace("_", " ")}', {value});"
            if k in convertable:
                value = convert_length(value, "m", self._simulation._global_units)
            self._current_settings[k] = value
            self._insert_command("BASE_STRUCTURE", command, k.upper())

        self._current_settings["convertable"] = convertable
        self._crystal.__getattribute__("_update")()

    def _get_spans(self):

        structure = self._current_settings.get("type")

        if structure == "Rectangle":
            x_span = self._current_settings.get("x_span")
            y_span = self._current_settings.get("y_span")
            z_span = self._current_settings.get("z_span")
        elif structure == "Circle":
            x_span = self._current_settings.get("radius") * 2
            y_span = self._current_settings.get("radius_2")
            if y_span is None:
                y_span = x_span
            else:
                y_span *= 2
            z_span = self._current_settings.get("z_span")
        else:
            raise ValueError("Unexpected structure type.")

        return x_span, y_span, z_span

    def rectangle(self, **kwargs: Unpack[_RectangleKwargs]) -> None:

        if self._current_settings.get("type", None) == "Rectangle":
            defaults = self._current_settings
        else:
            defaults = {"type": "Rectangle",
                        "x_span": 200,
                        "y_span": 200,
                        "z_span": 200,
                        "material": "<Object defined dielectric>",
                        "index": None,
                        "convertable": ["x_span", "y_span", "z_span"]}
            defaults.update(kwargs)  # type: ignore
            if defaults.get("material") != "<Object defined dielectric>":
                self._crystal._remove_command("BASE_STRUCTURE", "INDEX")
            self._current_settings = {"type": "Rectangle", "convertable": ["x_span", "y_span", "z_span"]}


        self._clear_base_structure()
        self._insert_creation_command()
        self._apply_kwargs(self._RectangleKwargs, defaults, **kwargs)
        if self._creation:
            self._create_grid()

    def _insert_creation_command(self) -> None:
        if self._current_settings.get("type") == "Rectangle":
            self._insert_command("BASE_STRUCTURE", "addrect(); set('name', 'BASE_STRUCTURE');", "CREATION COMMAND")
        elif self._current_settings.get("type") == "Circle":
            self._insert_command("BASE_STRUCTURE", "addcircle(); set('name', 'BASE_STRUCTURE'); "
                                                   "set('make ellipsoid', true);", "CREATION COMMAND")

    def circle(self, **kwargs: Unpack[_CircleKwargs]) -> None:

        if self._current_settings.get("type", None) == "Circle":
            defaults = self._current_settings
        else:
            defaults = {"type": "Circle",
                        "radius": 200,
                        "radius_2": None,
                        "material": "<Object defined dielectric>",
                        "index": None,
                        "convertable": ["radius", "radius_2", "z_span"]}
            defaults.update(kwargs)  # type: ignore
            if defaults.get("material") != "<Object defined dielectric>":
                self._crystal._remove_command("BASE_STRUCTURE", "INDEX")
            self._current_settings = {"type": "Circle", "convertable": ["x_span", "y_span", "z_span"]}

        if defaults.get("radius_2") is None:
            defaults["radius_2"] = defaults.get("radius")

        self._clear_base_structure()
        self._insert_creation_command()
        self._apply_kwargs(self._CircleKwargs, defaults, **kwargs)
        if self._creation:
            self._create_grid()


class PhotonicCrystal(RotateableSimulationObject, ABC):

    _settings = []
    _settings_names = []
    _default_values: ClassVar = {"pitch_x": 200., "pitch_y": 200., "rows": 2, "columns": 2}

    _bulk_mesh: Mesh
    set_structure: CrystalBaseStructure
    _script: str
    __slots__ = RotateableSimulationObject.__slots__ + ["set_structure", "_script", "_bulk_mesh"]

    def __init__(self, name: str, simulation: TSimulation, **kwargs) -> None:

        pitch_x = kwargs.pop("pitch_x", None)
        pitch_y = kwargs.pop("pitch_y", None)
        rows = kwargs.pop("rows", None)
        columns = kwargs.pop("columns", None)
        super().__init__(name, simulation, **kwargs)
        self._set_as_construction_group()

        if columns is not None:
            Validate.positive_integer(columns, "columns")
            self._default_values["columns"] = columns  # type: ignore
        if rows is not None:
            Validate.positive_integer(rows, "rows")
            self._default_values["rows"] = rows  # type: ignore
        if pitch_x is not None:
            Validate.number(pitch_x, "pitch_x")
            self._default_values["pitch_x"] = pitch_x  # type: ignore
        if pitch_y is not None:
            Validate.number(pitch_y, "pitch_y")
            self._default_values["pitch_y"] = pitch_y  # type: ignore

        self.set_structure = CrystalBaseStructure(self)

    @property
    def pitch_x(self) -> float:
        return self._default_values["pitch_x"]

    @property
    def pitch_y(self) -> float:
        return self._default_values["pitch_y"]

    @property
    def x_span(self) -> float:
        bounding = self._get_bounding_box()
        return float(bounding[1][0] - bounding[0][0])

    @property
    def y_span(self) -> float:
        bounding = self._get_bounding_box()
        return float(bounding[1][1] - bounding[0][1])

    @property
    def z_span(self) -> float:
        bounding = self._get_bounding_box()
        return float(bounding[1][2] - bounding[0][2])

    @property
    def unit_cell_x(self) -> float:
        return self.set_structure._get_spans()[0] + self._default_values.get("pitch_x")

    @property
    def unit_cell_y(self) -> float:
        return self.set_structure._get_spans()[1] + self._default_values.get("pitch_y")

    @property
    def bulk_mesh(self) -> Optional[Mesh]:
        return self._bulk_mesh

    def place_on_top_of(self, obj: TSimulationObject, offset: float = 0) -> None:
        """
        Places the current structure directly on top of another structure.

        This method adjusts the z-coordinate of the current structure such that its `z_min`
        aligns with the `z_max` of the specified `structure`. An optional `offset` can be
        applied to introduce additional spacing between the two structures.

        Args:
            obj (TStructure): The structure on top of which the current structure
                                    will be placed.
            offset (float, optional): Additional spacing to apply between the two structures
                                      along the z-axis. Defaults to 0.

        Raises:
            AttributeError: If the provided `structure` does not have a `z_max` property.

        Behavior:
            - Calculates the `z_min` position of the current structure based on the `z_max`
              of the provided `structure`.
            - Updates the z-coordinate of the current structure such that it sits on top of
              the provided `structure`, with the specified `offset` applied.
            - The x and y coordinates of the current structure remain unchanged.

        Example:
            If `structure` has a `z_max` of 100, and the current structure has a `z_span`
            (z_max - z_min) of 20, calling:
                `place_on_top_of(structure, offset=5)`
            will position the current structure such that its `z_min` is at 105 (100 + 5),
            and its `z_max` is at 125.
        """
        self.z = obj.z_max + ((self.z_max - self.z_min) / 2) + offset

    def place_next_to(self, obj: TSimulationObject,
                      boundary: Literal["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"],
                      offset: float = 0) -> None:
        """
        Places the current structure adjacent to the specified boundary of another simulation object.

        This method adjusts the position of the current structure such that its designated boundary
        (e.g., x_min, x_max, etc.) is placed adjacent to the specified boundary of the given simulation
        object (`obj`). The `offset` argument can be used to introduce additional spacing between the
        two objects. The coordinates along the axes not specified in the `boundary` argument will remain
        unchanged.

        Args:
            obj (TSimulationObject): The simulation object to position this structure next to.
            boundary (Literal["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]):
                The boundary of the current structure to align with the corresponding boundary of
                the target object (`obj`). For example:
                    - "x_min": Align this structure's minimum x-boundary.
                    - "x_max": Align this structure's maximum x-boundary.
                    - Similar behavior for "y_min", "y_max", "z_min", "z_max".
            offset (Optional[float]):
                            The additional distance to place between the two objects along the
                            specified axis. Positive values increase the spacing, while negative
                            values overlap the objects. Default value is zero.

        Raises:
            ValueError: If the provided `boundary` is not a valid boundary literal.

        Behavior:
            - Determines the position of the specified `boundary` of the target object (`obj`).
            - Calculates the new position of the current structure based on its span along the
              specified axis and the given offset.
            - Updates the position of the current structure to ensure it is adjacent to the
              target object's boundary, without altering its coordinates on the other axes.

        Example:
            If `obj` is positioned such that its `x_max` is at 100, and the current structure's
            `x_span` is 20, calling this method with:
                `place_next_to(obj, "x_max", offset=5)`
            will place the current structure such that its `x_min` is at 105 (100 + 5).
            The `y` and `z` coordinates of the current structure will remain unchanged.
        """

        Validate.in_literal(boundary, "boundary", Literal["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"])
        axis = boundary[0]
        min_ = -1 if boundary[2:] == "min" else 1

        obj_extreme = obj.__getattribute__(boundary)
        new_position = obj_extreme + (min_ * self.__getattribute__(f"{axis}_span") / 2) + offset
        self.__setattr__(f"{axis}", new_position)

    @abstractmethod
    def _create_grid(self) -> None:
        ...

    def set_pitch(self, x: float = None, y: float = None) -> None:
        """Sets the pitches in the x and y direction of the grid.

        The pitch refers to the distance between the end point of a grid structure and the closest end point of the
        adjacent grid structure. The unit cell is then the width/height of the grid structures + the pitch_x/pitch_y.
        The pitch can be a negative number. This makes the structures in the grid overlap.
        """
        create_grid = False
        if x is not None:
            Validate.number(x, "x")
            self._default_values["pitch_x"] = x
            create_grid = True

        if y is not None:
            Validate.number(y, "y")
            self._default_values["pitch_y"] = y
            create_grid=True

        if create_grid:
            self._create_grid()

    def set_rows_and_cols(self, rows: int | float = None, cols: int | float = None) -> None:
        """Sets the nr of rows and columns in the grid. Rows are the number of structures in the y-direction,
        while cols is the number of structures in the x-direction.
        """
        create_grid = False
        if rows is not None:
            rows = int(rows)
            Validate.positive_integer(rows, "rows")
            self._default_values["rows"] = rows
            create_grid = True

        if cols is not None:
            cols = int(cols)
            Validate.positive_integer(cols, "cols")
            self._default_values["columns"] = cols
            create_grid = True

        if create_grid:
            self._create_grid()

    def _insert_command(self, identifier: str, command: str, command_identifier: str) -> None:
        start_marker = f"##_##_##{identifier.upper()}:START##_##_##"
        end_marker = f"##_##_##{identifier.upper()}:END##_##_##"

        # Find positions
        start_pos = self._script.find(start_marker) + len(start_marker)
        end_pos = self._script.find(end_marker)

        if start_pos < end_pos:  # Ensure the markers are in the correct order
            # Extract the region between the markers
            region = self._script[start_pos:end_pos]

            # Check if a line with the same command identifier exists
            existing_line_pattern = rf".*#\s*{command_identifier}.*"
            match = re.search(existing_line_pattern, region)

            if match:
                # Replace the existing line with the new command
                region = re.sub(existing_line_pattern, command + f"  #{command_identifier.upper()}", region)
            else:
                # Append the new command to the region
                region += command + f"  #{command_identifier.upper()}"

            # Reconstruct the script
            self._script = self._script[:start_pos] + region + "\n" + self._script[end_pos:]

    def _remove_command(self, identifier: str, command_identifier: str) -> None:
        """Removes a command with the specified command identifier from the region between markers."""
        start_marker = f"##_##_##{identifier.upper()}:START##_##_##"
        end_marker = f"##_##_##{identifier.upper()}:END##_##_##"

        # Find positions
        start_pos = self._script.find(start_marker) + len(start_marker)
        end_pos = self._script.find(end_marker)

        if start_pos < end_pos:  # Ensure markers are in the correct order
            # Extract the region between the markers
            region = self._script[start_pos:end_pos]

            # Check if a line with the same command identifier exists
            existing_line_pattern = rf".*#\s*{command_identifier}.*"

            match = re.search(existing_line_pattern, region)

            if match:
                # Remove the existing line
                region = re.sub(existing_line_pattern + r"\n?", "", region).strip()

            # Reconstruct the script
            self._script = self._script[:start_pos] + "\n" + region + "\n" + self._script[end_pos:]

    def _clear_base_structure(self) -> None:
        """Clears the string area between the BASE STRUCTURE START and BASE STRUCTURE END markers."""
        start_marker = "##_##_##BASE_STRUCTURE:START##_##_##"
        end_marker = "##_##_##BASE_STRUCTURE:END##_##_##"

        # Find positions
        start_pos = self._script.find(start_marker) + len(start_marker)
        end_pos = self._script.find(end_marker)

        if start_pos < end_pos:  # Ensure markers are in the correct order
            # Clear the content between the markers
            self._script = self._script[:start_pos] + "\n" + self._script[end_pos:]

    def _set_as_construction_group(self) -> None:
        self._simulation.__getattribute__("_lumapi").setnamed(self.name, "construction group", True)
        self._simulation.__getattribute__("_lumapi").setnamed(self.name, "script", "")
        self._script = "deleteall;\n##_##_##BASE_STRUCTURE:START##_##_##\n##_##_##BASE_STRUCTURE:END##_##_##"

    def _get_active_parameters(self) -> None:
        return None

    def _get_corners(self) -> List[np.ndarray]:
        pitch_x = self._default_values.get("pitch_x")
        pitch_y = self._default_values.get("pitch_y")

        x_span, y_span, z_span = self.set_structure._get_spans()
        x = convert_length(self._get_parameter("x", "float"), "m", self._simulation._global_units)
        y = convert_length(self._get_parameter("y", "float"), "m", self._simulation._global_units)
        z = convert_length(self._get_parameter("z", "float"), "m", self._simulation._global_units)
        unit_cell = (x_span + pitch_x, y_span + pitch_y)

        min_x = x - self._default_values.get("columns") * unit_cell[0] / 2 + pitch_x/2
        max_x = x + self._default_values.get("columns") * unit_cell[0] / 2 - pitch_x/2
        min_y = y - self._default_values.get("rows") * unit_cell[1] / 2 + pitch_y/2
        max_y = y + self._default_values.get("rows") * unit_cell[1] / 2 - pitch_y/2
        min_z = z - z_span / 2
        max_z = z + z_span / 2

        corners = [np.array([min_x, min_y, min_z]), np.array([min_x, min_y, max_z]),
                   np.array([min_x, max_y, min_z]), np.array([min_x, max_y, max_z]),
                   np.array([max_x, min_y, min_z]), np.array([max_x, min_y, max_z]),
                   np.array([max_x, max_y, min_z]), np.array([max_x, max_y, max_z])]

        return corners

    def _get_min_max(self, axis: Literal["x", "y", "z"], min_max: Literal["min", "max"]) -> float:

        min_max_map = {"min": 0, "max": 1}
        axis_map = {"x": 0, "y": 1, "z": 2}

        value = float(self._get_bounding_box()[min_max_map[min_max]][axis_map[axis]])

        return value

    def _update(self, save_temp: bool = False) -> None:
        self._set_parameter("script", self._script, "str")
        # self._simulation.__getattribute__("_save_temp")()


class RectangularLattice(PhotonicCrystal):

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float
        pitch_x: float
        pitch_y: float
        rows: int
        columns: int

    __slots__ = PhotonicCrystal.__slots__

    def _create_grid(self) -> None:

        self._clear_base_structure()
        self.set_structure._creation = False
        struct_type = self.set_structure._current_settings.get("type")
        if struct_type == "Rectangle":
            self.set_structure.rectangle()
        elif struct_type == "Circle":
            self.set_structure.circle()
            self.set_structure._creation = True

        x_span, y_span, _ = self.set_structure._get_spans()
        x_span = convert_length(x_span, self._simulation._global_units, "m")
        y_span = convert_length(y_span, self._simulation._global_units, "m")

        unit_cell_x = x_span + convert_length(self._default_values["pitch_x"], self._simulation._global_units, "m")
        total_x = unit_cell_x * self._default_values["columns"]

        unit_cell_y = y_span + convert_length(self._default_values["pitch_y"], self._simulation._global_units, "m")
        total_y = unit_cell_y * self._default_values["rows"]

        first_x = -(total_x / 2) + unit_cell_x / 2
        first_y = -(total_y / 2) + unit_cell_y / 2

        first_structure = True

        for column in range(self._default_values["columns"]):

            for row in range(self._default_values["rows"]):

                if first_structure:
                    self._insert_command("base_structure", f"set('x', {first_x});", "x")
                    self._insert_command("base_structure", f"set('y', {first_y});", "y")
                    self._insert_command("base_structure", f"set('z', 0);", "z")
                else:
                    self._insert_command("base_structure", f"select('BASE_STRUCTURE');", f"selection_{column},{row}")
                    self._insert_command("base_structure", f"copy();", f"copy_{column},{row}")
                    self._insert_command("base_structure", f"set('name', '{self.name}_structure');",
                                         f"name_{column},{row}")
                    self._insert_command("base_structure",
                                         f"set('x', {first_x + unit_cell_x * column});", f"x_{column},{row}")
                    self._insert_command("base_structure",
                                         f"set('y', {first_y + unit_cell_y * row});", f"y_{column},{row}")

                first_structure = False

        self._insert_command("base_structure",
                             f"setnamed('BASE_STRUCTURE', 'name', '{self.name}_structure');",
                             f"RENAME_BASE_STRUCTURE")
        self._update()












TYPE_TO_STRUCTURE_MAP = {
    "Rectangle": Rectangle,
    "Polygon": Polygon,
    "Circle": Circle,
    "Sphere": Sphere,
    "Pyramid": Pyramid,
    "Ring": Ring,
    "Structure Group": StructureGroup,
    "Layout Group": LayoutGroup,
}
