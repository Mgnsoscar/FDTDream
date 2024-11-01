from __future__ import annotations

# Standard library imports
from typing import Unpack, TypedDict, List, Tuple

# Third-party imports
from lumapi_import import lumapi
import numpy as np
from scipy.spatial.transform import Rotation as R

# Local imports
from base_classes import SimulationObjectBase
from geometry import CartesianGeometry, Rotations
from local_resources import convert_length


########################################################################################################################
#                                             SIMULATION OBJECT CLASS
########################################################################################################################

class SimulationObject(SimulationObjectBase):
    """Class representing a simulation object with associated settings."""

    class _Kwargs(TypedDict, total=False):
        x: float
        y: float
        z: float

    # Helper lists for easy initialization
    _settings = [CartesianGeometry]
    _settings_names = ["geometry_settings"]

    # Declare variables
    geometry_settings: CartesianGeometry

    __slots__ = SimulationObjectBase.__slots__ + _settings_names

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[SimulationObject._Kwargs]) -> None:
        super().__init__(name, simulation)
        # Set the geometry based on the keyword arguments
        self._apply_kwargs(kwargs)

    def _apply_kwargs(self, kwargs: dict) -> None:
        for key, arg in kwargs.items():
            # Check if the key is a method or variable in the main class
            if hasattr(self, key):
                if callable(getattr(self, key)):
                    method = getattr(self, key)
                    method(arg)
                else:
                    setattr(self, key, arg)
            elif hasattr(self, f"set_{key}") and callable(getattr(self, f"set_{key}")):
                method = getattr(self, f"set_{key}")
                method(arg)
            else:
                # Check each subclass for the key
                for subclass_name in self._settings_names:
                    subclass = getattr(self, subclass_name)
                    if hasattr(subclass, key):
                        if callable(getattr(subclass, key)):
                            method = getattr(subclass, key)
                            method(arg)
                        else:
                            setattr(subclass, key, arg)
                        break
                    elif hasattr(subclass, f"set_{key}") and callable(getattr(subclass, f"set_{key}")):
                        method = getattr(subclass, f"set_{key}")
                        method(arg)


class RotateableSimulationObject(SimulationObject):

    _settings = SimulationObject._settings + [Rotations]
    _settings_names = SimulationObject._settings_names + ["rotations_settings"]

    # Declare variables
    rotations_settings: Rotations

    def _get_corners(self) -> List[Tuple[float, float, float]]:
        pass

    def _get_bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate the bounding box of a structure after rotations in a specified order.

        Args:
            corners (np.ndarray): Array of corner points of the structure in its local space (shape: [8, 3]).
            axis_angles_ordered (list of tuples): Ordered list of (axis, angle) for each rotation.

        Returns:
            tuple: (min_coords, max_coords), bounding box coordinates after rotations.
        """
        rotated_corners = self._get_corners()
        axis_to_array = {"x": np.array([1, 0, 0]), "y": np.array([0, 1, 0]), "z": np.array([0, 0, 1]), "none": None}
        axes = [axis_to_array[self._get_parameter(f"{nr} axis", "str")]
                for nr in ["first", "second", "third"]]
        angles = [self._get_parameter(f"rotation {i + 1}", "float") for i in range(3)]

        # Initial 0 degree rotation
        rotation = R.from_rotvec(0 * axis_to_array["x"])
        rotated_corners = rotation.apply(rotated_corners)

        for axis, angle in zip(axes, angles):
            if not isinstance(axis, np.ndarray):
                continue
            rotation = R.from_rotvec(np.radians(angle) * axis)
            rotated_corners = rotation.apply(rotated_corners)

        min_coords = rotated_corners.min(axis=0)
        max_coords = rotated_corners.max(axis=0)
        return min_coords, max_coords

    @property
    def x_max(self) -> float:
        return convert_length(float(self._get_bounding_box()[1][0]), "m", self._simulation.global_units)

    @property
    def x_min(self) -> float:
        return convert_length(float(self._get_bounding_box()[0][0]), "m", self._simulation.global_units)

    @property
    def y_max(self) -> float:
        return convert_length(float(self._get_bounding_box()[1][1]), "m", self._simulation.global_units)

    @property
    def y_min(self) -> float:
        return convert_length(float(self._get_bounding_box()[0][1]), "m", self._simulation.global_units)

    @property
    def z_max(self) -> float:
        return convert_length(float(self._get_bounding_box()[1][2]), "m", self._simulation.global_units)

    @property
    def z_min(self) -> float:
        return convert_length(float(self._get_bounding_box()[0][2]), "m", self._simulation.global_units)


