from typing import TypedDict, Unpack

from ....base_classes import Module
from ....resources import validation
from ....resources.literals import BLOCH_UNITS


class KKwargs(TypedDict, total=False):
    kx: float
    ky: float
    kz: float


class FDTDBlochSubsettings(Module):

    def based_on_source_angle(self, true_or_false: bool) -> None:
        """
        Sets whether the wave vector components (kx, ky, kz) for Bloch boundary conditions
        should be determined based on the source angle in the current simulation.

        When this option is enabled, the values of kx, ky, and kz are automatically
        calculated based on the angle of the defined source. This is particularly useful
        when injecting plane waves at specific angles into periodic structures. If
        multiple sources are defined, all must require consistent Bloch settings for
        this feature to work correctly.

        By default, this option is enabled. If disabled, the user must manually set
        kx, ky, and kz.

        Parameters:
            true_or_false (bool):
                True to enable automatic determination of kx, ky, and kz based on
                the source angle; False to disable this feature and set kx, ky,
                and kz manually.

        Raises:
            ValueError: If the input is not a boolean value.

        """
        validation.boolean(true_or_false, "true_or_false")
        self._set("set based on source angle", true_or_false)

    def set_bloch_units(self, bloch_units: BLOCH_UNITS) -> None:
        """
        Sets the units used for specifying the values of kx, ky, and kz in Bloch boundary conditions.

        Two types of units are allowed:

        - **Bandstructure Units**: In these units, kx, ky, and kz are defined in terms of
          (2pi/a_x, 2pi/a_y, 2pi/a_z), where (a_x, a_y, a_z) are the x, y, and z spans of the FDTD simulation region.
          These units are particularly convenient for bandstructure calculations.

        - **SI Units**: In SI units, kx, ky, and kz are defined in units of 1/m.
          This is generally more convenient for the injection of plane waves at specific angles.

        Parameters:
            bloch_units (BLOCH_UNITS):
                The units to be used for kx, ky, and kz, which should be one of the
                predefined values in the BLOCH_UNITS enumeration.

        Raises:
            ValueError: If the provided units are not valid.

        """
        validation.in_literal(bloch_units, "bloch_units", BLOCH_UNITS)
        self._set("bloch units", bloch_units)

    def set_k(self, **kwargs: Unpack[KKwargs]) -> None:
        """
        Sets the values of the wavevector components for the Bloch symmetry conditions. If the boundaries
        corresponding to the wavevector compontent is not a Bloch boundary, a ValueError will be raised.

        """
        valid_arguments = KKwargs.__annotations__.keys()
        for k, value in kwargs.items():
            if k not in valid_arguments:
                raise ValueError(f"'{k}' is not a valid k-vector component. Choose from {valid_arguments}.")
            elif self._get(f"{k[1]} min bc", str) != "Bloch":
                raise ValueError(f"You cannot set '{k}' when the min and max {k[1]} boundaries "
                                 f"are not Bloch boundaries.")
            validation.number(value, k)
            self._set(k, value)
