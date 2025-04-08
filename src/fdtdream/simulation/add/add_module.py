from .monitors import Monitors
from .sources import Sources
from .structures import Structures
from .simulation import Simulation
from ...base_classes.object_modules import ModuleCollection


class Add(ModuleCollection):
    __slots__ = ["structures", "sources", "monitors", "simulation"]
    structures: Structures
    sources: Sources
    monitors: Monitors
    simulation: Simulation

    def __init__(self, sim, lumapi, units, check_name) -> None:
        self.structures = Structures(sim, lumapi, units, check_name)
        self.sources = Sources(sim, lumapi, units, check_name)
        self.monitors = Monitors(sim, lumapi, units, check_name)
        self.simulation = Simulation(sim, lumapi, units, check_name)
