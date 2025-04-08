from typing import Unpack, Self

from .scripted_structure import ScriptedStructure
from ..regular_polygon import RegularPolygon, RegularPolygonKwargs
from ...interfaces import SimulationInterface


class ScriptedRegularPolygon(RegularPolygon, ScriptedStructure):

    _sides: int
    _z_span: float

    __slots__ = ["_sides"]

    def __init__(self, sim: SimulationInterface, name: str = "regular polygon", **kwargs: RegularPolygonKwargs):
        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _initialize_variables(self) -> None:
        super()._initialize_variables()
        self._sides = 6
        self._z_span = 100e-9

    def copy(self, name: str = None, **kwargs: Unpack[RegularPolygonKwargs]) -> Self:
        return ScriptedStructure.copy(self, name, **kwargs)


