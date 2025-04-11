from abc import ABC
from copy import copy
from typing import TypeVar, Type, Self, Any
from ...resources.errors import FDTDreamParameterNotFound

from ..structure import Structure

T = TypeVar("T")


class ScriptedStructure(Structure, ABC):

    # region Class Body

    _closest_parent: Structure | None

    _enabled: bool
    _name: str

    # Positional
    _x: float
    _y: float
    _z: float
    _use_relative_coordinates: bool

    # Rotational
    _first_axis: str
    _second_axis: str
    _third_axis: str
    _rotation_1: float
    _rotation_2: float
    _rotation_3: float

    # Material
    _material: str
    _index: str
    _index_units: str
    _mesh_order: int
    _grid_attribute_name: str | None

    __slots__ = ["_enabled", "_name", "_x", "_y", "_z", "_use_relative_coordinates",
                 "_first_axis", "_second_axis", "_third_axis", "_rotation_1", "_rotation_2", "_rotation_3",
                 "_material", "_index", "_index_units", "_mesh_order", "_grid_attribute_name",
                 "_closest_parent"]

    # endregion Class Body

    # region Dev. Methods

    def _add_parent(self, parent) -> None:
        """Replaces the closest parent object."""

        if self._closest_parent is not None:
            if self in self._closest_parent._structures:
                self._closest_parent._structures.remove(self)
            if self._closest_parent in self._parents:
                self._parents.remove(self._closest_parent)

            self._closest_parent = parent


            if self not in self._closest_parent._structures:
                self._closest_parent._structures.append(self)
            if self._closest_parent not in self._parents:
                self._parents.insert(0, self._closest_parent)
        else:
            self._closest_parent = parent
            if self not in self._closest_parent._structures:
                self._closest_parent._structures.append(self)
            if self._closest_parent not in self._parents:
                self._parents.insert(0, self._closest_parent)

    def _initialize_variables(self) -> None:
        """Initializes default attributes common for all structure types."""

        self._closest_parent = None
        self._enabled = True
        self._use_relative_coordinates = True
        self._x, self._y, self._z = 0, 0, 0
        self._first_axis, self._second_axis, self._third_axis = "none", "none", "none"
        self._rotation_1, self._rotation_2, self._rotation_3 = 0, 0, 0
        self._material = "<Object defined dielectric>"
        self._index = "1.4"
        self._grid_attribute_name = None

    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        return getattr(self, "_" + parameter.replace(" ", "_"))

    def _set(self, parameter: str, value: Type[T]) -> T:

        # Correctly format
        parameter = f"_{parameter.replace(' ', '_')}"

        # Check if parameter exists
        if parameter not in ScriptedStructure.__slots__ + self.__slots__:
            raise FDTDreamParameterNotFound(f"Parameter {parameter} is not a valid parameter for class "
                                            f"{self.__class__.__name__}")

        setattr(self, parameter, value)

        # Update the script of the parent object if one has been assigned.
        if self._closest_parent is not None:
            self._closest_parent._update()

        return value

    # endregion Dev. Methods

    # region User Methods

    def copy(self, name: str = None, **kwargs: Any) -> Self:

        # Create a copy of the object.
        copied = copy(self)

        if name is not None:
            copied._name = name

        if new_parent := kwargs.get("new_parent", None):
            if self._closest_parent in copied._parents:
                copied._parents.remove(self._closest_parent)

            copied._closest_parent = None
            copied._closest_parent = new_parent
            copied._parents.insert(0, self._closest_parent)

        else:
            new_parent = self._closest_parent

        if copied not in new_parent._structures:
            new_parent._structures.append(copied)

        # Remove closest parent to avoid uneccesary uppdate() calls.
        copied._closest_parent = None
        #
        # Copy over the settings modules.
        copied.settings = self.settings._copy(copied)
        #
        # Apply kwargs
        copied._process_kwargs(copied=True, **kwargs)
        #
        # Reassign closest parent
        copied._closest_parent = new_parent
        #
        # Update closest parent
        if not kwargs.get("new_parent", None):
            self._closest_parent._update()

        return copied

    # endregion User Methods
