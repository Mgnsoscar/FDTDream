from abc import ABC
from typing import Self

import numpy as np
from numpy.typing import NDArray

from ..base_classes import SimulationObject
from ..resources.functions import convert_length


class Monitor(SimulationObject, ABC):

    def copy(self, name, **kwargs) -> Self:

        # Copy through super() call
        copied = super().copy(name, **kwargs)

        # Add the python object to the parent simulation
        self._sim._monitors.append(copied)

        return copied

    def _get_corners(self, absolute: bool = False) -> NDArray[np.float64]:
        # Fetch the parameters for radius, radius_2, and z_span, and center position
        half_spans = np.array([self._get("x span", float), self._get("y span", float), self._get("z span", float)]) / 2
        position = self._get_position(absolute)

        min_pos = position - half_spans
        max_pos = position + half_spans

        corners = np.array([
            [min_pos[0], position[1], min_pos[2]], [min_pos[0], position[1], max_pos[2]],
            [max_pos[0], position[1], min_pos[2]], [max_pos[0], position[1], max_pos[2]],
            [position[0], min_pos[1], min_pos[2]], [position[0], min_pos[1], max_pos[2]],
            [position[0], max_pos[1], min_pos[2]], [position[0], max_pos[1], max_pos[2]]
        ])

        return np.unique(corners, axis=0)

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