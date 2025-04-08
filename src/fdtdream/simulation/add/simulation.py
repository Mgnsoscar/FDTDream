from __future__ import annotations

from typing import Callable, Unpack

from ...fdtd import FDTDRegion, FDTDRegionKwargs
from ...interfaces import SimulationInterface
from ...lumapi import Lumapi
from ...mesh import Mesh, MeshKwargs
from ...resources.errors import FDTDreamDuplicateFDTDRegionError
from ...resources.literals import LENGTH_UNITS


class Simulation:

    __slots__ = ["_sim", "_lumapi", "_units", "_check_name"]
    _check_name: Callable[[str], None]
    _sim: SimulationInterface
    _units: Callable[[], LENGTH_UNITS]
    _lumapi: Callable[[], Lumapi]

    def __init__(self, sim: SimulationInterface, lumapi: Lumapi, units: Callable[[], LENGTH_UNITS],
                 check_name: Callable[[str], None]):
        self._sim = sim
        self._lumapi = lumapi
        self._units = units
        self._check_name = check_name

    def mesh(self, name: str, **kwargs: Unpack[MeshKwargs]) -> Mesh:
        self._check_name(name)
        self._lumapi().addmesh()
        self._lumapi().set("name", name)
        mesh = Mesh(name, self._sim, **kwargs)
        self._sim._meshes.append(mesh)
        return mesh

    def fdtd_region(self, **kwargs: Unpack[FDTDRegionKwargs]) -> FDTDRegion:

        if self._sim._fdtd is not None:
            raise FDTDreamDuplicateFDTDRegionError("You cannot add another FDTDRegion to the simulation, as only one "
                                                   "is allowed.")
        self._lumapi().addfdtd()
        fdtd = FDTDRegion(self._sim, **kwargs)
        self._sim._fdtd = fdtd
        return fdtd
