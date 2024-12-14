from __future__ import annotations

# Standard library imports
from typing import Any, Union, get_args, Unpack, cast, TypedDict
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Third-party library imports
import numpy as np

# Local library imports
from base_classes import SettingTab, SimulationObject, TSimulation, Settings, GlobalSettingTab
from Code.Resources.literals import (LENGTH_UNITS, PARAMETER_TYPES, FREQUENCY_UNITS, TIME_UNITS, AXES, SAMPLE_SPACINGS,
                                     SIMULATION_TYPE, SPATIAL_INTERPOLATIONS, APODIZATIONS)
from Code.Resources.local_resources import (convert_length, convert_frequency, convert_time, Validate, get_parameter,
                                            set_parameter)
from geometry import (MonitorGeometryAll, MonitorGeometry3D, MinMaxDirectProperties, TrippleSpansProperties,
                      TrippleSpansKwargs)


########################################################################################################################
#                                  SETTING CLASSES FOR THE MAIN SETTINGS CATEGORIES
########################################################################################################################
class MonitorGeneralSettingsBase(ABC):
    _parent: MonitorBase
    _simulation: TSimulation

    def _get_parameter(self, *args) -> None:
        return None

    def _set_parameter(self, *args) -> None:
        return None

    @dataclass
    class _Settings(Settings):
        sample_spacing: SAMPLE_SPACINGS
        use_wavelength_spacing: bool
        minimum_wavelength: float
        maximum_wavelength: float
        frequency_points: int
        custom_frequency_samples: np.ndarray

    def set_uniform_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to uniform.

        This method should only be called if the override global monitor settings are enabled.
        """

        self._set_parameter("sample spacing", "uniform", "str")

    def set_chebyshev_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to Chebyshev.

        This method should only be called if the override global monitor settings are enabled.
        """

        self._set_parameter("sample spacing", "chebyshev", "str")

    def set_custom_sample_spacing(self, frequencies: Union[np.ndarray, list]) -> None:
        """
        Sets the sample spacing for the monitor to custom.

        This method should only be called if the override global monitor settings are enabled.
        It also sets the custom frequency samples based on the provided list or array.

        Args:
            frequencies (Union[np.ndarray, list]): The custom frequency samples to be recorded.
        """

        self._set_parameter("sample spacing", "custom", "str")
        self._set_parameter("custom frequency samples", frequencies, "list")

    def set_use_wavelength_spacing(self, true_or_false: bool) -> None:
        """
        Toggles the use of wavelength spacing for recording data.

        If enabled, data will be recorded at specified wavelengths instead of frequencies.
        This method should only be called if the override global monitor settings are enabled.

        Args:
            true_or_false (bool): A flag indicating whether to use wavelength spacing.
        """

        self._set_parameter("use wavelength spacing", true_or_false, "bool")

    def set_use_source_limits(self, true_or_false: bool) -> None:
        """
        Toggles the use of source limits for the monitor.

        If enabled, the monitor will use the limits defined by the source.
        This method should only be called if the override global monitor settings are enabled.

        Args:
            true_or_false (bool): A flag indicating whether to use source limits.
        """

        self._set_parameter("use source limits", true_or_false, "bool")

    def set_bandwidth(self, wavelength_start: float, wavelength_stop: float, units: LENGTH_UNITS = None) -> None:
        """
        Sets the bandwidth for the monitor using specified minimum and maximum wavelengths.

        This method can only be called if the use of source limits is disabled.

        Args:
            wavelength_start (float): The minimum wavelength to record data.
            wavelength_stop (float): The maximum wavelength to record data.
            units (LENGTH_UNITS, optional): The units for the wavelength measurements. If None,
                                             the global simulation units will be used.
        """

        if self._get_parameter("use source limits", "bool"):
            raise ValueError(
                "You cannot set a custom monitor bandwidth when 'use source limits' is enabled. "
                "Disable this using the 'set_use_source_limits(False)' method before setting a custom bandwidth."
            )

        if units is None:
            units = self._simulation.__getattribute__("_global_units")

        start = convert_length(wavelength_start, units, "m")
        stop = convert_length(wavelength_stop, units, "m")

        self._set_parameter("minimum wavelength", start, "float")
        self._set_parameter("maximum wavelength", stop, "float")

    def set_frequency_points(self, points: int) -> None:
        """
        Sets the number of frequency points for the monitor.

        This method should only be called if the override global monitor settings are enabled.

        Args:
            points (int): The number of frequency points at which to record data.
        """

        Validate.integer_in_range(points, "points", (1, float('inf')))
        self._set_parameter("frequency points", points, "int")

    @abstractmethod
    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.sample_spacing = self._get_parameter("sample spacing", "str")
        if settings.sample_spacing == "custom":
            settings.custom_frequency_samples = np.array(self._get_parameter("custom frequency samples", "list"))
        else:
            settings.use_wavelength_spacing = self._get_parameter("use wavelength spacing", "bool")
            settings.minimum_wavelength = self._get_parameter("minimum wavelength", "float")
            settings.maximum_wavelength = self._get_parameter("maximum wavelength", "float")
            settings.frequency_points = self._get_parameter("frequency points", "int")
        return settings


class MonitorAdvancedSettingsBase(SettingTab):
    @dataclass
    class _Settings(Settings):
        spatial_interpolation: SPATIAL_INTERPOLATIONS
        record_data_in_pml: bool

    __slots__ = SettingTab.__slots__

    def set_spatial_interpolation(self, argument: SPATIAL_INTERPOLATIONS) -> None:
        """
        Sets the method for spatial interpolation of electromagnetic fields recorded by the monitor.

        The interpolation method determines how the electric and magnetic field components are
        aligned spatially for calculations of the Poynting vector and electromagnetic energy density.

        Options:
            - NEAREST MESH CELL: Interpolates fields to the nearest FDTD mesh cell boundary
              (default for 'field and power' monitors).
            - SPECIFIED POSITION: Records fields exactly where the monitor is located
              (default for 'profile' monitors).
            - NONE: No interpolation is performed; each field component is recorded at a different
              position within the Yee cell.

        Args:
            argument (SPATIAL_INTERPOLATIONS): The interpolation method to be applied.
        """
        Validate.in_literal(argument, "argument", SPATIAL_INTERPOLATIONS)
        prev_value = self._get_parameter("spatial interpolation", "str")
        if prev_value != argument:
            self._set_parameter("override global monitor settings", True, "bool")
            self._set_parameter("spatial interpolation", argument, "str")
        return

    def record_data_in_pml(self, true_or_false: bool) -> None:
        """
        Sets whether to collect monitor data within the Perfectly Matched Layer (PML) boundary
        condition region.

        Enabling this option allows the simulation to record data within the PML region, which is
        typically not recommended. It is advised to contact Lumerical support before using this
        feature as it is considered an advanced option.

        Note: The simulation region must have the
        'EXTEND STRUCTURE THROUGH PML' option disabled when this option is enabled.

        Args:
            true_or_false (bool): A flag indicating whether to record data in the PML region.

        Raises:
            UserWarning: If attempting to enable recording data in PML without disabling
            'EXTEND STRUCTURE THROUGH PML'.
        """
        self._set_parameter("record data in pml", true_or_false, "bool")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.spatial_interpolation = self._get_parameter("spatial interpolation", "str")
        settings.record_data_in_pml = self._get_parameter("record data in pml", "bool")
        return settings


# General Settings
class MonitorGeneralSettings(SettingTab, MonitorGeneralSettingsBase):
    @dataclass
    class _Settings(MonitorGeneralSettingsBase._Settings):
        simulation_type: str

    __slots__ = SettingTab.__slots__

    def override_global_monitor_settings(self, override: bool) -> None:
        """
        Enables or disables the override of global monitor settings.

        If enabled, the user can specify the frequency range and number of points for recording
        frequency-domain information. If disabled, the settings will default to global monitor settings.

        Args:
            override (bool): A flag indicating whether to override global monitor settings.
        """

        self._set_parameter("override global monitor settings", override, "bool")

    def _validate_global_settings_override(self) -> None:
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError(f"You must enable override global monitor settings before setting parameters of "
                             f"monitor {self._parent.name}.")

    def set_bandwidth(self, wavelength_start: float, wavelength_stop: float, units: LENGTH_UNITS = None) -> None:
        self._validate_global_settings_override()
        super().set_bandwidth(wavelength_start, wavelength_stop, units)

    def set_frequency_points(self, points: int) -> None:
        self._validate_global_settings_override()
        super().set_frequency_points(points)

    def set_chebyshev_sample_spacing(self) -> None:
        self._validate_global_settings_override()
        super().set_chebyshev_sample_spacing()

    def set_uniform_sample_spacing(self) -> None:
        self._validate_global_settings_override()
        super().set_uniform_sample_spacing()

    def set_custom_sample_spacing(self, frequencies: Union[np.ndarray, list]) -> None:
        self._validate_global_settings_override()
        super().set_custom_sample_spacing(frequencies)

    def set_use_source_limits(self, true_or_false: bool) -> None:
        self._validate_global_settings_override()
        super().set_use_source_limits(true_or_false)

    def set_use_wavelength_spacing(self, true_or_false: bool) -> None:
        self._validate_global_settings_override()
        super().set_use_wavelength_spacing(true_or_false)

    def set_simulation_type(self, simulation_type: SIMULATION_TYPE) -> None:
        """
        Sets the type of simulation data to be recorded.

        This method allows the user to specify the simulation type for data recording.
        The default setting is 'ALL', which records all available simulation data.
        Users can select specific types of simulation data based on their needs.

        Args:
            simulation_type (SIMULATION_TYPE): The type of simulation data to be recorded.

        Raises:
            ValueError: If the provided simulation type is not valid.
        """

        # Validate the provided simulation type
        if simulation_type not in get_args(SIMULATION_TYPE):
            raise ValueError(f"Invalid simulation type: {simulation_type}. Must be one of {list(SIMULATION_TYPE)}.")

        self._set_parameter("simulation type", simulation_type, "str")

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.simulation_type = self._get_parameter("simulation type", "str")
        settings.fill_hash_fields()
        return settings


# Advanced settings
class IndexMonitorAdvancedSettings(MonitorAdvancedSettingsBase):
    @dataclass
    class _Settings(MonitorAdvancedSettingsBase._Settings):
        record_surface_conductivity: bool
        record_conformal_mesh_when_possible: bool

    __slots__ = MonitorAdvancedSettingsBase.__slots__

    def record_conformal_mesh_when_possible(self, true_or_false: bool) -> None:
        """
        Enables or disables the recording of conformal mesh information.

        When enabled (default setting), this option allows the index monitor to record
        the effects of the conformal mesh. This information can be helpful for various
        analyses but may not be appropriate for absorption calculations.

        Conformal mesh information can only be recorded when:
        - The spatial interpolation setting is either 'NEAREST MESH CELL' or 'NONE'.
        - The spatial downsampling option is set to 1.

        Args:
            true_or_false (bool): A flag indicating whether to record conformal mesh information.

        Raises:
            UserWarning: If the setting is incompatible with the current spatial interpolation or downsampling settings.
        """

        # Set the parameter for recording conformal mesh
        self._set_parameter("record conformal mesh when possible", true_or_false, "bool")

    def record_surface_conductivity(self, true_or_false: bool) -> None:
        """
        Enables or disables the recording of surface conductivity.

        When enabled, the index monitor records the surface conductivity used in the simulation,
        which is returned as the SURFACE CONDUCTIVITY result. This feature is particularly useful
        when recording surface conductivity components over space with the spatial interpolation
        option set to either 'SPECIFIED POSITION' or 'NONE'.

        Args:
            true_or_false (bool): A flag indicating whether to record surface conductivity.
        """

        self._set_parameter("record surface conductivity", true_or_false, "bool")

    def _get_active_parameters(self) -> IndexMonitorAdvancedSettings._Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.record_conformal_mesh_when_possible = self._get_parameter("record conformal mesh when possible",
                                                                           "bool")
        settings.record_surface_conductivity = self._get_parameter("record surface conductivity", "bool")
        settings.fill_hash_fields()
        return settings


class FreqAndTimeDomainMonitorAdvancedSettings(MonitorAdvancedSettingsBase):
    @dataclass
    class _Settings(MonitorAdvancedSettingsBase._Settings):
        min_sampling_per_cycle: float

    __slots__ = MonitorAdvancedSettingsBase.__slots__

    def override_advanced_global_monitor_settings(self, true_or_false: bool) -> None:
        """
        Enables or disables the option to override advanced global monitor settings.

        When this option is selected, the MIN SAMPLING PER CYCLE can be set. This setting allows for customization of
        monitor behavior beyond the global defaults.

        Args:
            true_or_false (bool):
                - True to enable overriding advanced global monitor settings.
                - False to disable overriding.

        Raises:
            ValueError: If the provided value is not a boolean.
        """

        # Validate that the input is a boolean
        if not isinstance(true_or_false, bool):
            raise ValueError("The 'true_or_false' argument must be a boolean.")

        # Set the parameter to override advanced global monitor settings
        self._set_parameter("override advanced global monitor settings", true_or_false, "bool")

    def set_min_sampling_per_cycle(self, min_sampling: float) -> None:
        """
        Sets the minimum sampling per optical cycle for the monitor.

        This parameter determines the minimum amount of sampling per optical cycle that can be used.
        By default, it is set at 2 (the Nyquist limit) for optimum efficiency.

        Args:
            min_sampling (float): The minimum sampling per cycle, must be greater than or equal to 2.

        Raises:
            ValueError: If 'override advanced global monitor settings' is not enabled.
            ValueError: If min_sampling is less than 2.
        """

        # Validate the minimum sampling value
        Validate.number_in_range(min_sampling, "min_sampling", (2, float('inf')))

        # Check if advanced global monitor settings override is enabled
        if not self._get_parameter("override advanced global monitor settings", "bool"):
            raise ValueError(
                f"To specify the minimum sampling per cycle for monitor '{self._parent.name}', "
                f"you must first set 'override advanced global monitor settings' to True."
            )

        # Set the minimum sampling per cycle
        self._set_parameter("min sampling per cycle", min_sampling, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.min_sampling_per_cycle = self._get_parameter("min sampling per cycle", "float")
        settings.fill_hash_fields()
        return settings


# Global settings
class GlobalMonitorSettings(GlobalSettingTab, MonitorGeneralSettingsBase):
    @dataclass
    class _Settings(MonitorGeneralSettingsBase._Settings):
        min_sampling_per_cycle: float

    __slots__ = GlobalSettingTab.__slots__

    def _get_parameter(self, parameter_name: str, parameter_type: PARAMETER_TYPES, object_name: str = None) -> Any:
        return get_parameter(self._simulation.__getattribute__("_lumapi"), parameter_name, parameter_type,
                             object_name=None,
                             getter_function=self._simulation.__getattribute__("_lumapi").getglobalmonitor)

    def _set_parameter(self, parameter_name: str, value: Any, parameter_type: PARAMETER_TYPES,
                       object_name: str = None) -> Any:
        return set_parameter(self._simulation.__getattribute__("_lumapi"), parameter_name, value, parameter_type,
                             object_name=None,
                             getter_function=self._simulation.__getattribute__("_lumapi").getglobalmonitor,
                             setter_function=self._simulation.__getattribute__("_lumapi").setglobalmonitor)

    def set_min_sampling_per_cycle(self, min_sampling: float) -> None:
        """
        Sets the minimum sampling per optical cycle for the monitor.

        This parameter determines the minimum amount of sampling per optical cycle that can be used.
        By default, it is set at 2 (the Nyquist limit) for optimum efficiency.

        Args:
            min_sampling (float): The minimum sampling per cycle, must be greater than or equal to 2.

        Raises:
            ValueError: If 'override advanced global monitor settings' is not enabled.
            ValueError: If min_sampling is less than 2.
        """

        # Validate the minimum sampling value
        Validate.number_in_range(min_sampling, "min_sampling", (2, float('inf')))

        # Set the minimum sampling per cycle
        self._set_parameter("min sampling per cycle", min_sampling, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.min_sampling_per_cycle = self._get_parameter("min sampling per cycle", "float")
        settings.fill_hash_fields()
        return settings


# Data to record settings
class DataToRecord(SettingTab):
    class _SetDataToRecordKwargs(TypedDict, total=False):
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

    @dataclass
    class _Settings(Settings):
        standard_fourier_transform: bool
        partial_spectral_average: bool
        total_spectral_average: bool
        output_Ex: bool
        output_Ey: bool
        output_Ez: bool
        output_Hx: bool
        output_Hy: bool
        output_Hz: bool
        output_Px: bool
        output_Py: bool
        output_Pz: bool
        output_power: bool

    __slots__ = SettingTab.__slots__

    def set_data_to_record(self, **kwargs: Unpack[_SetDataToRecordKwargs]) -> None:
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
            raise ValueError("You must either choose to diable all first or enable all first, not both, as this is "
                             "ambigous.")
        elif disable_first:
            initial = {param: False for param in kwargs.keys()}
            initial.update(kwargs)
            kwargs = initial
        else:
            initial = {param: True for param in kwargs.keys()}
            initial.update(kwargs)
            kwargs = initial

        valid_parameters = list(self._SetDataToRecordKwargs.__annotations__.keys())
        for parameter, enabled in kwargs.items():
            Validate.in_list(parameter, parameter, valid_parameters)
            Validate.boolean(enabled, parameter)
            self._set_parameter("output " + parameter, enabled, "bool")

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
        self._set_parameter("standard fourier transform", true_or_false, "bool")

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
        self._set_parameter("partial spectral average", true_or_false, "bool")

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
        self._set_parameter("total spectral average", true_or_false, "bool")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.standard_fourier_transform = self._get_parameter("standard fourier transform", "bool")
        settings.partial_spectral_average = self._get_parameter("partial spectral average", "bool")
        settings.total_spectral_average = self._get_parameter("total spectral average", "bool")
        for field in ["E", "H", "P"]:
            for axis in get_args(AXES):
                settings.__setattr__(f"output_{field}{axis}", self._get_parameter(f"output {field}{axis}", "bool"))
        settings.output_power = self._get_parameter("Output power", "bool")
        settings.fill_hash_fields()
        return settings


# Spectral averaging and apodization settings
class SpectralAveraging(SettingTab):

    class _Settings(Settings):
        delta: float
        apodization: APODIZATIONS
        apodization_center: float
        apodization_time_width: float

    __slots__ = SettingTab.__slots__

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
            Validate.in_literal(frequency_unit, "frequency_unit", FREQUENCY_UNITS)

        frequency_unit: FREQUENCY_UNITS  # To not throw off the type-checker

        # Convert delta to Hz using the provided (or default) frequency unit
        delta_hz = convert_frequency(delta, from_unit=frequency_unit, to_unit="Hz")

        # Set the parameter for delta
        self._set_parameter("delta", delta_hz, "float")

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
        Validate.in_literal(apodization, "apodization", APODIZATIONS)

        # Set the parameter for apodization
        self._set_parameter("apodization", apodization, "str")

    def set_apodization_center(self, center: float, time_unit: TIME_UNITS = "fs") -> None:
        """
        Set the center of the apodization window.

        Args:
            center (float): The center time of the apodization window.
            time_unit (TIME_UNITS, optional): The time unit for the center. Defaults to 'fs'.

        Raises:
            ValueError: If apodization is set to 'None'.
        """

        if self._get_parameter("apodization", "str") == "None":
            raise ValueError(
                "You can only set apodization center if apodization is set to 'Full', 'Start', or 'End', not 'None'."
            )

        # Validate the provided time unit
        Validate.in_literal(time_unit, "time_unit", TIME_UNITS)

        # Convert the center time to seconds
        center = convert_time(value=center, from_unit=time_unit, to_unit="s")

        # Set the parameter for apodization center
        self._set_parameter("apodization center", center, "float")

    def set_apodization_time_width(self, time_width: float, time_unit: TIME_UNITS = "fs") -> None:
        """
        Set the time width of the apodization window.

        Args:
            time_width (float): The time width of the apodization window.
            time_unit (TIME_UNITS, optional): The time unit for the time width. Defaults to 'fs'.

        Raises:
            ValueError: If apodization is set to 'None'.
        """

        if self._get_parameter("apodization", "str") == "None":
            raise ValueError(
                "You can only set apodization time width if apodization is set to 'Full', 'Start', or 'End', not 'None'."
            )

        # Validate the provided time unit
        Validate.in_literal(time_unit, "time_unit", TIME_UNITS)

        # Convert the time width to seconds
        time_width = convert_time(value=time_width, from_unit=time_unit, to_unit="s")

        # Set the parameter for apodization time width
        self._set_parameter("apodization time width", time_width, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.delta = self._get_parameter("delta", "float")
        settings.apodization = self._get_parameter("apodization", "str")
        if settings.apodization != "None":
            settings.apodization_center = self._get_parameter("apodization center", "float")
            settings.apodization_time_width = self._get_parameter("apodization time width", "float")
        settings.fill_hash_fields()
        return settings


########################################################################################################################
#                                  CLASSES FOR ACTUAL MONITOR OBJECTS
########################################################################################################################


# Base class
class MonitorBase(SimulationObject, TrippleSpansProperties, MinMaxDirectProperties, ABC):
    class _Kwargs(SimulationObject._Kwargs, TrippleSpansKwargs, total=False):
        pass

    class _SettingsCollection(SimulationObject._SettingsCollection):
        general: MonitorGeneralSettings
        __slots__ = SimulationObject._SettingsCollection.__slots__

    @dataclass
    class _Settings(SimulationObject._Settings):
        general_settings: MonitorGeneralSettings._Settings

    settings: _SettingsCollection
    __slots__ = SimulationObject.__slots__

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.general_settings = self.settings.general.__getattribute__("_get_active_parameters")()
        return settings


# Monitor classes
class FreqDomainFieldAndPower(MonitorBase):
    class _SettingsCollection(MonitorBase._SettingsCollection):
        _settings = [MonitorGeneralSettings, MonitorGeometryAll, DataToRecord, SpectralAveraging,
                     FreqAndTimeDomainMonitorAdvancedSettings]
        _settings_names = ["general", "geometry", "data_to_record", "spectral_averaging_and_apodization", "advanced"]

        general: MonitorGeneralSettings
        geometry: MonitorGeometryAll
        data_to_record: DataToRecord
        spectral_averaging_and_apodization: SpectralAveraging
        advanced: FreqAndTimeDomainMonitorAdvancedSettings
        __slots__ = MonitorBase._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        use_relative_coordinates: bool
        x: float
        y: float
        z: float
        x_span: float
        y_span: float
        z_span: float


    @dataclass
    class _Settings(MonitorBase._Settings):
        geometry_settings: MonitorGeometryAll._Settings
        data_to_record_settings: DataToRecord._Settings
        spectral_averaging_and_apodization_settings: SpectralAveraging._Settings
        advanced_settings: FreqAndTimeDomainMonitorAdvancedSettings._Settings

    @dataclass
    class _Results:
        lambda_: np.ndarray
        f: np.ndarray
        power: np.ndarray
        E: np.ndarray
        H: np.ndarray
        P: np.ndarray

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = MonitorBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[_Kwargs]):
        super().__init__(name, simulation, **kwargs)

    def make_profile_monitor(self) -> None:
        """
        Turns the monitor into a profile monitor.

        Sets the method for spatial interpolation of electromagnetic fields recorded by the monitor to
        'specified position'. This means fields are recorded exactly where the monitor is located. This is the
        default for 'profile' monitors in lumerical FDTD.

        The interpolation method determines how the electric and magnetic field components are
        aligned spatially for calculations of the Poynting vector and electromagnetic energy density.
        """

        self.settings.advanced.set_spatial_interpolation("specified position")

    def _get_results(self) -> _Results:
        """
        Fetches the raw results from the index monitor.
        """
        results = self._simulation.__getattribute__("_get_results")(self.name, "T", "any")
        results["f_points"] = self._get_parameter("frequency points", "int")
        for axis in get_args(AXES):
            results[axis] = results[axis].flatten()

        results["lambda_"] = results.pop("lambda")
        del results["Lumerical_dataset"]

        results = self._Results(**results)
        return results

    def _get_active_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.geometry_settings = self.settings.geometry.__getattribute__("_get_active_parameters")()
        settings.data_to_record_settings = self.settings.data_to_record.__getattribute__("_get_active_parameters")()
        settings.spectral_averaging_and_apodization_settings = (self.settings.spectral_averaging_and_apodization
                                                                .__getattribute__("_get_active_parameters")())
        settings.advanced_settings = self.settings.advanced.__getattribute__("_get_active_parameters")()
        settings.fill_hash_fields()
        return settings


class IndexMonitor(MonitorBase):
    class _SettingsCollection(MonitorBase._SettingsCollection):
        _settings = [MonitorGeneralSettings, MonitorGeometry3D, IndexMonitorAdvancedSettings]
        _settings_names = ["general", "geometry", "advanced"]

        general: MonitorGeneralSettings
        geometry: MonitorGeometry3D
        advanced: IndexMonitorAdvancedSettings
        __slots__ = MonitorBase._SettingsCollection.__slots__ + _settings_names

    @dataclass
    class _Settings(MonitorBase._Settings):
        geometry_settings: MonitorGeometry3D._Settings
        advanced_settings: IndexMonitorAdvancedSettings._Settings

    @dataclass
    class _Results:
        lambda_: np.ndarray
        f: np.ndarray
        x: np.ndarray
        y: np.ndarray
        z: np.ndarray
        index_x: np.ndarray
        index_y: np.ndarray
        index_z: np.ndarray
        f_points: int

    class _Kwargs(TypedDict, total=False):
        use_relative_coordinates: bool
        x: float
        y: float
        z: float
        x_span: float
        y_span: float
        z_span: float

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = MonitorBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[_Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    def _get_results(self) -> _Results:
        """
        Fetches the raw results from the index monitor.
        """
        results = self._simulation.__getattribute__("_get_results")(self.name, "index", "any")
        results["f_points"] = self._get_parameter("frequency points", "int")
        for axis in get_args(AXES):
            results[axis] = results[axis].flatten()

        results["lambda_"] = results.pop("lambda")
        del results["Lumerical_dataset"]

        results = self._Results(**results)
        return results

    def get_currently_active_simulation_parameters(self) -> _Settings:
        settings = cast(self._Settings, super()._get_active_parameters())
        settings.geometry_settings = self.settings.geometry.__getattribute__("_get_active_parameters")()
        settings.advanced_settings = self.settings.advanced.__getattribute__("_get_active_parameters")()
        settings.fill_hash_fields()
        return settings
