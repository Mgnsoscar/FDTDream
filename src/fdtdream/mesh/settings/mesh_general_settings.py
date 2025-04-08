from typing import TypedDict, Unpack

from ...base_classes import Module
from ...resources.literals import LENGTH_UNITS
from ...resources.functions import convert_length
from ...resources import validation


class MaxMeshStepKwargs(TypedDict, total=False):
    dx: float
    dy: float
    dz: float
    units: LENGTH_UNITS


class AxesBoolKwargs(TypedDict, total=False):
    x: bool
    y: bool
    z: bool


class AxesFloatKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float


class MeshGeneralSettings(Module):

    def override_axis_mesh(self, **kwargs: Unpack[AxesBoolKwargs]) -> None:
        """
        Enable or disable mesh size overrides for the specified axes.

        This method allows users to set whether mesh size constraints should be overridden
        for a specific axis (x, y, or z). If multiple mesh override regions are present,
        the meshing algorithm will use the override region that results in the smallest mesh
        for that volume of space. Constraints from mesh override regions always take precedence
        over the default automatic mesh, even if they result in a larger mesh size.
        """
        for axis, truth in kwargs.items():
            validation.axis(axis)
            validation.boolean(truth, axis)
            self._set(f"override {axis} mesh", truth)

    def set_equivalent_index(self, **kwargs: Unpack[AxesFloatKwargs]) -> None:
        """
        Set the equivalent refractive indices for mesh size determination.

        This method allows users to define equivalent refractive indices for the x, y,
        and z directions, which will be used to determine the mesh spacing in the simulation.
        Setting an equivalent index leads to finer mesh spacing, as the mesh size is usually
        determined by the refractive index of the materials in the simulation.

        If any equivalent index is set, the respective axis mesh will be overridden to use
        this index. If multiple mesh override regions are present, the meshing algorithm
        will use the override region that results in the smallest mesh for that volume of
        space. Constraints from mesh override regions always take precedence over the default
        automatic mesh, even if they result in a larger mesh size.

        Args:
            x (float, optional): The equivalent refractive index in the x direction.
                                        If None, the x mesh will not be overridden.
            y (float, optional): The equivalent refractive index in the y direction.
                                        If None, the y mesh will not be overridden.
            z (float, optional): The equivalent refractive index in the z direction.
                                        If None, the z mesh will not be overridden.

        Raises:
            ValueError: If there are issues in setting the parameters.
        """

        self._set("set equivalent index", True)
        for axis, index in kwargs.items():
            validation.axis(axis)
            validation.positive_number(index, axis)
            self._set(f"override {axis} mesh", True)
            self._set(f"equivalent {axis} index", index)

    def set_maximum_mesh_step(self, **kwargs: Unpack[MaxMeshStepKwargs]) -> None:
        """
        Set the maximum mesh step sizes for the x, y, and z directions.

        This method allows users to specify the maximum mesh sizes for the simulation in the
        respective dimensions. If multiple mesh override regions are present, the meshing
        algorithm will use the override region that results in the smallest mesh for that
        volume of space. Constraints from mesh override regions always take precedence over
        the default automatic mesh, even if they result in a larger mesh size.

        The 'set maximum mesh step' parameter directly influences the granularity of the mesh,
        affecting the accuracy and performance of the simulation. Smaller mesh steps lead to
        finer meshes, resulting in more detailed simulations but potentially increased computation
        times.

        Args:
            dx (float, optional): Maximum mesh step size in the x direction. If None, the default
                                  mesh setting for x will be used.
            dy (float, optional): Maximum mesh step size in the y direction. If None, the default
                                  mesh setting for y will be used.
            dz (float, optional): Maximum mesh step size in the z direction. If None, the default
                                  mesh setting for z will be used.
            units (LENGTH_UNITS, optional): The units of the provided mesh sizes. If None,
                                                    the global units of the simulation will be used.

        Raises:
            ValueError: If the provided length_units is not valid.
        """

        units = kwargs.pop("units", self._units)
        validation.in_literal(units, "units", LENGTH_UNITS)

        self._set("set maximum mesh step", True)

        for axis, stepsize in kwargs.items():
            stepsize = convert_length(stepsize, from_unit=units, to_unit="m")  # type: ignore
            self._set(axis, stepsize)
