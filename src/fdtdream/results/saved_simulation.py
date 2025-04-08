from dataclasses import dataclass
from typing import List, Tuple
from trimesh import Trimesh
from .field_and_power_monitor import FieldAndPower


@dataclass
class SavedSimulation:
    parameters: dict
    category: str
    structures: List[Tuple[str, Trimesh]]
    monitor_results: List[FieldAndPower]
