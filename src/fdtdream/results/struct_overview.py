from __future__ import annotations

from typing import List, Union, Optional

from trimesh import Trimesh
from numpy.typing import NDArray
import numpy as np


class Simulation:
    category: str
    name: str
    monitors: List[Monitor]
    structures: List[Structure]


class Structure:
    simulation: Simulation
    name: str
    trimesh: Trimesh


# region Monitors

class Monitor:
    simulation: Simulation
    name: str
    monitor_type: str
    geometry_type: str
    position: tuple
    spans: tuple

    def __init__(self, simulation: Simulation, name: str, geometry_type: str, position: tuple, spans: tuple, *args) -> None:
        self.simulation = simulation
        self.name = name
        self.geometry_type = geometry_type
        self.position = position
        self.spans = spans


class FieldAndPowerMonitor(Monitor):
    wavelengths: NDArray
    x: NDArray
    y: NDArray
    z: NDArray
    E: Optional[Field]
    H: Optional[Field]
    P: Optional[Field]
    T: Optional[NDArray]
    power: Optional[NDArray]

    def __init__(self, simulation: Simulation, name: str, geometry_type: str, position: tuple, spans: tuple,
                 wavelengths: NDArray, x: NDArray, y: NDArray, z: NDArray,
                 E: Optional[Field], H: Optional[Field], P: Optional[Field],
                 T: Optional[NDArray], power: Optional[NDArray]) -> None:
        super().__init__(simulation, name, geometry_type, position, spans)

        self.monitor_type = "Field and Power"

        self.wavelengths = wavelengths
        self.x, self.y, self.z = x, y, z
        self.E, self.H, self.P = E, H, P
        self.T, self.power = T, power


class Field:

    monitor: FieldAndPowerMonitor
    field_name: str
    data: NDArray
    components: str

    def __init__(self, monitor: FieldAndPowerMonitor, field_name: str, data: NDArray, components: str) -> None:
        self.monitor = monitor
        self.field_name = field_name
        self.data = data
        self.components = components

# endregion


