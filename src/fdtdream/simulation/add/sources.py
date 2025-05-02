from __future__ import annotations

# Std library imports
from typing import Callable, Unpack

# Local imports
from ...interfaces import SimulationInterface
from ...resources.literals import LENGTH_UNITS
from ...lumapi import Lumapi
from ...sources import (PlaneWave, PlaneWaveKwargs, GaussianBeam, GaussianBeamKwargs, CauchyLorentzianBeam,
                        CauchyLorentzianBeamKwargs)


class Sources:
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

    def plane_wave(self, name: str, **kwargs: Unpack[PlaneWaveKwargs]) -> PlaneWave:
        self._check_name(name)
        self._lumapi().addplane({"name": name})
        plane_wave = PlaneWave(name, self._sim, **kwargs)
        self._sim._sources.append(plane_wave)
        return plane_wave

    def gaussian(self, name: str, **kwargs: Unpack[GaussianBeamKwargs]) -> GaussianBeam:
        self._check_name(name)
        self._lumapi().addgaussian({"name": name})
        gaussian = GaussianBeam(name, self._sim, **kwargs)
        self._sim._sources.append(gaussian)
        return gaussian

    def cauchy_lorentzian(self, name: str, **kwargs: Unpack[CauchyLorentzianBeamKwargs]) -> CauchyLorentzianBeam:
        self._check_name(name)
        self._lumapi().addgaussian({"name": name})
        cl_beam = CauchyLorentzianBeam(name, self._sim, **kwargs)
        self._sim._sources.append(cl_beam)
        return cl_beam
