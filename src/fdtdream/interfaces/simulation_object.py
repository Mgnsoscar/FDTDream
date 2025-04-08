from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar, Self

import numpy as np
from numpy.typing import NDArray

from ..resources.literals import LENGTH_UNITS

T = TypeVar("T")


class SimulationObjectInterface(ABC):
    """
    Interface for simulation objects within a Lumerical FDTD simulation.

    Provides a standardized structure for objects participating in the simulation hierarchy,
    ensuring consistent interaction with simulation settings, parameters, and hierarchy.
    """

    _name: str

    @abstractmethod
    def _check_name(self, name: str) -> None:
        pass

    @abstractmethod
    def _get_scope(self) -> str:
        pass

    @abstractmethod
    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        pass

    @abstractmethod
    def _set(self, parameter: str, value: T) -> T:
        pass

    @abstractmethod
    def _get_position(self, absolute: bool = False) -> NDArray[np.float64]:
        pass

    @abstractmethod
    def _get_bounding_box(self, absolute: bool = False) -> NDArray:
        pass

    @abstractmethod
    def place_next_to(self, other_object: SimulationObjectInterface, side: str, offset: float = 0) -> Self:
        pass

    @abstractmethod
    def min(self, axis: str, absolute: bool = False) -> float:
        pass

    @abstractmethod
    def max(self, axis: str, absolute: bool = False) -> float:
        pass

    @abstractmethod
    def span(self, axis: str) -> float:
        pass

    @abstractmethod
    def _get_corners(self, absolute: bool = False) -> NDArray:
        pass

    @property
    @abstractmethod
    def x(self) -> float:
        pass

    @x.setter
    @abstractmethod
    def x(self, x: float) -> None:
        pass

    @property
    @abstractmethod
    def y(self) -> float:
        pass

    @y.setter
    @abstractmethod
    def y(self, y: float) -> None:
        pass

    @property
    @abstractmethod
    def z(self) -> float:
        pass

    @z.setter
    @abstractmethod
    def z(self, z: float) -> None:
        pass

    @property
    @abstractmethod
    def _units(self) -> LENGTH_UNITS:
        pass
