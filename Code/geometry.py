from __future__ import annotations

# Standard library imports
from typing import TypedDict, Union, Optional, get_args

# Third-party imports

# Local imports
from lumapi_import import lumapi
from base_classes import SettingTab
from local_resources import convert_length, Validate, DECIMALS
from type_hint_resources import AXES, LENGTH_UNITS


########################################################################################################################
#                                               GEOMETRY CLASSES
########################################################################################################################


class GeometryBase(SettingTab):

    class _SettingsDict(TypedDict):
        x: float
        y: float
        z: float
        use_relative_coordinates: float

    # Declare slots
    __slots__ = SettingTab.__slots__

    def set_relative_coordinates(self, true_or_false: bool) -> None:
        """
        Sets the 'use relative coordinates' parameter in the FDTD simulation.

        Parameters:
        -----------
        true_or_false : bool
            If True, the object's 'use relative coordinates' parameter is enabled, else it's disabled.
        """
        self._set_parameter("use relative coordinates", true_or_false, "bool")

    def set_position(self, x: Optional[Union[int, float]] = None, y: Optional[Union[int, float]] = None,
                     z: Optional[Union[int, float]] = None, units: LENGTH_UNITS = None) -> None:
        """Set the position of the simulation object.

        Args:
            x (Optional[Union[int, float]]): The x-coordinate position (default: None).
            y (Optional[Union[int, float]]): The y-coordinate position (default: None).
            z (Optional[Union[int, float]]): The z-coordinate position (default: None).
            units (units_literal_m, optional): The units for the position (default: simulation's global units).
        """

        # Assign the simulation's global units if None are provided
        if units is None:
            units = self._simulation.global_units
        else:
            # Validate inputs (x, y, and z are validated in the setters of the Geometry module)
            Validate.in_literal(units, "units", LENGTH_UNITS)

        values = [x, y, z]
        for axis, value in zip(get_args(AXES), values):
            if value is not None:
                value = convert_length(value=value, from_unit=units, to_unit="m")
                self._set_parameter(axis, value, "float")

    def get_currently_active_simulation_parameters(self) -> GeometryBase._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        settings.update({
            "x": self._get_parameter("x", "float"),
            "y": self._get_parameter("y", "float"),
            "z": self._get_parameter("z", "float"),
            "use_relative_coordinates": self._get_parameter("use relative coordinates", "bool")
        })
        return settings


class CartesianGeometry(GeometryBase):

    class _SettingsDict(GeometryBase._SettingsDict):
        x_span: float
        y_span: float
        z_span: float

    # Declare slots
    __slots__ = GeometryBase.__slots__

    def set_spans(self, x_span: Optional[Union[int, float]] = None, y_span: Optional[Union[int, float]] = None,
                  z_span: Optional[Union[int, float]] = None, units: LENGTH_UNITS = None) -> None:
        """Set the spans of the simulation object.

        Args:
            x_span (Optional[Union[int, float]]): The span in the x-direction (default: None).
            y_span (Optional[Union[int, float]]): The span in the y-direction (default: None).
            z_span (Optional[Union[int, float]]): The span in the z-direction (default: None).
            units (units_literal_m, optional): The units for the spans (default: simulation's global units).
        """
        # Assign the simulation's global units if None are provided
        if units is None:
            units = self._simulation.global_units
        else:
            # Validate inputs (x, y, and z are validated in the setters of the Geometry module)
            Validate.in_literal(units, "units", LENGTH_UNITS)

        values = [x_span, y_span, z_span]
        for axis, value in zip(get_args(AXES), values):
            if value is not None:
                value = convert_length(value=value, from_unit=units, to_unit="m")
                self._set_parameter(f"{axis} span", value, "float")

    def get_currently_active_simulation_parameters(self) -> CartesianGeometry._SettingsDict:

        # Initialize dictionary with all values None
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(super().get_currently_active_simulation_parameters())
        settings.update({
            "x_span": self._get_parameter("x span", "float"),
            "y_span": self._get_parameter("y span", "float"),
            "z_span": self._get_parameter("z span", "float")
        })
        return settings


class Rotations(SettingTab):

    class _SettingsDict(TypedDict):
        first_axis: AXES
        second_axis: AXES
        third_axis: AXES
        rotation_1: float
        rotation_2: float
        rotation_3: float

    # Declare slots
    __slots__ = SettingTab.__slots__

    def set_first_axis(self, axis: AXES) -> None:
        """Set the first rotation axis.

        Args:
            axis (x, y, or z): The axis for the first rotation.
        """
        self._set_parameter("first axis", axis, "str")

    def set_second_axis(self, axis: AXES) -> None:
        """Set the second rotation axis.

        Args:
            axis (x, y, or z): The axis for the second rotation.
        """
        self._set_parameter("second axis", axis, "str")

    def set_third_axis(self, axis: AXES) -> None:
        """Set the third rotation axis.

        Args:
            axis (x, y, or z): The axis for the third rotation.
        """
        self._set_parameter("third axis", axis, "str")

    def set_first_axis_rotation(self, rotation_degrees: float) -> None:
        """Set the counter-clockwise rotation angle for the first axis.

        Args:
            rotation_degrees (float): The rotation angle in degrees for the first axis.
        """
        self._set_parameter("rotation 1", rotation_degrees, "float")

    def set_second_axis_rotation(self, rotation_degrees: float) -> None:
        """Set the counter-clockwise rotation angle for the second axis.

        Args:
            rotation_degrees (float): The rotation angle in degrees for the second axis.
        """
        self._set_parameter("rotation 2", rotation_degrees, "float")

    def set_third_axis_rotation(self, rotation_degrees: float) -> None:
        """Set the counter-clockwise rotation angle for the third axis.

        Args:
            rotation_degrees (float): The rotation angle in degrees for the third axis.
        """
        self._set_parameter("rotation 3", rotation_degrees, "float")

    def get_currently_active_simulation_parameters(self) -> Rotations._SettingsDict:

        # Initialize the dictionary with all values set to None
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        # Retrieve axis and rotation parameters
        first_axis = self._get_parameter("first axis", "str")
        first_rotation = self._get_parameter("rotation 1", "float")
        second_axis = self._get_parameter("second axis", "str")
        second_rotation = self._get_parameter("rotation 2", "float")
        third_axis = self._get_parameter("third axis", "str")
        third_rotation = self._get_parameter("rotation 3", "float")

        # Step 1: Set to "none" if the rotation is zero or the axis is "none"
        if first_axis == "none" or first_rotation == 0:
            first_axis, first_rotation = "none", None
        if second_axis == "none" or second_rotation == 0:
            second_axis, second_rotation = "none", None
        if third_axis == "none" or third_rotation == 0:
            third_axis, third_rotation = "none", None

        # Step 2: Consolidate rotations to fill the first, second, and third slots sequentially
        rotation_slots = [
            (first_axis, first_rotation),
            (second_axis, second_rotation),
            (third_axis, third_rotation)
        ]

        active_rotations = [(axis, rotation) for axis, rotation in rotation_slots if axis != "none"]
        int_to_str_map = {1: "first", 2: "second", 3: "third"}

        # Fill settings with active rotations in order
        for i, (axis, rotation) in enumerate(active_rotations):
            settings[f"{int_to_str_map[i + 1]}_axis"] = axis
            settings[f"rotation_{i + 1}"] = rotation

        return settings

