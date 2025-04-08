from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self, Type, TypeVar

from ..interfaces import SimulationObjectInterface
from ..resources.literals import LENGTH_UNITS

T = TypeVar("T")


class ModuleInterface(ABC):
    _parent_object: SimulationObjectInterface

    @abstractmethod
    def __init__(self, parent_object: SimulationObjectInterface, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def _copy(self, new_parent: SimulationObjectInterface, *args, **kwargs) -> Self:
        pass

    @abstractmethod
    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        pass

    @abstractmethod
    def _set(self, parameter: str, value: T) -> T:
        ...

    @property
    @abstractmethod
    def _units(self) -> LENGTH_UNITS:
        ...


class ModuleCollectionInterface(ModuleInterface, ABC):
    _parent_object: SimulationObjectInterface

    @abstractmethod
    def __init__(self, parent_object: SimulationObjectInterface, *args, **kwargs) -> None:
        ...

    @abstractmethod
    def _copy(self, new_parent: SimulationObjectInterface, *args, **kwargs) -> Self:
        ...

    @abstractmethod
    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        ...

    @abstractmethod
    def _set(self, parameter: str, value: T) -> T:
        ...
