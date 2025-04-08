from typing import Any, get_args, Tuple, Union
from .literals import AXES
from .materials_literal import Materials


def boolean(argument: Any, argument_name: str):
    if not isinstance(argument, bool):
        raise AttributeError(
            f"The '{argument_name}' parameter provided must be of type 'bool', got '{type(argument)}'."
        )


def material(argument: Any, argument_name: str) -> None:
    valid_materials = get_args(Materials)
    if argument not in valid_materials:
        raise AttributeError(
            f"The parameter '{argument_name}' is not allowed. Got '{argument}'. "
            f"Allowed values: {valid_materials}."
        )


def string(argument: any, argument_name: str) -> None:
    if not isinstance(argument, str):
        raise AttributeError(
            f"The parameter '{argument_name}' provided ust be of type 'str', not {type(argument)}"
        )


def axis(ax: Any) -> None:
    valid_axes = get_args(AXES)
    if ax not in valid_axes:
        raise AttributeError(
            f"The parameter 'axis' provided must be one of '{valid_axes}', not '{ax}'."
        )


def integer(argument: Any, argument_name: str) -> None:
    if not isinstance(argument, int):
        raise ValueError(f"'{argument_name}' must be a number of type 'int', got {argument}.")


def positive_integer(argument: Any, argument_name: str) -> None:
    integer(argument, argument_name)
    if argument < 0:
        raise ValueError(f"'{argument_name}' must be a non-negative integer, got {argument}.")


def integer_in_range(
        argument: Any, argument_name: str, range_: Tuple[Union[int, float], Union[int, float]]) -> None:
    integer(argument, argument)
    if range_[0] > argument > range_[1]:
        raise ValueError(
            f"The parameter '{argument_name}' must have integer values between and "
            f"including {range_[0]}, {range_[1]}, not {argument}"
        )


def number(argument: Any, argument_name: str) -> None:
    # Validate the argument (must be non-negative)
    if not isinstance(argument, (int, float)):
        raise ValueError(f"'{argument_name}' must be a number of type 'int' or 'float', got {argument}.")


def positive_number(argument: Any, argument_name: str) -> None:
    # Validate the argument (must be non-negative)
    number(argument, argument_name)
    if argument < 0:
        raise ValueError(f"'{argument_name}' must be a non-negative number, got {argument}.")


def number_in_range(argument: Any, argument_name: str, range_: Tuple[float, float]) -> None:
    number(argument, argument_name)
    if range_[0] > argument > range_[1]:
        raise ValueError(
            f"The parameter '{argument_name}' must have values between and including {range_[0]}, {range_[1]}, "
            f"not {argument}"
        )


def in_literal(argument: Any, argument_name: str, literal) -> None:
    literal_vals = [arg.lower() for arg in get_args(literal)]
    if argument.lower() not in literal_vals:
        raise ValueError(
            f"Invalid value for '{argument_name}': '{argument}'. "
            f"Expected one of: {literal_vals}."
        )


def in_list(element: str, list_: list) -> None:
    if element not in list_:
        raise ValueError(f"Invalid element '{element}'. Expected one of: {list_}.")
