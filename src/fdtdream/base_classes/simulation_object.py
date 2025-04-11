from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Any, List, TypeVar, Type, Unpack, Self, Tuple
from warnings import warn
from copy import copy as pythoncopy
from itertools import product
from scipy.spatial.transform import Rotation as R

import numpy as np
from numpy.typing import NDArray

from ..interfaces import SimulationObjectInterface, SimulationInterface, ModuleCollectionInterface
from ..resources import errors
from ..resources.functions import process_type, convert_length, transform_position_with_rotation
from ..resources.literals import LENGTH_UNITS, AXES, EXTREMITIES

T = TypeVar("T")


class SimulationObject(SimulationObjectInterface, ABC):

    # region Class Body

    # References to other objects
    _sim: SimulationInterface
    _parents: List[SimulationObject]  # Group hierarchy, starting with highest level
    _children: List[SimulationObject]  # Grouped objects (if instance is a group)

    # Instance specific variables
    _name: str
    settings: ModuleCollectionInterface

    __slots__ = ["_sim", "_parents", "_children", "_name", "settings"]

    # endregion Class Body

    # region Dev. Methods

    def __init__(self, name: str, simulation: SimulationInterface, *args, **kwargs) -> None:

        # Assign/initialize variables
        self._name = name
        self._sim = simulation
        self._parents = kwargs.get("parents", [])
        self._children = []

    def _check_name(self, name: str) -> None:
        """Checks if another object associated with the parent simulation has the same name as the input."""
        self._sim._check_name(name)

    def _get_scope(self):
        """Returns the scope of the object, including it's own name."""
        scope = "::model"
        for parent in self._parents:
            scope += f"::{parent._name}"
        scope += f"::{self._name}"
        return scope

    def _get(self, parameter: str, parameter_type: Type[T]) -> T:
        """Queries the Lumerical FDTD Api to fetch the value of a parameter attributed to the object."""
        try:
            value = self._lumapi.getnamed(self._get_scope(), parameter)
            return process_type(value, parameter_type)

        except errors.LumApiError as e:
            message = str(e)
            if "in getnamed, the requested property" in message:
                raise ValueError(f"Cannot find parameter '{parameter}' attributed to object '{self._get_scope()}'. "
                                 f"Either the parameter is not one of the object's parameters, or the parameter is "
                                 f"inactive.")
            raise e

    def _set(self, parameter: str, value: T) -> T:
        """
        Uses the Lumerical FDTD API to assign a value to a parameter attributing to the object.
        Returns the accepted value.
        """
        try:
            self._lumapi.setnamed(self._get_scope(), parameter, value)

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

        except errors.LumApiError as e:
            message = str(e)
            if "in setnamed, the requested property" in message:
                raise ValueError(f"Cannot find parameter '{parameter}' attributed to object '{self._get_scope()}'. "
                                 f"Either the parameter is not one of the object's parameters, or the parameter is "
                                 f"inactive.")
            raise e

    def _get_position(self, absolute: bool = False,
                      other_object_hierarchy: SimulationObject = None) -> NDArray[np.float64]:
        """
        Returns 3D position vector in meters.

        Args:
            absolute: If True, returns absolute position, if False returns relative to parent groups.
            other_object_hierarchy: If another object is passed, it computes the position
                in the other object's frame of reference.

        Returns:
            3-element Numpy array of type np.float64.

        """

        def get_pos(parent_obj, pos) -> Tuple[NDArray, bool]:

            # Check if the parent is an object that has a rotation. Then the rotation needs to be accounted for.
            if hasattr(parent_obj, "settings") and hasattr(getattr(parent_obj, "settings"), "rotation"):
                rot_vec, rot_angle_rad = parent_obj.settings.rotation._get_rotation_rot_vec()
                pos = transform_position_with_rotation(pos, rot_vec, rot_angle_rad)

            # Account for the position.
                pos += parent_obj._get_position(absolute=False)
            if not parent_obj._get("use relative coordinates", bool):
                return pos, True
            else:
                return pos, False

        # Method to convert absolute positions to positions in the reference frame of another object.
        def convert_reference_frame(parent_obj, pos) -> Tuple[NDArray, bool]:

            # Account for the position first. Moving the object into the reference system
            pos -= parent_obj._get_position(absolute=False)

            # Check if the parent is an object that has a rotation. Then the rotation needs to be accounted for.
            if hasattr(parent_obj, "settings") and hasattr(getattr(parent_obj, "settings"), "rotation"):
                rot_vec, rot_angle_rad = parent_obj.settings.rotation._get_rotation_rot_vec()
                pos = transform_position_with_rotation(pos, rot_vec, rot_angle_rad)

            if not parent_obj._get("use relative coordinates", bool):
                return pos, True
            else:
                return pos, False

        # Fetch the coordinates
        x, y, z = self._get("x", float), self._get("y", float), self._get("z", float)
        # Create the numpy vector
        position = np.array([x, y, z], dtype=np.float64)

        # Work out the absolute position based on the relative positions of the hierarchy above.
        if (absolute or other_object_hierarchy) and self._get("use relative coordinates", bool):
            for parent in self._parents:
                position, should_break = get_pos(parent, position)
                if should_break:
                    break

        # Now that the absolute position is computed, if another object is passed, convert the position to it's
        # coordinate system.
        if other_object_hierarchy:
            parents = other_object_hierarchy._parents
            for parent in parents:
                position, should_break = convert_reference_frame(parent, position)
                if should_break:
                    break

        return position

    def _get_bounding_box(self, absolute: bool = False) -> NDArray:
        """
        Fetches the extremal coordinates of the object's bounding box.

        Args:
            absolute: Flag deciding if the returned minimum value is in absolute or relative coordinates.

        Returns:
            Numpy array. First element is 3d vector with min coordinates, second with max coordinates.

        """
        corners = self._get_corners(absolute)

        # Extract the minimum and maximum coordinates from the corners
        min_coords = np.min(corners, axis=0)
        max_coords = np.max(corners, axis=0)

        return np.vstack((min_coords, max_coords))

    # endregion Dev. Methods

    # region User Methods

    def place_next_to(self, other_object: SimulationObject, side: EXTREMITIES,
                      offset: float = 0) -> SimulationObject.place_next_to:
        """
        Places the object next to the specified boundary of another object.

        The object will be placed so that the opposite side touches the side specified of the other object.
        The offset specifies a distance the object is moved from this possition along the specified axis.
        NB! Only the coordinate for the specified axis will be changed. If the two objects dosn't share any
        ie. x coordinates, they won't touch if you place it next to the other object's ie. y_max, but the y_max and
        y_min coordinates of the two objects will be the same.

        Args:
            other_object: The object this object will be placed next to.
            side: What side of the other object this side will be placed next to.
            offset: The distance to offset the obejct from the new position.

        Returns:
            A reference to the same method, allowing you to stack this method.
        """

        map = {"x": 0, "y": 1, "z": 2}
        #
        # # The rotation of the other object's coordinate system.
        # if hasattr(other_object.settings, "rotation"):
        #     other_rot = other_object.settings.rotation._get_coordinate_system_rotation()
        # else:
        #     other_rot = R.identity()
        #
        # # The rotation of this objtct's coordinate system
        # if hasattr(self.settings, "rotation"):
        #     this_rot = self.settings.rotation._get_coordinate_system_rotation()
        # else:
        #     this_rot = R.identity()

        # Fetch the absolute coordinate of the other object in the current object's frame of reference
        coordinate = getattr(other_object, side[2:])(side[0], absolute=True)
        position = convert_length(other_object._get_position(absolute=True)[map[side[0]]], "m", self._units)
        edge_offset = coordinate - position  # To find how far away from the position the edge is

        # Now find the edge coordinate in the correct reference frame
        position = convert_length(other_object._get_position(other_object_hierarchy=self)[map[side[0]]],
                                  "m", self._units)
        edge = position + edge_offset

        # Fetch the coordinate of the specified axis of this object
        axis_pos = self.pos[map[side[0]]]

        # Assign new coordinates
        if side[2:] == "max":
            # Fetch the min value along this axis of this object
            min = self.min(side[0])
            distance = axis_pos - min
            setattr(self, side[0], edge + distance + offset)
        else:
            max = self.max(side[0])
            distance = max - axis_pos
            setattr(self, side[0], edge - distance + offset)

        return self.place_next_to

    def _get_corners(self, absolute: bool = False) -> NDArray[np.float64]:
        """
        Calculates the object's corner coordinates.

        Args:
            absolute (bool): Flag to decide if the corner coordinates are absolute or relative to parent groups.

        Returns: A numpy array with position vectors of all the object's corners. Units in meters.

        """

        # Fetch the parameters for radius, radius_2, and z_span, and center position
        half_spans = np.array([self._get("x span", float), self._get("y span", float), self._get("z span", float)]) / 2
        position = self._get_position(absolute)

        min_pos = position - half_spans
        max_pos = position + half_spans

        corners = np.array(list(product(*zip(min_pos, max_pos))), dtype=np.float64)

        return np.unique(corners, axis=0)

    def _max_vec(self, axis: AXES, absolute: bool = False) -> NDArray:
        position = self._get_position(absolute=True)
        max_coord = convert_length(self._get(axis + " max", float), "m", self._units)
        mapping = {"x": 0, "y": 1, "z": 2}
        position[mapping[axis]] = max_coord
        return position

    def _min_vec(self, axis: AXES, absolute: bool = False) -> NDArray:
        position = self._get_position(absolute=True)
        min_coord = convert_length(self._get(axis + " min", float), "m", self._units)
        mapping = {"x": 0, "y": 1, "z": 2}
        position[mapping[axis]] = min_coord
        return position

    def max(self, axis: AXES, absolute: bool = False) -> float:
        max_coord = convert_length(self._get(axis + " max", float), "m", self._units)
        if self._get("use relative coordinates", bool) and absolute:
            for parent in self._parents:
                mapping = {"x": 0, "y": 1, "z": 2}
                max_coord += parent._get_position(absolute=False)[mapping[axis]]
        return max_coord

    def min(self, axis: AXES, absolute: bool = False) -> float:
        min_coord = convert_length(self._get(axis + " min", float), "m", self._units)
        if self._get("use relative coordinates", bool) and absolute:
            for parent in self._parents:
                mapping = {"x": 0, "y": 1, "z": 2}
                min_coord += parent._get_position(absolute=False)[mapping[axis]]
        return min_coord

    def span(self, axis: str) -> float:
        """
        Returns the distance between the min and max coordinate of the object along a specified axis.

        Args:
            axis: What axis to retireve the span along.

        Returns:
            The effective span along the specified axis.

        """
        mapping = {"x": 0, "y": 1, "z": 2}
        bbox = self._get_bounding_box()
        min_coords, max_coords = bbox
        return convert_length(max_coords[mapping[axis]] - min_coords[mapping[axis]], "m", self._units)

    # endregion User Methods

    # region Dev. Properties

    @property
    def _units(self) -> LENGTH_UNITS:
        """Fetches the global units associated with the parent simulation."""
        return self._sim._units()

    @property
    def _lumapi(self) -> Any:
        """Fetches the api associated with the parent simulation."""
        return self._sim._lumapi()

    # endregion Dev. Properties

    # region User Properties

    @property
    def name(self) -> str:
        """Returns the name of the object as it is in the lumerical FDTD simulation environment."""
        return self._get("name", str)

    @property
    def enabled(self) -> bool:
        """Fetches and returns the object's enabled-flag from the parent simulation."""
        return self._get("enabled", bool)

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        """Sets the object's enabled-flag in the parent simulation. I False, the object is disabled and vica versa."""
        self._set("enabled", enabled)

    @property
    def x(self) -> float:
        """
        Fetches and returns the object's x-coordinate from the parent simulation.
        If the "use relative coordinates" flag in Lumerical is True, this is what's returned.
        Units are dictated by what units are specified in the parent simulation.

        """
        x = self._get("x", float)
        return convert_length(x, "m", self._units)

    @x.setter
    def x(self, x: float) -> None:
        """
        Sets the object's y-coordinate in the parent simulation.
        Units are dictated by what units are specified in the parent simulation.

        """
        x = convert_length(x, self._units, "m")
        self._set("x", x)

    @property
    def y(self) -> float:
        """
        Fetches and returns the object's y-coordinate from the parent simulation.
        If the "use relative coordinates" flag in Lumerical is True, this is what's returned.
        Units are dictated by what units are specified in the parent simulation.

        """
        y = self._get("y", float)
        return convert_length(y, "m", self._units)

    @y.setter
    def y(self, y: float) -> None:
        """
        Sets the object's y-coordinate in the parent simulation.
        Units are dictated by what units are specified in the parent simulation.

        """
        y = convert_length(y, self._units, "m")
        self._set("y", y)

    @property
    def z(self) -> float:
        """
        Fetches and returns the object's z-coordinate from the parent simulation.
        If the "use relative coordinates" flag in Lumerical is True, this is what's returned.
        Units are dictated by what units are specified in the parent simulation.

        """
        z = self._get("z", float)
        return convert_length(z, "m", self._units)

    @z.setter
    def z(self, z: float) -> None:
        """
        Sets the object's z-coordinate in the parent simulation.
        Units are dictated by what units are specified in the parent simulation.

        """
        z = convert_length(z, self._units, "m")
        self._set("z", z)

    @property
    def pos(self) -> Tuple[float, float, float]:
        """Returns the x, y, z position of the object as a tuple."""
        return self.x, self.y, self.z

    @pos.setter
    def pos(self, pos: Tuple[float, float, float] | List[float, float, float] | np.ndarray) -> None:
        """Set the position vector of the object."""

        # Validate input type
        if not isinstance(pos, (tuple, list, np.ndarray)):
            raise TypeError(f"Expected a tuple, list, or ndarray, got {type(pos)}.")

        # Validate length
        if len(pos) != 3:
            raise ValueError(f"Expected a sequence of 3 elements, got {len(pos)}.")

        # Validate elements
        pos_dict = {}
        idx_to_coord = {0: "x", 1: "y", 2: "z"}
        for idx, element in enumerate(pos):
            if isinstance(element, (int, float)):
                pos_dict[idx_to_coord[idx]] = convert_length(element, self._units, "m")  # To meters
            elif element is None:
                continue
            else:
                raise TypeError(f"All elements must be int or float. An element is {type(element)}.")

        # Set each coordinate
        for coordinate, value in pos_dict.items():
            self._set(coordinate, value)

    # endregion User Properties

    # region Abstract Methods

    # The copy method should be overridden for each specific object type. The override should jsut append the copied
    # object to the simulation object's appropriate list of objects, ie. sim._structures for structure objects.
    @abstractmethod
    def copy(self, name, **kwargs: Unpack[Any]) -> Self:
        """
        Creates and returns a copy of the object. This copy is then added to the parent simulation.
        If the copied object is a part of a group hierarchy, the new object will also be.


        Args:
            name: The unique name of the new object.
            **kwargs: Keyword arguments specific to the object type.

        Returns:
            An instance of the new object copied from the old.

        """

        # Check if the name is available name
        self._check_name(name)

        # Copy the object in the simulation
        self._lumapi.select(self._get_scope())
        self._lumapi.copy()
        self._lumapi.set("name", name)

        # Make a shallow copy of the python object and update the name
        copied = pythoncopy(self)
        copied._name = name

        # Copy the settings with the new copy as their parent object
        copied.settings = self.settings._copy(copied)

        # Apply the kwargs
        copied._process_kwargs(copied=True, **kwargs)

        return copied

    @abstractmethod
    def _process_kwargs(self, copied: bool = False, **kwargs) -> None:
        """
        Filters and applies the kwargs specific to the object type.

        Args:
            copied (bool): Flag to indicate if the method is run on a recently copied object. If it is, default
            paramters shouldn't be implemented.

        """
        ...

    # endregion Abstract Methods
