from __future__ import annotations
from numpy.typing import NDArray
from typing import Optional, Dict
from abc import ABC


class Monitor(ABC):
    name: str
    monitor_type: str
    parameters: Dict[str, str]

    def __init__(self, name: str, parameters: dict, *args) -> None:
        self.name = name
        self.parameters = {k: str(v) for k, v in parameters.items()}


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

    def __init__(self, name: str, parameters: dict, wavelengths: NDArray, x: NDArray, y: NDArray, z: NDArray,
                 E: Optional[Field], H: Optional[Field], P: Optional[Field],
                 T: Optional[NDArray], power: Optional[NDArray]) -> None:
        super().__init__(name, parameters)

        self.monitor_type = "field_and_power"

        self.wavelengths = wavelengths
        self.x, self.y, self.z = x, y, z
        self.E, self.H, self.P = E, H, P
        self.T, self.power = T, power


class Field:

    field_name: str
    data: NDArray
    components: str

    def __init__(self, field_name: str, data: NDArray, components: str) -> None:
        self.field_name = field_name
        self.data = data
        self.components = components


