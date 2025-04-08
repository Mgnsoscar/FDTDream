from abc import ABC, abstractmethod
from typing import List, Any

from .simulation_object import SimulationObjectInterface
from ..lumapi import Lumapi
from ..resources.literals import LENGTH_UNITS


class SimulationInterface(ABC):
    _structures: List[SimulationObjectInterface]
    _sources: List[SimulationObjectInterface]
    _monitors: List[SimulationObjectInterface]
    _meshes: List[SimulationObjectInterface]
    _fdtd: Any

    @abstractmethod
    def _units(self) -> LENGTH_UNITS:
        ...

    @property
    @abstractmethod
    def _lumapi(self) -> Lumapi:
        ...

    @abstractmethod
    def _check_name(self, name: str) -> None:
        ...
