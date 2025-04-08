from abc import ABC, abstractmethod
from typing import Union, Type, TypeVar
from warnings import warn

import numpy as np
from numpy.typing import NDArray

from .literals import SIMULATION_TYPE
from ...base_classes.object_modules import Module
from ...resources import validation
from ...resources.functions import convert_length, process_type
from ...resources.literals import LENGTH_UNITS
from ...interfaces import SimulationInterface
from ...resources.errors import LumApiError

T = TypeVar("T")


class Base(Module, ABC):

    @abstractmethod
    def _override(self) -> None:
        ...

    def set_uniform_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to uniform.

        This method should only be called if the override global monitor settings are enabled.
        """
        self._override()
        self._set("sample spacing", "uniform")

    def set_chebyshev_sample_spacing(self) -> None:
        """
        Sets the sample spacing for the monitor to Chebyshev.

        This method should only be called if the override global monitor settings are enabled.
        """
        self._override()
        self._set("sample spacing", "chebyshev")

    def set_custom_sample_spacing(self, frequencies: Union[NDArray, list]) -> None:
        """
        Sets the sample spacing for the monitor to custom.

        This method should only be called if the override global monitor settings are enabled.
        It also sets the custom frequency samples based on the provided list or array.

        Args:
            frequencies (Union[np.ndarray, list]): The custom frequency samples to be recorded.
        """
        self._override()
        self._set("sample spacing", "custom")
        self._set("custom frequency samples", frequencies)

    def set_use_wavelength_spacing(self, true_or_false: bool) -> None:
        """
        Toggles the use of wavelength spacing for recording data.

        If enabled, data will be recorded at specified wavelengths instead of frequencies.
        This method should only be called if the override global monitor settings are enabled.

        Args:
            true_or_false (bool): A flag indicating whether to use wavelength spacing.
        """
        self._override()
        self._set("use wavelength spacing", true_or_false)

    def set_use_source_limits(self, true_or_false: bool) -> None:
        """
        Toggles the use of source limits for the monitor.

        If enabled, the monitor will use the limits defined by the source.
        This method should only be called if the override global monitor settings are enabled.

        Args:
            true_or_false (bool): A flag indicating whether to use source limits.
        """
        self._override()
        self._set("use source limits", true_or_false)

    def set_wavelength_range(self, wavelength_start: float, wavelength_stop: float, units: LENGTH_UNITS = None) -> None:
        """
        Sets the bandwidth for the monitor using specified minimum and maximum wavelengths.

        This method can only be called if the use of source limits is disabled.

        Args:
            wavelength_start (float): The minimum wavelength to record data.
            wavelength_stop (float): The maximum wavelength to record data.
            units (LENGTH_UNITS, optional): The units for the wavelength measurements. If None,
                                             the global simulation units will be used.
        """
        self._override()
        if self._get("use source limits", bool):
            raise ValueError(
                "You cannot set a custom monitor bandwidth when 'use source limits' is enabled. "
                "Disable this using the 'set_use_source_limits(False)' method before setting a custom bandwidth."
            )

        units = units if units is not None else self._units
        start = convert_length(wavelength_start, units, "m")
        stop = convert_length(wavelength_stop, units, "m")

        self._set("minimum wavelength", start)
        self._set("maximum wavelength", stop)

    def set_frequency_points(self, points: int) -> None:
        """
        Sets the number of frequency points for the monitor.

        This method should only be called if the override global monitor settings are enabled.

        Args:
            points (int): The number of frequency points at which to record data.
        """
        self._override()
        validation.integer_in_range(points, "points", (1, float('inf')))
        self._set("frequency points", points)


class General(Base):

    def _override(self) -> None:
        if not self._get("override global monitor settings", bool):
            self._set("override global monitor settings", True)

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

        validation.in_literal(simulation_type, "simulation_type", SIMULATION_TYPE)
        self._set("simulation type", simulation_type)

    def override_global_monitor_settings(self, override: bool) -> None:
        """
        Enables or disables the override of global monitor settings.

        If enabled, the user can specify the frequency range and number of points for recording
        frequency-domain information. If disabled, the settings will default to global monitor settings.

        Args:
            override (bool): A flag indicating whether to override global monitor settings.
        """

        self._set("override global monitor settings", override)


class GlobalMonitor(Base):

    _parent_object: SimulationInterface

    def _override(self) -> None:
        ...

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
        validation.number_in_range(min_sampling, "min_sampling", (2, float('inf')))

        # Set the minimum sampling per cycle
        self._set("min sampling per cycle", min_sampling)

    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        """Queries the Lumerical FDTD Api to fetch the value of a parameter attributed to the  global source."""
        try:
            value = self._parent_object._lumapi().getglobalmonitor(parameter)
            return process_type(value, parameter_type)

        except LumApiError as e:
            message = str(e)
            if "in getglobalmonitor, the requested property" in message:
                raise ValueError(f"Cannot find parameter '{parameter}' attributed to the global monitor. "
                                 f"Either the parameter is not one of the object's parameters, or the parameter is "
                                 f"inactive.")
            raise e

    def _set(self, parameter: str, value: T) -> T:
        """
        Uses the Lumerical FDTD API to assign a value to a parameter attributing to the object.
        Returns the accepted value.
        """
        try:
            self._parent_object._lumapi().setglobalmonitor(parameter, value)

            accepted_value = self._get(parameter, type(value))

            if type(value) is np.ndarray:
                equal = np.array_equal(value, accepted_value)
            elif isinstance(value, str):
                equal = value.lower() == accepted_value.lower()
            else:
                equal = value == accepted_value

            if not equal:
                warn(f"The value of '{parameter}' set to '{value}' was automatically adjusted. "
                     f"The accepted value is '{accepted_value}'.")

            return accepted_value

        except LumApiError as e:
            message = str(e)
            if "in setglobalmonitor, the requested property" in message:
                raise ValueError(f"Cannot find parameter '{parameter}' attributed to the global monitor. "
                                 f"Either the parameter is not one of the object's parameters, or the parameter is "
                                 f"inactive.")
            raise e

    @property
    def _units(self) -> LENGTH_UNITS:
        return self._parent_object._units()