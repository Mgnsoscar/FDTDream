from __future__ import annotations

# Standard library imports
from typing import Optional, get_args, List, Tuple, TypeVar, cast, TypedDict, Unpack, Union
from abc import abstractmethod, ABC
from dataclasses import dataclass

# Third-party library imports
import numpy as np

# Local imports
from Code.Resources.local_resources import DECIMALS, Validate, convert_length
from Code.Resources.literals import AXES, LENGTH_UNITS, MONITOR_TYPES_ALL, MONITOR_TYPES_3D, MONITOR_TYPES_2D
from base_classes import (TStructure)
from base_classes import (BaseGeometry, RelativeBaseGeometry, Settings, BaseGeometrySettings, Vertex, MeshBase,
                          TSimulation, BaseMixinClass, AxesIntKwargs)

# Imports not used in this module, but should be importable from this module
from base_classes import (RelPositionKwargs, PositionKwargs, PositionProperties, MinMaxBoundingBoxProperties,
                          MinMaxDirectProperties)


########################################################################################################################
#                                                   TYPEVARS
########################################################################################################################
TSGeometry = TypeVar("TSGeometry", bound="StructureGeometry")


########################################################################################################################
#                                                   TYPED DICTS
########################################################################################################################
class TrippleSpansKwargs(TypedDict, total=False):
    x_span: float
    y_span: float
    z_span: float


########################################################################################################################
#                                                METHOD CLASSES
########################################################################################################################
class ZSpanMethod(BaseMixinClass, ABC):

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
            length_units = self._simulation.__getattribute__("_global_units")
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        z_span = convert_length(z_span, length_units, "m")
        self._set_parameter("z span", z_span, "float")


class TrippleSpansProperties(BaseMixinClass, ABC):

    @property
    def x_span(self) -> float:
        return convert_length(self._get_parameter("x span", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @x_span.setter
    def x_span(self, x_span: float) -> None:
        Validate.positive_number(x_span, "x_span")
        self.settings.geometry.set_spans(x_span=x_span)

    @property
    def y_span(self) -> float:
        return convert_length(self._get_parameter("y span", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @y_span.setter
    def y_span(self, y_span: float) -> None:
        Validate.positive_number(y_span, "y_span")
        self.settings.geometry.set_spans(y_span=y_span)

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter("z span", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        Validate.positive_number(z_span, "z_span")
        self.settings.geometry.set_spans(z_span=z_span)


class SetSpansMethod(BaseMixinClass, ABC):
    class _SetSpansKwargs(TypedDict, total=False):
        pass

    @abstractmethod
    def set_spans(self, **kwargs) -> None:
        """Set the spans of the object. If the 'units' parameter is not provided, it defaults to
        the simulations' global_units parameter.
        """

        if not kwargs:
            raise ValueError("You must provide arguments to this function.")

        units = kwargs.pop("units", None)
        if units is None:
            units = self._simulation.__getattribute__("_global_units")
        else:
            Validate.in_literal(units, "units", LENGTH_UNITS)

        valid_arguments = list(self._SetSpansKwargs.__annotations__.keys())
        for span, value in kwargs.items():
            Validate.in_list(span, span, valid_arguments)
            Validate.positive_number(value, span)

            value = convert_length(value, units, "m")  # type: ignore
            self._set_parameter(span.replace("_", " "), value, "float")


########################################################################################################################
#                                                   DATACLASSES
########################################################################################################################
@dataclass
class TrippleSpans(Settings):
    x_span: float
    y_span: float
    z_span: float


########################################################################################################################
#                                               ABSTRACT BASE CLASSES
########################################################################################################################
class StructureGeometry(RelativeBaseGeometry, ABC):
    _parent: TStructure
    __slots__ = RelativeBaseGeometry.__slots__


class RoundGeometry(StructureGeometry, ABC):
    class _SetRadiusKwargs(TypedDict, total=False):
        pass

    @dataclass
    class _Spans(Settings):
        is_ellipsoid: bool

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: RoundGeometry._Spans

    __slots__ = StructureGeometry.__slots__

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

    @abstractmethod
    def set_radius(self, **kwargs) -> None:
        """
        Set the specified radius of the structure. If the 'units' parameter is not provided, it will default
        to the simulations' global_units variable.
        """

        if not kwargs:
            raise ValueError("You must provide arguments to this function.")

        valid_arguments = list(self._SetRadiusKwargs.__annotations__.keys())
        units = kwargs.pop("units", None)
        if units is None:
            units = self._simulation.__getattribute__("_global_units")
        else:
            Validate.in_literal(units, "units", LENGTH_UNITS)

        for radius, value in kwargs.items():

            Validate.in_list(radius, radius, valid_arguments)
            Validate.positive_number(value, radius)

            if any(char.isdigit() for char in radius):
                self._set_parameter("make ellipsoid", True, "bool")

            value = convert_length(value, units, "m")  # type: ignore
            self._set_parameter(radius.replace("_", " "), value, "float")


class CircularGeometry(RoundGeometry, ABC):
    class _SetRadiusKwargs(RoundGeometry._SetRadiusKwargs, total=False):
        radius: float
        radius_2: float

    @dataclass
    class _Spans(RoundGeometry._Spans):
        radius: float
        radius_2: float

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: CircularGeometry._Spans

    __slots__ = StructureGeometry.__slots__

    @abstractmethod
    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())

        radius = self._get_parameter("radius", "float")
        is_ellipsoid = self._get_parameter("make ellipsoid", "bool")
        if is_ellipsoid:
            radius_2 = self._get_parameter("radius 2", "float")
            if radius_2 == radius:
                is_ellipsoid = False
                radius_2 = None
        else:
            radius_2 = None

        settings.spans.radius = radius
        settings.spans.is_ellipsoid = is_ellipsoid
        settings.spans.radius_2 = radius_2
        return settings


class PolygonGeometryBase(StructureGeometry, ABC):
    @dataclass
    class _Spans:
        sides: int
        side_length: Optional[float]
        radius: Optional[float]
        is_equilateral: bool
        z_span: float

    @dataclass
    class _Settings(BaseGeometrySettings):
        vertices: List[Vertex]
        spans: PolygonGeometryBase._Spans

    __slots__ = RelativeBaseGeometry.__slots__

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
            length_units = self._simulation._global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        z_span = convert_length(z_span, length_units, "m")
        self._set_parameter("z span", z_span, "float")

    @staticmethod
    def _is_equilateral(vertices: List[Vertex]) -> bool:
        """
        Determines whether the polygon is equilateral by checking if all side lengths are equal.

        Returns:
        --------
        bool
            `True` if the polygon is equilateral, `False` otherwise.
        """

        # Calculate the side lengths
        side_lengths = []
        num_vertices = len(vertices)

        for i in range(num_vertices):
            # Get consecutive vertices (wraps around to the first vertex at the end)
            x1, y1 = vertices[i].x, vertices[i].y
            x2, y2 = vertices[(i + 1) % num_vertices].x, vertices[(i + 1) % num_vertices].y

            # Calculate the Euclidean distance between the two vertices
            side_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            side_lengths.append(side_length)

        # Check if all side lengths are approximately equal
        return np.allclose(side_lengths, side_lengths[0], atol=DECIMALS)

    def _get_side_length_and_radius(self, vertices: List[Vertex]) -> Optional[Tuple[float, float]]:
        """
        Returns the length of a side and the circumradius of the polygon if it is equilateral;
        otherwise, returns `None`.

        This method first checks if the polygon is equilateral by calling `_is_equilateral`. If the polygon
        is equilateral, it calculates the side length as the Euclidean distance between the first two vertices.
        It then computes the circumradius based on the side length and the number of vertices.

        Returns:
        --------
        Optional[Tuple[float, float]]
            A tuple containing:
            - The length of a side of the equilateral polygon.
            - The circumradius of the polygon.
            Returns `None` if the polygon is not equilateral.
        """

        # Check if the polygon is equilateral
        if not self._is_equilateral(vertices):
            return None

        # Get the first two vertices to calculate side length
        x1, y1 = vertices[0].x, vertices[0].x
        x2, y2 = vertices[1].y, vertices[1].y

        # Calculate the Euclidean distance as the side length
        side_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        # Calculate the circumradius
        num_vertices = len(vertices)

        circumradius = side_length / (2 * np.sin(np.pi / num_vertices))
        return side_length, circumradius

    def _get_list_of_vertices(self) -> List[Vertex]:
        """
        Retrieves all vertices of a polygon, rounding their coordinates, and creates a list of vertex
        dictionary objects.

        This method fetches the array of vertices for a polygon, rounds each vertex's coordinates to
        a specified number of decimal places, and converts them into `PolygonGeometry._Vertex` dictionary
        objects. Each vertex dictionary includes an `x` and `y` coordinate and a unique hash for
        identification.

        Returns:
        --------
        List[PolygonGeometry._Vertex]
            A list of dictionaries, where each dictionary represents a vertex with rounded coordinates
            (`x`, `y`) and a unique `hash`.
        """
        vertex_array = self._get_parameter("vertices", "list")
        vertices = []
        for vertex in vertex_array:
            vertex = np.round(vertex, decimals=DECIMALS).astype(float)
            vertex = Vertex(hash=None, x=float(vertex[0]), y=float(vertex[1]))
            vertex.fill_hash_fields()
            vertices.append(vertex)
        return vertices

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.vertices = self._get_list_of_vertices()
        z_span = self._get_parameter("z span", "float")
        sides = len(settings.vertices)
        side_length, radius = self._get_side_length_and_radius(settings.vertices)
        is_equilateral = False if side_length is None else True
        settings.spans.sides = sides
        settings.spans.side_length = side_length
        settings.spans.radius = radius
        settings.spans.is_equilateral = is_equilateral
        settings.spans.z_span = z_span
        settings.fill_hash_fields()
        return settings


########################################################################################################################
#                                               CONCRETE CLASSES
########################################################################################################################
class TrippleSpannableGeometryAbsolute(BaseGeometry, SetSpansMethod):
    class _SetSpansKwargs(TrippleSpansKwargs, total=False):
        units: Optional[LENGTH_UNITS]

    @dataclass
    class _Spans(TrippleSpans):
        ...

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: TrippleSpannableGeometryAbsolute._Spans

    __slots__ = RelativeBaseGeometry.__slots__

    def set_spans(self, **kwargs: Unpack[_SetSpansKwargs]) -> None:
        super().set_spans(**kwargs)

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.spans.x_span = self._get_parameter("x span", "float")
        settings.spans.y_span = self._get_parameter("y span", "float")
        settings.spans.z_span = self._get_parameter("z span", "float")
        settings.fill_hash_fields()
        return settings


class TrippleSpannableGeometryRelative(RelativeBaseGeometry, SetSpansMethod):
    class _SetSpansKwargs(TrippleSpansKwargs, total=False):
        units: Optional[LENGTH_UNITS
        ]

    @dataclass
    class _Spans(TrippleSpans):
        ...

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: TrippleSpannableGeometryRelative._Spans

    __slots__ = RelativeBaseGeometry.__slots__

    def set_spans(self, **kwargs: Unpack[_SetSpansKwargs]) -> None:
        super().set_spans(**kwargs)

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.spans.x_span = self._get_parameter("x span", "float")
        settings.spans.y_span = self._get_parameter("y span", "float")
        settings.spans.z_span = self._get_parameter("z span", "float")
        settings.fill_hash_fields()
        return settings


class RectangleGeometry(StructureGeometry, SetSpansMethod):
    class _SetSpansKwargs(TrippleSpansKwargs, total=False):
        units: Optional[LENGTH_UNITS]

    @dataclass
    class _Spans(TrippleSpans):
        ...

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: RectangleGeometry._Spans

    __slots__ = RelativeBaseGeometry.__slots__

    def set_spans(self, **kwargs: Unpack[_SetSpansKwargs]) -> None:
        super().set_spans(**kwargs)

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.spans.x_span = self._get_parameter("x span", "float")
        settings.spans.y_span = self._get_parameter("y span", "float")
        settings.spans.z_span = self._get_parameter("z span", "float")
        settings.fill_hash_fields()
        return settings


class CircleGeometry(CircularGeometry, ZSpanMethod):
    class _SetRadiusKwargs(CircularGeometry._SetRadiusKwargs, total=False):
        units: Optional[LENGTH_UNITS]

    @dataclass
    class _Spans(CircularGeometry._Spans):
        z_span: float

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: CircleGeometry._Spans

    __slots__ = RelativeBaseGeometry.__slots__

    def set_radius(self, **kwargs: Unpack[_SetRadiusKwargs]) -> None:
        super().set_radius(**kwargs)

    def _get_active_parameters(self) -> CircleGeometry._Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.spans.z_span = self._get_parameter("z span", "float")
        settings.fill_hash_fields()
        return settings


class SphereGeometry(CircularGeometry):
    class _SetRadiusKwargs(CircularGeometry._SetRadiusKwargs, total=False):
        radius_3: float
        units: Optional[LENGTH_UNITS]

    @dataclass
    class _Spans(CircularGeometry._Spans):
        radius_3: float

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: SphereGeometry._Spans

    __slots__ = CircularGeometry.__slots__

    def set_radius(self, **kwargs: Unpack[_SetRadiusKwargs]) -> None:
        super().set_radius(**kwargs)

    def _get_active_parameters(self) -> SphereGeometry._Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        if settings.spans.is_ellipsoid:
            radius_3 = self._get_parameter("radius 3", "float")
            if radius_3 == settings.spans.radius:
                settings.spans.is_ellipsoid = False
                radius_3 = None
        else:
            radius_3 = None
        settings.spans.radius_3 = radius_3
        settings.fill_hash_fields()
        return settings


class RingGeometry(RoundGeometry, ZSpanMethod):
    class _SetRadiusKwargs(RoundGeometry._SetRadiusKwargs, total=False):
        outer_radius: float
        inner_radius: float
        outer_radius_2: float
        inner_radius_2: float

    @dataclass
    class _Spans(RoundGeometry._Spans):
        outer_radius: float
        inner_radius: float
        outer_radius_2: float
        inner_radius_2: float
        theta_start: float
        theta_stop: float
        z_span: float

    @dataclass
    class _Settings(RoundGeometry._Settings):
        spans: RingGeometry._Spans

    __slots__ = RoundGeometry.__slots__

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

    def set_radius(self, **kwargs: Unpack[_SetRadiusKwargs]) -> None:
        super().set_radius(**kwargs)

    def _get_active_parameters(self) -> _Settings:

        settings = cast(self._Settings, super()._get_active_parameters())

        outer_radius = self._get_parameter("outer radius", "float")
        inner_radius = self._get_parameter("inner radius", "float")
        is_ellipsoid = self._get_parameter("make ellipsoid", "bool")

        if is_ellipsoid:
            outer_radius_2 = self._get_parameter("outer radius 2", "float")
            inner_radius_2 = self._get_parameter("inner radius 2", "float")

            if outer_radius == outer_radius_2 and inner_radius == inner_radius_2:
                is_ellipsoid = False
                outer_radius_2 = None
                inner_radius_2 = None
        else:
            outer_radius_2 = None
            inner_radius_2 = None

        settings.spans._update({"outer_radius": outer_radius, inner_radius: inner_radius,
                               "outer_radius_2": outer_radius_2, inner_radius_2: inner_radius_2,
                               "is_ellipsoid": is_ellipsoid,
                               "theta_start": self._get_parameter("theta start", "float"),
                               "theta_stop": self._get_parameter("theta stop", "float"),
                               "z_span": self._get_parameter("z span", "float")})
        settings.fill_hash_fields()
        return settings


class PolygonGeometry(PolygonGeometryBase):

    __slots__ = PolygonGeometryBase.__slots__

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
            length_units = self._simulation._global_units

        new_units = [(convert_length(vertex[0], from_unit=length_units, to_unit="m"),
                      convert_length(vertex[1], from_unit=length_units, to_unit="m")) for vertex in vertices]

        self._set_parameter("vertices", np.array(new_units), "list")
        self._parent.__setattr__("_nr_sides", len(vertices))


class EquilateralPolygonGeometry(PolygonGeometryBase):

    __slots__ = PolygonGeometryBase.__slots__

    def _create_regular_polygon(self, side_length=None, radius=None):
        """
        Creates vertices for an N-sided equilateral polygon.
        User can input either the side length or the radius.
        """

        if side_length is None and radius is None:
            raise ValueError("Either side_length or radius must be provided.")

        N = self._parent.__getattribute__("_nr_sides")

        if radius is None:
            # Calculate radius from side length if radius is not provided
            radius = side_length / (2 * np.sin(np.pi / N))

        vertices = []
        for i in range(N):
            # Rotate by adding pi/2 to place the first vertex at the top
            angle = i * 2 * np.pi / N  # Shift angle by -90 degrees
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
            length_units = self._simulation._global_units
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
            length_units = self._simulation._global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        vertices = self._create_regular_polygon(
            radius=convert_length(radius, length_units, "m")
        )

        self._set_parameter("vertices", vertices, "list")


class PyramidGeometry(StructureGeometry, SetSpansMethod):
    class _SetSpansKwargs(TypedDict, total=False):
        x_span_bottom: float
        x_span_top: float
        y_span_bottom: float
        y_span_top: float
        z_span: float
        units: Optional[LENGTH_UNITS]

    @dataclass
    class _Spans(Settings):
        x_span_bottom: float
        x_span_top: float
        y_span_bottom: float
        y_span_top: float
        z_span: float

    @dataclass
    class _Settings(BaseGeometrySettings):
        spans: PyramidGeometry._Spans

    __slots__ = RelativeBaseGeometry.__slots__

    def set_spans(self, **kwargs: Unpack[_SetSpansKwargs]) -> None:
        super().set_spans(**kwargs)

    def _get_active_parameters(self) -> PyramidGeometry._Settings:

        settings = cast(self._Settings, super()._get_active_parameters())
        settings.spans = PyramidGeometry._Spans(hash=None,
                                                x_span_bottom=self._get_parameter("x span bottom", "float"),
                                                x_span_top=self._get_parameter("x span top", "float"),
                                                y_span_bottom=self._get_parameter("y span bottom", "float"),
                                                y_span_top=self._get_parameter("y span top", "float"),
                                                z_span=self._get_parameter("z span", "float"))
        settings.fill_hash_fields()
        return settings


class MeshGeometry(TrippleSpannableGeometryRelative):
    @dataclass
    class _Settings(TrippleSpannableGeometryRelative._Settings):
        ...

    _parent: MeshBase
    __slots__ = TrippleSpannableGeometryRelative.__slots__

    def __init__(self, parent: MeshBase, simulation: TSimulation) -> None:
        super().__init__(parent, simulation)

    def set_based_on_a_structure(self, structure: Union['TStructure', 'PhotonicCrystal'], buffer: float = None,
                                 length_units: LENGTH_UNITS = None) -> None:
        """
        Configure the mesh override parameters based on an existing structure.

        This method allows users to set mesh override positions and spans based on a specified
        structure in the simulation. The position and spans are determined using the center position
        and dimensions of the named structure. Users can also specify a buffer to extend the
        mesh override region outwards in all directions.

        If multiple mesh override regions are present, the meshing algorithm will utilize the
        override region that results in the smallest mesh for that volume of space. Constraints
        from mesh override regions take precedence over the default automatic mesh, even if they
        lead to a larger mesh size.

        Args:
            structure (StructureBase): The structure to base the mesh override parameters on.
                                       This must be an instance of StructureBase or a subclass
                                       that includes a valid name.
            buffer (float, optional): A positive value indicating the buffer distance to extend
                                      the mesh override region in all directions. If None, no
                                      buffer will be applied.
            length_units (LENGTH_UNITS, optional): The units of the provided buffer distance.
                                                    If None, the global units of the simulation
                                                    will be used.

        Raises:
            ValueError: If the provided buffer is negative or if the length_units is not valid.
        """

        if hasattr(structure, "set_structure"):
            structure_name = structure.name + "_structure"
        else:
            structure_name = structure.name

        self._set_parameter("based on a structure", True, "bool")
        self._set_parameter("structure", structure_name, "str")

        # Assign the structure this mesh and the structure to the mesh
        if not hasattr(structure, "_bulk_mesh"):  # Check correct type without importing. All structures have this.
            raise ValueError("The 'structure' parameter must be an instance of StructureBase or a subclass.")
        structure._bulk_mesh = self._parent
        self._parent._structure = structure

        if buffer is not None:
            if length_units is None:
                length_units = self._simulation._global_units
            else:
                Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

            buffer = convert_length(buffer, from_unit=length_units, to_unit="m")
            self._set_parameter("buffer", buffer, "float")

    def set_directly_defined(self) -> None:
        """
        Enable direct definition of the mesh geometry.

        This method must be called to allow users to define the geometry of the mesh directly
        using coordinates and spans, similar to standard mesh definition practices.
        """
        self._parent._structure = None
        self._set_parameter("directly defined", True, "bool")

    def set_spans(self, **kwargs: Unpack[TrippleSpannableGeometryRelative._SetSpansKwargs]) -> None:

        if self._get_parameter("based on a structure", "bool"):
            raise ValueError("You cannot set the spans of the mesh when 'based on a structure' is enabled. "
                             "Enable 'directly defined' first.")
        super().set_spans(**kwargs)

    def set_position(self, **kwargs: Unpack[TrippleSpannableGeometryRelative._SetPositionKwargs]) -> None:

        if self._get_parameter("based on a structure", "bool"):
            raise ValueError("You cannot set the position of the mesh when 'based on a structure' is enabled. "
                             "Enable 'directly defined' first.")
        super().set_position(**kwargs)

    def _get_active_parameters(self) -> _Settings:
        settings = super()._get_active_parameters()
        if self._get_parameter("based on a structure", "bool"):
            spans = settings.spans
            structure = self._parent.based_on_structure
            settings.position = structure.geometry_settings._get_active_parameters().position
            buffer = self._get_parameter("buffer", "float")
            min_coords, max_coords = structure._get_bounding_box()
            x_min, y_min, z_min = min_coords[0], min_coords[1], min_coords[2]
            x_max, y_max, z_max = max_coords[0], max_coords[1], max_coords[2]
            spans.x_span = x_max - x_min + 2 * buffer
            spans.y_span = y_max - y_min + 2 * buffer
            spans.z_span = z_max - z_min + 2 * buffer
            settings.fill_hash_fields()
        return settings


########################################################################################################################
#                                               MONITOR GEOMETRIES
########################################################################################################################
class MonitorGeometryAll(TrippleSpannableGeometryRelative):
    @dataclass
    class _Spans(Settings):
        monitor_type: MONITOR_TYPES_ALL
        x_span: float
        y_span: float
        z_span: float
        down_sample_X: int
        down_sample_Y: int
        down_sample_Z: int

    @dataclass
    class _Settings(TrippleSpannableGeometryRelative._Settings):
        spans: MonitorGeometryAll._Spans

    __slots__ = TrippleSpannableGeometryRelative.__slots__

    def set_spans(self, **kwargs: Unpack[TrippleSpannableGeometryRelative._SetSpansKwargs]) -> None:

        monitor_type = self._get_parameter("monitor type", "str")

        x_span = kwargs.get("x_span", None)
        y_span = kwargs.get("y_span", None)
        z_span = kwargs.get("z_span", None)

        if monitor_type == "Point":
            raise ValueError(
                f"You are trying to set the spans of a monitor that is of type 'Point', as thus has no "
                f"spans in any directions. Set the monitor type to something not 1-dimensional to set spans."
            )
        elif monitor_type == "Linear X" and any([z_span is not None, y_span is not None]):
            raise ValueError(
                f"You are trying to set the Y or Z spans of a monitor that is of type 'Linear X', as thus has no "
                f"spans in these directions. Set the monitor type to something else to set these spans."
            )
        elif monitor_type == "Linear Y" and any([x_span is not None, z_span is not None]):
            raise ValueError(
                f"You are trying to set the X or Z spans of a monitor that is of type 'Linear Y', as thus has no "
                f"spans in these directions. Set the monitor type to something else to set these spans."
            )
        elif monitor_type == "Linear Z" and any([x_span is not None, y_span is not None]):
            raise ValueError(
                f"You are trying to set the X or Y spans of a monitor that is of type 'Linear Z', as thus has no "
                f"spans in these directions. Set the monitor type to something else to set these spans."
            )
        elif monitor_type == "2D X-normal" and x_span is not None:
            raise ValueError(
                f"You are trying to set the X span of a monitor that is of type '2D X-normal', as thus has no "
                f"span in this direction. Set the monitor type to something else to set this span."
            )
        elif monitor_type == "2D Y-normal" and y_span is not None:
            raise ValueError(
                f"You are trying to set the Y span of a monitor that is of type '2D Y-normal', as thus has no "
                f"span in this direction. Set the monitor type to something else to set this span."
            )
        elif monitor_type == "2D Z-normal" and z_span is not None:
            raise ValueError(
                f"You are trying to set the Z span of a monitor that is of type '2D Z-normal', as thus has no "
                f"span in this direction. Set the monitor type to something else to set this span."
            )

        super().set_spans(**kwargs)

    def set_monitor_type(self, monitor_type: MONITOR_TYPES_ALL) -> None:
        """
        Sets the type and orientation of the monitor for the simulation.

        The monitor type determines the available spatial settings for the simulation region.
        Depending on the monitor type selected, different spatial parameters will be enabled,
        including the center position, min/max positions, and span for the X, Y, and Z axes.

        Args:
            monitor_type (MONITOR_TYPES_ALL): The type of monitor to set, which controls the available
                                               spatial settings for the simulation region.

        Raises:
            ValueError: If the provided monitor_type is not a valid type.
        """

        self._set_parameter("monitor type", monitor_type, "str")

    def set_down_sampling(self, **kwargs: Unpack[AxesIntKwargs]) -> None:
        """
        Sets the spatial downsampling value for the specified monitor axes.

        The downsampling parameter controls how frequently data is recorded along the specified axis.
        A downsample value of N means that data will be sampled every Nth grid point.
        Setting the downsample value to 1 will provide the most detailed spatial information,
        recording data at every grid point.

        Args:
            x/y/z (int): The downsample value along the specified axis. Must be greater than or equal to 1.

        Raises:
            ValueError: If the down_sampling value is not within the valid range (1 to infinity).
        """

        if not kwargs:
            raise ValueError("You must provide arguments for this method")

        for axis, down_sampling in kwargs.items():
            Validate.integer_in_range(down_sampling, "down_sampling", (1, float('inf')))
            self._set_parameter(f"down sample {axis.capitalize()}", down_sampling, "int")

    def _get_active_parameters(self) -> _Settings:

        settings = cast(self._Settings, super()._get_active_parameters())
        settings.spans.monitor_type = self._get_parameter("monitor type", "str")

        for axis in get_args(AXES):
            axis = axis.capitalize()
            if axis.capitalize() not in settings.spans.monitor_type:
                settings.__setattr__(f"down_sample_{axis}", self._get_parameter(f"down sample {axis}", "int"))

        settings.spans.hash = None
        settings.hash = None
        settings.fill_hash_fields()
        return settings


class MonitorGeometry3D(MonitorGeometryAll):
    @dataclass
    class _Spans(MonitorGeometryAll._Spans):
        monitor_type: MONITOR_TYPES_3D

    @dataclass
    class _Settings(MonitorGeometryAll._Settings):
        spans: MonitorGeometry3D._Spans

    __slots__ = MonitorGeometryAll.__slots__

    def set_monitor_type(self, monitor_type: MONITOR_TYPES_3D) -> None:
        super().set_monitor_type(monitor_type)

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


class MonitorGeometry2D(MonitorGeometryAll):
    @dataclass
    class _Spans(MonitorGeometryAll._Spans):
        monitor_type: MONITOR_TYPES_2D

    @dataclass
    class _Settings(MonitorGeometryAll._Settings):
        spans: MonitorGeometry2D._Spans

    __slots__ = MonitorGeometryAll.__slots__

    def set_monitor_type(self, monitor_type: MONITOR_TYPES_2D) -> None:
        super().set_monitor_type(monitor_type)  # type: ignore

    def _get_active_parameters(self) -> _Settings:
        return cast(self._Settings, super()._get_active_parameters())


########################################################################################################################
#                                               SOURCE GEOMETRIES
########################################################################################################################
class SourceGeometry(TrippleSpannableGeometryRelative):

    __slots__ = TrippleSpannableGeometryRelative.__slots__

    def set_spans(self, **kwargs: Unpack[TrippleSpannableGeometryRelative._SetSpansKwargs]) -> None:

        injection_axis: str = self._get_parameter("injection axis", "str")

        units = kwargs.pop("units", None)
        for axis, span in kwargs.items():
            if injection_axis.startswith(axis[0]) and span is not None:
                raise UserWarning(f"You are trying to set the {axis[0]}-span of the source when the injection axis "
                                  f"is along the {axis[0]}-axis. The source does therefore not have a spatial extent "
                                  f"in this direction.")
        kwargs["units"] = units  # type: ignore
        super().set_spans(**kwargs)