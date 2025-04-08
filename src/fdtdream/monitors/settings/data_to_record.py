# Std lib
from typing import TypedDict, Unpack

from ...base_classes.object_modules import Module
from ...resources import validation


# region Kwargs
class SetDataToRecord(TypedDict, total=False):
    disable_all_first: bool
    enable_all_first: bool
    ex: bool
    ey: bool
    ez: bool
    hx: bool
    hy: bool
    hz: bool
    px: bool
    py: bool
    pz: bool
    power: bool


# endregion Kwargs


class DataToRecord(Module):

    def set_data_to_record(self, **kwargs: Unpack[SetDataToRecord]) -> None:
        """
        Set the what data should be recorded by the monitor.

        If enable_all_first or disable_all_first is true, all components will either be enabled
        or disabled before any arguments you pass will be applied.

        This method allows the user to specify which components of the electric and magnetic fields,
        as well as which poynting vectors will be measured during the simulation. Only the components passed
        will be updated.

        The 'output_power' parameter enables/disables the calculation of integrated power
        over the monitor surface (for 3D simulations) or along a monitor line
        (for 2D simulations). It requires much less memory after the simulation
        is completed, making it suitable for large parallel simulations where
        only the integrated power across a surface is needed.

        Args:
            Electric fields:
                ex (bool, optional):
                    True to include the Ex component in the output; False to exclude it.
                ey (bool, optional):
                    True to include the Ey component in the output; False to exclude it.
                ez (bool, optional):
                    True to include the Ez component in the output; False to exclude it.
            Magnetic fields:
                hx (bool, optional):
                    True to include the Hx component in the output; False to exclude it.
                hy (bool, optional):
                    True to include the Hy component in the output; False to exclude it.
                hz (bool, optional):
                    True to include the Hz component in the output; False to exclude it.
            Poynting vectors:
                px (bool, optional):
                    True to include the Px component in the output; False to exclude it.
                py (bool, optional):
                    True to include the Py component in the output; False to exclude it.
                pz (bool, optional):
                    True to include the Pz component in the output; False to exclude it.
            Output power:
                output_power (bool):
                    True to enable output power calculation; False to disable it.


        Raises:
            ValueError: If any provided parameters are not boolean, or if invalid argument is passed.
        """

        disable_first = kwargs.pop("disable_all_first", None)
        enable_first = kwargs.pop("enable_all_first", None)

        if enable_first and disable_first:
            raise ValueError("You must either choose to disable all first or enable all first, not both, as this is "
                             "ambigous.")
        elif disable_first:
            initial = {param: False for param in SetDataToRecord.__annotations__.keys()
                       if param not in ["disable_all_first", "enable_all_first"]}
            initial.update(kwargs)
            kwargs = initial
        else:
            initial = {param: True for param in SetDataToRecord.__annotations__.keys()
                       if param not in ["disable_all_first", "enable_all_first"]}
            initial.update(kwargs)
            kwargs = initial

        valid_parameters = list(SetDataToRecord.__annotations__.keys())
        for parameter, enabled in kwargs.items():
            validation.in_list(parameter, valid_parameters)
            validation.boolean(enabled, parameter)
            self._set("output " + parameter, enabled)

    def standard_fourier_transform(self, true_or_false: bool) -> None:
        """
        Enables or disables the standard Fourier transform output for the monitor.

        When enabled, the monitor will output data at specific frequencies, allowing for
        frequency-domain analysis of the simulation results. This setting is useful for
        applications that require frequency-specific data interpretation.

        Args:
            true_or_false (bool):
                - True to enable the standard Fourier transform output.
                - False to disable the standard Fourier transform output.

        Raises:
            ValueError: If the provided value is not a boolean.
        """

        # Validate that the input is a boolean
        if not isinstance(true_or_false, bool):
            raise ValueError("The 'true_or_false' argument must be a boolean.")

        # Set the parameter for standard Fourier transform
        self._set("standard fourier transform", true_or_false)

    def partial_spectral_average(self, true_or_false: bool) -> None:
        """
        Enables or disables the output of the partial spectral average power through
        the monitor surface, normalized to the partial spectral average of the source.

        When enabled, this option allows for the monitoring of the average power
        across specific spectral components, providing insights into how different
        wavelengths contribute to the overall power output. This is particularly useful
        for applications focused on selective wavelength analysis.

        Args:
            true_or_false (bool):
                - True to enable the partial spectral average output.
                - False to disable the partial spectral average output.

        Raises:
            ValueError: If the provided value is not a boolean.
        """

        # Validate that the input is a boolean
        if not isinstance(true_or_false, bool):
            raise ValueError("The 'true_or_false' argument must be a boolean.")

        # Set the parameter for partial spectral average
        self._set("partial spectral average", true_or_false)

    def total_spectral_average(self, true_or_false: bool) -> None:
        """
        Enables or disables the output of the total spectral average power through
        the monitor surface, normalized to the total spectral average of the source.

        When enabled, this option allows for the monitoring of the overall average power
        across all wavelengths, providing a comprehensive understanding of the power
        distribution in the simulation. This is particularly useful for applications
        where the total energy output is of interest.

        Args:
            true_or_false (bool):
                - True to enable the total spectral average output.
                - False to disable the total spectral average output.

        Raises:
            ValueError: If the provided value is not a boolean.
        """

        # Validate that the input is a boolean
        if not isinstance(true_or_false, bool):
            raise ValueError("The 'true_or_false' argument must be a boolean.")

        # Set the parameter for total spectral average
        self._set("total spectral average", true_or_false)
