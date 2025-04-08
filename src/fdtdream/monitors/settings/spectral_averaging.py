from .literals import APODIZATIONS
from ...base_classes.object_modules import Module
from ...resources import validation
from ...resources.functions import convert_frequency, convert_time
from ...resources.literals import FREQUENCY_UNITS, TIME_UNITS


class SpectralAveraging(Module):

    def set_partial_spectral_averaging_delta(self, delta: float, frequency_unit: FREQUENCY_UNITS = None) -> None:
        """
        Set the FWHM of the Lorentzian weighting function for partial spectral averaging.

        Args:
            delta (float): The FWHM value to set, in the specified frequency unit.
            frequency_unit (FREQUENCY_UNITS, optional): The unit of frequency for the delta value.
                If not provided, it defaults to 'THz'.

        Raises:
            ValueError: If the frequency unit is not recognized.
        """

        if frequency_unit is None:
            frequency_unit = "THz"  # Default unit if not provided
        else:
            validation.in_literal(frequency_unit, "frequency_unit", FREQUENCY_UNITS)

        frequency_unit: FREQUENCY_UNITS  # To not throw off the type-checker

        # Convert delta to Hz using the provided (or default) frequency unit
        delta_hz = convert_frequency(delta, from_unit=frequency_unit, to_unit="Hz")

        # Set the parameter for delta
        self._set("delta", delta_hz)

    def set_apodization(self, apodization: APODIZATIONS) -> None:
        """
        Set the window function for apodization.

        Args:
            apodization (APODIZATIONS): The apodization option to set.
                Options include:
                - 'none': No apodization applied.
                - 'start': Apodization applied at the beginning of the time signature.
                - 'end': Apodization applied at the end of the time signature.
                - 'full': Apodization applied at both the start and end.

        Raises:
            ValueError: If the provided apodization option is not recognized.
        """

        # Validate the provided apodization option
        validation.in_literal(apodization, "apodization", APODIZATIONS)

        # Set the parameter for apodization
        self._set("apodization", apodization)

    def set_apodization_center(self, center: float, time_unit: TIME_UNITS = "fs") -> None:
        """
        Set the center of the apodization window.

        Args:
            center (float): The center time of the apodization window.
            time_unit (TIME_UNITS, optional): The time unit for the center. Defaults to 'fs'.

        Raises:
            ValueError: If apodization is set to 'None'.
        """

        if self._get("apodization", str) == "None":
            raise ValueError(
                "You can only set apodization center if apodization is set to 'Full', 'Start', or 'End', not 'None'."
            )

        # Validate the provided time unit
        validation.in_literal(time_unit, "time_unit", TIME_UNITS)

        # Convert the center time to seconds
        center = convert_time(value=center, from_unit=time_unit, to_unit="s")

        # Set the parameter for apodization center
        self._set("apodization center", center)

    def set_apodization_time_width(self, time_width: float, time_unit: TIME_UNITS = "fs") -> None:
        """
        Set the time width of the apodization window.

        Args:
            time_width (float): The time width of the apodization window.
            time_unit (TIME_UNITS, optional): The time unit for the time width. Defaults to 'fs'.

        Raises:
            ValueError: If apodization is set to 'None'.
        """

        if self._get("apodization", str) == "None":
            raise ValueError(
                "You can only set apodization time width if apodization is set to 'Full', "
                "'Start', or 'End', not 'None'."
            )

        # Validate the provided time unit
        validation.in_literal(time_unit, "time_unit", TIME_UNITS)

        # Convert the time width to seconds
        time_width = convert_time(value=time_width, from_unit=time_unit, to_unit="s")

        # Set the parameter for apodization time width
        self._set("apodization time width", time_width)
