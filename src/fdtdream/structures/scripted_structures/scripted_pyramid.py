from typing import Unpack, Self

from .scripted_structure import ScriptedStructure
from ..pyramid import Pyramid, PyramidKwargs
from ...interfaces import SimulationInterface


class ScriptedPyramid(Pyramid, ScriptedStructure):
    _x_span_bottom: float
    _x_span_top: float
    _y_span_bottom: float
    _y_span_top: float
    _z_span: float

    __slots__ = ["_x_span_bottom", "_x_span_top", "_y_span_bottom", "_y_span_top", "_z_span"]

    def __init__(self, sim: SimulationInterface, name: str = "pyramid", **kwargs: PyramidKwargs):

        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _initialize_variables(self) -> None:
        super()._initialize_variables()
        self._x_span_bottom = 200e-9
        self._x_span_top = 100e-9
        self._y_span_bottom = 200e-9
        self._y_span_top = 200e-9
        self._z_span = 200e-9

    def copy(self, name: str = None, **kwargs: Unpack[PyramidKwargs]) -> Self:
        return ScriptedStructure.copy(self, name, **kwargs)


