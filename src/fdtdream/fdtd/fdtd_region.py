from typing import TypedDict, Unpack, Any, Self

from .settings import (FDTDAdvancedSettings, FDTDMeshSettings, FDTDBoundaryConditionsSettings, FDTDGeneralSettings,
                       FDTDRegionGeometry)
from ..base_classes import SimulationObject, ModuleCollection
from ..resources import validation
from ..resources.errors import FDTDreamDuplicateFDTDRegionError
from ..resources.functions import convert_length
from ..resources.literals import BOUNDARY_TYPES_LOWER


class FDTDRegionKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float
    x_span: float
    y_span: float
    z_span: float
    x_min_bc: BOUNDARY_TYPES_LOWER
    x_max_bc: BOUNDARY_TYPES_LOWER
    y_min_bc: BOUNDARY_TYPES_LOWER
    y_max_bc: BOUNDARY_TYPES_LOWER
    z_min_bc: BOUNDARY_TYPES_LOWER
    z_max_bc: BOUNDARY_TYPES_LOWER



class FDTDRegionSettings(ModuleCollection):
    general: FDTDGeneralSettings
    geometry: FDTDRegionGeometry
    mesh: FDTDMeshSettings
    boundary_conditions: FDTDBoundaryConditionsSettings
    advanced: FDTDAdvancedSettings
    __slots__ = ["general", "geometry", "mesh", "boundary_conditions", "advanced"]

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)

        # Assign the submodules
        self.general = FDTDGeneralSettings(parent_object)
        self.geometry = FDTDRegionGeometry(parent_object)
        self.mesh = FDTDMeshSettings(parent_object)
        self.boundary_conditions = FDTDBoundaryConditionsSettings(parent_object)
        self.advanced = FDTDAdvancedSettings(parent_object)


class FDTDRegion(SimulationObject):

    settings: FDTDRegionSettings

    def __init__(self, sim, **kwargs: Unpack[FDTDRegionKwargs]) -> None:
        super().__init__(name="FDTD", simulation=sim, **kwargs)

        # Assign the settings module
        self.settings = FDTDRegionSettings(self)

        # Filter and apply kwargs.
        self._process_kwargs(**kwargs)

    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """Filters and applies the kwargs specific to the Sphere structure type."""

        # Abort if the kwargs are empty
        if not kwargs:
            return

        # Initialize dicts
        position = {}
        dimensions = {}
        boundary_types = {}

        # Filter kwargs
        for k, v in kwargs.items():
            if k in ["x", "y", "z"]:
                position[k] = v
            elif "bc" in k:
                boundary_types[k[:-3]] = v
            elif k in ["x_span", "y_span", "z_span"]:
                dimensions[k] = v

        # Apply kwargs
        if position:
            self.settings.geometry.set_position(**position)
        if dimensions:
            self.settings.geometry.set_dimensions(**dimensions)
        if boundary_types:
            self.settings.boundary_conditions.boundaries.set_boundary_types(**boundary_types)

    def copy(self, name, **kwargs: Unpack[Any]) -> Self:
        raise FDTDreamDuplicateFDTDRegionError("You cannot copy the FDTD region, as a simulation is only allowed "
                                               "one such object.")

    @property
    def x_span(self) -> float:
        """Returns the x-span of the FDTDRegion."""
        return convert_length(self._get("x span", float), "m", self._units)

    @x_span.setter
    def x_span(self, span: float) -> None:
        validation.number(span, "x_span")
        self._set("x span", convert_length(span, self._units, "m"))

    @property
    def y_span(self) -> float:
        """Returns the y-span of the FDTDRegion."""
        return convert_length(self._get("y span", float), "m", self._units)

    @y_span.setter
    def y_span(self, span: float) -> None:
        validation.number(span, "y_span")
        self._set("y span", convert_length(span, self._units, "m"))

    @property
    def z_span(self) -> float:
        """Returns the z-span of the FDTDRegion."""
        return convert_length(self._get("z span", float), "m", self._units)

    @z_span.setter
    def z_span(self, span: float) -> None:
        validation.number(span, "z_span")
        self._set("z span", convert_length(span, self._units, "m"))