from typing import Unpack, Self

from .scripted_structure import ScriptedStructure
from ..sphere import Sphere, SphereKwargs
from ...interfaces import SimulationInterface


class ScriptedSphere(Sphere, ScriptedStructure):

    _radius: float
    _radius_2: float
    _radius_3: float
    _make_ellipsoid: bool

    __slots__ = ["_radius", "_radius_2", "_radius_3", "_make_ellipsoid"]

    def __init__(self, sim: SimulationInterface, name: str = "sphere", **kwargs: SphereKwargs):

        # Initialize variables first, then run the super() init.
        self._initialize_variables()
        super().__init__(name, sim, **kwargs)

    def _initialize_variables(self) -> None:
        super()._initialize_variables()
        self._radius = 100e-9
        self._radius_2 = 100e-9
        self._radius_3 = 100e-9
        self._make_ellipsoid = False

    def copy(self, name: str = None, **kwargs: Unpack[SphereKwargs]) -> Self:
        return ScriptedStructure.copy(self, name, **kwargs)
