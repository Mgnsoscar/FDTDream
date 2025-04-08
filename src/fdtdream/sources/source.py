from abc import ABC
from typing import TypedDict, Unpack, Self, Any

from ..base_classes import SimulationObject, BaseGeometry
from ..resources.functions import convert_length


class SourceGeometry(BaseGeometry):
    """
    Key-value pairs that can be used in the any Source type's constructor.
    """
    class _Dimensions(TypedDict, total=False):
        x_span: float
        y_span: float
        z_span: float

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        for k, v in kwargs.items():
            if k[0] == self._get("injection axis", str)[0]:
                raise ValueError(f"'{k}' cannot be set for source with injection axis '{k[0]}'.")
        super().set_dimensions(**kwargs)


class Source(SimulationObject, ABC):

    settings: Any

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Rectangle structure type."""

        # Abort if the kwargs are empty
        if not kwargs:
            return

        # Initialize dicts
        position = {}
        dimensions = {}
        injection_axis = None
        direction = None

        # Filter kwargs
        for k, v in kwargs.items():
            if k == "injection_axis":
                injection_axis = v
            elif k == "direction":
                direction = v
            elif k in ["x", "y", "z"]:
                position[k] = v
            elif k in ["x_span", "y_span", "z_span"]:
                dimensions[k] = v

        # Apply kwargs
        if position:
            self.settings.geometry.set_position(**position)
        if dimensions:
            self.settings.geometry.set_dimensions(**dimensions)
        if injection_axis:
            self.settings.general.set_injection_axis(injection_axis)
        if direction:
            self.settings.general.set_direction(direction)

    def copy(self, name, **kwargs) -> Self:

        # Copy through super() call
        copied = super().copy(name, **kwargs)

        # Add the python object to the parent simulation
        self._sim._sources.append(copied)

        return copied

    @property
    def polarization(self) -> float:
        """
        Returns the absolute polarization angle in degrees, where 0 deg is E-field along the positive x-axis when
        injection actis is backwards along the z-axis. Angle goes counrterclockwise.
        """
        definition = self._get("polarization definition", str)
        phi = self._get("angle phi", float)
        if definition == "angle":
            return (self._get("polarization angle", float) + phi) % 360
        elif definition == "S":
            return (90 + phi) % 360
        else:
            return phi % 360 - 180

    @polarization.setter
    def polarization(self, angle: float) -> None:
        """
        Sets the absolute polarization angle in degrees, where 0 deg is E-field along the positive x-axis when
        injection actis in backwards along the z-axis. Angle goes counrterclockwise.
        """
        definition = self._get("polarization definition", str)
        angle = angle % 360
        if definition == "angle":
            self._set("polarization angle", 0)
            self._set("angle phi", angle)
        elif definition == "S":
            self._set("angle phi", angle - 90)
        else:
            self._set("angle phi", angle - 180)

    @property
    def x_span(self) -> float:
        return convert_length(self._get("x span", float), "m", self._units)

    @x_span.setter
    def x_span(self, span: float) -> None:
        if self._get("injection axis", str) == "x-axis":
            raise ValueError(f"x-span cannot be set for source with injection axis x.")
        self._set("x span", convert_length(span, self._units, "m"))

    @property
    def y_span(self) -> float:
        return convert_length(self._get("y span", float), "m", self._units)

    @y_span.setter
    def y_span(self, span: float) -> None:
        if self._get("injection axis", str) == "y-axis":
            raise ValueError(f"y-span cannot be set for source with injection axis y.")
        self._set("y span", convert_length(span, self._units, "m"))

    @property
    def z_span(self) -> float:
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        if self._get("injection axis", str) == "z-axis":
            raise ValueError(f"z-span cannot be set for source with injection axis x.")
        self._set("z span", convert_length(span, self._units, "m"))