from __future__ import annotations

# Standard library imports
from typing import Any, Literal, Union, get_args, Unpack, Optional

# Third-party library imports
from lumapi_import import lumapi
import numpy as np

# Local library imports
from base_classes import SettingTab
from simulation_object import SimulationObject
from type_hint_resources import LENGTH_UNITS, PARAMETER_TYPES, FREQUENCY_UNITS, TIME_UNITS, AXES
from local_resources import convert_length, convert_frequency, convert_time, Validate
from geometry import CartesianGeometry


########################################################################################################################
#                                          LITERALS AND CONSTANTS
########################################################################################################################

SAMPLE_SPACINGS = Literal["uniform", "chebyshev", "custom"]
SIMULATION_TYPE = Literal["All", "3D", "2D Z-normal"]
SPATIAL_INTERPOLATIONS = Literal["specified position", "nearest mesh cell", "none"]
APODIZATIONS = Literal["None", "Full", "Start", "End"]
MONITOR_TYPES_ALL = Literal["Point", "Linear X", "Linear Y", "Linear Z",
                            "2D X-normal", "2D Y-normal", "2D Z-normal", "3D"]
MONITOR_TYPES_3D = Literal["2D X-normal", "2D Y-normal", "2D Z-normal", "3D"]
MONITOR_TYPES_2D = Literal["2D X-normal", "2D Y-normal", "2D Z-normal"]

########################################################################################################################
#                                  OVERRIDDEN GEOMETRY CLASSES FOR MONITORS
########################################################################################################################


class MonitorGeometryAll(CartesianGeometry):

    class _SettingsDict(CartesianGeometry._SettingsDict):
        down_sample_X: int
        down_sample_Y: int
        down_sample_Z: int
        monitor_type: MONITOR_TYPES_ALL

    __slots__ = CartesianGeometry.__slots__

    def set_spans(
            self, x_span: Optional[Union[int, float]] = None, y_span: Optional[Union[int, float]] = None,
            z_span: Optional[Union[int, float]] = None, units: LENGTH_UNITS = None) -> None:

        monitor_type: MONITOR_TYPES_ALL = self._get_parameter("monitor rype", "str")

        if monitor_type == "Point":
            raise ValueError(
                f"You are trying to set the spans of a monitor that is of type 'Point', as thus has no "
                f"spans in any directions. Set the monitor type to something not 1-dimensional to set spans."
            )
        elif monitor_type == "Linear X" and any([z_span is not None, y_span is not None]):
            raise ValueError(
                f"You are trying to set the Y or Z spans of a monitor that is of type 'Linear X', as thus has no "
                f"spans in these directions. Set the monitor type to something else to set these spans."
            )
        elif monitor_type == "Linear Y" and any([x_span is not None, z_span is not None]):
            raise ValueError(
                f"You are trying to set the X or Z spans of a monitor that is of type 'Linear Y', as thus has no "
                f"spans in these directions. Set the monitor type to something else to set these spans."
            )
        elif monitor_type == "Linear Z" and any([x_span is not None, y_span is not None]):
            raise ValueError(
                f"You are trying to set the X or Y spans of a monitor that is of type 'Linear Z', as thus has no "
                f"spans in these directions. Set the monitor type to something else to set these spans."
            )
        elif monitor_type == "2D X-normal" and x_span is not None:
            raise ValueError(
                f"You are trying to set the X span of a monitor that is of type '2D X-normal', as thus has no "
                f"span in this direction. Set the monitor type to something else to set this span."
            )
        elif monitor_type == "2D Y-normal" and y_span is not None:
            raise ValueError(
                f"You are trying to set the Y span of a monitor that is of type '2D Y-normal', as thus has no "
                f"span in this direction. Set the monitor type to something else to set this span."
            )
        elif monitor_type == "2D X-normal" and z_span is not None:
            raise ValueError(
                f"You are trying to set the Z span of a monitor that is of type '2D Z-normal', as thus has no "
                f"span in this direction. Set the monitor type to something else to set this span."
            )

        super().set_spans(x_span, y_span, z_span, units)

    def set_monitor_type(self, monitor_type: MONITOR_TYPES_ALL) -> None:
        """
        Sets the type and orientation of the monitor for the simulation.

        The monitor type determines the available spatial settings for the simulation region.
        Depending on the monitor type selected, different spatial parameters will be enabled,
        including the center position, min/max positions, and span for the X, Y, and Z axes.

        Args:
            monitor_type (MONITOR_TYPES_ALL): The type of monitor to set, which controls the available
                                               spatial settings for the simulation region.

        Raises:
            ValueError: If the provided monitor_type is not a valid type.
        """
        self._set_parameter("monitor type", monitor_type, "str")

    def set_down_sampling(self, axis: AXES, down_sampling: int) -> None:
        """
        Sets the spatial downsampling value for the specified monitor axis.

        The downsampling parameter controls how frequently data is recorded along the specified axis.
        A downsample value of N means that data will be sampled every Nth grid point.
        Setting the downsample value to 1 will provide the most detailed spatial information,
        recording data at every grid point.

        Args:
            axis (AXES): The axis along which to set the downsampling.
                         This should be one of the predefined axes (X, Y, Z).
            down_sampling (int): The downsample value, must be greater than or equal to 1.

        Raises:
            ValueError: If the down_sampling value is not within the valid range (1 to infinity).
        """
        Validate.integer_in_range(down_sampling, "down_sampling", (1, float('inf')))
        self._set_parameter(f"down sample {axis.capitalize()}", down_sampling, "int")

    def get_currently_active_simulation_parameters(self) -> MonitorGeometryAll._SettingsDict:

        settings = MonitorGeometryAll._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["monitor_type"] = self._get_parameter("monitor type", "str")

        for axis in get_args(AXES):
            axis = axis.capitalize()
            if axis.capitalize() in settings["monitor_type"]:
                settings[f"down_sample_{axis}"] = None
            else:
                settings[f"down_sample_{axis}"] = self._get_parameter(
                    f"down sample {axis}", "int")
        return settings


class MonitorGeometry3D(MonitorGeometryAll):

    class _SettingsDict(SettingTab._SettingsDict):
        down_sample_X: int
        down_sample_Y: int
        down_sample_Z: int
        monitor_type: MONITOR_TYPES_3D

    __slots__ = MonitorGeometryAll.__slots__

    def set_monitor_type(self, monitor_type: MONITOR_TYPES_3D) -> None:
        super().set_monitor_type(monitor_type)

    def get_currently_active_simulation_parameters(self) -> MonitorGeometry3D._SettingsDict:
        return MonitorGeometry3D._SettingsDict(**super().get_currently_active_simulation_parameters())


class MonitorGeometry2D(MonitorGeometryAll):

    class _SettingsDict(SettingTab._SettingsDict):
        down_sample_X: int
        down_sample_Y: int
        down_sample_Z: int
        monitor_type: MONITOR_TYPES_3D

    __slots__ = MonitorGeometryAll.__slots__

    def set_monitor_type(self, monitor_type: MONITOR_TYPES_2D) -> None:
        super().set_monitor_type(monitor_type)

    def get_currently_active_simulation_parameters(self) -> MonitorGeometry2D._SettingsDict:
        return MonitorGeometry2D._SettingsDict(**super().get_currently_active_simulation_parameters())


########################################################################################################################
#                                  SETTING CLASSES FOR THE MAIN SETTINGS CATEGORIES
########################################################################################################################


# Base settings classes
class GeneralBase(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        sample_spacing: SAMPLE_SPACINGS
        use_wavelength_spacing: bool
        use_source_limits: bool
        minimum_wavelength: float
        maximum_wavelength: float
        frequency_points: int
        custom_frequency_samples: np.ndarray

    __slots__ = SettingTab.__slots__

    def set_uniform_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to uniform.

        This method should only be called if the override global monitor settings are enabled.

        Raises:
            ValueError: If the global monitor settings override is not enabled.
        """
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting sample spacing.")

        self._set_parameter("sample spacing", "uniform", "str")

    def set_chebyshev_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to Chebyshev.

        This method should only be called if the override global monitor settings are enabled.

        Raises:
            ValueError: If the global monitor settings override is not enabled.
        """
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting sample spacing.")

        self._set_parameter("sample spacing", "chebyshev", "str")

    def set_custom_sample_spacing(self, frequencies: Union[np.ndarray, list]) -> None:
        """
        Sets the sample spacing for the monitor to custom.

        This method should only be called if the override global monitor settings are enabled.
        It also sets the custom frequency samples based on the provided list or array.

        Args:
            frequencies (Union[np.ndarray, list]): The custom frequency samples to be recorded.

        Raises:
            ValueError: If the global monitor settings override is not enabled.
        """
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting sample spacing.")

        self._set_parameter("sample spacing", "custom", "str")
        self._set_parameter("custom frequency samples", frequencies, "list")

    def set_use_wavelength_spacing(self, true_or_false: bool) -> None:
        """
        Toggles the use of wavelength spacing for recording data.

        If enabled, data will be recorded at specified wavelengths instead of frequencies.
        This method should only be called if the override global monitor settings are enabled.

        Args:
            true_or_false (bool): A flag indicating whether to use wavelength spacing.

        Raises:
            ValueError: If the global monitor settings override is not enabled.
        """
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting wavelength spacing.")

        self._set_parameter("use wavelength spacing", true_or_false, "bool")

    def set_use_source_limits(self, true_or_false: bool) -> None:
        """
        Toggles the use of source limits for the monitor.

        If enabled, the monitor will use the limits defined by the source.
        This method should only be called if the override global monitor settings are enabled.

        Args:
            true_or_false (bool): A flag indicating whether to use source limits.

        Raises:
            ValueError: If the global monitor settings override is not enabled.
        """
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting source limits.")

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

        Raises:
            ValueError: If the use of source limits is enabled.
        """
        if self._get_parameter("use source limits", "bool"):
            raise ValueError(
                "You cannot set a custom monitor bandwidth when 'use source limits' is enabled. "
                "Disable this using the 'set_use_source_limits(False)' method before setting a custom bandwidth."
            )
        elif not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting source limits.")

        if units is None:
            units = self._simulation.global_units

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

        Raises:
            ValueError: If the global monitor settings override is not enabled or if points are not valid.
        """
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting frequency points.")

        Validate.integer_in_range(points, "points", (1, float('inf')))
        self._set_parameter("frequency points", points, "int")

    def get_currently_active_simulation_parameters(self) -> GeneralBase._SettingsDict:

        # Initialize dict with all values as None
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        # Fill inn initial set of parameters
        settings["sample_spacing"] = self._get_parameter("sample spacing", "str")

        if settings["sample_spacing"] == "custom":
            settings["custom_frequency_samples"] = np.array(
                self._get_parameter("custom frequency samples", "list"))
        else:
            settings["use_wavelength_spacing"] = self._get_parameter(
                "use wavelength spacing", "bool")
            settings["use_source_limits"] = self._get_parameter(
                "use source limits", "bool")
            settings["minimum_wavelength"] = self._get_parameter(
                "minimum wavelength", "float")
            settings["maximum_wavelength"] = self._get_parameter(
                "maximum wavelength", "float")
            settings["frequency_points"] = self._get_parameter(
                "frequency points", "int")

        return settings


class AdvancedBase(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
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

        Raises:
            ValueError: If the global monitor settings override is not enabled.
        """
        if not self._get_parameter("override global monitor settings", "bool"):
            raise ValueError("You must enable override global monitor settings before setting spatial interpolation.")
        Validate.in_literal(argument, "argument", SPATIAL_INTERPOLATIONS)
        self._set_parameter("spatial interpolation", argument, "str")

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
        # Check if the "EXTEND STRUCTURE THROUGH PML" option is disabled
        if self._get_parameter("extend structure through pml", "bool"):
            raise UserWarning(
                "You must disable 'EXTEND STRUCTURE THROUGH PML' before recording data in PML."
            )

        self._set_parameter("record data in pml", true_or_false, "bool")

    def get_currently_active_simulation_parameters(self) -> AdvancedBase._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update({
            "spatial_interpolation": self._get_parameter("spatial interpolation", "str"),
            "record_data_in_pml": self._get_parameter("record data in pml", "bool")
        })
        return settings


# General Settings
class General(GeneralBase):

    class _SettingsDict(GeneralBase._SettingsDict):
        simulation_type: str

    __slots__ = GeneralBase.__slots__

    def override_global_monitor_settings(self, override: bool) -> None:
        """
        Enables or disables the override of global monitor settings.

        If enabled, the user can specify the frequency range and number of points for recording
        frequency-domain information. If disabled, the settings will default to global monitor settings.

        Args:
            override (bool): A flag indicating whether to override global monitor settings.
        """
        self._set_parameter("override global monitor settings", override, "bool")

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
        if simulation_type not in SIMULATION_TYPE:
            raise ValueError(f"Invalid simulation type: {simulation_type}. Must be one of {list(SIMULATION_TYPE)}.")

        self._set_parameter("simulation type", simulation_type, "str")

    def get_currently_active_simulation_parameters(self) -> General._SettingsDict:
        settings = General._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["simulation_type"] = self._get_parameter("simulation type", "str")
        return settings


# Advanced settings
class IndexAdvanced(AdvancedBase):

    class _SettingsDict(AdvancedBase._SettingsDict):
        record_surface_conductivity: bool
        record_conformal_mesh_when_possible: bool

    __slots__ = AdvancedBase.__slots__

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

    def get_currently_active_simulation_parameters(self) -> IndexAdvanced._SettingsDict:
        settings = IndexAdvanced._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["record_conformal_mesh_when_possible"] = self._get_parameter(
            "record conformal mesh when possible", "bool")
        settings["record_surface_conductivity"] = self._get_parameter(
            "record surface conductivity", "bool")
        return settings


class FreqAndTimeDomainAdvanced(AdvancedBase):

    class _SettingsDict(AdvancedBase._SettingsDict):
        min_sampling_per_cycle: float

    __slots__ = AdvancedBase.__slots__

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

    def get_currently_active_simulation_parameters(self) -> FreqAndTimeDomainAdvanced._SettingsDict:
        settings = FreqAndTimeDomainAdvanced._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["min_sampling_per_cycle"] = self._get_parameter(
            "min sampling per cycle", "float")
        return settings


# Global settings
class GlobalMonitorSettings(GeneralBase):

    class _SettingsDict(GeneralBase._SettingsDict):
        min_sampling_per_cycle: float

    __slots__ = GeneralBase.__slots__

    def _get_parameter(
            self, parameter_name: str, type_: PARAMETER_TYPES, object_name: str = None, getter_function=None) -> Any:
        # Pass the getglobalmonitor() method as the getter method.
        return super()._get_parameter(
            parameter_name=parameter_name, type_=type_, getter_function=self._simulation.getglobalmonitor)

    def _set_parameter(self, parameter_name: str, value: Any, type_: PARAMETER_TYPES, object_name: str = None,
                       setter_function=None, getter_function=None) -> Any:
        return super()._set_parameter(
            parameter_name=parameter_name, value=value, type_=type_,
            setter_function=self._simulation.setglobalmonitor, getter_function=self._simulation.getglobalmonitor)

    def set_uniform_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to uniform.

        This method should only be called if the override global monitor settings are enabled.

        Raises:
            ValueError: If the global monitor settings override is not enabled.
        """
        self._set_parameter("sample spacing", "uniform", "str")

    def set_chebyshev_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to Chebyshev.

        This method should only be called if the override global monitor settings are enabled.

        Raises:
            ValueError: If the global monitor settings override is not enabled.
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

        Raises:
            ValueError: If the use of source limits is enabled.
        """
        if self._get_parameter("use source limits", "bool"):
            raise ValueError(
                "You cannot set a custom monitor bandwidth when 'use source limits' is enabled. "
                "Disable this using the 'set_use_source_limits(False)' method before setting a custom bandwidth."
            )

        if units is None:
            units = self._simulation.global_units

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

    def get_currently_active_simulation_parameters(self) -> GlobalMonitorSettings._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["min_sampling_per_cycle"] = self._get_parameter(
            "min sampling per cycle", "float")
        return settings


# Data to record settings
class DataToRecord(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
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

    def electric_field(self, Ex: bool = None, Ey: bool = None, Ez: bool = None) -> None:
        """
        Set the what electric field components should be recorded..

        This method allows the user to specify which components of the electric field
        (Ex, Ey, Ez) will be measured during the simulation. Only the components passed
        will be updated.

        Args:
            Ex (bool, optional):
                True to include the Ex component in the output; False to exclude it.
            Ey (bool, optional):
                True to include the Ey component in the output; False to exclude it.
            Ez (bool, optional):
                True to include the Ez component in the output; False to exclude it.

        Raises:
            ValueError: If any provided parameters are not boolean.
        """
        for value, name in zip((Ex, Ey, Ez), ("Ex", "Ey", "Ez")):
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean value.")

        if Ex is not None:
            self._set_parameter("output Ex", Ex, "bool")
        if Ey is not None:
            self._set_parameter("output Ey", Ey, "bool")
        if Ez is not None:
            self._set_parameter("output Ez", Ez, "bool")

    def magnetic_field(self, Hx: bool = None, Hy: bool = None, Hz: bool = None) -> None:
        """
        Set the what magnetic field components should be recorded..

        This method allows the user to specify which components of the magnetic field
        (Hx, Hy, Hz) will be measured during the simulation. Only the components passed
        will be updated.

        Args:
            Hx (bool, optional):
                True to include the Hx component in the output; False to exclude it.
            Hy (bool, optional):
                True to include the Hy component in the output; False to exclude it.
            Hz (bool, optional):
                True to include the Hz component in the output; False to exclude it.

        Raises:
            ValueError: If any provided parameters are not boolean.
        """
        for value, name in zip((Hx, Hy, Hz), ("Hx", "Hy", "Hz")):
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean value.")

        if Hx is not None:
            self._set_parameter("output Hx", Hx, "bool")
        if Hy is not None:
            self._set_parameter("output Hy", Hy, "bool")
        if Hz is not None:
            self._set_parameter("output Hz", Hz, "bool")

    def poynting_vector(self, Px: bool = None, Py: bool = None, Pz: bool = None) -> None:
        """
        Set the what Peynting vector components should be recorded..

        This method allows the user to specify which components of the Poynting vector
        (Px, Py, Pz) will be measured during the simulation. Only the components passed
        will be updated.

        Args:
            Px (bool, optional):
                True to include the Px component in the output; False to exclude it.
            Py (bool, optional):
                True to include the Py component in the output; False to exclude it.
            Pz (bool, optional):
                True to include the Pz component in the output; False to exclude it.

        Raises:
            ValueError: If any provided parameters are not boolean.
        """
        for value, name in zip((Px, Py, Pz), ("Px", "Py", "Pz")):
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean value.")

        if Px is not None:
            self._set_parameter("output Px", Px, "bool")
        if Py is not None:
            self._set_parameter("output Py", Py, "bool")
        if Pz is not None:
            self._set_parameter("output Pz", Pz, "bool")

    def output_power(self, true_or_false: bool) -> None:
        """
        Set the output power parameter for the monitor.

        This method enables or disables the calculation of integrated power
        over the monitor surface (for 3D simulations) or along a monitor line
        (for 2D simulations). It requires much less memory after the simulation
        is completed, making it suitable for large parallel simulations where
        only the integrated power across a surface is needed.

        Args:
            true_or_false (bool):
                True to enable output power calculation; False to disable it.

        Raises:
            ValueError: If the provided parameter is not boolean.
        """
        if not isinstance(true_or_false, bool):
            raise ValueError("true_or_false must be a boolean value.")

        self._set_parameter("output power", true_or_false, "bool")

    def get_currently_active_simulation_parameters(self) -> DataToRecord._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        settings["standard_fourier_transform"] = self._get_parameter(
            "standard fourier transform", "bool")
        settings["partial_spectral_average"] = self._get_parameter(
            "partial spectral average", "bool")
        settings["total_spectral_average"] = self._get_parameter(
            "total spectral average", "bool")

        for field in ["E", "H", "P"]:
            for axis in get_args(AXES):
                settings[f"output_{field}{axis}"] = self._get_parameter(
                    f"output {field}{axis}", "bool")

        settings["output_power"] = self._get_parameter("Output power", "bool")

        return settings


# Spectral averaging and apodization settings
class SpectralAveraging(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
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

    def get_currently_active_simulation_parameters(self) -> SpectralAveraging._SettingsDict:

        settings = SpectralAveraging._SettingsDict(**self._init_empty_settings_dict())
        settings["delta"] = self._get_parameter("delta", "float")
        settings["apodization"] = self._get_parameter("apodization", "str")
        if settings["apodization"] != "None":
            settings["apodization_center"] = self._get_parameter("apodization center", "float")
            settings["apodization_time_width"] = self._get_parameter(
                "apodization time width", "float")
        return settings


########################################################################################################################
#                                  CLASSES FOR ACTUAL MONITOR OBJECTS
########################################################################################################################


# Base class
class MonitorBase(SimulationObject):

    class _SettingsDict(SimulationObject._SettingsDict):
        general_settings: General._SettingsDict

    class _Kwargs(SimulationObject._Kwargs, total=False):
        x_span: float
        y_span: float
        z_span: float

    _settings = [_setting for _setting in SimulationObject._settings if _setting != CartesianGeometry] + [General]
    _settings_names = [_setting_name for _setting_name in SimulationObject._settings_names
                       if _setting_name != "geometry_settings"] + ["general_settings"]

    # Declare variables
    general_settings: General

    __slots__ = SimulationObject.__slots__ + _settings_names

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[MonitorBase._Kwargs]) -> None:

        ordered = self.__class__._Kwargs(**{
            parameter: None for parameter in self.__class__.__annotations__.keys()})

        for key, value in kwargs.items():
            ordered[key] = value

        poppable = []
        for key, value in ordered.items():
            if value is None:
                poppable.append(key)

        for pop in poppable:
            ordered.pop(pop)

        super().__init__(name, simulation, **kwargs)
        simulation.__class__._monitors.append(self)

    @property
    def x_span(self) -> float:
        return convert_length(self._get_parameter(
            "x span", "float"), "m", self._simulation.global_units)

    @x_span.setter
    def x_span(self, x_span: float) -> None:
        Validate.positive_number(x_span, "x_span")
        self.geometry_settings.set_spans(x_span=x_span)

    @property
    def y_span(self) -> float:
        return convert_length(self._get_parameter(
            "y span", "float"), "m", self._simulation.global_units)

    @y_span.setter
    def y_span(self, y_span: float) -> None:
        Validate.positive_number(y_span, "y_span")
        self.geometry_settings.set_spans(y_span=y_span)

    @property
    def z_span(self) -> float:
        return convert_length(self._get_parameter(
            "z span", "float"), "m", self._simulation.global_units)

    @z_span.setter
    def z_span(self, z_span: float) -> None:
        Validate.positive_number(z_span, "z_span")
        self.geometry_settings.set_spans(z_span=z_span)

    @property
    def x_min(self) -> float:
        return convert_length(self._get_parameter(
            "x min", "float"), "m", self._simulation.global_units)

    @property
    def x_max(self) -> float:
        return convert_length(self._get_parameter(
            "x max", "float"), "m", self._simulation.global_units)

    @property
    def y_min(self) -> float:
        return convert_length(self._get_parameter(
            "y min", "float"), "m", self._simulation.global_units)

    @property
    def y_max(self) -> float:
        return convert_length(self._get_parameter(
            "y max", "float"), "m", self._simulation.global_units)

    @property
    def z_min(self) -> float:
        return convert_length(self._get_parameter(
            "z min", "float"), "m", self._simulation.global_units)

    @property
    def z_max(self) -> float:
        return convert_length(self._get_parameter(
            "z max", "float"), "m", self._simulation.global_units)

    def get_currently_active_simulation_parameters(self) -> MonitorBase._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["general_settings"] = self.general_settings.get_currently_active_simulation_parameters()
        return settings


# Monitor classes
class FreqDomainFieldAndPowerMonitor(MonitorBase):

    class _SettingsDict(MonitorBase._SettingsDict):
        geometry_settings: MonitorGeometryAll._SettingsDict
        data_to_record_settings: DataToRecord._SettingsDict
        spectral_averaging_and_apodization_settings: SpectralAveraging._SettingsDict
        advanced_settings: FreqAndTimeDomainAdvanced._SettingsDict

    class _Kwargs(MonitorBase._Kwargs, total=False):
        monitor_type: MONITOR_TYPES_ALL

    _settings = MonitorBase._settings + [MonitorGeometryAll, DataToRecord, SpectralAveraging,
                                         FreqAndTimeDomainAdvanced]
    _settings_names = MonitorBase._settings_names + ["geometry_settings", "data_to_record_settings",
                                                     "spectral_averaging_and_apodization_settings",
                                                     "advanced_settings"]

    # Declare variables
    geometry_settings: MonitorGeometryAll
    data_to_record_settings: DataToRecord
    spectral_averaging_and_apodization_settings: SpectralAveraging
    advanced_settings: FreqAndTimeDomainAdvanced

    __slots__ = MonitorBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[FreqDomainFieldAndPowerMonitor._Kwargs]):
        super().__init__(name, simulation, **kwargs)

    def get_currently_active_simulation_parameters(self) -> FreqDomainFieldAndPowerMonitor._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["geometry_settings"] = self.geometry_settings.get_currently_active_simulation_parameters()
        settings["data_to_record_settings"] = self.data_to_record_settings.get_currently_active_simulation_parameters()
        settings["spectral_averaging_and_apodization_settings"] = (
            self.spectral_averaging_and_apodization_settings.get_currently_active_simulation_parameters())
        settings["advanced_settings"] = self.advanced_settings.get_currently_active_simulation_parameters()
        return settings

    def __str__(self) -> str:
        return "FrequencyDomainFieldAndPowerMonitor"


class IndexMonitor(MonitorBase):

    class _SettingsDict(MonitorBase._SettingsDict):
        geometry_settings: MonitorGeometry3D._SettingsDict
        advanced_settings: IndexAdvanced._SettingsDict

    class _Kwargs(MonitorBase._Kwargs, total=False):
        monitor_type: MONITOR_TYPES_3D

    _settings = MonitorBase._settings + [MonitorGeometry3D, IndexAdvanced]
    _settings_names = MonitorBase._settings_names + ["geometry_settings", "advanced_settings"]

    # Declare variables
    geometry_settings: MonitorGeometry3D
    advanced_settings: IndexAdvanced

    __slots__ = MonitorBase.__slots__

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[IndexMonitor._Kwargs]) -> None:
        super().__init__(name, simulation, **kwargs)

    def get_currently_active_simulation_parameters(self) -> IndexMonitor._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings["geometry_settings"] = self.geometry_settings.get_currently_active_simulation_parameters()
        settings["advanced_settings"] = self.advanced_settings.get_currently_active_simulation_parameters()
        return settings

    def __repr__(self) -> str:
        return "IndexMonitor"
