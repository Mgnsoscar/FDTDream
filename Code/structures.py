from __future__ import annotations

# Standard library imports
from typing import Literal, Unpack, TypedDict, List, Tuple, Union, Optional
import math
import warnings
from dataclasses import dataclass

# Third-party library imports
import numpy as np
from lumapi_import import lumapi

# Local library imports
from geometry import GeometryBase
from fdtd_region import Mesh
from simulation_object import RotateableSimulationObject
from base_classes import SettingTab
from type_hint_resources import MATERIALS, LENGTH_UNITS
from local_resources import Validate, convert_length, DECIMALS
from geometry import CartesianGeometry


########################################################################################################################
#                                           CONSTANTS AND LITERALS
########################################################################################################################
# Defining literals here for improved readability later

INDEX_UNITS = Literal["m", "microns", "nm"]

########################################################################################################################
#                                               GEOMETRY CLASSES
########################################################################################################################


class CircularGeometryBase(GeometryBase):

    class _SettingsDict(GeometryBase._SettingsDict):
        radius: float
        radius_2: float
        make_ellipsoid: bool

    # Declare slots
    __slots__ = GeometryBase.__slots__

    def make_ellipsoid(self, true_or_false: bool) -> None:
        """
        Set the object to be an ellipsoid shape.

        If `true_or_false` is set to True, enables the option to define a second radius, allowing
        the object to take an ellipsoidal form with potentially different radii along different
        axes. If set to False, all radii will default to a single 'radius' parameter, creating a
        spherical form.

        Args:
            true_or_false (bool): True to enable ellipsoid shape with two radii; False for a
                                  spherical shape with one radius.
        """
        self._set_parameter("make ellipsoid", true_or_false, "bool")

    def set_radius(self, radius: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the primary radius of the object.

        This defines the main radius, affecting the size of the object. If an ellipsoidal
        shape is selected (through `make_ellipsoid`), this will act as one of the radii.

        Args:
            radius (float): The desired radius of the object. Must be a positive number.
            length_units (LENGTH_UNITS, optional): The unit for the radius. Defaults to the
                                                   simulation's global units if None.
        """
        Validate.positive_number(radius, "radius")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        radius = convert_length(radius, length_units, "m")
        self._set_parameter("radius", radius, "float")

    def set_radius_2(self, radius_2: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the secondary radius of the object.

        This defines a secondary radius for the object to create an ellipsoidal shape, which
        requires that `make_ellipsoid` is enabled. When `make_ellipsoid` is disabled, an error
        will be raised if this method is called, as only the primary radius can be set.

        Args:
            radius_2 (float): The desired secondary radius of the object. Must be a positive number.
            length_units (LENGTH_UNITS, optional): The unit for the secondary radius. Defaults to the
                                                   simulation's global units if None.

        Raises:
            ValueError: If `make ellipsoid` is not enabled.
        """
        Validate.positive_number(radius_2, "radius")

        if not self._get_parameter("make ellipsoid", "bool"):
            raise ValueError(
                "You cannot set the secondary radius when 'make ellipsoid' is disabled. "
                "Enable this first."
            )

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        radius_2 = convert_length(radius_2, length_units, "m")
        self._set_parameter("radius 2", radius_2, "float")

    def get_currently_active_simulation_parameters(self) -> CircularGeometryBase._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["radius"] = self._get_parameter("radius", "float")
        settings["make_ellipsoid"] = self._get_parameter("make ellpisoid", "bool")

        radius_2 = self._get_parameter("radius 2", "float")

        if settings["make_ellipsoid"]:
            if not radius_2 == settings["radius"]:
                settings["radius_2"] = radius_2

        return settings


class CircleGeometry(CircularGeometryBase):

    class _SettingsDict(CircularGeometryBase._SettingsDict):
        z_span: float

    # Declare slots
    __slots__ = GeometryBase.__slots__

    def set_z_span(self, z_span: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the z-axis span of the object.

        This method defines the extent of the object along the z-axis, specifying the span
        in the given units. If no units are provided, the simulation's global units are used.

        Args:
            z_span (float): The desired span along the z-axis, which must be a positive number.
            length_units (LENGTH_UNITS, optional): Units for the span value. Defaults to the
                                                   simulation's global units if None.

        Raises:
            ValueError: If `z_span` is not a positive number or if `length_units` is invalid.
        """
        Validate.positive_number(z_span, "z span")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        z_span = convert_length(z_span, length_units, "m")
        self._set_parameter("z span", z_span, "float")

    def get_currently_active_simulation_parameters(self) -> CircleGeometry._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["z_span"] = self._get_parameter("z span", "float")

        return settings


class SphereGeometry(CircularGeometryBase):

    class _SettingsDict(CircularGeometryBase._SettingsDict):
        radius_3: float

    __slots__ = GeometryBase.__slots__

    def set_radius_3(self, radius_3: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the secondary radius of the object.

        This defines a tertiary radius for the object to create an ellipsoidal shape, which
        requires that `make_ellipsoid` is enabled. When `make_ellipsoid` is disabled, an error
        will be raised if this method is called, as only the primary radius can be set.

        Args:
            radius_3 (float): The desired tertiary radius of the object. Must be a positive number.
            length_units (LENGTH_UNITS, optional): The unit for the secondary radius. Defaults to the
                                                   simulation's global units if None.

        Raises:
            ValueError: If `make ellipsoid` is not enabled.
        """
        Validate.positive_number(radius_3, "radius")

        if not self._get_parameter("make ellipsoid", "bool"):
            raise ValueError(
                "You cannot set the tertiary radius when 'make ellipsoid' is disabled. "
                "Enable this first."
            )

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        radius_3 = convert_length(radius_3, length_units, "m")
        self._set_parameter("radius 3", radius_3, "float")

    def get_currently_active_simulation_parameters(self) -> SphereGeometry._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())

        radius_3 = self._get_parameter("radius 3", "float")

        if settings["make_ellipsoid"]:
            if not radius_3 == settings["radius"]:
                settings["radius_3"] = radius_3

        return settings


class RingGeometry(GeometryBase):

    class _SettingsDict(GeometryBase._SettingsDict):
        z_span: float
        outer_radius: float
        inner_radius: float
        theta_start: float
        theta_stop: float
        make_ellipsoid: bool
        outer_radius_2: float
        inner_radius_2: float

    __slots__ = GeometryBase.__slots__

    def set_z_span(self, z_span: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the z-axis span of the object.

        This method defines the extent of the object along the z-axis, specifying the span
        in the given units. If no units are provided, the simulation's global units are used.

        Args:
            z_span (float): The desired span along the z-axis, which must be a positive number.
            length_units (LENGTH_UNITS, optional): Units for the span value. Defaults to the
                                                   simulation's global units if None.

        Raises:
            ValueError: If `z_span` is not a positive number or if `length_units` is invalid.
        """
        Validate.positive_number(z_span, "z span")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        z_span = convert_length(z_span, length_units, "m")
        self._set_parameter("z span", z_span, "float")

    def make_ellipsoid(self, true_or_false: bool) -> None:
        """
        Set the object to be an ellipsoid shape.

        If `true_or_false` is set to True, enables the option to define a second radius, allowing
        the object to take an ellipsoidal form with potentially different radii along different
        axes. If set to False, all radii will default to a single 'radius' parameter, creating a
        spherical form.

        Args:
            true_or_false (bool): True to enable ellipsoid shape with two radii; False for a
                                  spherical shape with one radius.
        """
        self._set_parameter("make ellipsoid", true_or_false, "bool")

    def set_outer_radius(self, outer_radius: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the outer radius of the ring structure.

        This function sets the outer radius of the ring shape, ensuring that it meets the
        required specifications for positive values and converts the provided radius to meters
        based on the specified or default simulation length units.

        Args:
            outer_radius (float): The desired outer radius of the ring. Must be a positive value.
            length_units (LENGTH_UNITS, optional): The units in which `outer_radius` is specified.
                If omitted, the function uses the simulation's global units.

        Raises:
            ValueError: If `outer_radius` is not a positive value or if `length_units` is invalid.

        """
        Validate.positive_number(outer_radius, "outer_radius")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        outer_radius = convert_length(outer_radius, length_units, "m")
        self._set_parameter("outer radius", outer_radius, "float")

    def set_inner_radius(self, inner_radius: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the inner radius of the ring structure.

        This function sets the inner radius for the ring shape, ensuring it is positive and converts
        it into meters based on the provided or default length units. The inner radius is typically
        smaller than the outer radius, defining the thickness of the ring.

        Args:
            inner_radius (float): The desired inner radius of the ring. Must be a positive value.
            length_units (LENGTH_UNITS, optional): The units in which `inner_radius` is specified.
                Defaults to the simulation's global units if not provided.

        Raises:
            ValueError: If `inner_radius` is not a positive value or if `length_units` is invalid.

        """
        Validate.positive_number(inner_radius, "inner_radius")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        inner_radius = convert_length(inner_radius, length_units, "m")
        self._set_parameter("inner radius", inner_radius, "float")

    def set_theta_start(self, theta_start: float) -> None:
        """
        Set the starting angle for the ring.

        This method specifies the angle at which the ring drawing begins, measured in degrees. The ring is drawn
        counterclockwise from the starting point.
        The angle must be within the range of 0 to 360 degrees.

        Args:
            theta_start (float): The starting angle for the ring in degrees. Must be within
                the range [0, 360].

        Raises:
            ValueError: If `theta_start` is outside the valid range of 0 to 360 degrees.

        """
        Validate.number_in_range(theta_start, "theta_start", (0, 360))
        self._set_parameter("theta start", theta_start, "float")

    def set_theta_stop(self, theta_stop: float) -> None:
        """
        Set the stopping angle for the ring.

        This method specifies the angle at which the ring drawing ends, measured in degrees. The ring is drawn
        counterclockwise from the starting point.
        The angle must be within the range of 0 to 360 degrees.

        Args:
            theta_stop (float): The stopping angle for the ring in degrees. Must be within
                the range [0, 360].

        Raises:
            ValueError: If `theta_stop` is outside the valid range of 0 to 360 degrees.

        """
        Validate.number_in_range(theta_stop, "theta_stop", (0, 360))
        self._set_parameter("theta stop", theta_stop, "float")

    def set_outer_radius_2(self, outer_radius_2: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the secondary outer radius of the object.

        This function sets the secondary outer radius for the object when the ellipsoid
        configuration is enabled. It ensures that the specified radius is positive and converts
        it to meters based on the provided or default length units.

        Args:
            outer_radius_2 (float): The desired secondary outer radius of the object. Must be a
                positive value.
            length_units (LENGTH_UNITS, optional): The units in which `outer_radius_2` is specified.
                Defaults to the simulation's global units if not provided.

        Raises:
            ValueError: If `outer_radius_2` is not a positive value, if the 'make ellipsoid'
            parameter is disabled, or if `length_units` is invalid.

        """
        Validate.positive_number(outer_radius_2, "outer_radius_2")

        if not self._get_parameter("make ellipsoid", "bool"):
            raise ValueError("Cannot set outer_radius_2 when 'make ellipsoid' is disabled. Enable it first.")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        outer_radius_2 = convert_length(outer_radius_2, length_units, "m")
        self._set_parameter("outer radius 2", outer_radius_2, "float")

    def set_inner_radius_2(self, inner_radius_2: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the secondary inner radius of the object.

        This function sets the secondary inner radius for the object when the ellipsoid
        configuration is enabled. It ensures that the specified radius is positive and converts
        it to meters based on the provided or default length units.

        Args:
            inner_radius_2 (float): The desired secondary inner radius of the object. Must be a
                positive value.
            length_units (LENGTH_UNITS, optional): The units in which `inner_radius_2` is specified.
                Defaults to the simulation's global units if not provided.

        Raises:
            ValueError: If `inner_radius_2` is not a positive value, if the 'make ellipsoid'
            parameter is disabled, or if `length_units` is invalid.

        """
        Validate.positive_number(inner_radius_2, "inner_radius_2")

        if not self._get_parameter("make ellipsoid", "bool"):
            raise ValueError("Cannot set inner_radius_2 when 'make ellipsoid' is disabled. Enable it first.")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        inner_radius_2 = convert_length(inner_radius_2, length_units, "m")
        self._set_parameter("inner radius 2", inner_radius_2, "float")

    def get_currently_active_simulation_parameters(self) -> RingGeometry._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters()))
        settings["z_span"] = self._get_parameter("z span", "float")
        settings["outer_radius"] = self._get_parameter("outer radius", "float")
        settings["inner_radius"] = self._get_parameter("inner radius", "float")
        settings["theta_start"] = self._get_parameter("theta start", "float")
        settings["theta_stop"] = self._get_parameter("theta stop", "float")
        settings["make_ellipsoid"] = self._get_parameter("make ellipsoid", "bool")

        outer_radius_2 = self._get_parameter("outer radius 2", "float")
        inner_radius_2 = self._get_parameter("inner radius 2", "float")
        if settings["make_ellipsoid"]:
            if not (outer_radius_2 == settings["outer_radius"] and inner_radius_2 == settings["inner_radius"]):
                settings["outer_radius_2"] = outer_radius_2
                settings["inner_radius_2"] = inner_radius_2

        return settings


class PolygonGeometry(GeometryBase):

    class _Vertex(TypedDict):
        x: float
        y: float

    class _SettingsDict(GeometryBase._SettingsDict):
        vertices: List[PolygonGeometry._Vertex]
        z_span: float

    __slots__ = GeometryBase.__slots__

    def set_vertices(self, vertices: List[Tuple[float, float]], length_units: LENGTH_UNITS = None) -> None:
        """
        Set the vertices of the polygon.

        This method allows you to define the vertices of a polygon by providing a list
        of tuples, where each tuple represents the x and y coordinates of a vertex.
        The coordinates can be specified in any length unit, and they will be converted
        to meters for internal processing.

        Args:
            vertices (List[Tuple[float, float]]): A list of tuples, each containing
                the (x, y) coordinates of a vertex. For example: [(1, 2), (4, 5), (9, 3)].
            length_units (LENGTH_UNITS, optional): The units of the provided coordinates.
                If None, the global units of the simulation will be used.

        Raises:
            ValueError: If any vertex coordinates are invalid or cannot be converted.

        """
        if length_units is None:
            length_units = self._simulation.global_units

        new_units = [(convert_length(vertex[0], from_unit=length_units, to_unit="m"),
                      convert_length(vertex[1], from_unit=length_units, to_unit="m")) for vertex in vertices]

        self._set_parameter("vertices", np.array(new_units), "list")

    def set_z_span(self, z_span: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the z-axis span of the object.

        This method defines the extent of the object along the z-axis, specifying the span
        in the given units. If no units are provided, the simulation's global units are used.

        Args:
            z_span (float): The desired span along the z-axis, which must be a positive number.
            length_units (LENGTH_UNITS, optional): Units for the span value. Defaults to the
                                                   simulation's global units if None.

        Raises:
            ValueError: If `z_span` is not a positive number or if `length_units` is invalid.
        """
        Validate.positive_number(z_span, "z span")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        z_span = convert_length(z_span, length_units, "m")
        self._set_parameter("z span", z_span, "float")

    def get_currently_active_simulation_parameters(self: Union[PolygonGeometry, EquilateralPolygonGeometry]
                                                   ) -> PolygonGeometry._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings.update({
            "z_span": self._get_parameter("z span", "float"),
        })
        vertices = self._get_parameter("vertices", "list")
        vertices_list = []
        for vertex in vertices:
            vertex = np.round(vertex, decimals=DECIMALS).astype(float)
            vertices_list.append(self.__class__._Vertex(**{"x": vertex[0], "y": vertex[1]}))

        settings["vertices"] = vertices_list

        return settings


class EquilateralPolygonGeometry(GeometryBase):

    __slots__ = GeometryBase.__slots__

    def set_z_span(self, z_span: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the z-axis span of the object.

        This method defines the extent of the object along the z-axis, specifying the span
        in the given units. If no units are provided, the simulation's global units are used.

        Args:
            z_span (float): The desired span along the z-axis, which must be a positive number.
            length_units (LENGTH_UNITS, optional): Units for the span value. Defaults to the
                                                   simulation's global units if None.

        Raises:
            ValueError: If `z_span` is not a positive number or if `length_units` is invalid.
        """
        Validate.positive_number(z_span, "z span")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        z_span = convert_length(z_span, length_units, "m")
        self._set_parameter("z span", z_span, "float")

    def _create_regular_polygon(self, side_length=None, radius=None):
        """
        Creates vertices for an N-sided equilateral polygon.
        User can input either the side length or the radius.
        """
        if side_length is None and radius is None:
            raise ValueError("Either side_length or radius must be provided.")

        N = self._parent._nr_vertices

        if radius is None:
            # Calculate radius from side length if radius is not provided
            radius = side_length / (2 * np.sin(np.pi / N))

        vertices = []
        for i in range(N):
            # Rotate by adding pi/2 to place the first vertex at the top
            angle = i * 2 * np.pi / N # Shift angle by -90 degrees
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertices.append((x, y))

        return np.array(vertices)

    def set_side_length(self, side_length: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the length of each side of the equilateral polygon.

        This method configures the polygon to be equilateral by setting the length of each side.
        The vertices of the polygon are calculated based on the provided side length, which is
        then converted to meters for internal processing.

        Args:
            side_length (float): The length of each side of the equilateral polygon.
            length_units (LENGTH_UNITS, optional): The units of the provided side length.
                If None, the global units of the simulation will be used.

        Note:
            The vertices of the polygon will be automatically recalculated based on the
            specified side length.

        """
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        vertices = self._create_regular_polygon(
            side_length=convert_length(side_length, length_units, "m")
        )

        self._set_parameter("vertices", vertices, "list")

    def set_radius(self, radius: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the size of the equilateral polygon based on the radius.

        This method defines the polygon by specifying its circumradius. The vertices
        of the equilateral polygon are calculated based on the provided radius, which
        is converted to meters for internal processing.

        Args:
            radius (float): The radius of the circumcircle of the equilateral polygon.
            length_units (LENGTH_UNITS, optional): The units of the provided radius.
                If None, the global units of the simulation will be used.

        Raises:
            ValueError: If the provided radius is invalid or cannot be converted.

        Note:
            The vertices of the polygon will be automatically recalculated based on the
            specified radius.

        """

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        vertices = self._create_regular_polygon(
            radius=convert_length(radius, length_units, "m")
        )

        self._set_parameter("vertices", vertices, "list")

    def _get_side_length(self) -> float:

        vertices = self._get_parameter("vertices", "list")
        length = np.sqrt((vertices[1][0] - vertices[0][0]) ** 2 + (vertices[1][1] - vertices[0][1]) ** 2)
        length = convert_length(length, "m", self._simulation.global_units)
        return length

    def _get_radius(self) -> float:
        """Calculates the radius of a polygon given its vertices."""

        vertices = self._get_parameter("vertices", "list")

        # Calculate the centroid
        x_coords = [v[0] for v in vertices]
        y_coords = [v[1] for v in vertices]

        centroid_x = sum(x_coords) / len(vertices)
        centroid_y = sum(y_coords) / len(vertices)

        # Calculate the distance from the centroid to the first vertex
        radius = np.sqrt((centroid_x - x_coords[0]) ** 2 + (centroid_y - y_coords[0]) ** 2)

        return radius

    def get_currently_active_simulation_parameters(self) -> PolygonGeometry._SettingsDict:

        return PolygonGeometry.get_currently_active_simulation_parameters(self)


class PyramidGeometry(GeometryBase):

    class _SettingsDict(GeometryBase._SettingsDict):
        x_span_bottom: float
        x_span_top: float
        y_span_bottom: float
        y_span_top: float
        z_span: float

    __slots__ = GeometryBase.__slots__

    def set_z_span(self, z_span: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the z-axis span of the object.

        This method defines the extent of the object along the z-axis, specifying the span
        in the given units. If no units are provided, the simulation's global units are used.

        Args:
            z_span (float): The desired span along the z-axis, which must be a positive number.
            length_units (LENGTH_UNITS, optional): Units for the span value. Defaults to the
                                                   simulation's global units if None.

        Raises:
            ValueError: If `z_span` is not a positive number or if `length_units` is invalid.
        """
        Validate.positive_number(z_span, "z span")

        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        z_span = convert_length(z_span, length_units, "m")
        self._set_parameter("z span", z_span, "float")

    def set_x_span_bottom(self, x_span_bottom: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the bottom span of the pyramid along the x-axis.

        This parameter defines the lower boundary of the base of the pyramid in the x-direction.

        Args:
            x_span_bottom (float): The lower boundary of the x span of the pyramid's base.
            length_units (LENGTH_UNITS, optional): The units of the provided span.
                If None, the global units of the simulation will be used.

        Raises:
            ValueError: If the provided x_span_bottom is invalid.
        """
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        x_span_bottom = convert_length(x_span_bottom, length_units, "m")
        self._set_parameter("x span bottom", x_span_bottom, "float")

    def set_x_span_top(self, x_span_top: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the top span of the pyramid along the x-axis.

        This parameter defines the upper boundary of the span in the x-direction, affecting the apex of the pyramid.

        Args:
            x_span_top (float): The upper boundary of the x span of the pyramid.
            length_units (LENGTH_UNITS, optional): The units of the provided span.
                If None, the global units of the simulation will be used.

        Raises:
            ValueError: If the provided x_span_top is invalid.
        """
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        x_span_top = convert_length(x_span_top, length_units, "m")
        self._set_parameter("x span top", x_span_top, "float")

    def set_y_span_bottom(self, y_span_bottom: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the bottom span of the pyramid along the y-axis.

        This parameter defines the lower boundary of the base of the pyramid in the y-direction.

        Args:
            y_span_bottom (float): The lower boundary of the y span of the pyramid's base.
            length_units (LENGTH_UNITS, optional): The units of the provided span.
                If None, the global units of the simulation will be used.

        Raises:
            ValueError: If the provided y_span_bottom is invalid.
        """
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        y_span_bottom = convert_length(y_span_bottom, length_units, "m")
        self._set_parameter("y span bottom", y_span_bottom, "float")

    def set_y_span_top(self, y_span_top: float, length_units: LENGTH_UNITS = None) -> None:
        """
        Set the top span of the pyramid along the y-axis.

        This parameter defines the upper boundary of the span in the y-direction, affecting the apex of the pyramid.

        Args:
            y_span_top (float): The upper boundary of the y span of the pyramid.
            length_units (LENGTH_UNITS, optional): The units of the provided span.
                If None, the global units of the simulation will be used.

        Raises:
            ValueError: If the provided y_span_top is invalid.
        """
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        y_span_top = convert_length(y_span_top, length_units, "m")
        self._set_parameter("y span top", y_span_top, "float")

    def get_currently_active_simulation_parameters(self) -> PyramidGeometry._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["x_span_bottom"] = self._get_parameter("x span bottom", "float")
        settings["x_span_top"] = self._get_parameter("x span top", "float")
        settings["y_span_bottom"] = self._get_parameter("y span bottom", "float")
        settings["y_span_top"] = self._get_parameter("y span top", "float")
        settings["z_span"] = self._get_parameter("z span", "float")
        return settings


########################################################################################################################
#                                          CLASSES FOR MAIN SETTINGS CATEGORIES
########################################################################################################################

class MaterialSettings(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        material: MATERIALS
        index: float
        index_units: INDEX_UNITS
        mesh_order: int
        grid_attribute: str

    __slots__ = SettingTab.__slots__

    def set_material(self, material: MATERIALS, index: Optional[Union[float, str]] = None) -> None:
        """
        Set the material of the object, validating the selection against available materials.
        If the material is "<Object defined dielectric>", an index value must be provided.
        The index can be specified as:
            - Isotropic: A single float > 1
            - Anisotropic: A semicolon-separated string of three float values for xx, yy, and zz indices, e.g., "1;1.5;1"
            - Spatially Varying: A spatial equation in terms of x, y, and z, e.g., "2+0.1*x"

        Args:
            material (MATERIALS): The material to assign to the object, validated from a predefined list.
            index (float or str, optional): The refractive index for "<Object defined dielectric>". Must be a float > 1 for isotropic,
                                            a semicolon-separated string for anisotropic, or an equation for spatially varying index.

        Raises:
            ValueError: If "<Object defined dielectric>" is chosen and no index is provided,
                        or if the index is invalid for the selected material type.
        """
        # Validate the material selection
        Validate.in_literal(material, "material", MATERIALS)
        self._set_parameter("material", material, "str")

        # Check for required index when using "<Object defined dielectric>"
        if material == "<Object defined dielectric>":
            if index is None:
                raise ValueError("The 'index' parameter must be provided for '<Object defined dielectric>' material.")

            # Validate isotropic index
            if isinstance(index, float):
                if index <= 1:
                    raise ValueError("Isotropic index must be a float greater than or equal to one.")
                self._set_parameter("index", index, "float")

            # Validate anisotropic index (semicolon-separated values)
            elif isinstance(index, str) and ';' in index:
                components = index.split(';')
                if len(components) != 3 or not all(float(comp) > 0 for comp in components):
                    raise ValueError(
                        "Anisotropic index must contain three positive float values separated by semicolons.")
                self._set_parameter("index", index, "str")

            # Validate spatially varying index (equation)
            else:
                # Additional checks can be implemented here if a specific format is required for equations.
                self._set_parameter("index", index, "str")

        elif index is not None:
            # If the material is not "<Object defined dielectric>", ignore the index value and warn the user
            warnings.warn("Warning: 'index' parameter is only applicable for '<Object defined dielectric>'. "
                          "Ignoring the provided index.")

    def set_index(self, index: Union[float, str], index_units: INDEX_UNITS = "m") -> None:
        """
        Set the refractive index for the material when the material type is "<Object defined dielectric>".

        For structures with material type "<Object defined dielectric>", this method assigns a refractive index.
        The index can be a single float value greater than 1 or a spatially varying equation using x, y, z variables
        (e.g., "2 + 0.1 * x"). When specifying an equation, `index_units` is used to define the units for x, y, z.

        Args:
            index (Union[float, str]): The refractive index of the structure. Must be either:
                - A float greater than 1 for isotropic materials, or
                - A string representing a spatial equation (e.g., "2 + 0.1 * x") for spatially varying indices.
            index_units (INDEX_UNITS, optional): Units for x, y, z variables when `index` is an equation. Default is "m" (meters).

        Raises:
            ValueError: If the material is not set to "<Object defined dielectric>".
            ValueError: If a numeric `index` value is not greater than 1.
        """
        # Retrieve and verify material type
        material = self._get_parameter("material", "str")
        if material != "<Object defined dielectric>":
            raise ValueError(
                f"Structure name: '{self._parent.name}'.\n"
                "The index can only be set when the material is '<Object defined dielectric>', "
                f"not '{material}'."
            )

        # Validate the type and value of the index
        if isinstance(index, float):
            if index <= 1:
                raise ValueError("Index must be greater than or equals 1 for '<Object defined dielectric>' "
                                 "material type.")
        elif isinstance(index, str):
            # Ensure valid spatial equation format
            if not any(var in index for var in ('x', 'y', 'z')):
                raise ValueError(
                    "Index equation must contain spatial variables x, y, or z for spatially varying indices."
                )
        else:
            raise TypeError("Index must be either a float or a spatial equation string.")

        # Validate index_units
        Validate.in_literal(index_units, "index_units", INDEX_UNITS)

        # Set parameters
        self._set_parameter("index", index, "float" if isinstance(index, float) else "str")
        self._set_parameter("index units", index_units, "str")

    def override_mesh_order_from_material_database(self, override: bool, mesh_order: int = None) -> None:
        """
        Overrides the mesh order setting from the material database and allows manual setting of a mesh order.

        When `override` is set to True, the `mesh_order` parameter can be specified to determine priority
        during material overlap in the simulation engine. Higher-priority materials (lower mesh order values)
        will override lower-priority materials in overlap regions.

        Args:
            override (bool): If True, enables manual mesh order setting; otherwise, uses the database's mesh order.
            mesh_order (int, optional): Mesh order to assign if overriding the database setting. Only allowed if `override` is True.

        Raises:
            ValueError: If `override` is False and `mesh_order` is provided.
            ValueError: If `mesh_order` is set but does not fall within an acceptable range (e.g., >= 1).
        """
        # Set the override parameter
        self._set_parameter("override mesh order from material database", override, "bool")

        # Validate and set mesh order if overriding is enabled
        if not override:
            if mesh_order is not None:
                raise ValueError("Cannot set 'mesh_order' when 'override' is False.")
        else:
            if mesh_order is not None:
                if mesh_order < 1:
                    raise ValueError("Mesh order must be 1 or higher when overriding the database.")
                Validate.integer(mesh_order, "mesh_order")
                self._set_parameter("mesh order", mesh_order, "int")

    def set_grid_attribute_name(self, name: str) -> None:
        """
        Sets the name of the grid attribute that applies to this object.

        The grid attribute name is used to identify specific grid configurations
        relevant to the object's simulation. It is relevant when creating anisotropic optical materials.

        Args:
            name (str): The grid attribute name for this object.

        Raises:
            ValueError: If `name` is an empty string or only whitespace.
        """
        # Validate that the name is a non-empty string
        if not name.strip():
            raise ValueError("Grid attribute name cannot be empty or only whitespace.")

        # Set the grid attribute name
        self._set_parameter("grid attribute name", name, "str")

    def get_currently_active_simulation_parameters(self) -> MaterialSettings._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["material"] = self._get_parameter("material", "str")
        if settings["material"] == "<Object defined dielectric>":
            settings["index"] = self._get_parameter("index", "float")
            if isinstance(settings["index"], str):
                settings["index_units"] = self._get_parameter("index units", "str")
        settings["mesh_order"] = self._get_parameter("mesh order", "int")
        settings["grid_attribute"] = self._get_parameter("grid attribute name", "str")
        return settings


########################################################################################################################
#                                             CLASSES FOR STRUCTURE OBJECTS
########################################################################################################################


# Base classes
class StructureBase(RotateableSimulationObject):

    class _SettingsDict(RotateableSimulationObject._SettingsDict):
        material_settings: MaterialSettings._SettingsDict
        rotation_settings: RotateableSimulationObject.rotations_settings._SettingsDict

    class _Kwargs(RotateableSimulationObject._Kwargs, total=False):
        material: MATERIALS
        index: float

    _settings = RotateableSimulationObject._settings + [MaterialSettings]
    _settings_names = RotateableSimulationObject._settings_names + ["material_settings"]

    # Declare variables
    material_settings: MaterialSettings
    _bulk_mesh: Mesh | None

    __slots__ = RotateableSimulationObject.__slots__ + _settings_names

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[StructureBase._Kwargs]) -> None:

        if name in simulation._names:
            raise ValueError(f"A simulation object with the name '{name}' already exists. Choose another name.")

        ordered = self.__class__._Kwargs(**{
            parameter: None for parameter in self.__class__.__annotations__.keys()})

        for key, value in kwargs.items():
            ordered[key] = value

        poppable = []
        for key, value in ordered.items():
            if value is None:
                poppable.append(key)

        for pop in poppable:
            ordered.pop(pop)

        self._bulk_mesh = None
        super().__init__(name, simulation, **ordered)
        self._simulation._structures.append(self)
        self._simulation._names.append(self.name)

    @property
    def bulk_mesh(self) -> Mesh | None:
        return self._bulk_mesh

    def get_currently_active_simulation_parameters(self) -> StructureBase._SettingsDict:
        settings = self.__class__._SettingsDict(**{
            "material_settings": self.material_settings.get_currently_active_simulation_parameters(),
            "rotation_settings": self.rotations_settings.get_currently_active_simulation_parameters(),
            "geometry_settings": self.geometry_settings.get_currently_active_simulation_parameters()
        })
        return settings


class CircularStructureBase(StructureBase):

    class _Kwargs(StructureBase._Kwargs):
        make_ellipsoid: bool
        radius: float
        radius_2: float

    _settings = [CircularGeometryBase if _setting == CartesianGeometry else _setting for
                 _setting in StructureBase._settings]
    geometry_settings: CircularGeometryBase

    # Declare slots
    __slots__ = StructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[CircularStructureBase._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    @property
    def radius(self) -> float:
        return convert_length(self._get_parameter(
            "radius", "float"), from_unit="m", to_unit=self._simulation.global_units)

    @radius.setter
    def radius(self, radius: float) -> None:
        self.geometry_settings.set_radius(radius)

    @property
    def make_ellipsoid(self) -> None:
        return self._get_parameter("make ellipsoid", "bool")

    @make_ellipsoid.setter
    def make_ellipsoid(self, true_or_false: bool) -> None:
        self.geometry_settings.make_ellipsoid(true_or_false)

    @property
    def radius_2(self) -> float:
        return convert_length(self._get_parameter(
            "radius 2", "float"), from_unit="m", to_unit=self._simulation.global_units)

    @radius_2.setter
    def radius_2(self, radius_2: float) -> None:
        self.geometry_settings.set_radius_2(radius_2)

    def get_currently_active_simulation_parameters(self) -> CircularStructureBase._SettingsDict:

        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())

        return settings


class Rectangle(StructureBase):

    class _SettingsDict(StructureBase._SettingsDict):
        geometry_settings: CartesianGeometry

    class _Kwargs(StructureBase._Kwargs, total=False):
        x_span: float
        y_span: float
        z_span: float

    __slots__ = StructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Rectangle._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    @property
    def x_span(self) -> float:
        return convert_length(self._get_parameter(
            "x span", "float"), "m", self._simulation.global_units)

    @x_span.setter
    def x_span(self, x_span: float) -> None:
        self.geometry_settings.set_spans(x_span=x_span)

    @property
    def y_span(self) -> float:
        return convert_length(self._get_parameter(
            "y span", "float"), "m", self._simulation.global_units)

    @y_span.setter
    def y_span(self, y_span: float) -> None:
        self.geometry_settings.set_spans(y_span=y_span)

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter(
            "z span", "float"), "m", self._simulation.global_units)

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.geometry_settings.set_spans(z_span=z_span)

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        # Fetch min and max values only once
        x_min = self._get_parameter("x min", "float")
        x_max = self._get_parameter("x max", "float")
        y_min = self._get_parameter("y min", "float")
        y_max = self._get_parameter("y max", "float")
        z_min = self._get_parameter("z min", "float")
        z_max = self._get_parameter("z max", "float")

        # Return the list of corners using the stored values
        return [
            (x_min, y_min, z_min), (x_min, y_min, z_max),
            (x_min, y_max, z_min), (x_min, y_max, z_max),
            (x_max, y_min, z_min), (x_max, y_min, z_max),
            (x_max, y_max, z_min), (x_max, y_max, z_max)
        ]


class Circle(CircularStructureBase):

    class _SettingsDict(CircularStructureBase._SettingsDict):
        geometry_settings: CircleGeometry

    class _Kwargs(CircularStructureBase._Kwargs, total=False):
        z_span: float

    _settings = [CircleGeometry if _setting == CartesianGeometry else _setting for
                 _setting in CircularStructureBase._settings]
    geometry_settings: CircleGeometry

    __slots__ = CircularStructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Circle._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        # Fetch the parameters for radius, radius_2, and z_span, and center position
        radius = self._get_parameter("radius", "float")
        radius_2 = self._get_parameter("radius 2", "float")
        z_span = self._get_parameter("z_span", "float")

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
        return convert_length(self._get_parameter(
            "z span", "float"), "m", self._simulation.global_units)

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.geometry_settings.set_z_span(z_span)

    def get_currently_active_simulation_parameters(self) -> Circle._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        return settings


class Sphere(CircularStructureBase):

    class _SettingsDict(CircularStructureBase._SettingsDict):
        geometry_settings: SphereGeometry

    class _Kwargs(CircularStructureBase._Kwargs, total=False):
        radius_3: float

    _settings = [SphereGeometry if _setting == CartesianGeometry
                 else _setting for _setting in CircularStructureBase._settings]
    geometry_settings: SphereGeometry

    __slots__ = CircularStructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Sphere._Kwargs]):
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
        return convert_length(self._get_parameter(
            "radius 3", "float"), from_unit="m", to_unit=self._simulation.global_units)

    @radius_3.setter
    def radius_3(self, radius_3: float) -> None:
        self.geometry_settings.set_radius_3(radius_3)

    def get_currently_active_simulation_parameters(self) -> Sphere._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        return settings


class Ring(StructureBase):

    class _SettingsDict(StructureBase._SettingsDict):
        geometry_settings: RingGeometry

    class _Kwargs(StructureBase._Kwargs, total=False):
        make_ellipsoid: bool
        z_span: float
        outer_radius: float
        inner_radius: float
        outer_radius_2: float
        inner_radius_2: float
        theta_start: float
        theta_stop: float

    _settings = [RingGeometry if _setting == CartesianGeometry
                 else _setting for _setting in StructureBase._settings]
    geometry_settings: RingGeometry
    __slots__ = StructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Ring._Kwargs]) -> None:
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
        z_min = z_center - z_span/2
        z_max = z_center + z_span/2

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

            x = x_center + (math.cos(theta_rad)/np.sqrt((np.square(math.cos(theta_rad))/np.square(radius_x))
                                                        + (np.square(math.sin(theta_rad))/np.square(radius_y))))
            y = y_center + (math.sin(theta_rad) / np.sqrt((np.square(math.cos(theta_rad)) / np.square(radius_x))
                                                          + (np.square(math.sin(theta_rad)) / np.square(radius_y))))

            return x, y

        # Calculate points for the outer and inner edges
        outer_points = [polar_to_cartesian(outer_radius_x, outer_radius_y, angle, x_center, y_center) for angle in angles]
        inner_points = [polar_to_cartesian(inner_radius_x, inner_radius_y, angle, x_center, y_center) for angle in angles]

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
        return convert_length(self._get_parameter(
            "outer radius", "float"), "m", self._simulation.global_units)

    @outer_radius.setter
    def outer_radius(self, outer_radius: float) -> None:
        self.geometry_settings.set_outer_radius(outer_radius)

    @property
    def inner_radius(self) -> float:
        return convert_length(self._get_parameter(
            "inner radius", "float"), "m", self._simulation.global_units)

    @inner_radius.setter
    def inner_radius(self, inner_radius: float) -> None:
        self.geometry_settings.set_inner_radius(inner_radius)

    @property
    def outer_radius_2(self) -> float:
        return convert_length(self._get_parameter(
            "outer radius 2", "float"), "m", self._simulation.global_units)

    @outer_radius_2.setter
    def outer_radius_2(self, outer_radius_2: float) -> None:
        self.geometry_settings.set_outer_radius_2(outer_radius_2)

    @property
    def inner_radius_2(self) -> float:
        return convert_length(self._get_parameter(
            "inner radius 2", "float"), "m", self._simulation.global_units)

    @inner_radius_2.setter
    def inner_radius_2(self, inner_radius_2: float) -> None:
        self.geometry_settings.set_inner_radius_2(inner_radius_2)

    @property
    def theta_start(self) -> float:
        return self._get_parameter("theta start", "float")

    @theta_start.setter
    def theta_start(self, theta_start: float) -> None:
        self.geometry_settings.set_theta_start(theta_start)

    @property
    def theta_stop(self) -> float:
        return self._get_parameter("theta stop", "float")

    @theta_stop.setter
    def theta_stop(self, theta_stop: float) -> None:
        self.geometry_settings.set_theta_stop(theta_stop)

    @property
    def make_ellipsoid(self) -> bool:
        return self._get_parameter("make ellipsoid", "bool")

    @make_ellipsoid.setter
    def make_ellipsoid(self, true_or_false: bool) -> None:
        self.geometry_settings.make_ellipsoid(true_or_false)

    def get_currently_active_simulation_parameters(self) -> Ring._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        return settings


class Polygon(StructureBase):

    class _SettingsDict(StructureBase._SettingsDict):
        geometry_settings: PolygonGeometry

    class _Kwargs(StructureBase._Kwargs, total=False):
        vertices: List[Tuple[float, float]]
        z_span: float

    _settings = [PolygonGeometry if _setting == CartesianGeometry else _setting for _setting in StructureBase._settings]
    geometry_settings: PolygonGeometry

    __slots__ = StructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Polygon._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter(
            "z span", "float"), "m", self._simulation.global_units)

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.geometry_settings.set_z_span(z_span)

    @property
    def vertices(self) -> List[Tuple[float, float]]:
        return self._get_parameter("vertices", "list")

    @vertices.setter
    def vertices(self, vertices: List[Tuple[float, float]]) -> None:
        self.geometry_settings.set_vertices(vertices)

    def get_currently_active_simulation_parameters(self) -> Polygon._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        return settings

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        # Retrieve vertices and z_span
        vertices = self._get_parameter("vertices", "list")
        z_span = self._get_parameter("z_span", "float")

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


class EquilateralNSidedPolygon(StructureBase):

    class _SettingsDict(StructureBase._SettingsDict):
        geometry_settings: EquilateralPolygonGeometry

    class _Kwargs(StructureBase._Kwargs, total=False):
        z_span: float
        radius: float
        side_length: float

    _settings = [EquilateralPolygonGeometry if _setting == CartesianGeometry
                 else _setting for _setting in StructureBase._settings]
    geometry_settings: EquilateralPolygonGeometry

    _nr_vertices: int

    __slots__ = StructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, vertices: int,
                 **kwargs: Unpack[EquilateralNSidedPolygon._Kwargs]) -> None:
        self._nr_vertices = vertices
        super().__init__(name, simulation, **kwargs)
        if not kwargs.get("radius", None) and not kwargs.get("side_length", None):
            self.geometry_settings.set_radius(100, None)
        elif kwargs.get("radius", None) and kwargs.get("side_length"):
            raise ValueError("Specify either radius or sidelength, not both.")

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter(
            "z span", "float"), "m", self._simulation.global_units)

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.geometry_settings.set_z_span(z_span)

    @property
    def side_length(self) -> float:
        return self.geometry_settings._get_side_length()

    @side_length.setter
    def side_length(self, side_length: float) -> None:
        self.geometry_settings.set_side_length(side_length)

    @property
    def radius(self) -> float:
        return self.geometry_settings._get_radius()

    @radius.setter
    def radius(self, radius: float) -> None:
        self.geometry_settings.set_radius(radius)

    def get_currently_active_simulation_parameters(self) -> EquilateralNSidedPolygon._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        return settings


class Triangle(EquilateralNSidedPolygon):

    __slots__ = EquilateralNSidedPolygon.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Triangle._Kwargs]) -> None:
        super().__init__(name, simulation, vertices=3, **kwargs)

    def get_currently_active_simulation_parameters(self) -> Triangle._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        return settings


class Pyramid(StructureBase):

    class _SettingsDict(StructureBase._SettingsDict):
        geometry_settings: PyramidGeometry

    class _Kwargs(StructureBase._Kwargs, total=False):
        x_span_top: float
        x_span_bottom: float
        y_span_top: float
        y_span_bottom: float
        z_span: float

    _settings = [PyramidGeometry if _setting == CartesianGeometry
                 else _setting for _setting in StructureBase._settings]
    geometry_settings: PyramidGeometry

    __slots__ = StructureBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Pyramid._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        z_center = self._get_parameter("z", "float")
        z_span = self._get_parameter("z span", "float")
        z_min = z_center - z_span/2
        z_max = z_center + z_span/2
        x_span_bottom = self._get_parameter("x span bottom", "float")
        y_span_bottom = self._get_parameter("y span bottom", "float")
        x_span_top = self._get_parameter("x span top", "float")
        y_span_top = self._get_parameter("y span top", "float")
        x_center = self._get_parameter("x", "float")
        y_center = self._get_parameter("y", "float")

        return [
            (x_center - x_span_bottom/2, y_center - y_span_bottom/2, z_min),
            (x_center - x_span_bottom / 2, y_center - y_span_bottom / 2, z_max),
            (x_center - x_span_bottom / 2, y_center + y_span_bottom / 2, z_min),
            (x_center - x_span_bottom / 2, y_center + y_span_bottom / 2, z_max),
            (x_center + x_span_bottom / 2, y_center - y_span_bottom / 2, z_min),
            (x_center + x_span_bottom / 2, y_center - y_span_bottom / 2, z_max),
            (x_center + x_span_bottom / 2, y_center + y_span_bottom / 2, z_min),
            (x_center + x_span_bottom / 2, y_center + y_span_bottom / 2, z_max)
        ]

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter(
            "z span", "float"), "m", self._simulation.global_units)

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        self.geometry_settings.set_z_span(z_span)

    @property
    def x_span_bottom(self) -> float:
        return convert_length(self._get_parameter(
            "x span bottom", "float"), "m", self._simulation.global_units)

    @x_span_bottom.setter
    def x_span_bottom(self, x_span_bottom: float) -> None:
        Validate.positive_number(x_span_bottom, "x_span_bottom")
        x_span_bottom = convert_length(x_span_bottom, self._simulation.global_units, "m")
        self._set_parameter("x span bottom", x_span_bottom, "float")

    @property
    def x_span_top(self) -> float:
        return convert_length(self._get_parameter(
            "x span top", "float"), "m", self._simulation.global_units)

    @x_span_top.setter
    def x_span_top(self, x_span_top: float) -> None:
        Validate.positive_number(x_span_top, "x_span_top")
        x_span_top = convert_length(x_span_top, self._simulation.global_units, "m")
        self._set_parameter("x span top", x_span_top, "float")

    @property
    def y_span_bottom(self) -> float:
        return convert_length(self._get_parameter(
            "y span bottom", "float"), "m", self._simulation.global_units)

    @y_span_bottom.setter
    def y_span_bottom(self, y_span_bottom: float) -> None:
        Validate.positive_number(y_span_bottom, "y_span_bottom")
        y_span_bottom = convert_length(y_span_bottom, self._simulation.global_units, "m")
        self._set_parameter("y span bottom", y_span_bottom, "float")

    @property
    def y_span_top(self) -> float:
        return convert_length(self._get_parameter(
            "y span top", "float"), "m", self._simulation.global_units)

    @y_span_top.setter
    def y_span_top(self, y_span_top: float) -> None:
        Validate.positive_number(y_span_top, "y_span_top")
        y_span_top = convert_length(y_span_top, self._simulation.global_units, "m")
        self._set_parameter("y span top", y_span_top, "float")

    def get_currently_active_simulation_parameters(self) -> Pyramid._SettingsDict:
        settings = self.__class__._SettingsDict(**super().get_currently_active_simulation_parameters())
        return settings
