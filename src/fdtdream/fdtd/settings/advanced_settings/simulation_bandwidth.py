from ....base_classes import Module
from ....resources.functions import convert_length
from ....resources.literals import LENGTH_UNITS


class FDTDSimulationBandwidthSubsettings(Module):

    def set_simulation_bandwidth(self, true_or_false: bool, min_wavelength: float = None,
                                 max_wavelength: float = None, units: LENGTH_UNITS = None) -> None:
        """
        Set the simulation bandwidth directly, allowing for greater control over the
        simulation parameters.

        By default, the simulation bandwidth is inherited from the source bandwidth.
        Enabling this option allows the user to specify the minimum and maximum
        wavelengths for the simulation, affecting various aspects such as mesh generation,
        material fits, and monitor frequency ranges.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable (True) or disable (False)
          direct setting of the simulation bandwidth.

        - min_wavelength: The minimum wavelength for the simulation bandwidth. If provided,
          it will override the inherited value. The value must be convertible to meters.
          Default is None.

        - max_wavelength: The maximum wavelength for the simulation bandwidth. If provided,
          it will override the inherited value. The value must be convertible to meters.
          Default is None.

        - units: The units for the wavelengths (e.g., nm, um). If None, the global units
          from the simulation will be used.

        Raises:
        - ValueError: If min_wavelength or max_wavelength are provided but are invalid
          (e.g., negative values, incompatible types).

        Usage:
        - This method should be used when fine control over the simulation bandwidth is necessary,
          particularly in scenarios where the characteristics of the simulation depend heavily
          on the specified wavelength range.

        """
        self._set("set simulation bandwidth", true_or_false)

        if units is None:
            units = self._units

        if true_or_false:
            if min_wavelength is not None:
                min_wavelength = convert_length(float(min_wavelength), units, "m")
                self._set("simulation wavelength min", min_wavelength)
            if max_wavelength is not None:
                max_wavelength = convert_length(float(max_wavelength), units, "m")
                self._set("simulation wavelength max", max_wavelength)
