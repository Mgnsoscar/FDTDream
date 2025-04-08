from typing import Unpack, Self

from .scripted_structure import ScriptedStructure
from ..rectangle import Rectangle, RectangleKwargs
from ...interfaces import SimulationInterface


class ScriptedRectangle(Rectangle, ScriptedStructure):

    _x_span: float
    _y_span: float
    _z_span: float

    __slots__ = ["_x_span", "_y_span", "_z_span"]

    def __init__(self, sim: SimulationInterface, name: str = "rectangle", **kwargs: RectangleKwargs):

        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _initialize_variables(self) -> None:
        super()._initialize_variables()
        self._x_span = 100e-9
        self._y_span = 100e-9
        self._z_span = 100e-9

    def copy(self, name: str = None, **kwargs: Unpack[RectangleKwargs]) -> Self:
        return ScriptedStructure.copy(self, name, **kwargs)


