# Standard library imports
from typing import Union, Any, Tuple, get_args
import numpy as np

# Local imports
from type_hint_resources import LENGTH_UNITS, FREQUENCY_UNITS, TIME_UNITS, MATERIALS, AXES
from scipy import constants

########################################################################################################################
#                                             CONSTANTS AND LITERALS
########################################################################################################################

UNIT_TO_METERS = {"m": 1, "mm": 1e-3, "um": 1e-6, "nm": 1e-9, "angstrom": 1e-10, "pm": 1e-12, "fm": 1e-15}
METERS_TO_UNIT = {"m": 1, "mm": 1e3, "um": 1e6, "nm": 1e9, "angstrom": 1e10, "pm": 1e12, "fm": 1e15}
UNIT_TO_SECONDS = {"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12, "fs": 1e-15}
SECONDS_TO_UNIT = {"s": 1, "ms": 1e3, "us": 1e6, "ns": 1e9, "ps": 1e12, "fs": 1e15}
UNIT_TO_HERTZ = {"Hz": 1, "KHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12, "PHz": 1e15}
HERTZ_TO_UNIT = {"Hz": 1, "KHz": 1e-3, "MHz": 1e-6, "GHz": 1e-9, "THz": 1e-12, "PHz": 1e-15}
DECIMALS = 16  # Number of decimal points to round all floats to.

########################################################################################################################
#                                               HELPER FUNCTIONS
########################################################################################################################


def wavelength_to_frequency(wavelength_meters):
    """
    Convert wavelength in meters to frequency in Hertz.

    Parameters:
    wavelength_meters (float): Wavelength in meters.

    Returns:
    float: Frequency in Hertz.
    """
    speed_of_light = constants.c  # Speed of light in m/s
    return speed_of_light / wavelength_meters


def frequency_to_wavelength(frequency_hz):
    """
    Convert frequency in Hertz to wavelength in meters.

    Parameters:
    frequency_hz (float): Frequency in Hertz.

    Returns:
    float: Wavelength in meters.
    """
    speed_of_light = constants.c  # Speed of light in m/s
    return speed_of_light / frequency_hz


def convert_frequency(value: Union[int, float], from_unit: FREQUENCY_UNITS, to_unit: FREQUENCY_UNITS) -> float:
    # Validate correct input arguments
    Validate.number(value, "value")
    Validate.in_literal(from_unit, "from_unit", FREQUENCY_UNITS)
    Validate.in_literal(to_unit, "to_unit", FREQUENCY_UNITS)

    # Convert units and return
    hertz = value * UNIT_TO_HERTZ[from_unit]
    new_unit = np.round(hertz * HERTZ_TO_UNIT[to_unit], decimals=DECIMALS)

    return float(new_unit)


def convert_length(value: Union[int, float], from_unit: LENGTH_UNITS, to_unit: LENGTH_UNITS) -> float:
    # Validate correct input arguments
    Validate.number(value, "value")
    Validate.in_literal(from_unit, "from_unit", LENGTH_UNITS)
    Validate.in_literal(to_unit, "to_unit", LENGTH_UNITS)

    # Convert units and return
    meters = value * UNIT_TO_METERS[from_unit]
    new_unit = np.round(meters * METERS_TO_UNIT[to_unit], decimals=DECIMALS)
    return float(new_unit)


def convert_time(value: Union[int, float], from_unit: TIME_UNITS, to_unit: TIME_UNITS) -> float:
    # Validate correct input arguments
    Validate.number(value, "value")
    Validate.in_literal(from_unit, "from_unit", TIME_UNITS)
    Validate.in_literal(to_unit, "to_unit", TIME_UNITS)

    # Perform the conversion and return
    seconds = value * UNIT_TO_SECONDS[from_unit]
    new_unit = np.round(seconds * SECONDS_TO_UNIT[to_unit], decimals=DECIMALS)
    return float(new_unit)


########################################################################################################################
#                      ARGUMENT VALIDATION CLASS WITH REUSABLE VALIDATION METHODS FOR INPUT ARGUMENTS
########################################################################################################################

class Validate:

    @staticmethod
    def boolean(argument: Any, argument_name: str):
        if not isinstance(argument, bool):
            raise AttributeError(
                f"The '{argument_name}' parameter provided must be of type 'bool', got '{type(argument)}'."
            )

    @staticmethod
    def material(argument: Any, argument_name: str) -> None:
        valid_materials = get_args(MATERIALS)
        if argument not in valid_materials:
            raise AttributeError(
                f"The parameter '{argument_name}' is not allowed. Got '{argument}'. "
                f"Allowed values: {valid_materials}."
            )

    @staticmethod
    def string(argument: any, argument_name: str) -> None:
        if not isinstance(argument, str):
            raise AttributeError(
                f"The parameter '{argument_name}' provided ust be of type 'str', not {type(argument)}"
            )

    @staticmethod
    def axis(axis: Any) -> None:
        valid_axes = get_args(AXES)
        if axis not in valid_axes:
            raise AttributeError(
                f"The parameter 'axis' provided must be one of '{valid_axes}', not '{axis}'."
            )

    @staticmethod
    def integer(argument: Any, argument_name: str) -> None:
        if not isinstance(argument, int):
            raise ValueError(f"'{argument_name}' must be a number of type 'int', got {argument}.")

    @staticmethod
    def positive_integer(argument: Any, argument_name: str) -> None:
        # Validate the argument (must be non-negative)
        Validate.integer(argument, argument_name)
        if argument < 0:
            raise ValueError(f"'{argument_name}' must be a non-negative integer, got {argument}.")

    @staticmethod
    def integer_in_range(
            argument: Any, argument_name: str, range_: Tuple[Union[int, float], Union[int, float]]) -> None:
        Validate.integer(argument, argument)
        if range_[0] > argument > range_[1]:
            raise ValueError(
                f"The parameter '{argument_name}' must have integer values between and "
                f"including {range_[0]}, {range_[1]}, not {argument}"
            )

    @staticmethod
    def number(argument: Any, argument_name: str) -> None:
        # Validate the argument (must be non-negative)
        if not isinstance(argument, (int, float)):
            raise ValueError(f"'{argument_name}' must be a number of type 'int' or 'float', got {argument}.")

    @staticmethod
    def positive_number(argument: Any, argument_name: str) -> None:
        # Validate the argument (must be non-negative)
        Validate.number(argument, argument_name)
        if argument < 0:
            raise ValueError(f"'{argument_name}' must be a non-negative number, got {argument}.")

    @staticmethod
    def number_in_range(argument: Any, argument_name: str, range_: Tuple[float, float]) -> None:
        Validate.number(argument, argument_name)
        if range_[0] > argument > range_[1]:
            raise ValueError(
                f"The parameter '{argument_name}' must have values between and including {range_[0]}, {range_[1]}, "
                f"not {argument}"
            )

    @staticmethod
    def in_literal(argument: Any, argument_name: str, literal) -> None:
        literal_vals = get_args(literal)
        if argument not in literal_vals:
            raise ValueError(
                f"Invalid value for '{argument_name}': '{argument}'. "
                f"Expected one of: {literal_vals}."
            )
