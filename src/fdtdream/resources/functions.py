from typing import (Any, Type, TypeVar, Union, Tuple, TypedDict)

import numpy as np
from numpy import ndarray, bool
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation as R
import re

from . import validation as Validate
from .constants import DECIMALS
from .constants import (UNIT_TO_HERTZ, HERTZ_TO_UNIT, UNIT_TO_METERS, METERS_TO_UNIT,
                        UNIT_TO_SECONDS, SECONDS_TO_UNIT)
from .literals import (FREQUENCY_UNITS, LENGTH_UNITS, TIME_UNITS)


# region Type variables
T = TypeVar("T")


# endregion


# region Misc

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


def process_type(value: Any, parameter_type: Type[T]) -> T:
    """Makes sure the provided value is processed appropriately as the provided type."""

    if parameter_type is float:
        return float(np.round(float(value), decimals=DECIMALS))
    elif parameter_type is int:
        return int(value)
    elif parameter_type is bool:
        return bool(value)
    elif parameter_type is list:
        return list(value)
    elif parameter_type is ndarray:
        return np.asarray(value)
    else:
        return value


def filter_None_from_dict(dictionary: dict) -> dict:
    new_dict = {}
    for k, v in dictionary.items():
        if v:
            new_dict[k] = v
    return new_dict

# endregion Misc


# region Conversions

def convert_frequency(value: float, from_unit: FREQUENCY_UNITS, to_unit: FREQUENCY_UNITS) -> float:
    """ Converts a frequency value from one scale unit to another"""
    hertz = value * UNIT_TO_HERTZ[from_unit]
    new_unit = np.round(hertz * HERTZ_TO_UNIT[to_unit], decimals=DECIMALS)
    return float(new_unit)


def convert_length(value: Union[float, np.ndarray, np.floating], from_unit: LENGTH_UNITS | Any,
                   to_unit: LENGTH_UNITS | Any,
                   power: int = 1) -> float | np.ndarray | np.floating:
    Validate.in_literal(from_unit, "from_unit", LENGTH_UNITS)
    Validate.in_literal(to_unit, "to_unit", LENGTH_UNITS)
    meters = value * UNIT_TO_METERS[from_unit]
    new_unit = np.round(meters * METERS_TO_UNIT[to_unit], decimals=DECIMALS)
    if not isinstance(value, np.ndarray):
        new_unit = float(new_unit)
    return new_unit


def convert_time(value: Union[int, float], from_unit: TIME_UNITS, to_unit: TIME_UNITS) -> float:
    # Validate correct input arguments
    Validate.number(value, "value")
    Validate.in_literal(from_unit, "from_unit", TIME_UNITS)
    Validate.in_literal(to_unit, "to_unit", TIME_UNITS)

    # Perform the conversion and return
    seconds = value * UNIT_TO_SECONDS[from_unit]
    new_unit = np.round(seconds * SECONDS_TO_UNIT[to_unit], decimals=DECIMALS)
    return float(new_unit)

# endregion Conversions


# region Geometry

def rotate(sequence: str, rotations: NDArray[3], vector: NDArray[3], angle: float, position: NDArray[3],
           point: NDArray[3] = None) -> tuple[str, NDArray[3], NDArray[3]]:
    """
    Performs a counterclockwise rotation around the 'vector' going through the provided point.

    Arguments:
        'Sequence' (str):
            Three letter sequence of axes, ie. "xyz", or "zyx".
        'vector' (NDArray[3]):
            3D Vector which to rotate around.
        'point' (NDArray[3]):
            Coordinate the vector goes through. If None, only axes and rotations are returned.

    Returns:
        sequence (str):
            Sequence of axes to represent the new rotation state.
        rotations (Tuple[float, float, float]):
            Rotations for each axis in degrees.
        position (Tuple[float, float, flaot]):
            Position of the new rotated state.
    """
    # Normalize the provided vector
    vector = np.array(vector)
    vector /= np.linalg.vector_norm(vector)

    rotation = R.from_rotvec(np.deg2rad(angle) * vector)  # Create rotation object

    if point is not None:
        if position is None:
            raise ValueError("If a 'point' is provided, so must an original position.")
        # Translate to origin, apply rotation, and translate back
        translated_position = position - point
        position = rotation.apply(translated_position) + point

    # Apply the rotation

    current_rotation = R.from_euler(sequence, rotations, degrees=True)
    new_rotation = current_rotation * rotation  # Apply the rotation
    euler_angles = new_rotation.as_euler('xyz', degrees=True)

    # Return axes sequence, rotations, and position
    return "xyz", euler_angles, position


def axis_angle_rotation_matrix(axis, angle):
    """Generate a rotation matrix for a given axis and angle."""
    return R.from_rotvec(angle * np.array(axis)).as_matrix()


def euler_to_rotvec(axes, angles) -> Tuple[NDArray, float]:
    """Convert a sequence of axis/angle rotations to a single vector-angle rotation."""

    # Start with the identity matrix
    combined_matrix = np.eye(3)

    # Iterate over the axes and angles and accumulate the rotations
    for ax, angle in zip(axes, angles):
        if ax == 'x':
            axis = [1, 0, 0]
        elif ax == 'y':
            axis = [0, 1, 0]
        elif ax == 'z':
            axis = [0, 0, 1]
        else:
            raise ValueError(f"Expected x, y, or z, got {ax}")

        # Generate the rotation matrix and update the combined matrix
        rotation_matrix = axis_angle_rotation_matrix(axis, np.radians(angle))
        combined_matrix = np.dot(combined_matrix, rotation_matrix)

    # Extract the axis and angle from the combined rotation matrix
    rotation = R.from_matrix(combined_matrix)
    angle_out = rotation.magnitude()  # Rotation angle in radians
    axis_out = rotation.as_rotvec() / angle_out if angle_out != 0 else np.array([0, 0, 0])

    return axis_out, np.degrees(angle_out)  # Return axis and angle in degrees


def transform_position_with_rotation(pos: np.ndarray, rot_vec: np.ndarray, rot_angle_rad: float) -> np.ndarray:
    """
    Rotates a position vector `pos` around a given rotation axis `rot_vec`
    by `rot_angle_rad` radians using Rodrigues' rotation formula.

    Parameters:
    - pos (np.ndarray): The position vector (3D).
    - rot_vec (np.ndarray): The rotation axis (must be a unit vector).
    - rot_angle_rad (float): The rotation angle in radians.

    Returns:
    - np.ndarray: The rotated position vector.
    """

    # Ensure inputs are numpy arrays
    pos = np.asarray(pos, dtype=np.float64)
    rot_vec = np.asarray(rot_vec, dtype=np.float64)

    # Normalize the rotation axis (avoid division by zero)
    norm = np.linalg.norm(rot_vec)
    if norm == 0:
        return pos
    rot_vec /= norm

    # If pos is [0, 0, 0], rotation has no effect
    if np.allclose(pos, 0):
        return pos

    # Compute Rodrigues' rotation formula components
    cos_theta = np.cos(rot_angle_rad)
    sin_theta = np.sin(rot_angle_rad)

    # Compute cross product only if necessary
    cross_prod = np.cross(rot_vec, pos) if not np.allclose(rot_vec, pos / np.linalg.norm(pos)) else np.zeros(3)

    dot_prod = np.dot(rot_vec, pos)

    # Apply Rodrigues' formula
    rotated_pos = (pos * cos_theta +
                   cross_prod * sin_theta +
                   rot_vec * dot_prod * (1 - cos_theta))

    # Round to DECIMALS to avoid floating point errors (ie. numbers like 1.4234e-23)
    rounded_pos = np.round(rotated_pos, decimals=DECIMALS)

    return rounded_pos

# endregion Geometry

