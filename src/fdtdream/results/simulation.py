from typing import List, Dict
from .monitors import Monitor
from trimesh import Trimesh


class Structure:
    name: str
    trimesh: Trimesh

    def __init__(self, name: str, trimesh: Trimesh) -> None:
        self.name = name
        self.trimesh = trimesh


class Simulation:
    category: str
    name: str
    parameters: Dict[str, str]
    monitors: List[Monitor]
    structures: List[Structure]

    def __init__(self, category: str, name: str, parameters: dict, monitors: List[Monitor],
                 structures: List[Structure]) -> None:
        self.category = category
        self.name = name
        self.parameters = parameters
        self.monitors = monitors
        self.structures = structures


