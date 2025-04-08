from __future__ import annotations

from abc import ABC, abstractmethod
from copy import copy
from typing import Self, Type, TypeVar

from ..interfaces import SimulationObjectInterface, ModuleInterface, ModuleCollectionInterface
from ..resources.literals import LENGTH_UNITS

T = TypeVar("T")


class Module(ModuleInterface, ABC):

    # region Class Body

    _parent_object: SimulationObjectInterface
    __slots__ = ["_parent_object"]

    # endregion Class Body

    # region Dev. Methods

    def __init__(self, parent_object: SimulationObjectInterface, *args, **kwargs) -> None:

        # Assign variables
        self._parent_object = parent_object

    def _copy(self, new_parent: SimulationObjectInterface, *args, **kwargs) -> Self:
        """Creates a new copy of the module and assigns a new parent object to the copied one."""
        copied = self.__class__(new_parent, *args, **kwargs)
        return copied

    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        """Queries the Lumerical FDTD Api to fetch the value of a parameter attributed to the object."""
        return self._parent_object._get(parameter, parameter_type)

    def _set(self, parameter: str, value: T) -> T:
        """
        Uses the Lumerical FDTD API to assign a value to a parameter attributing to the object.
        Returns the accepted value.
        """
        return self._parent_object._set(parameter, value)

    # endregion Dev. Methods

    # region Dev. Properties

    @property
    def _units(self) -> LENGTH_UNITS:
        """Fetches the global units associated with the parent simulation."""
        return self._parent_object._units

    # endregion Dev. Properties


class ModuleCollection(ModuleCollectionInterface, ABC):

    # region Class Body

    _parent_object: SimulationObjectInterface
    __slots__ = ["_parent_object"]

    # endregion Class Body

    # region Dev. Methods

    @abstractmethod
    def __init__(self, parent_object: SimulationObjectInterface, *args, **kwargs) -> None:

        # Assign the parent object.
        self._parent_object = parent_object

    def _copy(self, new_parent: SimulationObjectInterface, *args, **kwargs) -> Self:
        """
        Creates a copy of the module collection whith a new parent object. All submodules are also copied with new
        references to the parent object.

        Args:
            new_parent: The new parent object.
            *args:
            **kwargs:

        Returns:
            The copied module collection.

        """
        # Create copy and assign new parent object
        copied = copy(self)
        copied._parent_object = new_parent

        # Fetch a dictionary with the references to contained submodules
        submodules = {k: self.__getattribute__(k) for k in self.__slots__}

        # Copy all submodules an assign them to the copied module collection
        for name, module in submodules.items():
            setattr(copied, name, module._copy(new_parent))

        return copied

    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        """Queries the Lumerical FDTD Api to fetch the value of a parameter attributed to the object."""
        return self._parent_object._get(parameter, parameter_type)

    def _set(self, parameter: str, value: T) -> T:
        """
        Uses the Lumerical FDTD API to assign a value to a parameter attributing to the object.
        Returns the accepted value.
        """
        return self._parent_object._set(parameter, value)

    @property
    def _units(self) -> LENGTH_UNITS:
        """Fetches the global units associated with the parent simulation."""
        return self._parent_object._units

    # endregion Dev. Methods
