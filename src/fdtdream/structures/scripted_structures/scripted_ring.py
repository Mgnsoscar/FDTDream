from typing import Unpack, Self

from .scripted_structure import ScriptedStructure
from ..ring import Ring, RingKwargs
from ...interfaces import SimulationInterface


class ScriptedRing(Ring, ScriptedStructure):

    _inner_radius: float
    _inner_radius_2: float
    _outer_radius: float
    _outer_radius_2: float
    _theta_start: float
    _theta_stop: float
    _z_span: float
    _make_ellipsoid: bool

    __slots__ = ["_inner_radius", "_outer_radius", "_inner_radius_2", "_outer_radius_2", "_theta_start", "_theta_stop",
                 "_z_span", "_make_ellipsoid"]

    def __init__(self, sim: SimulationInterface, name: str = "ring", **kwargs: RingKwargs):

        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _initialize_variables(self) -> None:
        super()._initialize_variables()
        self._inner_radius = 100e-9
        self._outer_radius = 200e-9
        self._inner_radius_2 = 100e-9
        self._outer_radius_2 = 100e-9
        self._theta_start = 0
        self._theta_stop = 360
        self._z_span = 100e-9
        self._make_ellipsoid = False

    def copy(self, name: str = None, **kwargs: Unpack[RingKwargs]) -> Self:
        return ScriptedStructure.copy(self, name, **kwargs)
