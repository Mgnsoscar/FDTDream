
import os
import random
import re
import string
from typing import Union, Any, Tuple, get_args, Optional

import numpy as np
from scipy import constants
from scipy.spatial.transform import Rotation as R

from .literals import (AXES)
from .materials_literal import Materials

########################################################################################################################
#                                             CONSTANTS AND LITERALS
########################################################################################################################

UNIT_TO_METERS = {"m": 1, "cm": 1e-2, "mm": 1e-3, "um": 1e-6, "nm": 1e-9, "angstrom": 1e-10, "pm": 1e-12, "fm": 1e-15}
METERS_TO_UNIT = {"m": 1, "cm": 1e2, "mm": 1e3, "um": 1e6, "nm": 1e9, "angstrom": 1e10, "pm": 1e12, "fm": 1e15}
UNIT_TO_SECONDS = {"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12, "fs": 1e-15}
SECONDS_TO_UNIT = {"s": 1, "ms": 1e3, "us": 1e6, "ns": 1e9, "ps": 1e12, "fs": 1e15}
UNIT_TO_HERTZ = {"Hz": 1, "KHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12, "PHz": 1e15}
HERTZ_TO_UNIT = {"Hz": 1, "KHz": 1e-3, "MHz": 1e-6, "GHz": 1e-9, "THz": 1e-12, "PHz": 1e-15}
DECIMALS = 16  # Number of decimal points to round all floats to.


########################################################################################################################
#                                               HELPER FUNCTIONS
########################################################################################################################


def reverse_dict_order(dictionary: dict, reverse_nested_dicts: bool) -> dict:
    keys = []
    values = []
    for k, v in dictionary.items():
        keys.append(k)
        if isinstance(v, dict):
            v = reverse_dict_order(v, reverse_nested_dicts)
        values.append(v)
    keys.reverse()
    values.reverse()
    reversed_dict = {k: v for k, v in zip(keys, values)}
    return reversed_dict


def generate_random_hash(length=32):
    characters = string.ascii_letters + string.digits  # Alphanumeric characters
    return ''.join(random.choices(characters, k=length))


def has_different_objects(lst):
    seen = set()
    for obj in lst:
        # Use the object's current parameters as the hashable key
        key = tuple(sorted(obj.as_dict().items()))  # Create a hashable tuple from parameters
        if key in seen:
            return True
        seen.add(key)
    return False


def euler_to_axis_angle(first_axis: AXES = None, second_axis: AXES = None, third_axis: AXES = None,
                        rotation_1: float = None, rotation_2: float = None, rotation_3: float = None
                        ) -> Tuple[Optional[np.ndarray], Optional[float]]:
    axes = [first_axis, second_axis, third_axis]
    input_rotations = [rotation_1, rotation_2, rotation_3]
    rotations = []
    axes_str = ""
    for axis, rotation in zip(axes, input_rotations):
        if (axis is not None and axis != "none") and (rotation is not None and rotation != 0):
            Validate.in_literal(axis, "axis", AXES)
            axes_str += axis
            rotations.append(rotation)

    # Check for the number of defined axes
    if len(axes) == 0:
        return None, None

    if axes_str == "":
        return None, None
    else:
        # Convert to axis-angle using only defined axes and rotations
        rotation = R.from_euler(axes_str, rotations, degrees=True)
        rot_vec = rotation.as_rotvec(degrees=True)
        magnitude = float(np.round(np.linalg.norm(rot_vec), decimals=8))
        normalized = rot_vec / magnitude
        axis, angle = normalized, magnitude

        return axis, angle


def get_unique_name(name: str, used_names: list[str], last_checked: int = 1) -> str:
    if name in used_names:

        no_suffix_name, suffix = ends_with_number(name)
        same_names = [same_name for same_name in used_names if same_name.startswith(name)]

        if suffix:
            used_suffixes = set(ends_with_number(used_name)[1] for used_name in same_names)
            while last_checked in used_suffixes:
                last_checked += 1
            name = no_suffix_name + str(last_checked)
        else:
            name += "1"

        if name in used_names:
            name = get_unique_name(name, used_names, last_checked)

    return name


def get_absolute_directory_path(file_path: str) -> str:
    """
    Checks if the directory of the given file path exists and returns the absolute path.
    If the directory does not exist, raises a FileNotFoundError.

    Parameters:
    -----------
    file_path : str
        The file path for which to check the directory.

    Returns:
    --------
    str
        The absolute path to the directory.

    Raises:
    -------
    FileNotFoundError
        If the directory of the given file path does not exist.
    """
    directory = os.path.dirname(file_path)
    # Check if the directory exists
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"The directory '{directory}' does not exist.")

    # Return the absolute path to the directory
    return os.path.abspath(directory)


def snake_to_camel(snake_str):
    # Split the string by underscores and capitalize the first letter of each word
    components = snake_str.split('_')
    # Capitalize each component and join them
    return ''.join(word.capitalize() for word in components)


def camel_to_snake(name):
    # Insert underscores between lowercase and uppercase letters
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Handle cases where there are consecutive uppercase letters
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def ends_with_number(s) -> Tuple[str, Union[int, None]]:
    """
    Splits a string into its main part and the trailing number, if present.

    This function checks if a string ends with a sequence of digits. If it does,
    it returns a tuple containing:
    - The original string without the trailing number.
    - The trailing number as an integer.

    If the string does not end with a number, it returns the original string and None.

    Parameters
    ----------
    s : str
        The input string to be split.

    Returns
    -------
    tuple
        A tuple (main_str, trailing_number) where:
        - main_str : str
            The portion of the string without the trailing number.
        - trailing_number : int or None
            The trailing number as an integer if found, or None if no trailing number is present.
    """

    match = re.search(r'(\d+)$', s)
    if match:
        # Separate the part without the number and the trailing number itself
        main_str = s[:match.start()]
        trailing_number = int(match.group(1))  # Convert to integer if needed
        return main_str, trailing_number
    return s, None  # If no trailing number, return the original string and None


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
        valid_materials = get_args(Materials)
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
        literal_vals = [arg.lower() for arg in get_args(literal)]
        if argument.lower() not in literal_vals:
            raise ValueError(
                f"Invalid value for '{argument_name}': '{argument}'. "
                f"Expected one of: {literal_vals}."
            )

    @staticmethod
    def in_list(argument: Any, argument_name: str, list_: list) -> None:
        if argument not in list_:
            raise ValueError(
                f"Invalid value for '{argument_name}': '{argument}'. "
                f"Expected one of: {list_}."
            )
