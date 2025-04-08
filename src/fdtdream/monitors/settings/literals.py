from typing import Literal

SIMULATION_TYPE = Literal["all", "3D", "2D z-normal"]
SPATIAL_INTERPOLATIONS = Literal["specified position", "nearest mesh cell", "none"]
APODIZATIONS = Literal["None", "Full", "Start", "End"]