from typing import Unpack, Self

import numpy as np

from .scripted_structure import ScriptedStructure
from ..planar_solid import PlanarSolid, PlanarSolidKwargs
from ...interfaces import SimulationInterface


class ScriptedPlanarSolid(PlanarSolid, ScriptedStructure):
    _scale: float
    _vertices: np.ndarray
    _facets: np.ndarray
    __slots__ = ["_scale", "_vertices", "_facets"]

    def __init__(self, sim: SimulationInterface, name: str = "solid", **kwargs: PlanarSolidKwargs):

        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _initialize_variables(self) -> None:
        super()._initialize_variables()
        self._scale = 1
        # Initialize as a rectangle, as in Lumerical FDTD
        self._vertices = np.array([
            [-1.8e-07, - 1.8e-07, - 1.8e-07],
            [1.8e-07, - 1.8e-07, - 1.8e-07],
            [1.8e-07, 1.8e-07, - 1.8e-07],
            [-1.8e-07, 1.8e-07, - 1.8e-07],
            [-1.8e-07, - 1.8e-07, 1.8e-07],
            [1.8e-07, - 1.8e-07, 1.8e-07],
            [1.8e-07, 1.8e-07, 1.8e-07],
            [-1.8e-07, 1.8e-07, 1.8e-07]
        ])
        self._facets = np.array([
            [[[1, 1, 2, 3, 4, 5,]],
             [[4, 5, 6, 7, 8, 6,]],
             [[3, 8, 5, 6, 7, 7,]],
             [[2, 4, 1, 2, 3, 8,]]]
        ])

    def copy(self, name: str = None, **kwargs: Unpack[PlanarSolidKwargs]) -> Self:
        return ScriptedStructure.copy(self, name, **kwargs)
