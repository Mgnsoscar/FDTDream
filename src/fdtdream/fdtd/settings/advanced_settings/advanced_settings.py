from .advanced_mesh import FDTDAdvancedMeshSubsettings
from .auto_shutoff import FDTDAutoShutoffSubsettings
from .bfast import FDTDBFASTSubsettings
from .checkpoint import FDTDCheckpointSubsettings
from .misc import FDTDMiscellaneousSubsettings
from .paralell_engine import FDTDParalellEngineSubsettings
from .simulation_bandwidth import FDTDSimulationBandwidthSubsettings
from ....base_classes import ModuleCollection


class FDTDAdvancedSettings(ModuleCollection):

    simulation_bandwidth: FDTDSimulationBandwidthSubsettings
    mesh: FDTDAdvancedMeshSubsettings
    auto_shutoff: FDTDAutoShutoffSubsettings
    paralell_engine: FDTDParalellEngineSubsettings
    checkpoint: FDTDCheckpointSubsettings
    bfast: FDTDBFASTSubsettings
    misc: FDTDMiscellaneousSubsettings
    __slots__ = ["simulation_bandwidth", "mesh", "auto_shutoff",
                 "paralell_engine", "checkpoint", "bfast", "misc"]

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)

        # Assign submodules
        self.simulation_bandwidth = FDTDSimulationBandwidthSubsettings(parent_object)
        self.mesh = FDTDAdvancedMeshSubsettings(parent_object)
        self.auto_shutoff = FDTDAutoShutoffSubsettings(parent_object)
        self.paralell_engine = FDTDParalellEngineSubsettings(parent_object)
        self.checkpoint = FDTDCheckpointSubsettings(parent_object)
        self.bfast = FDTDBFASTSubsettings(parent_object)
        self.misc = FDTDMiscellaneousSubsettings(parent_object)

    def set_express_mode(self, true_or_false: bool) -> None:
        """Enables the express mode, which has something to do with running FDTD on GPU."""
        self._set("express mode", true_or_false)


