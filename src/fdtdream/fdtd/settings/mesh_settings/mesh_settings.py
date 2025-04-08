from typing import Union

from .mesh_refinement import FDTDMeshRefinementSubsettings
from .mesh_type import FDTDMeshTypeSubsettings
from ....base_classes import ModuleCollection
from ....resources import validation
from ....resources.functions import convert_length
from ....resources.literals import LENGTH_UNITS


class FDTDMeshSettings(ModuleCollection):

    mesh_type: FDTDMeshTypeSubsettings
    mesh_refinement: FDTDMeshRefinementSubsettings

    __slots__ = ["mesh_type", "mesh_refinement"]

    def __init__(self, parent_object) -> None:
        super().__init__(parent_object)

        # Assign the submodules
        self.mesh_type = FDTDMeshTypeSubsettings(parent_object)
        self.mesh_refinement = FDTDMeshRefinementSubsettings(parent_object)

    def set_dt_stability_factor(self, factor: float) -> None:
        """
        Set the time step stability factor for the simulation.

        The DT Stability Factor determines the size of the time step used during the
        simulation, defined as a fraction of the Courant numerical stability limit. A
        larger factor will lead to faster simulation times, while a smaller factor will
        result in slower simulation times.

        Note: The Courant stability condition requires that this factor be less than 1
        for the FDTD algorithm to remain numerically stable.

        Args:
            factor (float): The stability factor for the time step, where a value
                            less than 1 ensures numerical stability in the simulation.

        Raises:
            ValueError: If the factor is not a positive number.
        """

        validation.positive_number(factor, "factor")
        self._set("dt stability factor", factor)

    def set_min_mesh_step(self, min_step: Union[int, float], units: LENGTH_UNITS = None) -> None:
        """
        Set the absolute minimum mesh size for the entire solver region.

        The MIN mesh STEP defines the smallest allowable mesh size for the simulation.
        This value overrides all other mesh size settings, including those specified
        in mesh override regions. It ensures that the solver maintains a consistent
        mesh size across the entire simulation domain, which is crucial for
        maintaining numerical stability and accuracy.

        Args:
            min_step (Union[int, float]): The minimum mesh size to be set. This can be
                                           provided as either an integer or a float.
            units (LENGTH_UNITS, optional): The units in which the min_step is specified.
                                             If not provided, the global units of the
                                             simulation will be used.

        Raises:
            ValueError: If the min_step is a non-positive value, as mesh size must be
                        greater than zero.
        """
        if min_step <= 0:
            raise ValueError("The minimum mesh step must be a positive value.")

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        min_step = convert_length(min_step, units, "m")
        self._set("min mesh step", min_step)
