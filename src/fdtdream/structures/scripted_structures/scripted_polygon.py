from typing import Unpack, Self

import numpy as np
from numpy.typing import NDArray

from .scripted_structure import ScriptedStructure
from ..polygon import Polygon, PolygonKwargs
from ...interfaces import SimulationInterface


class ScriptedPolygon(Polygon, ScriptedStructure):

    _vertices: NDArray
    _z_span: float

    __slots__ = ["_vertices", "_z_span"]

    def __init__(self, sim: SimulationInterface, name: str = "polygon", **kwargs: Unpack[PolygonKwargs]):
        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _initialize_variables(self) -> None:
        super()._initialize_variables()
        self._vertices = np.array([(-100e-9, -100e-9), (0, 100e-9), (100e-9, 100e-9)])
        self._z_span = 100e-9

    def copy(self, name: str = None, **kwargs: Unpack[PolygonKwargs]) -> Self:
        return ScriptedStructure.copy(self, name, **kwargs)

