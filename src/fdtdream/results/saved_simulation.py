from dataclasses import dataclass
from typing import List, Tuple
from trimesh import Trimesh
from .field_and_power_monitor import FieldAndPower
from .plotted_structure import PlottedStructure


@dataclass
class SavedSimulation:
    parameters: dict
    category: str
    structures: List[PlottedStructure]
    monitor_results: List[FieldAndPower]
