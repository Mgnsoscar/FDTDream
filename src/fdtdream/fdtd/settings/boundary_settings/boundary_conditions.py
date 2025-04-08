from ....base_classes import ModuleCollection
from .pml import FDTDPMLSubsettings
from .bloch import FDTDBlochSubsettings
from .boundaries import FDTDBoundariesSubsettings


class FDTDBoundaryConditionsSettings(ModuleCollection):

    boundaries: FDTDBoundariesSubsettings
    bloch: FDTDBlochSubsettings
    pml: FDTDPMLSubsettings
    __slots__ = ["pml", "bloch", "boundaries"]

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)

        # Assign subsettings
        self.boundaries = FDTDBoundariesSubsettings(parent_object)
        self.bloch = FDTDBlochSubsettings(parent_object)
        self.pml = FDTDPMLSubsettings(parent_object)

