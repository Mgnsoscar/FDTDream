from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

import trimesh

from .simulation_object import SimulationObjectInterface


class StructureInterface(SimulationObjectInterface, ABC):
    """
    Interface for structure-type simulation objects.

    Defines the required methods and properties that a structure must implement, 
    ensuring compatibility with Lumerical's FDTD API and mesh handling.
    """

    @abstractmethod
    def _getmaterial(self, name: Optional[str], parameter: Optional[str]) -> Any:
        """Fetches material data from the material database."""
        pass

    @abstractmethod
    def _get_mesh_order(self) -> int:
        """Returns the mesh order of the material in the structure."""
        pass

    @abstractmethod
    def _get_scripted(self, position: Iterable) -> str:
        """Returns the Lumerical FDTD script that reproduces the object at the given position (in meters)."""
        pass

    @abstractmethod
    def _get_trimesh(self) -> trimesh.Trimesh:
        """Creates and returns a 3D trimesh object representing the structure."""
        pass
