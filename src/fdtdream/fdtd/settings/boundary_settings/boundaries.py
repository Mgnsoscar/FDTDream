from typing import TypedDict, Unpack, get_args

from ....base_classes import Module
from ....resources import validation
from ....resources.literals import BOUNDARY_TYPES_LOWER


class BoundaryTypesKwargs(TypedDict, total=False):
    x_min: BOUNDARY_TYPES_LOWER
    x_max: BOUNDARY_TYPES_LOWER
    y_min: BOUNDARY_TYPES_LOWER
    y_max: BOUNDARY_TYPES_LOWER
    z_min: BOUNDARY_TYPES_LOWER
    z_max: BOUNDARY_TYPES_LOWER


class FDTDBoundariesSubsettings(Module):

    def set_boundary_types(self, **kwargs: Unpack[BoundaryTypesKwargs]) -> None:
        """
        Configure boundary types for specified boundaries.

        This method sets the boundary conditions (e.g., PML, Metal, Symmetric, etc.) for each axis
        and direction in the simulation. Boundary conditions control how the simulation domain
        interacts with electromagnetic fields at its edges.

        Args:
            **kwargs (BoundaryTypesKwargs):
                Key-value pairs where the keys are boundary identifiers (`x_min`, `x_max`,
                `y_min`, `y_max`, `z_min`, `z_max`) and the values are boundary condition types
                (from `BOUNDARY_TYPES`).

        BOUNDARY_TYPES:

                - PML (Perfectly Matched Layer)**: Absorbs electromagnetic waves to model open boundaries.
                        Best when structures extend through the boundary.
                - Metal (Perfect Electric Conductor)**: Reflects all electromagnetic waves, with zero electric
                        field component parallel to the boundary.
                - PMC (Perfect Magnetic Conductor)**: Reflects magnetic fields, with zero magnetic field component
                        parallel to the boundary.
                - Periodic: Used for structures that are periodic in one or more directions, simulating infinite
                        repetition.
                - Bloch: Used for periodic structures with a phase shift, suitable for plane waves at angles or
                        bandstructure calculations.
                - Symmetric: Mirrors electric fields and anti-mirrors magnetic fields; requires symmetric sources.
                - Anti-Symmetric: Anti-mirrors electric fields and mirrors magnetic fields; requires anti-symmetric
                        sources.

        Raises:
            ValueError:
                - If a provided boundary is invalid (not one of `x_min`, `x_max`, `y_min`, `y_max`, `z_min`, `z_max`).
                - If a provided boundary type is invalid (not in `BOUNDARY_TYPES`).

        """
        valid_boundaries = BoundaryTypesKwargs.__annotations__
        valid_types = get_args(BOUNDARY_TYPES_LOWER)
        for b, b_type in kwargs.items():
            if b not in BoundaryTypesKwargs.__annotations__:
                raise ValueError(f"'{b}' is not a valid boundary. Choose from {valid_boundaries}.")
            elif b_type not in valid_types:
                raise ValueError(f"'{b_type}' is not a valid boundary type. Choose from {valid_types}.")

            if "max" in b:
                if b_type in ["symmetric", "anti-symmetric"]:
                    self._set("allow symmetry on all boundaries", True)

            b_type = b_type.split("-")
            b_type = "-".join([word.capitalize() for word in b_type])

            self._set(f"{b.replace("_", " ")} bc", b_type)

    def set_allow_symmetry_on_all_boundaries(self, true_or_false: bool) -> None:
        """
        Set the option to allow symmetric boundary conditions for periodic structures.

        This option enables the use of symmetric boundary conditions with periodic structures.
        When enabled, symmetric and anti-symmetric boundary conditions can be applied to the
        simulation, allowing for the modeling of structures that exhibit symmetry.

        Args:
            true_or_false (bool): Set to True to allow symmetry on all boundaries;
                                  set to False to disallow symmetry.

        """
        validation.boolean(true_or_false, "true_or_false")
        self._set("allow symmetry on all boundaries", true_or_false)
