from typing import TypedDict, Unpack

from ....base_classes import Module
from ....resources import validation
from ....resources.functions import convert_length
from ....resources.literals import LENGTH_UNITS


class AxesBoolKwargs(TypedDict, total=False):
    x: bool
    y: bool
    z: bool


class FDTDAdvancedMeshSubsettings(Module):

    def force_symmetric_mesh(self, **kwargs: Unpack[AxesBoolKwargs]) -> None:
        """
        Force a symmetric mesh about the specified axes (x, y, or z) in the simulation.

        When this option is enabled, the meshing algorithm only considers objects in the
        positive half of the simulation region. The mesh in the negative half is generated
        as a direct copy of the positive half mesh. Consequently, any physical structures
        and mesh override regions in the negative half will not be considered by the
        meshing algorithm. Additionally, this option ensures a mesh point is placed at
        the center of the simulation region.

        This method is particularly useful for ensuring consistent mesh behavior when
        transitioning between simulations with and without symmetry.

        Raises:
            ValueError:
                - If the provided axis is not "x", "y", or "z".
                - If the argument value is not a boolean value

        Usage:
        - Call this method when you want to simplify the meshing process for simulations
          that exhibit symmetry, ensuring computational efficiency and consistency in the
          generated mesh structure.
        """

        for axis, truth in kwargs.items():
            validation.axis(axis)
            validation.boolean(truth, axis)
            self._set(f"force symmetric {axis} mesh", truth)

    def override_simulation_bandwidth_for_mesh_generation(self, override: bool, min_wavelength: float = None,
                                                          max_wavelength: float = None,
                                                          units: LENGTH_UNITS = None) -> None:
        """
        Override the simulation bandwidth for mesh generation with a custom wavelength
        or frequency range.

        By default, the simulation bandwidth is inherited from the source bandwidth.
        Enabling this option allows the user to define a specific wavelength or frequency
        range for generating the simulation mesh. This can be useful for fine-tuning the
        mesh generation process based on specific requirements that differ from the source
        parameters.

        Parameters:
        - override: A boolean value indicating whether to enable (True) or disable (False)
          the override of the simulation bandwidth for mesh generation.

        - min_wavelength: The minimum wavelength (in the specified units) for mesh generation.
          If provided, it will set the lower limit of the wavelength range.

        - max_wavelength: The maximum wavelength (in the specified units) for mesh generation.
          If provided, it will set the upper limit of the wavelength range.

        - units: The length units to be used for the min and max wavelengths. If not
          specified, the global units of the simulation will be used.

        Raises:
        - ValueError: If the provided min_wavelength or max_wavelength is negative or
          invalid.
        - ValueError: If the provided length units are invalid.

        Usage:
        - Call this method when you need to customize the wavelength range for the mesh
          generation, especially in cases where the source bandwidth does not align with
          the desired simulation parameters.

        """
        self._set("override simulation bandwidth for mesh generation", override)

        if units is None:
            units = self._units

        if override:
            if min_wavelength is not None:
                min_wavelength = convert_length(float(min_wavelength), units, "m")
                self._set("mesh wavelength min", min_wavelength)

            if max_wavelength is not None:
                max_wavelength = convert_length(float(max_wavelength), units, "m")
                self._set("mesh wavelength max", max_wavelength)

    def snap_pec_to_yee_cell_boundary(self, true_or_false: bool) -> None:
        """
        Snap PEC structures to Yee cell boundaries for proper alignment of interfaces.

        This option forces structures defined as Perfect Electric Conductors (PEC) to have
        their interfaces aligned with the boundaries of the Yee cells. This alignment ensures
        that all electric field components at the PEC interface are tangential, preventing
        complications that can arise if normal electric field components are inadvertently
        set to zero at the PEC interface.

        When this option is enabled, the PEC interface may be shifted by as much as
        dx/2 (where dx is the size of the Yee cell) during the simulation mesh creation.
        This adjustment helps maintain the accuracy and integrity of the simulation results.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable (True) or disable (False)
          the snapping of PEC structures to Yee cell boundaries.

        Usage:
        - Call this method when you want to ensure that PEC interfaces are correctly aligned
          with the Yee cell boundaries, particularly in simulations involving PEC materials.

        Raises:
        - ValueError: If the provided true_or_false value is not a boolean.

        """
        validation.boolean(true_or_false, "true_or_false")
        self._set("snap pec to yee cell boundary", true_or_false)
