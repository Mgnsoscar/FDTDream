
from typing import TypedDict, Unpack

from .literals import PULSE_TYPES
from ...base_classes.object_modules import Module
from ...resources import validation
from ...resources.functions import convert_length, convert_frequency, convert_time
from ...resources.literals import LENGTH_UNITS, FREQUENCY_UNITS, TIME_UNITS


# region Kwargs
class SetWavelengthRange(TypedDict, total=False):
    wavelength_start: float
    wavelength_stop: float
    units: LENGTH_UNITS


class SetFrequencyRange(TypedDict, total=False):
    frequency_start: float
    frequency_stop: float
    units: FREQUENCY_UNITS

# endregion Kwargs


class FrequencyWavelengthGlobal(Module):

    def _override(self) -> None:
        ...

    def set_wavelength_range(self, start: float = None, stop: float = None, units: LENGTH_UNITS = None) -> None:
        """
        Sets the start and stop wavelengths for the source, with optional unit conversion.

        This method defines the wavelength range of the source by specifying the starting and
        ending wavelengths. If `units` are not provided, the simulation's global units
        are used as the default.

        Args:
            start (float): The starting wavelength value.
            stop (float): The stopping wavelength value.
            units (LENGTH_UNITS, optional): The units of the wavelength values
                (e.g., 'nm', 'um'). If not provided, the simulation's global length units are used.
        """

        self._override()
        self._set("set wavelength", True)

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        if start > stop:
            raise ValueError("The wavelength start parameter cannot be greater than the wavelength stop parameter.")

        if start:
            self._set("wavelength start", convert_length(start, units, "m"))
        if stop:
            self._set("wavelength stop", convert_length(stop, units, "m"))

    def set_frequency_range(self, start: float = None, stop: float = None, units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets the start and stop frequencies for the source, with optional unit conversion.

        This method defines the frequency range of the source by specifying the starting and
        ending frequencies. If `units` are not provided, the default units are THz.

        Args:
            start (float): The starting frequency value.
            stop (float): The stopping frequency value.
            units (FREQUENCY_UNITS, optional): The units of the frequency values
                (default is "THz").
        """
        self._override()
        self._set("set frequency", True)

        if units != "THz":
            units = self._units
        else:
            validation.in_literal(units, "units", FREQUENCY_UNITS)

        if start > stop:
            raise ValueError("The frequency start parameter cannot be greater than the wavelength stop parameter.")

        if start:
            self._set("frequency start", convert_length(start, units, "m"))
        if stop:
            self._set("frequency stop", convert_length(stop, units, "m"))

    def set_time_domain(self) -> None:
        """
        Enables the time domain setting for the source.
        """
        self._override()
        self._set("set time domain", True)

    def set_pulse_type(self, pulse_type: PULSE_TYPES) -> None:
        """
        Sets the pulse type for the source, specifying either a standard or broadband pulse.

        The `pulse_type` parameter configures the source as follows:
        - **Standard**: An optical carrier with a fixed frequency and a Gaussian envelope, ideal for
          narrowband applications.
        - **Broadband**: A chirped optical carrier with a Gaussian envelope, covering a wider spectrum
          suitable for broadband applications.

        Args:
            pulse_type (PULSE_TYPES): The type of pulse to set, either 'standard' or 'broadband'.

        Raises:
            ValueError: If 'eliminate dc' is enabled and the pulse type is not 'standard'.
        """
        self._override()
        eliminate_dc = self._get("eliminate dc", bool)
        if eliminate_dc and pulse_type != "standard":
            raise ValueError(f"When 'eliminate dc' is enabled, pulse type can only be 'standard', not '{pulse_type}'.")

        self._set("pulse type", pulse_type)

    def set_frequency(self, frequency: float, units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets the center frequency of the optical carrier for the source, with unit conversion.

        This method allows you to define the frequency at which the optical source operates.
        The frequency can be specified in various units, with the default set to Terahertz (THz).
        The provided frequency will be converted to Hertz (Hz) for internal consistency.

        Args:
            frequency (float): The frequency to set for the optical carrier.
            units (FREQUENCY_UNITS): The units of the frequency (default is "THz").

        Notes:
            This function expects a valid frequency value and will convert it to Hertz for internal processing.
        """
        self._override()
        frequency = convert_frequency(frequency, units, "Hz")
        self._set("frequency", frequency)

    def set_pulselength(self, pulselength: float, units: TIME_UNITS = "fs") -> None:
        """
        Sets the full-width at half-maximum (FWHM) power temporal duration of the pulse for the source,
        with unit conversion.

        This method allows you to define the pulselength of the optical source, which is
        represented as the full-width at half-maximum (FWHM) duration of the pulse. The
        pulselength can be specified in various units, with the default set to femtoseconds (fs).
        The provided pulselength will be converted to seconds (s) for internal consistency.

        Args:
            pulselength (float): The pulselength to set, specified as the FWHM duration of the pulse.
            units (TIME_UNITS): The units of the pulselength (default is "fs").
        """
        self._override()
        pulselength = convert_time(pulselength, units, "s")
        self._set("pulselength", pulselength)

    def set_offset(self, offset: float, units: TIME_UNITS = "fs") -> None:
        """
        Sets the time at which the source reaches its peak amplitude, measured relative to the start of the simulation,
        with unit conversion.

        An offset of N seconds corresponds to a source that reaches its peak amplitude N seconds after
        the start of the simulation. This method allows you to define the offset for the optical source.
        The provided offset will be converted to seconds (s) for internal consistency.

        Args:
            offset (float): The offset time to set, indicating when the source reaches its peak amplitude.
            units (TIME_UNITS): The units of the offset (default is "fs").

        Notes:
            This function expects a valid offset value and will convert it to seconds for internal processing.
        """
        self._override()
        offset = convert_time(offset, units, "s")
        self._set("offset", offset)

    def set_bandwidth(self, bandwidth: float, units: FREQUENCY_UNITS = "THz") -> None:
        """
        Sets the bandwidth for the source if the pulse type is 'broadband'.

        The bandwidth represents the full-width at half-maximum (FWHM) frequency width of the time-domain
        pulse. This method allows you to specify the bandwidth, ensuring it is only applicable for sources
        configured with a 'broadband' pulse type. The provided bandwidth will be converted to Hertz (Hz)
        for internal consistency.

        Args:
            bandwidth (float): The bandwidth to set, indicating the frequency width of the pulse.
            units (FREQUENCY_UNITS): The units of the bandwidth (default is "THz").

        Raises:
            ValueError: If 'pulse type' is not set to 'broadband'.

        Notes:
            This function expects a valid bandwidth value and will convert it to Hertz for internal processing.
        """

        self._override()
        pulse_type = self._get("pulse type", str)
        if pulse_type != "broadband":
            raise ValueError(f"You can only set bandwidth when 'pulse type' is set to 'broadband', not '{pulse_type}'.")

        bandwidth = convert_frequency(bandwidth, from_unit=units, to_unit="Hz")
        self._set("bandwidth", bandwidth)

    def set_eliminate_discontinuities(self, true_or_false: bool) -> None:
        """
        Enables or disables the elimination of discontinuities in the source.

        This setting ensures the function has a continuous derivative (smooth transitions from/to zero)
        at the start and end of a user-defined source time signal, reducing artifacts by eliminating
        abrupt changes in the source profile. It is enabled by default. Requires global source settings
        to be overridden.

        Args:
            true_or_false (bool): Set to `True` to enable the elimination of discontinuities,
                                  or `False` to disable it.

        Raises:
            ValueError: If 'eliminate dc' is enabled while setting 'eliminate discontinuities'.
        """
        self._override()
        eliminate_dc = self._get("eliminate dc", bool)
        if eliminate_dc:
            raise ValueError("Cannot enable 'eliminate discontinuities' while 'eliminate dc' is enabled.")

        self._set("eliminate discontinuities", true_or_false)

    def set_optimize_for_short_pulse(self, true_or_false: bool) -> None:
        """
        Enables or disables optimization for short pulse sources.

        When enabled, this setting optimizes the source for better performance with short pulses.
        This option is enabled by default in the FDTD solver and should only be disabled when
        it is necessary to minimize the power injected by the source outside of the source range
        (e.g., convergence problems related to broadband steep angled injection).
        In the varFDTD solver, this option is disabled by default as it improves the algorithm's
        numerical stability. Requires global source settings to be overridden to be changed.

        Args:
            true_or_false (bool): Set to `True` to enable optimization for short pulses, or `False` to disable it.

        Raises:
            ValueError: If 'eliminate dc' is enabled while setting 'optimize for short pulse'.
        """
        self._override()
        eliminate_dc = self._get("eliminate dc", bool)
        if eliminate_dc:
            raise ValueError("Cannot enable 'optimize for short pulse' while 'eliminate dc' is enabled.")

        self._set("optimize for short pulse", true_or_false)

    def set_eliminate_dc(self, true_or_false: bool) -> None:
        """
        Enables or disables the elimination of DC (direct current) components in the source.

        The 'eliminate dc' option can be used to eliminate the DC component of the source signal
        by forcing a symmetry on it. This setting can be useful in applications where only AC
        (alternating current) components are relevant. Requires global source settings to be overridden.

        Args:
            true_or_false (bool): Set to `True` to enable DC elimination, or `False` to disable it.

        Raises:
            RuntimeError: If global source settings are not overridden.
        """
        self._override()
        self._set("eliminate dc", true_or_false)


class FrequencyWavelength(FrequencyWavelengthGlobal):

    def _override(self) -> None:
        if not self._get("override global source settings", bool):
            self._set("override global source settings", True)

    def override_global_source_settings(self, override_bool: bool) -> None:
        """
        Overrides the global source settings for this source.

        This method allows specific source settings to be configured independently of the
        global simulation settings. If not set to `True`, an attempt to configure
        source-specific parameters (such as frequency or wavelength ranges) will raise an error.

        Args:
            override_bool (bool): Set to `True` to override global source settings, enabling
                                  custom configuration of this source's parameters. Set to `False`
                                  to revert to using global settings.

        """

        self._set("override global source settings", override_bool)
