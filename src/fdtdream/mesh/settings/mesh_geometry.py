from typing import TypedDict, Unpack

from ...base_classes import BaseGeometry
from ...interfaces import StructureInterface
from ...resources import validation
from ...resources.functions import convert_length
from ...resources.literals import LENGTH_UNITS
from ...resources.errors import FDTDreamNotBasedOnAStructureError


class MeshGeometry(BaseGeometry):

    class _Dimensions(TypedDict, total=False):
        x_span: float
        y_span: float
        z_span: float

    def set_buffer(self, buffer: float, units: LENGTH_UNITS = None) -> None:
        """
        If the mesh is based on a structure, this method allows to buffer the mesh inwards or outward by a
        certain distance from the structure's bounding box..

        Args:
            buffer: The distance to buffer the mesh.
            units: What length units the buffer argument is provided in. If None, the parent simulation's
                    units are used.

        Returns:
            None

        """
        if not self._get("based on a structure", bool):
            raise FDTDreamNotBasedOnAStructureError(f"You cannot buffer the mesh, as the mesh is not "
                                                    f"based on a structure.")

        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)

        validation.number(buffer, "buffer")
        self._set("buffer", convert_length(buffer, units, "m"))

    def set_based_on_a_structure(self, structure_name: str, buffer: float = None,
                                 length_units: LENGTH_UNITS = None) -> None:
        """
        Configure the mesh override parameters based on an existing structure.

        This method allows users to set mesh override positions and spans based on a specified
        structure in the simulation. The position and spans are determined using the center position
        and dimensions of the named structure. Users can also specify a buffer to extend the
        mesh override region outwards in all directions.

        If multiple mesh override regions are present, the meshing algorithm will utilize the
        override region that results in the smallest mesh for that volume of space. Constraints
        from mesh override regions take precedence over the default automatic mesh, even if they
        lead to a larger mesh size.

        Args:
            structure_name (str): The name of the structure(s) the mesh shall be based on.
            buffer (float, optional): A positive value indicating the buffer distance to extend
                                      the mesh override region in all directions. If None, no
                                      buffer will be applied.
            length_units (LENGTH_UNITS, optional): The units of the provided buffer distance.
                                                    If None, the global units of the simulation
                                                    will be used.

        Raises:
            ValueError: If the provided buffer is negative or if the length_units is not valid.
        """

        self._set("based on a structure", True)
        self._set("structure", structure_name)

        if buffer is not None:
            if length_units is None:
                length_units = self._units
            else:
                validation.in_literal(length_units, "length_units", LENGTH_UNITS)

            buffer = convert_length(buffer, from_unit=length_units, to_unit="m")
            self._set("buffer", buffer)

    def set_directly_defined(self) -> None:
        """
        Enable direct definition of the mesh geometry.

        This method must be called to allow users to define the geometry of the mesh directly
        using coordinates and spans, similar to standard mesh definition practices.
        """
        self._set("directly defined", True)

    def set_dimensions(self, **kwargs: Unpack[_Dimensions]) -> None:

        if self._get("based on a structure", bool):
            raise ValueError("You cannot set the spans of the mesh when 'based on a structure' is enabled. "
                             "Enable 'directly defined' first.")
        super().set_dimensions(**kwargs)

    def set_position(self, x: float = None, y: float = None, z: float = None) -> None:

        if self._get("based on a structure", bool):
            raise ValueError("You cannot set the position of the mesh when 'based on a structure' is enabled. "
                             "Enable 'directly defined' first.")

        super().set_position(x, y , z)
