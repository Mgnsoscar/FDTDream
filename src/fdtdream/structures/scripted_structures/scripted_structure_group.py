from typing import Unpack, Self, Sequence, Any

from copy import copy
from .scripted_structure import ScriptedStructure
from ..sphere import Sphere, SphereKwargs
from ...interfaces import SimulationInterface
from ..structure_group import StructureGroup


class ScriptedStructureGroup(StructureGroup, ScriptedStructure):

    # region Class Body

    _construction_group: bool
    _script: str

    __slots__ = ["_construction_group", "str"]

    # endregion Class Body

    # region Dev. Methods

    def __init__(self, sim: SimulationInterface, name: str = "structure group", **kwargs: SphereKwargs):

        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _add_parent(self, parent) -> None:
        """Adds a group type object to the scripted structure and updates the parent."""
        self._parents.append(parent)
        self._closest_parent = parent
        parent._structures.append(self)
        parent._update()

    def _remove_parent(self):
        """Removes the scripted structure from the parent group and updates the parent group."""
        self._parents.remove(self._closest_parent)
        closest_parent = self._closest_parent
        self._closest_parent = None
        closest_parent._structures.remove(self)
        closest_parent._update()

    def _initialize_variables(self) -> None:
        """Initializes default attributes common for all structure types."""
        super()._initialize_variables()
        self._construction_group = True
        self._script = ""

    # endregion Dev. Methods

    # region User Methods

    def copy(self, name: str = None, **kwargs: Any) -> Self:

        return ScriptedStructure.copy(self, name, **kwargs)

    # endregion User Methods
