from typing import TypedDict, Unpack

from ....base_classes import Module
from ....resources import validation
from ....resources.functions import convert_length
from ....resources.literals import LENGTH_UNITS, DEFINE_MESH_BY, MESH_TYPE


class MaxStepKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float
    units: LENGTH_UNITS


class DefineMeshByKwargs(TypedDict, total=False):
    x_definition: DEFINE_MESH_BY
    y_definition: DEFINE_MESH_BY
    z_definition: DEFINE_MESH_BY


class AxesBoolKwargs(TypedDict, total=False):
    x: bool
    y: bool
    z: bool


class AxesIntKwargs(TypedDict, total=False):
    x: int
    y: int
    z: int


class FDTDMeshTypeSubsettings(Module):

    def set_mesh_type(self, mesh_type: MESH_TYPE) -> None:
        """
        Set the type of mesh generation algorithm.

        Mesh Generation Algorithms:

        1. **Auto Non-Uniform (Default)**:
           - Automatically generates a non-uniform mesh based on the mesh accuracy slider bar.
           - Recommended to start with a mesh accuracy of 1-2 for initial simulations.
           - Mesh Accuracy Parameter: Integer from 1 to 8.
             - 1: Low accuracy (target of 6 points per wavelength, ppw)
             - 2: Target of 10 ppw
             - 3: Target of 14 ppw
             - Increments of 4 ppw per accuracy level.
           - Factors influencing the meshing algorithm include source wavelength, material properties, and structure geometry.
           - Note: Wavelength is inversely proportional to the refractive index; high-index materials will use a smaller mesh.

        2. **Custom Non-Uniform**:
           - Provides additional customization options for non-uniform mesh generation.
           - Default setting of 10 mesh cells per wavelength is usually sufficient, but can be reduced to 6-8 for coarse simulations.
           - Grading Factor: Determines the maximum rate of mesh modification.
             - Formula: If `dx(i+1) = a*dx(i)`, then `1/(GRADING FACTOR) <= a <= GRADING FACTOR`.
             - Recommended range: Between 1 and 2 (default: `sqrt(2)`).

        3. **Uniform**:
           - Applies a uniform mesh to the entire simulation volume, regardless of material properties.
           - If a mesh override region is used, the uniform mesh size will apply everywhere, not just within the override region.

        Parameters:
        - mesh_type: A value representing the mesh type (MESH_TYPE).

        Raises:
        - ValueError: If the mesh_type is not a valid literal.
        """

        validation.in_literal(mesh_type, "mesh_type", MESH_TYPE)
        self._set("mesh type", mesh_type)

    def set_mesh_accuracy(self, mesh_accuracy: int) -> None:
        """
        Set the accuracy of the mesh generation.

        Parameters:
        - mesh_accuracy: An integer value from 1 to 8, representing mesh accuracy.

        Raises:
        - ValueError: If mesh_accuracy is not in the range (1, 8).
        - ValueError: If the current mesh type is not 'auto non-uniform'.

        The mesh accuracy determines how finely the mesh is generated:
        - 1 corresponds to low accuracy (6 points per wavelength),
        - 2 to 10 points per wavelength,
        - 3 to 14 points per wavelength, and so on,
        increasing by 4 points per level up to a maximum of 8.
        """

        # Fetch the current mesh type
        current_mesh_type = self._get("mesh type", str)

        if current_mesh_type != "auto non-uniform":
            raise ValueError("Mesh accuracy can only be set when the mesh type is 'auto non-uniform'.")

        validation.integer_in_range(mesh_accuracy, "mesh_accuracy", (1, 8))
        self._set("mesh accuracy", mesh_accuracy)

    def define_mesh_by(self, **kwargs: Unpack[DefineMeshByKwargs]) -> None:
        """
        Define the mesh generation criteria for the specified axes.

        Parameters:
            x/y/z_definition: DEFINITION

        DEFINITION: Specifies how the mesh will be defined. Options include:
            - 'mesh cells per wavelength': Defines the number of mesh cells based on
              the wavelength, allowing for variable mesh resolution.
            - 'maximum mesh step': Sets a maximum allowable step size for mesh
              generation, ensuring no individual mesh cell exceeds this size.
            - 'max mesh step and mesh cells per wavelength': Combines both previous
              options to achieve a balance between cell count and size.
            - 'number of mesh cells': Defines the mesh by specifying an absolute
              number of cells along the specified axis.

        Raises:
        - ValueError: If the axis is not valid, if the definition is not one of the
          allowed options, or if the current mesh type is not 'Custom non-uniform'
          or 'Uniform'.

        The choice of mesh definition impacts the accuracy and performance of the
        simulation. It is important to select the definition that best suits the
        specific simulation requirements.
        """

        # Check the current mesh type
        current_mesh_type = self._get("mesh type", str)

        # Ensure the mesh type is either 'Custom non-uniform' or 'Uniform'
        if current_mesh_type not in ["custom non-uniform", "uniform"]:
            raise ValueError("Mesh type must be 'custom non-uniform' or 'uniform' to define mesh by.")

        valid_arguments = list(DefineMeshByKwargs.__annotations__.keys())
        for axis, definition in kwargs.items():
            validation.in_list(axis, valid_arguments)
            validation.in_literal(definition, axis, DEFINE_MESH_BY)
            self._set(f"define {axis[0]} mesh by", definition)

    def allow_mesh_grading(self, **kwargs: Unpack[AxesBoolKwargs]) -> None:
        """
        Enable or disable mesh grading for specified axes.

        Raises:
        - ValueError: If the axis is not valid, if the current mesh type is not
          'custom non-uniform', or if the 'define x/y/z mesh by' parameter is set
          to 'number of mesh cells'.

        Enabling mesh grading allows for more flexible mesh adjustments, improving
        simulation accuracy but may increase computation time.
        """

        # Check the current mesh type
        current_mesh_type = self._get("mesh type", str)

        # Ensure the mesh type is 'custom non-uniform'
        if current_mesh_type != "custom non-uniform":
            raise ValueError("Mesh type must be 'custom non-uniform' to allow mesh grading.")

        for axis, truth in kwargs.items():

            # Fetch the 'define {axis} mesh by' parameter
            define_mesh_by = self._get(f"define {axis} mesh by", str)

            # Raise an error if it is set to 'number of mesh cells'
            if define_mesh_by == "number of mesh cells":
                raise ValueError(
                    f"Mesh grading cannot be allowed when 'define {axis} mesh by' is set to 'number of mesh cells'.")

            validation.axis(axis)
            validation.boolean(truth, axis)
            self._set(f"allow grading in {axis}", truth)

    def set_grading_factor(self, grading_factor: float) -> None:
        """
        Set the grading factor for mesh generation.

        Parameters:
        - grading_factor: A float value representing the grading factor, which
          determines the maximum rate at which the mesh can be modified.

        Raises:
        - ValueError: If the current mesh type is not 'custom non-uniform'.
        - ValueError: If the grading factor is not between 1.01 and 2..

        The grading factor should be between 1.01 and 2, with a default setting of
        sqrt(2). It controls how quickly the mesh size can change from one
        element to the next.
        """

        # Check the current mesh type
        current_mesh_type = self._get("mesh type", str)

        # Ensure the mesh type is 'custom non-uniform'
        if current_mesh_type != "custom non-uniform":
            raise ValueError("Mesh type must be 'custom non-uniform' to set the grading factor.")

        validation.number_in_range(grading_factor, "grading_factor", (1.01, 2))
        self._set("grading factor", grading_factor)

    def set_maximum_mesh_step(self, **kwargs: Unpack[MaxStepKwargs]) -> None:
        """
        Set the maximum mesh step size for the specified axes.

        Parameters:
            - x/y/z (float): maximum stepsize along the specified axis
            - units ("m", "cm", "mm" "um", "nm", "angstrom", "fm"):  If None, the global units will be used.

        Raises:
        - ValueError: If the current definition for the specified axis is not
          'maximum mesh step' or 'max mesh step and mesh cells per wavelength', or
          if the mesh type is not 'custom non-uniform' or 'uniform'.

        The maximum mesh step sets the absolute maximum size for the mesh step in the
        specified direction, overriding other mesh size settings.
        """

        # Check the current mesh type
        current_mesh_type = self._get("mesh type", str)

        # Ensure the mesh type is 'custom non-uniform' or 'uniform'
        if current_mesh_type not in {"custom non-uniform", "uniform"}:
            raise ValueError("The mesh type must be 'custom non-uniform' or 'uniform' to set the maximum mesh step.")

        units = kwargs.pop("units", None)
        if units is None:
            units = self._units
        else:
            validation.in_literal(units, "units", LENGTH_UNITS)
        for axis, value in kwargs.items():
            validation.axis(axis)

            # Fetch the current definition for the specified axis
            definition = self._get(f"define {axis} mesh by", str)

            # Ensure the definition is either 'maximum mesh step' or
            # 'max mesh step and mesh cells per wavelength'
            if definition not in {"maximum mesh step", "max mesh step and mesh cells per wavelength"}:
                raise ValueError(
                    f"The definition for '{axis}' mesh must be either 'maximum mesh step' or "
                    "'max mesh step and mesh cells per wavelength', but it is currently '{definition}'."
                )
            max_step = convert_length(value, units, "m") # type: ignore
            self._set(f"d{axis}", max_step)

    def set_mesh_cells_per_wavelength(self, mesh_cells: float) -> None:
        """
        Set the number of mesh cells per wavelength for the simulation.

        Parameters:
        - mesh_cells: A float value representing the number of mesh cells per wavelength.

        Raises:
        - ValueError: If the current mesh type is not 'custom non-uniform'.

        The mesh cells per wavelength setting determines how finely the mesh is generated
        based on the wavelength of the simulation. A higher value results in a finer mesh.
        """

        # Fetch the current mesh type
        mesh_type = self._get("mesh type", str)

        # Ensure the mesh type is 'custom non-uniform'
        if mesh_type != "custom non-uniform":
            raise ValueError(f"The mesh type must be 'custom non-uniform', but it is currently '{mesh_type}'.")

        # Set the parameter for mesh cells per wavelength
        self._set("mesh cells per wavelength", mesh_cells)

    def set_number_of_mesh_cells_without_override_regions(self, **kwargs: Unpack[AxesIntKwargs]) -> None:
        """
        Set the number of mesh cells without override regions for the specified axes .

        Raises:
        - ValueError: If the mesh type is not 'custom non-uniform' or 'uniform',
          or if the current definition for the specified axis is not 'number of mesh cells'.

        This method sets the number of mesh cells for the specified axis, ensuring that
        it does not override any regions specified by the user.
        """

        # Check the current mesh type
        current_mesh_type = self._get("mesh type", str)

        # Ensure the mesh type is 'custom non-uniform' or 'uniform'
        if current_mesh_type not in {"custom non-uniform", "uniform"}:
            raise ValueError("The mesh type must be 'custom non-uniform' or 'uniform' to set the number of mesh cells.")

        for axis, value in kwargs.items():

            validation.axis(axis)

            # Fetch the current definition for the specified axis
            definition = self._get(f"define {axis} mesh by", str)

            # Ensure the definition is 'number of mesh cells'
            if definition != "number of mesh cells":
                raise ValueError(
                    f"The definition for '{axis}' mesh must be 'number of mesh cells', "
                    f"but it is currently '{definition}'."
                )

            validation.positive_integer(value, "nr")
            self._set(f"mesh cells {axis}", value, int)
