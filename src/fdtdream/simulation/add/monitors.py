from __future__ import annotations

# Std library imports
from typing import Callable, Unpack

# Local imports
from ...interfaces import SimulationInterface
from ...lumapi import Lumapi
from ...monitors import FreqDomainFieldAndPowerMonitor, FreqDomainFieldAndPowerKwargs, IndexMonitor, IndexMonitorKwargs
from ...resources.literals import LENGTH_UNITS


class Monitors:
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

    def power(self, name: str, **kwargs: Unpack[FreqDomainFieldAndPowerKwargs]) -> FreqDomainFieldAndPowerMonitor:
        self._check_name(name)
        self._lumapi().addpower()
        self._lumapi().set("name", name)
        power = FreqDomainFieldAndPowerMonitor(name, self._sim, **kwargs)
        self._sim._monitors.append(power)
        return power

    def profile(self, name: str, **kwargs: Unpack[FreqDomainFieldAndPowerKwargs]) -> FreqDomainFieldAndPowerMonitor:
        self._check_name(name)
        self._lumapi().addprofile()
        self._lumapi().set("name", name)
        profile = FreqDomainFieldAndPowerMonitor(name, self._sim, **kwargs)
        self._sim._monitors.append(profile)
        return profile

    def index(self, name: str, **kwargs: Unpack[IndexMonitorKwargs]) -> IndexMonitor:
        self._check_name(name)
        self._lumapi().addindex()
        self._lumapi().set("name", name)
        index_monitor = IndexMonitor(name, self._sim, **kwargs)
        self._sim._monitors.append(index_monitor)
        return index_monitor
