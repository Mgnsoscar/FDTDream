from typing import Type
import numpy as np
from warnings import warn
from .settings import frequency_wavelength
from ..base_classes.object_modules import T
from ..interfaces import SimulationInterface
from ..resources.functions import convert_length, process_type
from ..resources.errors import LumApiError
from ..resources.literals import LENGTH_UNITS


class GlobalSource(frequency_wavelength.FrequencyWavelengthGlobal):

    _parent_object: SimulationInterface

    def __init__(self, parent_object: SimulationInterface):
        super().__init__(parent_object)  # type: ignore

    @property
    def lambda_max(self) -> float:
        return convert_length(self._get("wavelength stop", float), "m", self._units)

    @property
    def lambda_min(self) -> float:
        return convert_length(self._get("wavelength start", float), "m", self._units)

    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        """Queries the Lumerical FDTD Api to fetch the value of a parameter attributed to the  global source."""
        try:
            value = self._parent_object._lumapi().getglobalsource(parameter)
            return process_type(value, parameter_type)

        except LumApiError as e:
            message = str(e)
            if "in getglobalsource, the requested property" in message:
                raise ValueError(f"Cannot find parameter '{parameter}' attributed to the global source. "
                                 f"Either the parameter is not one of the object's parameters, or the parameter is "
                                 f"inactive.")
            raise e

    def _set(self, parameter: str, value: T) -> T:
        """
        Uses the Lumerical FDTD API to assign a value to a parameter attributing to the object.
        Returns the accepted value.
        """
        try:
            self._parent_object._lumapi().setglobalsource(parameter, value)

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
            if "in setglobalsource, the requested property" in message:
                raise ValueError(f"Cannot find parameter '{parameter}' attributed tothe global source. "
                                 f"Either the parameter is not one of the object's parameters, or the parameter is "
                                 f"inactive.")
            raise e

    @property
    def _units(self) -> LENGTH_UNITS:
        return self._parent_object._units()