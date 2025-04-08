from __future__ import annotations

from typing import Tuple, Iterable

from scipy.spatial.transform import Rotation as R
import numpy as np
from numpy.typing import NDArray

from ..interfaces import SimulationObjectInterface
from ..resources.functions import rotate
from ..resources.literals import AXES
from ..base_classes.object_modules import Module


class Rotation(Module):

    def _assign_rotation(self, sequence: str, angles: NDArray[np.float64], position: NDArray[np.float64]) -> None:
        """
        Takes in a sequence of axes, a sequance of rotation angles (degrees), and a position ve tor,
        and assigns the total rotation and new position to the parent object in Lumerical FDTD.

        Args:
            sequence (str): Three letter sequence with the rotation order. Ie. "xyz", "xzy", "yzx", etc...
            angles (NDArray): Three-element array with the rotation angles around the axes corresponing to the sequence.
            position (NDArray): Three-element position vector or another simulation object.

        """

        self._set("first axis", sequence[0]), self._set("rotation 1", angles[0])
        self._set("second axis", sequence[1]), self._set("rotation 2", angles[1])
        self._set("third axis", sequence[2]), self._set("rotation 3", angles[2])
        self._set("x", position[0]), self._set("y", position[1]), self._set("z", position[2])

    def _get_rotation_euler(self) -> Tuple[str, NDArray[np.float64]]:
        """
        Returns the current rotation state as a string sequence of axes and 3D array of rotation angles in degrees.

        Returns:
            A tuple where the first element is a string sequence, and the second a three-element numpy array.

        """
        axes = ""
        rotations = []
        for ax, queue, num in zip(["x", "y", "z"], ["first", "second", "third"], ["1", "2", "3"]):
            axis = self._get(queue + " axis", str)
            if axis == "none" or rotations == 0:
                continue
            else:
                rotations.append(self._get("rotation " + num, float))
                axes += ax

        return axes, np.array(rotations, dtype=np.float64)

    def _get_rotation_rot_vec(self) -> Tuple[NDArray, np.float64]:
        """
        Returns the current rotation state as a rotation vector and an angle in radians.

        Returns:
            A tuple where the first element is a three element numpy array (vector), and the second the rotation angle
            around that vector.

        """
        # Fetch rotation state and convert angles to radians
        axes, angles = self._get_rotation_euler()
        angles = np.deg2rad(angles)

        # Create a Rotation object by applying individual rotations
        rotation = R.identity()  # Start with the identity rotation (no rotation)

        for axis, angle in zip(axes, angles):
            rotation = rotation * R.from_euler(axis, angle)

        # Convert to axis-angle representation
        axis = rotation.as_rotvec()  # axis is a vector, angle is in radians
        angle = np.linalg.norm(axis)

        return axis.astype(np.float64), angle.astype(np.float64)

    def _is_rotated(self) -> bool:
        """
        Check if the parent object is rotated or not.

        Returns:
            A boolean indicating if the parent object is rotated or not.

        """
        _, rotations = self._get_rotation_euler()
        if rotations.size != 0:
            return True
        return False

    def _get_position(self) -> NDArray[3]:
        """Returns the position of the object as a 3D array."""
        return np.array([self._get("x", float), self._get("y", float), self._get("z", float)])

    def rotate(self, rot_vec: AXES | Iterable[float], rot_angle: float,
               rot_point: Tuple[float, float, float] | SimulationObjectInterface = None) -> Rotation.rotate:
        """
        Rotates the object as instructed from its present rotational state.

        The object will be rotated counterclockwise in degrees around the provided 'vector' going through the
        provided 'point'. If no 'point' argument is provided, the object's position will be used. If the point is
        not the object's position, its position will change.

        The method returns a reference to the same method, meaning it can be stacked. In this example, the object is
        first rotated 90 around the x-axis, then 90 degrees around the y-axis, then 90 degrees around the z-axis.

        obj.settings.rotation.rotate((1, 0, 0), 90)((0, 1, 0), 90)((0, 0, 1), 90)

        Args:
            rot_vec: The vector the structure is rotated around. Can be a tuple with three floats, "x", "y", or "z".
            rot_angle: The rotation angle. Rotation is performed counterclockwise around the vector.
            rot_point: The coordinate the vector passes through. Can be a tuple with three floats or another simulation
                object. If the latter, the other object's position will be used.

        Returns:
            The method itself, allowing the user to stack the method.
        """
        if not rot_vec or not rot_angle:
            return

        # Gert current rotation and position
        if not self._is_rotated():
            sequence = "xyz"
            rotations = np.array([0, 0, 0])
        else:
            sequence, rotations = self._get_rotation_euler()
        position = self._get_position()
        if rot_point is None:
            rot_point = position
        elif isinstance(rot_point, SimulationObjectInterface):
            rot_point = rot_point._get_position()

        if rot_vec == "x":
            rot_vec = (1, 0, 0)
        elif rot_vec == "y":
            rot_vec = (0, 1, 0)
        elif rot_vec == "z":
            rot_vec = (0, 0, 1)

        # Rotate
        sequence, rotations, position = rotate(sequence, rotations, np.array(rot_vec, dtype=float), rot_angle,
                                               position, np.array(rot_point, dtype=float))

        self._assign_rotation(sequence, rotations, position)
        return self.rotate  # Return reference to the same method for stacking rotations

    def set_rotation(self, rot_vec: AXES | Iterable[float], rot_angle: float,
                     rot_point: Tuple[float, float, float] | SimulationObjectInterface = None) -> Rotation.rotate:
        """
        Sets the rotation of the object from its unrotated state, regardless if the object is rotated to begin with.

        The object will be rotated counterclockwise in degrees around the provided 'vector' going through the
        provided 'point'. If no 'point' argument is provided, the object's position will be used. If the point is
        not the object's position, its position will change.

        The method returns a reference to the 'rotate' method, meaning an initial rotation can be stacked
        with subsequent rotations. In this example, the object is first rotated 90 around the x-axis,
        then 90 degrees around the y-axis, then 90 degrees around the z-axis..

        obj.settings.rotation.rotate((1, 0, 0), 90)((0, 1, 0), 90)((0, 0, 1), 90)

        Args:
            rot_vec: The vector the structure is rotated around. Can be a tuple with three floats, "x", "y", or "z".
            rot_angle: The rotation angle. Rotation is performed counterclockwise around the vector.
            rot_point: The coordinate the vector passes through. Can be a tuple with three floats or another simulation
                object. If the latter, the other object's position will be used.

        Returns:
            The method itself, allowing the user to stack the method.
        """
        self.reset_rotation()
        self.rotate(rot_vec, rot_angle, rot_point)

    def reset_rotation(self) -> None:
        """Resets the object to its unrotated state."""
        self._set("first axis", "none")
        self._set("second axis", 'none')
        self._set("third axis", 'none')
