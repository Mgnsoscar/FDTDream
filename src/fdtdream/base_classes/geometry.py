from typing import TypedDict, Unpack, Any, Union, Tuple, Optional

import numpy as np

from ..interfaces import SimulationObjectInterface
from ..resources import validation
from ..resources.functions import convert_length
from ..base_classes.object_modules import Module


class BaseGeometry(Module):
    """
    Module containing the most universal Geometry settings. Some types of simulation objects can have this module
    directly assigned, although many must have it tailored.

    When creating subclasses of this module for tailoring, the `_Dimensions` nested class should be redefined as a new
    `TypedDict` containing the key-value pairs associated with the dimensions that define the geometry of the
    object type in question.

    Example:

    ....class RectangleGeometry(BaseGeometry):
    ........class _Dimensions(TypedDict, total=False):
    ............x_span: float
    ............y_span: float
    ............z_span: float
    """

    class _Dimensions(TypedDict, total=False):
        kwargs: Any

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:
        """
        Sets the dimensions of the object.

        Args:
            **kwargs: Possible key-value pairs are fetched from the _Dimensions nested class.

        Returns:
            None

        """
        for k, v in kwargs.items():
            if v is None:
                continue
            validation.positive_number(v, k)
            self._set(k.replace("_", " "), convert_length(v, self._units, "m"))

    def set_position(self, x: float = None, y: float = None, z: float = None) -> None:
        """
        Sets the position of the object. If no coordinate is provided for an axis, it remains unchanged.

        Args:
            x (float): The new x coordinate.
            y (float): The new y coordinate.
            z (float): The new z coordinate.

        Returns:
            None

        """
        kwargs = {"x": x, "y": y, "z": z}
        for k, v in kwargs.items():
            if v is None:
                continue
            validation.number(v, k)
            self._set(k, convert_length(v, self._units, "m"))

    def set_position_cylindrically(self, origin: Union[Tuple[float, float], SimulationObjectInterface],
                                   theta: float, radius: float, z_offset: Optional[float] = None) -> None:
        """
        Sets the new position of the object by cylindrical coordinates with origin in the specified point.

        Parameters:
            origin (Tuple[float, float] | TSimulationObject): Can either be a 2D tuple with the x and y coordinate, or
                a simulation object. If the latter, the object's center coordinate will be used as the origin.
            theta (float): The counterclockwise angle from the positive x-axis in degrees.
            radius (float): The radial displacement from the origin.
            z_offset (Optional[float]): The displacement along the z-axis. If None is provided, it defaults to 0.
        """
        # Extract origin coordinates
        if isinstance(origin, SimulationObjectInterface):
            origin_x, origin_y = origin.x, origin.y
        else:
            origin_x, origin_y = origin

        # Convert theta to radians and calculate new position
        theta_rad = np.deg2rad(theta)
        displacement = radius * np.array([np.cos(theta_rad), np.sin(theta_rad)])

        x = float(origin_x + displacement[0])
        y = float(origin_y + displacement[1])
        z_offset = convert_length(self._get("z", float), "m", self._units) + z_offset if z_offset is not None else None
        self.set_position(x=x, y=y, z=z_offset)

    def set_position_spherically(self, origin: Union[Tuple[float, float, float], SimulationObjectInterface],
                                 radius: float, theta: float, phi: float) -> None:
        """
        Sets the new position of the object by spherical coordinates with origin in the specified point.

        Parameters:
            origin (Tuple[float, float, float] | TSimulationObject): Can either be a 3D tuple with the x, y, and z
                coordinates or a simulation object. If the latter, the object's center coordinate will be used as the
                origin.
            radius (float): The radial distance from the origin.
            theta (float): The counterclockwise angle from the positive x-axis in the xy-plane in degrees.
            phi (float): The angle from the positive z-axis in degrees.
        """

        # Extract origin coordinates
        if isinstance(origin, SimulationObjectInterface):
            origin_x, origin_y, origin_z = origin.x, origin.y, origin.z
        else:
            origin_x, origin_y, origin_z = origin

        # Convert theta and phi to radians
        theta_rad = np.deg2rad(theta)
        phi_rad = np.deg2rad(phi)

        # Calculate new position using spherical coordinate formulas
        x_displacement = radius * np.sin(phi_rad) * np.cos(theta_rad)
        y_displacement = radius * np.sin(phi_rad) * np.sin(theta_rad)
        z_displacement = radius * np.cos(phi_rad)

        x = origin_x + x_displacement
        y = origin_y + y_displacement
        z = origin_z + z_displacement
        self.set_position(x=x, y=y, z=z)
