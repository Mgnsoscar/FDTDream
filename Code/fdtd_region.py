from __future__ import annotations

# Standard library imports
from typing import Union, get_args, Unpack, Optional, TypedDict, Any, cast
from dataclasses import dataclass
import warnings

# Third-party imports
import numpy as np

# Local imports
from Code.Resources.local_resources import convert_length, Validate, LENGTH_UNITS, has_different_objects, DECIMALS
from Code.Resources.literals import (AXES, DIMENSION, MATERIALS, DEFINE_MESH_BY, MESH_TYPE, MESH_REFINEMENT, PML_TYPES,
                                     PML_PROFILES, BOUNDARIES, BOUNDARY_TYPES, BLOCH_UNITS, BOUNDARY_TYPES_LOWER)
from base_classes import (TStructure, TSimulation)
from base_classes import Settings, AxesBoolKwargs, AxesFloatKwargs, AxesIntKwargs
from base_classes import (MeshBase, SettingTab, SimulationObject)
from structures import PhotonicCrystal
from geometry import (MeshGeometry, TrippleSpannableGeometryRelative, TrippleSpannableGeometryAbsolute, PositionKwargs,
                      RelPositionKwargs, TrippleSpansProperties, MinMaxDirectProperties, TrippleSpansKwargs)


########################################################################################################################
#                                             DATACLASSES
########################################################################################################################
@dataclass
class Stepsizes(Settings):
    dx: float
    dy: float
    dz: float


@dataclass
class EquivalentIndices(Settings):
    equivalent_x_index: float
    equivalent_y_index: float
    equivalent_z_index: float


@dataclass
class MeshDefinitions(Settings):
    define_x_mesh_by: DEFINE_MESH_BY
    define_y_mesh_by: DEFINE_MESH_BY
    define_z_mesh_by: DEFINE_MESH_BY


@dataclass
class Gradings(Settings):
    allow_grading_in_x: bool
    allow_grading_in_y: bool
    allow_grading_in_z: bool
    grading_factor: float


@dataclass
class MeshCells(Settings):
    mesh_cells_x: int
    mesh_cells_y: int
    mesh_cells_z: int


@dataclass
class PMLBoundarySettings(Settings):
    pml_type: PML_TYPES
    pml_profile: PML_PROFILES
    pml_layers: int
    pml_kappa: float
    pml_sigma: float
    pml_polynomial: float
    pml_alpha: float
    pml_alpha_polynomial: float
    pml_min_layers: int
    pml_max_layers: int


@dataclass
class KVector(Settings):
    kx: float
    ky: float
    kz: float


########################################################################################################################
#                                          SIMULATION MESH CLASSES
########################################################################################################################
class MeshGeneralSettings(SettingTab):
    class _MaxMeshStepKwargs(TypedDict, total=False):
        dx: float
        dy: float
        dz: float
        units: Optional[LENGTH_UNITS]

    @dataclass
    class _Settings(Settings):
        stepsizes: Stepsizes
        equivalent_indices: EquivalentIndices

    __slots__ = SettingTab.__slots__

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
            Validate.axis(axis)
            Validate.boolean(truth, axis)
            self._set_parameter(f"override {axis} mesh", truth, "bool")

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

        self._set_parameter("set equivalent index", True, "bool")
        for axis, index in kwargs.items():
            Validate.axis(axis)
            Validate.positive_number(index, axis)
            self._set_parameter(f"override {axis} mesh", True, "bool")
            self._set_parameter(f"equivalent {axis} index", index, "float")

    def set_maximum_mesh_step(self, **kwargs: Unpack[_MaxMeshStepKwargs]) -> None:
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

        units = kwargs.pop("units", None)
        if units is None:
            units = self._simulation.__getattribute__("_global_units")
        else:
            Validate.in_literal(units, "length_units", LENGTH_UNITS)

        self._set_parameter("set maximum mesh step", True, "bool")
        for axis, stepsize in kwargs.items():
            stepsize = convert_length(stepsize, from_unit=units, to_unit="m")  # type: ignore
            self._set_parameter(axis, stepsize, "float")

    def _get_active_parameters(self) -> Optional[_Settings]:

        settings = self._Settings.initialize_empty()

        if self._get_parameter("set maximum mesh step", "bool"):
            for axis in get_args(AXES):
                if self._get_parameter(f"override {axis} mesh", "bool"):
                    settings.stepsizes.__setattr__(f"d{axis}", self._get_parameter(f"d{axis}", "float"))
        else:
            for axis in get_args(AXES):
                if self._get_parameter(f"override {axis} mesh", "bool"):
                    settings.equivalent_indices.__setattr__(f"equivalent {axis} index",
                                                            self._get_parameter(f"equivalent {axis} index", "float"))
        settings.fill_hash_fields()
        return settings


class Mesh(MeshBase, TrippleSpansProperties):
    class _SettingsCollection(MeshBase._SettingsCollection):
        _settings = [MeshGeneralSettings, MeshGeometry]
        _settings_names = ["general", "geometry"]

        general: MeshGeneralSettings
        geometry: MeshGeometry
        __slots__ = MeshBase._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(TypedDict, total=False):
        use_relative_coordinates: bool
        x: float
        y: float
        z: float
        x_span: float
        y_span: float
        z_span: float
        based_on_a_structure: Union[TStructure, PhotonicCrystal]
        dx: float
        dy: float
        dz: float

    @dataclass
    class _Settings(MeshBase._Settings):
        general_settings: MeshGeneralSettings._Settings
        geometry_settings: MeshGeometry._Settings

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = SimulationObject.__slots__ + _settings_names

    @property
    def based_on_structure(self) -> Optional[TStructure]:
        return self._structure

    @based_on_structure.setter
    def based_on_structure(self, structure: Optional[Union[TStructure, PhotonicCrystal]]) -> None:
        if structure is None:
            self.settings.geometry.set_directly_defined()
        else:
            self.settings.geometry.set_based_on_a_structure(structure)

    @property
    def dx(self) -> float:
        return convert_length(self._get_parameter("dx", "float"),
                              from_unit="m", to_unit=self._simulation.__getattribute__("_global_units"))

    @dx.setter
    def dx(self, dx: float):
        self.settings.general.set_maximum_mesh_step(dx=dx)

    @property
    def dy(self) -> float:
        return convert_length(self._get_parameter("dy", "float"),
                              from_unit="m", to_unit=self._simulation.__getattribute__("_global_units"))

    @dy.setter
    def dy(self, dy: float):
        self.settings.general.set_maximum_mesh_step(dy=dy)

    @property
    def dz(self) -> float:
        return convert_length(self._get_parameter("dz", "float"),
                              from_unit="m", to_unit=self._simulation.__getattribute__("_global_units"))

    @dz.setter
    def dz(self, dz: float):
        self.settings.general.set_maximum_mesh_step(dz=dz)

    def _get_active_parameters(self) -> Optional[_Settings]:
        settings = self._Settings.initialize_empty()
        settings.general_settings = self.settings.general.__getattribute__("_get_active_parameters")()
        if not settings.general_settings:
            return None
        settings.geometry_settings = self.settings.general.__getattribute__("_get_active_parameters")()
        settings.fill_hash_fields()
        return settings


########################################################################################################################
#                                     FDTD SIMULATION REGION CLASSES
########################################################################################################################

#============================ FDTD General Settings ============================
class FDTDGeneralSettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        dimension: DIMENSION
        simulation_time: float
        simulation_temperature: float
        background_material: MATERIALS
        index: float

    __slots__ = SettingTab.__slots__

    def set_dimension(self, dimension: DIMENSION) -> None:
        """
        Set the dimension of the simulation region.

        The dimension can be either 2D or 3D, affecting how the simulation is performed
        and the parameters that are available.

        Args:
            dimension (DIMENSION): The dimension of the simulation (2D or 3D).
        """
        Validate.in_literal(dimension, "dimension", DIMENSION)
        self._set_parameter("dimension", dimension, "str")

    def set_simulation_time(self, simulation_time: float) -> None:
        """
        Set the maximum duration of the simulation.

        The simulation time is specified in femtoseconds (fs). The actual simulation may
        terminate early if the autoshutoff criteria are met before reaching this maximum time.

        Args:
            simulation_time (float): Maximum simulation time in femtoseconds (fs).

        Raises:
            ValueError: If the provided simulation time is negative.
        """
        Validate.positive_number(simulation_time, "simulation_time")
        self._set_parameter("simulation time", simulation_time, "float")

    def set_simulation_temperature(self, simulation_temperature: float) -> None:
        """
        Set the temperature for the simulation.

        This temperature setting is used for simulations that include temperature-dependent
        objects, and it is specified in Kelvin (K).

        Args:
            simulation_temperature (float): Simulation temperature in Kelvin (K).

        Raises:
            ValueError: If the provided temperature is not positive.
        """
        Validate.positive_number(simulation_temperature, "simulation_temperature")
        self._set_parameter("simulation temperature", simulation_temperature, "float")

    def set_background_material(self, material: MATERIALS, index: float = None) -> None:
        """
        Set the background material for the simulation.

        Optionally, a refractive index can be provided if the selected material is
        "<Object defined dielectric>". This allows for a more specific simulation setup
        based on the dielectric properties of the material.

        Args:
            material (MATERIALS): The material to be used for the background.
            index (float, optional): The refractive index to be set if the material is
                                     "<Object defined dielectric>".

        Raises:
            ValueError:
                If the material is "<Object defined dielectric>" but no index is provided.
                If a non-dielectric material is provided but an index is given.
        """

        # Set the background material parameter
        self._set_parameter("background material", material, "str")

        # Check for specific conditions related to "<Object defined dielectric>"
        if material == "<Object defined dielectric>" and index is None:
            raise ValueError(
                "A refractive index must be provided when the material is set to '<Object defined dielectric>'."
            )
        elif material != "<Object defined dielectric>" and index is not None:
            raise ValueError(
                f"The material '{material}' does not support a refractive index. Remove the index argument."
            )
        elif material == "<Object defined dielectric>" and index is not None:
            # Set the index if applicable
            self._set_parameter("index", index, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.__getattribute__("_update")({
            "dimension": self._get_parameter("dimension", "str"),
            "simulation_time": self._get_parameter("simulation time", "float"),
            "simulation_temperature": self._get_parameter("simulation temperature", "float"),
            "background_material": self._get_parameter("background material", "str"),
            "index": self._get_parameter("index", "float")
        })
        settings.fill_hash_fields()
        return settings


#============================ FDTD Mesh Settings ============================
class FDTDMeshTypeSubsettings(SettingTab):
    class _MaxStepKwargs(AxesFloatKwargs, total=False):
        units: Optional[LENGTH_UNITS]

    class _DefineMeshByKwargs(TypedDict, total=False):
        x_definition: DEFINE_MESH_BY
        y_definition: DEFINE_MESH_BY
        z_definition: DEFINE_MESH_BY

    @dataclass
    class _Settings(Settings):
        mesh_definitions: MeshDefinitions
        gradings: Gradings
        stepsizes: Stepsizes
        mesh_cells: MeshCells
        mesh_type: MESH_TYPE
        mesh_accuracy: int
        mesh_cells_per_wavelength: float

    __slots__ = SettingTab.__slots__

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

        Validate.in_literal(mesh_type, "mesh_type", MESH_TYPE)
        self._set_parameter("mesh type", mesh_type, "str")

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
        current_mesh_type = self._get_parameter("mesh type", "str")

        if current_mesh_type != "auto non-uniform":
            raise ValueError("Mesh accuracy can only be set when the mesh type is 'auto non-uniform'.")

        Validate.integer_in_range(mesh_accuracy, "mesh_accuracy", (1, 8))
        self._set_parameter("mesh accuracy", mesh_accuracy, "int")

    def define_mesh_by(self, **kwargs: Unpack[_DefineMeshByKwargs]) -> None:
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
        current_mesh_type = self._get_parameter("mesh type", "str")

        # Ensure the mesh type is either 'Custom non-uniform' or 'Uniform'
        if current_mesh_type not in ["custom non-uniform", "uniform"]:
            raise ValueError("Mesh type must be 'custom non-uniform' or 'uniform' to define mesh by.")

        valid_arguments = list(self._DefineMeshByKwargs.__annotations__.keys())
        for axis, definition in kwargs.items():
            Validate.in_list(axis, axis, valid_arguments)
            Validate.in_literal(definition, axis, DEFINE_MESH_BY)
            self._set_parameter(f"define {axis[0]} mesh by", definition, "str")

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
        current_mesh_type = self._get_parameter("mesh type", "str")

        # Ensure the mesh type is 'custom non-uniform'
        if current_mesh_type != "custom non-uniform":
            raise ValueError("Mesh type must be 'custom non-uniform' to allow mesh grading.")

        for axis, truth in kwargs.items():

            # Fetch the 'define {axis} mesh by' parameter
            define_mesh_by = self._get_parameter(f"define {axis} mesh by", "str")

            # Raise an error if it is set to 'number of mesh cells'
            if define_mesh_by == "number of mesh cells":
                raise ValueError(
                    f"Mesh grading cannot be allowed when 'define {axis} mesh by' is set to 'number of mesh cells'.")

            Validate.axis(axis)
            Validate.boolean(truth, axis)
            self._set_parameter(f"allow grading in {axis}", truth, "bool")

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
        current_mesh_type = self._get_parameter("mesh type", "str")

        # Ensure the mesh type is 'custom non-uniform'
        if current_mesh_type != "custom non-uniform":
            raise ValueError("Mesh type must be 'custom non-uniform' to set the grading factor.")
        Validate.number_in_range(grading_factor, "grading_factor", (1.01, 2))
        self._set_parameter("grading factor", grading_factor, "float")

    def set_maximum_mesh_step(self, **kwargs: Unpack[_MaxStepKwargs]) -> None:
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
        current_mesh_type = self._get_parameter("mesh type", "str")

        # Ensure the mesh type is 'custom non-uniform' or 'uniform'
        if current_mesh_type not in {"custom non-uniform", "uniform"}:
            raise ValueError("The mesh type must be 'custom non-uniform' or 'uniform' to set the maximum mesh step.")

        units = kwargs.pop("units", None)
        if units is None:
            units = self._simulation.__getattribute__("_global_units")
        else:
            Validate.in_literal(units, "units", LENGTH_UNITS)
        for axis, value in kwargs.items():

            Validate.axis(axis)

            # Fetch the current definition for the specified axis
            definition = self._get_parameter(f"define {axis} mesh by", "str")

            # Ensure the definition is either 'maximum mesh step' or
            # 'max mesh step and mesh cells per wavelength'
            if definition not in {"maximum mesh step", "max mesh step and mesh cells per wavelength"}:
                raise ValueError(
                    f"The definition for '{axis}' mesh must be either 'maximum mesh step' or "
                    "'max mesh step and mesh cells per wavelength', but it is currently '{definition}'."
                )
            max_step = convert_length(value, units, "m")  # type: ignore
            self._set_parameter(f"d{axis}", max_step, "float")

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
        mesh_type = self._get_parameter("mesh type", "str")

        # Ensure the mesh type is 'custom non-uniform'
        if mesh_type != "custom non-uniform":
            raise ValueError(f"The mesh type must be 'custom non-uniform', but it is currently '{mesh_type}'.")

        # Set the parameter for mesh cells per wavelength
        self._set_parameter("mesh cells per wavelength", mesh_cells, "float")

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
        current_mesh_type = self._get_parameter("mesh type", "str")

        # Ensure the mesh type is 'custom non-uniform' or 'uniform'
        if current_mesh_type not in {"custom non-uniform", "uniform"}:
            raise ValueError("The mesh type must be 'custom non-uniform' or 'uniform' to set the number of mesh cells.")

        for axis, value in kwargs.items():

            Validate.axis(axis)

            # Fetch the current definition for the specified axis
            definition = self._get_parameter(f"define {axis} mesh by", "str")

            # Ensure the definition is 'number of mesh cells'
            if definition != "number of mesh cells":
                raise ValueError(
                    f"The definition for '{axis}' mesh must be 'number of mesh cells', "
                    f"but it is currently '{definition}'."
                )

            Validate.positive_integer(value, "nr")
            self._set_parameter(f"mesh cells {axis}", value, "int")

    def _get_active_parameters(self) -> _Settings:

        settings = self._Settings.initialize_empty()

        settings.mesh_type = self._get_parameter("mesh type", "str")

        if settings.mesh_type == "auto non-uniform":
            settings.mesh_accuracy = self._get_parameter("mesh accuracy", "int")

        else:
            for axis in get_args(AXES):
                definition = self._get_parameter(f"define {axis} mesh by", "str")
                settings.mesh_definitions.__setattr__(f"define_{axis}_mesh_by", definition)
                if definition in ["maximum mesh step", "max mesh step and mesh cells per wavelength"]:
                    settings.stepsizes.__setattr__(f"d{axis}", self._get_parameter(f"d{axis}", "float"))

                elif definition == "number of mesh cells":
                    settings.mesh_cells.__setattr__(f"mesh_cells_{axis}",
                                                    self._get_parameter(f"mesh cells {axis}", "int"))

            if settings.mesh_type == "custom non-uniform":
                settings.mesh_cells_per_wavelength = self._get_parameter("mesh cells per wavelength", "float")

                for axis in get_args(AXES):
                    settings.gradings.__setattr__(f"allow_grading_in_{axis}",
                                                  self._get_parameter(f"allow grading in {axis}", "bool"))

                if any([settings.gradings.__getattribute__(f"allow_grading_in_{axis}") for axis in get_args(AXES)]):
                    settings.gradings.grading_factor = self._get_parameter("grading factor", "float")

        settings.fill_hash_fields()
        return settings


class FDTDMeshRefinementSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        mesh_refinement: MESH_REFINEMENT
        meshing_refinement: int

    __slots__ = SettingTab.__slots__

    def set_staircase(self) -> None:
        """
        Set the mesh refinement method to Staircasing.

        This method configures the mesh refinement approach to use the Staircasing
        technique. In this method, the material properties at each position of the
        Yee cell are evaluated, using only the properties of the material at that
        location for the E-field calculation.

        Limitations:
        - This approach does not account for variations within a Yee cell, resulting
          in a "staircase" permittivity mesh that aligns with the Cartesian mesh.
        - Layer thickness cannot be resolved more finely than the mesh step size,
          limiting the resolution of structure details.

        Usage:
        - Ideal for simulations where high resolution and material variation
          within the Yee cell are not critical.
        """

        self._set_parameter("mesh refinement", "staircase", "str")

    def set_conformal_variant_0(self) -> None:
        """
        Set the mesh refinement method to Conformal Variant 0.

        This method configures the mesh refinement approach to use Conformal
        Variant 0. In this variant, Lumerical's Conformal Mesh Technology (CMT)
        is not applied to interfaces involving metals or Perfect Electrical
        Conductors (PEC). This approach leverages a rigorous physical description
        of Maxwell's equations to handle material interfaces, but does not enhance
        accuracy for metallic interfaces.

        Benefits:
        - Suitable for simulations involving dielectric materials where metal
          interfaces do not require special handling.
        - Can improve accuracy for dielectric interfaces compared to the
          Staircasing method.

        Usage:
        - Ideal when modeling materials that do not involve PEC or metal
          interfaces, allowing for improved simulation performance.
        """

        self._set_parameter("mesh refinement", "conformal variant 0", "str")

    def set_conformal_variant_1(self) -> None:
        """
        Set the mesh refinement method to Conformal Variant 1.

        This method configures the mesh refinement approach to use Conformal
        Variant 1, where Lumerical's Conformal Mesh Technology (CMT) is applied
        to all materials, including Perfect Electrical Conductors (PEC) and metals.
        This variant provides enhanced accuracy for a given mesh size, allowing for
        faster simulations without sacrificing accuracy.

        Benefits:
        - Provides greater accuracy in simulations involving a wider variety of
          materials, including metals and PEC.
        - Can significantly reduce computation time while maintaining accuracy.

        Usage:
        - Suitable for general simulations requiring robust handling of material
          interfaces, particularly when both dielectric and metallic materials are present.
        """

        self._set_parameter("mesh refinement", "conformal variant 1", "str")

    def set_conformal_variant_2(self) -> None:
        """
        Set the mesh refinement method to Conformal Variant 2.

        This method configures the mesh refinement approach to use Conformal
        Variant 2, which applies Lumerical's Conformal Mesh Technology (CMT)
        to all materials except for interfaces involving Perfect Electrical
        Conductors (PEC) and metals, where the Yu-Mittra method 1 is employed.
        This variant allows for greater accuracy in modeling interfaces while
        still improving performance compared to traditional methods.

        Benefits:
        - Combines the benefits of CMT for general material interfaces with
          improved handling of PEC and metallic interfaces via the Yu-Mittra method 1.
        - Provides a balanced approach for accuracy and simulation speed.

        Usage:
        - Ideal for simulations that involve complex material interfaces, especially
          those containing both dielectric and PEC materials.
        """

        self._set_parameter("mesh refinement", "conformal variant 2", "str")

    def set_dielectric_volume_average(self, meshing_refinement: float = None) -> None:
        """
        Set the mesh refinement method to Dielectric Volume Average.

        This method configures the mesh refinement approach to utilize the
        dielectric volume average method. This method averages the permittivity
        of dielectric materials within each Yee cell by dividing the cell into
        subcells. The average permittivity is calculated based on the volume
        fraction of dielectric materials present. The method is particularly useful
        for low index contrast dielectric structures.

        Parameters:
        - meshing_refinement: A float value representing the refinement level for
          the meshing process. This parameter determines how finely the cell is
          subdivided to achieve the volume average. Higher values will yield more
          precise results but may increase computational costs.

        Benefits:
        - Provides a simple yet effective way to handle dielectric interfaces
          within Yee cells.
        - Suitable for cases where low index contrast spatial variations are present,
          allowing for effective averaging of permittivity.

        Usage:
        - Ideal for simulations where dielectric materials dominate and non-dielectric
          materials are either absent or present only in minimal amounts.

        Raises:
        - Any exceptions related to parameter setting in the simulation,
          including invalid values for meshing_refinement.
        """

        self._set_parameter("mesh refinement", "dielectric volume average", "str")
        if meshing_refinement is not None:
            self._set_parameter("meshing refinement", meshing_refinement, "float")

    def set_volume_average(self) -> None:
        """
        Set the mesh refinement method to Volume Average.

        This method configures the mesh refinement approach to utilize the
        volume average method. In this approach, the permittivity of each Yee cell
        is calculated as the simple volume average of the permittivities of the
        materials present in that cell. This method allows for the inclusion of
        multiple dispersive materials and provides a straightforward way to model
        their interactions.

        Benefits:
        - Suitable for simulating scenarios where the interaction of two materials
          within a Yee cell is important.
        - Provides a reasonable balance between accuracy and computational efficiency
          compared to more complex methods.

        Usage:
        - Ideal for simulations that require a basic yet effective treatment of
          permittivity averaging in regions with two materials.
        """

        self._set_parameter("mesh refinement", "volume average", "str")

    def set_Yu_Mittra_method_1(self) -> None:
        """
        Set the mesh refinement method to Yu-Mittra Method 1.

        This method configures the simulation to use Yu-Mittra Method 1 for mesh refinement.
        This approach enhances the accuracy when modeling interfaces between perfect electric
        conductors (PEC) and dielectric materials. It evaluates the electric field by
        considering only the region outside the PEC where the electric field is non-zero.

        Benefits:
        - Provides improved accuracy for simulations involving PEC/dielectric interfaces.
        - Extends the original Yu-Mittra formulation to accommodate arbitrary dispersive media.

        Usage:
        - Recommended for cases where precision at PEC interfaces is critical for the simulation
          results.
        """

        self._set_parameter("mesh refinement", "Yu-Mittra method 1", "str")

    def set_Yu_Mittra_method_2(self) -> None:
        """
        Set the mesh refinement method to Yu-Mittra Method 2.

        This method configures the simulation to use Yu-Mittra Method 2 for mesh refinement.
        This approach improves accuracy when modeling dielectric interfaces by assigning an
        effective permittivity to each material component in the Yee cell, weighted by the
        fraction of the mesh step that is inside each material.

        Benefits:
        - Enhances simulation fidelity when dealing with dielectric interfaces with spatial
          variations in permittivity.
        - Suitable for scenarios where precise modeling of permittivity distribution is necessary.

        Usage:
        - Ideal for simulations that involve complex dielectric interactions and require
          higher accuracy in permittivity averaging.
        """

        self._set_parameter("mesh refinement", "Yu-Mittra method 2", "str")

    def set_precise_volume_average(self, meshing_refinement: float = None) -> None:
        """
        Set the mesh refinement method to Precise Volume Average.

        This method configures the simulation to use the Precise Volume Average approach for
        mesh refinement. It provides a highly sensitive meshing technique that accurately
        calculates the average permittivity in the mesh cells, especially important for
        photonic inverse design.

        Parameters:
        - meshing_refinement: A float value that specifies the level of refinement for the
          meshing process. This parameter enhances the accuracy of permittivity averaging,
          with a default value of 5 (can be increased up to 12 for maximum precision).

        Benefits:
        - Allows for fine-tuned accuracy in simulations that require sensitive adjustments
          to small geometric variations, such as those needed for accurate gradient
          calculations in inverse design processes.
        - It is memory intensive but essential for applications demanding high precision.

        Usage:
        - Recommended for scenarios where small variations in geometry or permittivity can
          significantly affect simulation outcomes, particularly in advanced photonic design.
        """

        self._set_parameter("mesh refinement", "precise volume average", "str")
        if meshing_refinement is not None:
            self._set_parameter("meshing refinement", meshing_refinement, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.mesh_refinement = self._get_parameter("mesh refinement", "str")
        if settings.mesh_refinement in ["volume average", "precise volume average"]:
            settings.meshing_refinement = self._get_parameter("meshing refinement", "int")
        settings.fill_hash_fields()
        return settings


class FDTDMeshSettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        hash: str
        mesh_type_settings: FDTDMeshTypeSubsettings._Settings
        mesh_refinement_settings: FDTDMeshRefinementSubsettings._Settings
        dt_stability_factor: float
        min_mesh_step: float

    # Helper lists for initialization/refreshing
    _settings = [FDTDMeshTypeSubsettings, FDTDMeshRefinementSubsettings]
    _settings_names = ["mesh_type_settings", "mesh_refinement_settings"]

    mesh_type_settings: FDTDMeshTypeSubsettings
    mesh_refinement_settings: FDTDMeshRefinementSubsettings
    __slots__ = SettingTab.__slots__ + _settings_names

    def set_dt_stability_factor(self, factor: float) -> None:
        """
        Set the time step stability factor for the simulation.

        The DT Stability Factor determines the size of the time step used during the
        simulation, defined as a fraction of the Courant numerical stability limit. A
        larger factor will lead to faster simulation times, while a smaller factor will
        result in slower simulation times.

        Note: The Courant stability condition requires that this factor be less than 1
        for the FDTD algorithm to remain numerically stable.

        Args:
            factor (float): The stability factor for the time step, where a value
                            less than 1 ensures numerical stability in the simulation.

        Raises:
            ValueError: If the factor is not a positive number.
        """

        Validate.positive_number(factor, "factor")
        self._set_parameter("dt stability factor", factor, "float")

    def set_min_mesh_step(self, min_step: Union[int, float], units: LENGTH_UNITS = None) -> None:
        """
        Set the absolute minimum mesh size for the entire solver region.

        The MIN MESH STEP defines the smallest allowable mesh size for the simulation.
        This value overrides all other mesh size settings, including those specified
        in mesh override regions. It ensures that the solver maintains a consistent
        mesh size across the entire simulation domain, which is crucial for
        maintaining numerical stability and accuracy.

        Args:
            min_step (Union[int, float]): The minimum mesh size to be set. This can be
                                           provided as either an integer or a float.
            units (LENGTH_UNITS, optional): The units in which the min_step is specified.
                                             If not provided, the global units of the
                                             simulation will be used.

        Raises:
            ValueError: If the min_step is a non-positive value, as mesh size must be
                        greater than zero.
        """
        if min_step <= 0:
            raise ValueError("The minimum mesh step must be a positive value.")

        if units is None:
            units = self._simulation.__getattribute__("_global_units")
        else:
            Validate.in_literal(units, "units", LENGTH_UNITS)

        min_step = convert_length(min_step, units, "m")
        self._set_parameter("min mesh step", min_step, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.mesh_type_settings = self.mesh_type_settings.__getattribute__("_get_active_parameters")()
        settings.mesh_refinement_settings = self.mesh_refinement_settings.__getattribute__("_get_active_parameters")()
        settings.dt_stability_factor = self._get_parameter("dt stability factor", "float")
        settings.min_mesh_step = self._get_parameter("min mesh step", "float")
        settings.fill_hash_fields()
        return settings


#============================ FDTD Boundary Conditions Settings ============================
class FDTDPMLSubsettings(SettingTab):
    class _BoundariesKwargs(TypedDict, total=False):
        x_min: Any
        x_max: Any
        y_min: Any
        y_max: Any
        z_min: Any
        z_max: Any

    class _ProfileKwargs(TypedDict, total=False):
        x_min: PML_PROFILES
        x_max: PML_PROFILES
        y_min: PML_PROFILES
        y_max: PML_PROFILES
        z_min: PML_PROFILES
        z_max: PML_PROFILES

    class _IntKwargs(TypedDict, total=False):
        x_min: int
        x_max: int
        y_min: int
        y_max: int
        z_min: int
        z_max: int

    class _FloatKwargs(TypedDict, total=False):
        x_min: Union[float, int]
        x_max: Union[float, int]
        y_min: Union[float, int]
        y_max: Union[float, int]
        z_min: Union[float, int]
        z_max: Union[float, int]

    @dataclass
    class _Settings(Settings):
        same_settings_on_all_boundaries: bool
        x_min_bc: Optional[PMLBoundarySettings]
        x_max_bc: Optional[PMLBoundarySettings]
        y_min_bc: Optional[PMLBoundarySettings]
        y_max_bc: Optional[PMLBoundarySettings]
        z_min_bc: Optional[PMLBoundarySettings]
        z_max_bc: Optional[PMLBoundarySettings]
        extend_structure_through_pml: bool
        auto_scale_pml_parameters: bool

    __slots__ = SettingTab.__slots__

    def set_stretched_coordinate_PML(self) -> None:
        """
        Set the PML type to stretched coordinate PML.

        This is the default and recommended option for PML settings
        in simulations. The stretched coordinate PML is based on
        the formulation proposed by Gedney and Zhao and provides
        effective absorption characteristics.
        """

        self._set_parameter("pml type", "stretched coordinate PML", "str")

    def set_uniaxial_anisotropic_PML(self) -> None:
        """
        Set the PML type to legacy uniaxial anisotropic PML.

        This option provides a legacy formulation of PML that is
        rarely used in practice. It may be suitable for specific
        scenarios but is not the default choice.
        """

        self._set_parameter("type", "uniaxial anisotropic PML (legacy)", "str")

    def set_same_settings_on_all_boundaries(self, true_or_false: bool) -> None:
        """
        Set whether to apply the same PML settings to all boundaries.

        When enabled, all PML boundaries will share the same settings.
        Disabling this option allows for individual customization of
        PML profiles for each boundary, which can significantly reduce
        simulation times by allowing adjustments only where necessary.

        Parameters:
        - true_or_false: A boolean indicating whether to use the same
          PML settings for all boundaries.
        """

        Validate.boolean(true_or_false, "true_or_false")
        extend = self._get_parameter("extend structure through pml", "bool")
        auto_scale = self._get_parameter("auto scale pml parameters", "bool")
        self._set_parameter("same settings on all boundaries", true_or_false, "bool")
        self.auto_scale_pml_parameters(auto_scale)
        self.extend_structure_through_pml(extend)

    def _set_value(self, parameter_name: str, **kwargs: Unpack[_BoundariesKwargs]) -> None:
        """Helper function to set pml boundary settings."""

        self._set_parameter("same settings on all boundaries", False, "bool")

        valid_boundaries = self._BoundariesKwargs.__annotations__
        boundary_types = {boundary: self._get_parameter(f"{boundary.replace("_", " ")} bc", "str")
                          for boundary in valid_boundaries}
        boundary_to_index_map = {boundary: i for i, boundary in enumerate(valid_boundaries)}
        prev_values = np.array(self._get_parameter(parameter_name, "list")).flatten().tolist()
        profiles = np.array(self._get_parameter("pml profile", "list")).flatten().tolist()
        idx_to_p = {(i + 1): profile for i, profile in enumerate(get_args(PML_PROFILES))}

        for b, value in kwargs.items():
            if b not in valid_boundaries:
                raise ValueError(f"'{b}' is not a valid boundary. Choose from {valid_boundaries}.")
            elif (parameter_name in ["pml kappa", "pml sigma", "pml polynomial", "pml alpha",
                                     "pml alpha polynomial", "pml min layers", "pml max layers"]
                  and idx_to_p[profiles[boundary_to_index_map[b]]] != "custom"):

                raise ValueError(f"You are trying to set the '{parameter_name}' parameter of boundary '{b}', which "
                                 f"'pml profile' is currently set to '{idx_to_p[profiles[boundary_to_index_map[b]]]}'. "
                                 f"To set this parameter you must first set the pml profile to custom.")

            if boundary_types[b] != "PML":
                warnings.warn(f"Setting '{parameter_name}' on boundary '{b}' will not have any effect, as it is "
                              f"of type '{boundary_types[b]}', not 'PML'.")

            prev_values[boundary_to_index_map[b]] = value

        # Convert to numpy array and transpose to match the format we fetch from the simulation
        new_values = np.array([np.array([value]) for value in prev_values])

        # Supress the warnings that comes if the set value differs from the one accepted by the simulation
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")

            accepted_values = cast(np.ndarray, self._set_parameter(parameter_name, new_values, "list"))

            if not caught_warnings:
                return

            warning = (f"\nMethod: set_{parameter_name.split("pml ")[1].replace(" ", "_")}\n"
                       "The following values accepted by the simulation enviroment differs from the input values:\n")
            for b, new_value, accepted_value in zip(valid_boundaries, new_values, accepted_values):
                if parameter_name in ["pml layers", "pml min layers", "pml max layers", "pml polynomial"]:
                    new_value = int(new_value[0])
                    accepted_value = int(accepted_value[0])
                else:
                    new_value = new_value[0]
                    accepted_value = accepted_value[0]

                if new_value != accepted_value:
                    warning += f"\t{b}: input value={new_value}, accepted value={accepted_value}\n"

        warnings.warn(warning)

    def set_profile(self, **kwargs: Unpack[_ProfileKwargs]) -> None:
        """
        Sets the PML (Perfectly Matched Layer) profile for the simulation boundaries.

        This method allows the user to specify a PML profile, which determines the absorption properties
        of the PML boundaries in the simulation region. The choice of profile can affect the numerical behavior
        and performance of the simulation.

        Available profiles:
            - **Standard**: Provides good overall absorption with a relatively small number of layers.
              It is recommended when structures extend completely through the PML region and there are no material
              boundaries cutting through PML regions.

            - **Stabilized**: Designed to enhance stability when material boundaries cut through PML regions.
              It may require a higher number of layers compared to the standard profile to achieve similar absorption performance,
              but it effectively mitigates numerical instabilities.

            - **Steep Angle**: Similar to the standard profile but optimized for use with periodic boundary conditions.
              It provides enhanced absorption when light travels nearly parallel to the PML boundaries,
              though it may be less absorptive at coarse discretizations.

            - **Custom**: Allows users to define all PML parameter values manually.
              This profile starts with the parameters of the standard profile and is suitable for advanced users who wish to experiment.

        Raises:
            ValueError:
                - If the specified profile is not valid.
                - If the specified boundary is not valid.
        """

        profile_to_index_map = {profile: i + 1 for i, profile in enumerate(get_args(PML_PROFILES))}
        kwargs = dict(**kwargs)
        for b, value in kwargs.items():
            Validate.in_literal(value, "pml_profile", PML_PROFILES)
            kwargs[b] = profile_to_index_map[value]
        self._set_value("pml profile", **kwargs)

    def set_layers(self, **kwargs: Unpack[_IntKwargs]) -> None:
        """
        Sets the number of PML layers for the specified boundaries.

        PML boundaries occupy a finite volume surrounding the simulation region and are divided into layers
        for discretization. The number of layers can significantly affect the absorption properties of the PML.
        Generally, increasing the number of layers leads to lower reflections but may also increase simulation time.

        Raises:
            ValueError:
                - If the provided boundary is invalid.
                - If the provided value is not a positive integer.
        """
        self._set_parameter("same settings on all boundaries", False, "bool")
        min_layers = self._get_parameter("pml min layers", "list")
        min_layers = {b: v for b, v in zip(self._BoundariesKwargs.__annotations__, min_layers)}
        max_layers = self._get_parameter("pml max layers", "list")
        max_layers = {b: v for b, v in zip(self._BoundariesKwargs.__annotations__, max_layers)}
        for b, value in kwargs.items():
            Validate.positive_integer(value, "pml_layers")
            if value < min_layers[b]:
                raise ValueError(f"You are trying to set the 'layers' parameter for boundary '{b}' to '{value}', "
                                 f"but the 'min layers' parameter is currently '{int(min_layers[b][0])}'. Change the "
                                 f"'min layers' parameter if you want to set the nr of layers to this value.")
            elif value > max_layers[b]:
                raise ValueError(f"You are trying to set the 'layers' parameter for boundary '{b}' to '{value}', "
                                 f"but the 'max layers' parameter is currently '{int(max_layers[b][0])}'. Change the "
                                 f"'max layers' parameter if you want to set the nr of layers to this value.")

        self._set_value("pml layers", **kwargs)

    def set_kappa(self, **kwargs: Unpack[_FloatKwargs]) -> None:
        """
        Sets the kappa parameter for PML boundaries.

        Kappa is a unitless parameter that controls the absorption properties of the PML regions.
        It is graded inside the PML using polynomial functions. The effective range of kappa should
        be carefully chosen to ensure optimal absorption without compromising numerical stability.

        Raises:
            ValueError:
                - If the specified boundary is invalid
                - If the specified value is a positive number.
        """

        for b, value in kwargs.items():
            Validate.positive_number(value, "pml_kappa")
        self._set_value("pml kappa", **kwargs)

    def set_sigma(self, **kwargs: Unpack[_FloatKwargs]) -> None:
        """
        Sets the sigma parameter for PML boundaries.

        Sigma is another unitless parameter that contributes to the absorption properties of PML regions.
        It must be entered as a normalized unitless value. Increasing sigma can enhance absorption but
        may also impact stability, particularly when combined with the alpha parameter.

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive number.
        """

        for b, value in kwargs.items():
            Validate.positive_number(value, "pml_sigma")
        self._set_value("pml sigma", **kwargs)

    def set_polynomial(self, **kwargs: Unpack[_IntKwargs]) -> None:
        """
        Sets the polynomial order for grading kappa and sigma in PML boundaries.

        The polynomial order specifies how kappa and sigma are graded inside the PML regions.
        Higher-order polynomials can improve the absorption characteristics of the PML but may
        also complicate the numerical stability.

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive integer.
        """

        for b, value in kwargs.items():
            Validate.positive_number(value, "pml_polynomial")
        self._set_value("pml polynomial", **kwargs)

    def set_alpha(self, **kwargs: Unpack[_FloatKwargs]) -> None:
        """
        Sets the alpha parameter for PML boundaries.

        Alpha is a unitless parameter that influences the absorption properties of the PML regions.
        This parameter can only be set if the PML type is "stretched coordinate PML."

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive number
        """

        if self._get_parameter("pml type", "str") != "stretched coordinate PML":
            raise ValueError("'alpha' can only be set when PML type is 'stretched coordinate PML'.")
        for b, value in kwargs.items():
            Validate.positive_number(value, "pml_alpha")
        self._set_value("pml alpha", **kwargs)

    def set_alpha_polynomial(self, **kwargs: Unpack[_FloatKwargs]) -> None:
        """
        Sets the alpha polynomial order for PML boundaries.

        The alpha polynomial order specifies how alpha is graded inside the PML regions.
        This parameter can only be set if the PML type is "stretched coordinate PML."

        Raises:
            ValueError:
                - If the specified boundary is invalid.
                - If the specified value is not a positive number.
        """

        if self._get_parameter("pml type", "str") != "stretched coordinate PML":
            raise ValueError("'alpha polynomial' can only be set when PML type is 'stretched coordinate PML'.")
        for b, value in kwargs.items():
            Validate.positive_number(value, 'pml_alpha_polynomial')
        self._set_value("pml alpha polynomial", **kwargs)

    def set_min_layers(self, **kwargs: Unpack[_IntKwargs]) -> None:
        """
        Sets the minimum number of PML layers for the specified boundaries.

        The minimum number of layers enforces a lower limit on how many layers
        are used in the PML region, which can influence the absorption performance.
        Setting a sensible minimum is important to ensure that the PML can effectively
        absorb outgoing waves without significant reflections.

        Raises:
            ValueError:
                - If the provided boundary is invalid.
                - If the provided value is not a positive integer.
        """

        for b, value in kwargs.items():
            Validate.positive_integer(value, "pml_min_layers")
        self._set_value("pml min layers", **kwargs)

    def set_max_layers(self, **kwargs: Unpack[_IntKwargs]) -> None:
        """
        Sets the maximum number of PML layers for the specified boundaries.

        The maximum number of layers enforces an upper limit on how many layers
        can be used in the PML region. This can help manage simulation performance,
        as excessively high layer counts may lead to longer simulation times without
        significant improvements in absorption.

        Raises:
            ValueError:
                - If the provided boundary is invalid.
                - If the provided value is not a positive integer.
        """

        for b, value in kwargs.items():
            Validate.positive_integer(value, "pml_min_layers")
        self._set_value("pml max layers", **kwargs)

    def extend_structure_through_pml(self, true_or_false: bool) -> None:
        """
        Sets whether structures that touch the inner PML boundary should be extended
        in the direction normal to the boundary.

        If enabled, this option will automatically extend any structures
        that are in contact with the inner PML boundary. This is useful for
        ensuring that the structures are adequately represented in the PML region,
        as illustrated in the accompanying images. However, this behavior may not be
        suitable for all types of structures, particularly those that should not
        extend into the PML.

        If the extension is not desired, this option can be disabled, allowing
        the user to manually draw the structure through the PML.

        Parameters:
            true_or_false (bool):
                True to enable the extension of structures through PML,
                False to disable it and allow manual drawing of the structures.

        Raises:
            ValueError: If the input is not a boolean value.
        """

        Validate.boolean(true_or_false, "true_or_false")
        self._set_parameter("extend structure through pml", true_or_false, "bool")

    def auto_scale_pml_parameters(self, true_or_false: bool) -> None:
        """
        Sets whether the PML parameters should be automatically scaled
        based on variations in the time step (dt) during the simulation.

        Enabling this option allows the PML to adjust its parameters
        to maintain optimal absorption performance when the time step
        becomes significantly smaller than expected. This can occur
        due to regions with a very fine mesh or the use of a reduced
        "dt stability factor." Automatic scaling helps ensure that
        the PML remains effective, preserving the accuracy and stability
        of the simulation.

        Parameters:
            true_or_false (bool):
                True to enable automatic scaling of PML parameters,
                False to disable it.

        Raises:
            ValueError: If the input is not a boolean value.
        """

        Validate.boolean(true_or_false, "true_or_false")
        self._set_parameter("auto scale pml parameters", true_or_false, "bool")

    def _get_active_parameters(self) -> _Settings:

        settings = self._Settings.initialize_empty()

        settings.same_settings_on_all_boundaries = self._get_parameter("same settings on all boundaries", "bool")
        settings.extend_structure_through_pml = self._get_parameter("extend structure through pml", "bool")
        settings.auto_scale_pml_parameters = self._get_parameter("auto scale pml parameters", "bool")

        pml_type = self._get_parameter("pml type", "str")

        boundary_keys = [boundary.replace(" ", "_") for boundary in get_args(BOUNDARIES)]
        boundary_types = [self._get_parameter(boundary, "str") for boundary in get_args(BOUNDARIES)]
        int_to_profile = {1: "standard", 2: "stabilized", 3: "steep angle", 4: "custom"}
        boundary_to_index = {"x_min_bc": 0, "x_max_bc": 1, "y_min_bc": 2, "y_max_bc": 3, "z_min_bc": 4, "z_max_bc": 5}

        if settings.same_settings_on_all_boundaries:

            pml_boundary_settings = PMLBoundarySettings.initialize_empty()
            pml_boundary_settings.__getattribute__("_update")({
                "pml_type": pml_type,
                "pml_profile": int_to_profile[self._get_parameter("pml profile", "int")],
                "pml_layers": self._get_parameter("pml layers", "int"),
                "pml_kappa": self._get_parameter("pml kappa", "float"),
                "pml_sigma": self._get_parameter("pml sigma", "float"),
                "pml_polynomial": self._get_parameter("pml polynomial", "float"),
                "pml_min_layers": self._get_parameter("pml min layers", "int"),
                "pml_max_layers": self._get_parameter("pml max layers", "int"),
            })

            if pml_type == "stretched coordinate PML":
                pml_boundary_settings.pml_alpha = self._get_parameter("pml alpha", "float")
                pml_boundary_settings.pml_alpha_polynomial = self._get_parameter("pml alpha polynomial", "float")

            pml_boundary_settings.fill_hash_fields()

            for boundary, boundary_type in zip(boundary_keys, boundary_types):

                if boundary_type == "PML":
                    settings.__setattr__(boundary, pml_boundary_settings)
                else:
                    settings.__setattr__(boundary, None)

        else:

            pml_profiles = self._get_parameter("pml profile", "list")
            pml_layers = self._get_parameter("pml layers", "list")
            pml_kappas = self._get_parameter("pml kappa", "list")
            pml_sigmas = self._get_parameter("pml sigma", "list")
            pml_polynomials = self._get_parameter("pml polynomial", "list")
            pml_min_layers = self._get_parameter("pml min layers", "list")
            pml_max_layers = self._get_parameter("pml max layers", "list")
            if pml_type == "stretched coordinate PML":
                pml_alphas = self._get_parameter("pml alpha", "list")
                pml_alpha_polynomials = self._get_parameter("pml alpha polynomial", "list")
            else:
                pml_alphas = None
                pml_alpha_polynomials = None

            for boundary, boundary_type in zip(boundary_keys, boundary_types):

                if boundary_type != "PML":
                    settings.__setattr__(boundary, None)
                    continue

                pml_boundary_settings = PMLBoundarySettings.initialize_empty()

                pml_boundary_settings._update({
                    "pml_type": pml_type,
                    "pml_profile": int_to_profile[int(pml_profiles[boundary_to_index[boundary]])],
                    "pml_layers": int(pml_layers[boundary_to_index[boundary]]),
                    "pml_kappa": float(pml_kappas[boundary_to_index[boundary]]),
                    "pml_sigma": float(pml_sigmas[boundary_to_index[boundary]]),
                    "pml_polynomial": float(pml_polynomials[boundary_to_index[boundary]]),
                    "pml_min_layers": int(pml_min_layers[boundary_to_index[boundary]]),
                    "pml_max_layers": int(pml_max_layers[boundary_to_index[boundary]])
                })

                if pml_type == "stretched coordinate PML":
                    pml_boundary_settings.pml_alpha = float(pml_alphas[boundary_to_index[boundary]])
                    pml_boundary_settings.pml_polynomial = float(pml_alpha_polynomials[boundary_to_index[boundary]])

                pml_boundary_settings.fill_hash_fields()
                settings.__setattr__(boundary, pml_boundary_settings)

        pml_boundaries = [settings.__getattribute__(boundary) for boundary in boundary_keys]
        pml_boundaries = [pml_boundary for pml_boundary in pml_boundaries if pml_boundary is not None]
        different_settings = has_different_objects(pml_boundaries)
        settings.same_settings_on_all_boundaries = not different_settings
        settings.fill_hash_fields()
        return settings


class FDTDBlochSubsettings(SettingTab):
    class _KKwargs(TypedDict, total=False):
        kx: float
        ky: float
        kz: float

    @dataclass
    class _Settings(Settings):
        set_based_on_source_angle: bool
        bloch_units: BLOCH_UNITS
        k_vectors: KVector

    __slots__ = SettingTab.__slots__

    def based_on_source_angle(self, true_or_false: bool) -> None:
        """
        Sets whether the wave vector components (kx, ky, kz) for Bloch boundary conditions
        should be determined based on the source angle in the current simulation.

        When this option is enabled, the values of kx, ky, and kz are automatically
        calculated based on the angle of the defined source. This is particularly useful
        when injecting plane waves at specific angles into periodic structures. If
        multiple sources are defined, all must require consistent Bloch settings for
        this feature to work correctly.

        By default, this option is enabled. If disabled, the user must manually set
        kx, ky, and kz.

        Parameters:
            true_or_false (bool):
                True to enable automatic determination of kx, ky, and kz based on
                the source angle; False to disable this feature and set kx, ky,
                and kz manually.

        Raises:
            ValueError: If the input is not a boolean value.
        """

        Validate.boolean(true_or_false, "true_or_false")
        self._set_parameter("set based on source angle", true_or_false, "bool")

    def set_bloch_units(self, bloch_units: BLOCH_UNITS) -> None:
        """
        Sets the units used for specifying the values of kx, ky, and kz in Bloch boundary conditions.

        Two types of units are allowed:

        - **Bandstructure Units**: In these units, kx, ky, and kz are defined in terms of
          (2pi/a_x, 2pi/a_y, 2pi/a_z), where (a_x, a_y, a_z) are the x, y, and z spans of the FDTD simulation region.
          These units are particularly convenient for bandstructure calculations.

        - **SI Units**: In SI units, kx, ky, and kz are defined in units of 1/m.
          This is generally more convenient for the injection of plane waves at specific angles.

        Parameters:
            bloch_units (BLOCH_UNITS):
                The units to be used for kx, ky, and kz, which should be one of the
                predefined values in the BLOCH_UNITS enumeration.

        Raises:
            ValueError: If the provided units are not valid.
        """

        Validate.in_literal(bloch_units, "bloch_units", BLOCH_UNITS)
        self._set_parameter("bloch units", bloch_units, "str")

    def set_k(self, **kwargs: Unpack[_KKwargs]) -> None:
        """
        Sets the values of the wavevector components for the Bloch symmetry conditions. If the boundaries
        corresponding to the wavevector compontent is not a Bloch boundary, a ValueError will be raised.
        """
        valid_arguments = kwargs.__annotations__.keys()
        for k, value in kwargs.items():
            if k not in valid_arguments:
                raise ValueError(f"'{k}' is not a valid k-vector component. Choose from {valid_arguments}.")
            elif self._get_parameter(f"{k[1]} min bc", "str") != "Bloch":
                raise ValueError(f"You cannot set '{k}' when the min and max {k[1]} boundaries "
                                 f"are not Bloch boundaries.")
            Validate.number(value, k)
            self._set_parameter(k, value, "float")

    def _get_active_parameters(self) -> Optional[_Settings]:

        settings = self._Settings.initialize_empty()

        boundary_types = [self._get_parameter(boundary, "str") for boundary in get_args(BOUNDARIES)]
        bloch_boundaries = [boundary_type for boundary_type in boundary_types if boundary_type == "Bloch"]
        if bloch_boundaries:
            based_on_source_angle = self._get_parameter("set based on source angle", "bool")
            settings.bloch_units = self._get_parameter("bloch units", "str")
            settings.k_vectors.__getattribute__("_update")({"kx": self._get_parameter(f"kx", "float"),
                                                            "ky": self._get_parameter(f"ky", "float"),
                                                            "kz": self._get_parameter(f"kz", "float")})
            settings.fill_hash_fields()
            settings.set_based_on_source_angle = based_on_source_angle
            return settings
        else:
            return None


class FDTDBoundariesSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        x_min_bc: BOUNDARY_TYPES
        x_max_bc: BOUNDARY_TYPES
        y_min_bc: BOUNDARY_TYPES
        y_max_bc: BOUNDARY_TYPES
        z_min_bc: BOUNDARY_TYPES
        z_max_bc: BOUNDARY_TYPES

    __slots__ = SettingTab.__slots__

    class _BoundaryTypesKwargs(TypedDict, total=False):
        x_min: BOUNDARY_TYPES_LOWER
        x_max: BOUNDARY_TYPES_LOWER
        y_min: BOUNDARY_TYPES_LOWER
        y_max: BOUNDARY_TYPES_LOWER
        z_min: BOUNDARY_TYPES_LOWER
        z_max: BOUNDARY_TYPES_LOWER

    def set_boundary_types(self, **kwargs: Unpack[_BoundaryTypesKwargs]) -> None:
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

        valid_boundaries = self._BoundaryTypesKwargs.__annotations__
        valid_types = get_args(BOUNDARY_TYPES_LOWER)
        for b, b_type in kwargs.items():
            if b not in self._BoundaryTypesKwargs.__annotations__:
                raise ValueError(f"'{b}' is not a valid boundary. Choose from {valid_boundaries}.")
            elif b_type not in valid_types:
                raise ValueError(f"'{b_type}' is not a valid boundary type. Choose from {valid_types}.")

            if "max" in b:
                if b_type in ["symmetric", "anti-symmetric"]:
                    self._set_parameter("allow symmetry on all boundaries", True, "bool")

            b_type = b_type.split("-")
            b_type = "-".join([word.capitalize() for word in b_type])

            self._set_parameter(f"{b.replace("_", " ")} bc", b_type, "str")

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

        Validate.boolean(true_or_false, "true_or_false")
        self._set_parameter("allow symmetry on all boundaries", true_or_false, "bool")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        for boundary in get_args(BOUNDARIES):
            settings.__setattr__(boundary.replace(" ", "_"), self._get_parameter(boundary, "str"))
        settings.fill_hash_fields()
        return settings


class FDTDBoundaryConditionsSettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        boundary_settings: FDTDBoundariesSubsettings._Settings
        pml_settings: FDTDPMLSubsettings._Settings
        bloch_settings: FDTDBlochSubsettings._Settings

    _settings = [FDTDPMLSubsettings, FDTDBlochSubsettings, FDTDBoundariesSubsettings]
    _settings_names = ["pml_settings", "bloch_settings", "boundary_settings"]

    boundary_settings: FDTDBoundariesSubsettings
    bloch_settings: FDTDBlochSubsettings
    pml_settings: FDTDPMLSubsettings
    __slots__ = SettingTab.__slots__ + _settings_names

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.boundary_settings = self.boundary_settings.__getattribute__("_get_active_parameters")()
        settings.bloch_settings = self.bloch_settings.__getattribute__("_get_active_parameters")()
        settings.pml_settings = self.pml_settings.__getattribute__("_get_active_parameters")()
        settings.fill_hash_fields()
        return settings


#============================ FDTD Advanced Settings ============================
class FDTDSimulationBandwidthSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        set_simulation_bandwidth: bool
        simulation_wavelength_min: float
        simulation_wavelength_max: float

    __slots__ = SettingTab.__slots__

    def set_simulation_bandwidth(self, true_or_false: bool, min_wavelength: float = None,
                                 max_wavelength: float = None, units: LENGTH_UNITS = None) -> None:
        """
        Set the simulation bandwidth directly, allowing for greater control over the
        simulation parameters.

        By default, the simulation bandwidth is inherited from the source bandwidth.
        Enabling this option allows the user to specify the minimum and maximum
        wavelengths for the simulation, affecting various aspects such as mesh generation,
        material fits, and monitor frequency ranges.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable (True) or disable (False)
          direct setting of the simulation bandwidth.

        - min_wavelength: The minimum wavelength for the simulation bandwidth. If provided,
          it will override the inherited value. The value must be convertible to meters.
          Default is None.

        - max_wavelength: The maximum wavelength for the simulation bandwidth. If provided,
          it will override the inherited value. The value must be convertible to meters.
          Default is None.

        - units: The units for the wavelengths (e.g., nm, um). If None, the global units
          from the simulation will be used.

        Raises:
        - ValueError: If min_wavelength or max_wavelength are provided but are invalid
          (e.g., negative values, incompatible types).

        Usage:
        - This method should be used when fine control over the simulation bandwidth is necessary,
          particularly in scenarios where the characteristics of the simulation depend heavily
          on the specified wavelength range.
        """

        self._set_parameter("set simulation bandwidth", true_or_false, "bool")

        if units is None:
            units = self._simulation.__getattribute__("_global_units")

        if true_or_false:
            if min_wavelength is not None:
                min_wavelength = convert_length(float(min_wavelength), units, "m")
                self._set_parameter("simulation wavelength min", min_wavelength, "float")
            if max_wavelength is not None:
                max_wavelength = convert_length(float(max_wavelength), units, "m")
                self._set_parameter("simulation wavelength max", max_wavelength, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.set_simulation_bandwidth = self._get_parameter("set simulation bandwidth", "bool")
        if settings.set_simulation_bandwidth:
            settings.simulation_wavelength_min = self._get_parameter("simulation wavelength min", "float")
            settings.simulation_wavelength_max = self._get_parameter("simulation wavelength max", "float")
        settings.fill_hash_fields()
        return settings


class FDTDAdvancedMeshSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        force_symmetric_x_mesh: bool
        force_symmetric_y_mesh: bool
        force_symmetric_z_mesh: bool
        override_simulation_bandwidth_for_mesh_generation: bool
        mesh_wavelength_min: float
        mesh_wavelength_max: float
        snap_pec_to_yee_cell_boundary: bool

    __slots__ = SettingTab.__slots__

    def force_symmetric_mesh(self, **kwargs: Unpack[AxesBoolKwargs]) -> None:
        """
        Force a symmetric mesh about the specified axes (x, y, or z) in the simulation.

        When this option is enabled, the meshing algorithm only considers objects in the
        positive half of the simulation region. The mesh in the negative half is generated
        as a direct copy of the positive half mesh. Consequently, any physical structures
        and mesh override regions in the negative half will not be considered by the
        meshing algorithm. Additionally, this option ensures a mesh point is placed at
        the center of the simulation region.

        This method is particularly useful for ensuring consistent mesh behavior when
        transitioning between simulations with and without symmetry.

        Raises:
            ValueError:
                - If the provided axis is not "x", "y", or "z".
                - If the argument value is not a boolean value

        Usage:
        - Call this method when you want to simplify the meshing process for simulations
          that exhibit symmetry, ensuring computational efficiency and consistency in the
          generated mesh structure.
        """

        for axis, truth in kwargs.items():
            Validate.axis(axis)
            Validate.boolean(truth, axis)
            self._set_parameter(f"force symmetric {axis} mesh", truth, "bool")

    def override_simulation_bandwidth_for_mesh_generation(self, override: bool, min_wavelength: float = None,
                                                          max_wavelength: float = None,
                                                          units: LENGTH_UNITS = None) -> None:
        """
        Override the simulation bandwidth for mesh generation with a custom wavelength
        or frequency range.

        By default, the simulation bandwidth is inherited from the source bandwidth.
        Enabling this option allows the user to define a specific wavelength or frequency
        range for generating the simulation mesh. This can be useful for fine-tuning the
        mesh generation process based on specific requirements that differ from the source
        parameters.

        Parameters:
        - override: A boolean value indicating whether to enable (True) or disable (False)
          the override of the simulation bandwidth for mesh generation.

        - min_wavelength: The minimum wavelength (in the specified units) for mesh generation.
          If provided, it will set the lower limit of the wavelength range.

        - max_wavelength: The maximum wavelength (in the specified units) for mesh generation.
          If provided, it will set the upper limit of the wavelength range.

        - units: The length units to be used for the min and max wavelengths. If not
          specified, the global units of the simulation will be used.

        Raises:
        - ValueError: If the provided min_wavelength or max_wavelength is negative or
          invalid.
        - ValueError: If the provided length units are invalid.

        Usage:
        - Call this method when you need to customize the wavelength range for the mesh
          generation, especially in cases where the source bandwidth does not align with
          the desired simulation parameters.
        """

        self._set_parameter("override simulation bandwidth for mesh generation", override, "bool")

        if units is None:
            units = self._simulation.__getattribute__("_global_units")

        if override:
            if min_wavelength is not None:
                min_wavelength = convert_length(float(min_wavelength), units, "m")
                self._set_parameter("mesh wavelength min", min_wavelength, "float")

            if max_wavelength is not None:
                max_wavelength = convert_length(float(max_wavelength), units, "m")
                self._set_parameter("mesh wavelength max", max_wavelength, "float")

    def snap_pec_to_yee_cell_boundary(self, true_or_false: bool) -> None:
        """
        Snap PEC structures to Yee cell boundaries for proper alignment of interfaces.

        This option forces structures defined as Perfect Electric Conductors (PEC) to have
        their interfaces aligned with the boundaries of the Yee cells. This alignment ensures
        that all electric field components at the PEC interface are tangential, preventing
        complications that can arise if normal electric field components are inadvertently
        set to zero at the PEC interface.

        When this option is enabled, the PEC interface may be shifted by as much as
        dx/2 (where dx is the size of the Yee cell) during the simulation mesh creation.
        This adjustment helps maintain the accuracy and integrity of the simulation results.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable (True) or disable (False)
          the snapping of PEC structures to Yee cell boundaries.

        Usage:
        - Call this method when you want to ensure that PEC interfaces are correctly aligned
          with the Yee cell boundaries, particularly in simulations involving PEC materials.

        Raises:
        - ValueError: If the provided true_or_false value is not a boolean.
        """

        Validate.boolean(true_or_false, "true_or_false")
        self._set_parameter("snap pec to yee cell boundary", true_or_false, "bool")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.snap_pec_to_yee_cell_boundary = self._get_parameter("snap pec to yee cell boundary", "bool")
        settings.force_symmetric_x_mesh = self._get_parameter("force symmetric x mesh", "bool")
        settings.force_symmetric_y_mesh = self._get_parameter("force symmetric y mesh", "bool")
        settings.force_symmetric_z_mesh = self._get_parameter("force symmetric z mesh", "bool")
        settings.override_simulation_bandwidth_for_mesh_generation = \
            self._get_parameter("override simulation bandwidth for mesh generation", "bool")
        if settings.override_simulation_bandwidth_for_mesh_generation:
            settings.mesh_wavelength_min = self._get_parameter("mesh wavelength min", "float")
            settings.mesh_wavelength_max = self._get_parameter("mesh wavelength max", "float")
        settings.fill_hash_fields()
        return settings


class FDTDAutoShutoffSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        use_early_shutoff: bool
        auto_shutoff_min: float
        use_divergence_checking: bool
        auto_shutoff_max: float
        down_sample_time: int

    __slots__ = SettingTab.__slots__

    def use_early_shutoff(self, true_or_false: bool, auto_shutoff_min: float = None) -> None:
        """
        Enable or disable early shutoff for the simulation based on energy levels.

        This method configures the simulation to automatically terminate when
        most of the energy has exited the simulation volume. By enabling early
        shutoff, you can save computation time by preventing the simulation
        from running longer than necessary.

        When enabled, the simulation will end when the total energy in the
        simulation volume falls to the specified fraction of the maximum
        energy injected. The simulation data will be automatically saved at
        this point.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable (True)
          or disable (False) the early shutoff feature.
        - auto_shutoff_min: An optional float specifying the minimum fraction
          of maximum energy injected at which the simulation should terminate.
          This parameter is only considered if early shutoff is enabled.

        Usage:
        - Call this method when you want to implement early shutoff for your
          simulation, particularly useful in long-running simulations where
          energy loss is a key consideration.

        Raises:
        - ValueError: If the provided true_or_false value is not a boolean.
        """

        self._set_parameter("use early shutoff", true_or_false, "bool")

        if true_or_false and auto_shutoff_min is not None:
            Validate.positive_number(auto_shutoff_min, "auto_shutoff_min")
            self._set_parameter("auto shutoff min", auto_shutoff_min, "float")

    def use_divergence_checking(self, true_or_false: bool, auto_shutoff_max: float = None) -> None:
        """
        Enable or disable divergence checking for the simulation.

        This method allows the simulation to automatically terminate when
        the total energy in the simulation volume exceeds a specified
        multiple of the maximum energy injected. This feature is useful
        for preventing runaway simulations that could lead to excessive
        resource usage or invalid results.

        Parameters:
        - true_or_false: A boolean value indicating whether to enable
          (True) or disable (False) divergence checking.
        - auto_shutoff_max: An optional float specifying the maximum
          factor by which the total energy in the simulation volume can
          exceed the maximum energy injected before the simulation is
          automatically ended. If this parameter is provided, it is
          validated to ensure it is a positive number.

        Usage:
        - Call this method to configure the divergence checking behavior
          in the simulation. This ensures that the simulation can safely
          shut down if energy levels become unmanageable.

        Raises:
        - ValueError: If auto_shutoff_max is provided but is not a
          positive number.
        """

        self._set_parameter("use divergence checking", true_or_false, "bool")

        if true_or_false and auto_shutoff_max is not None:
            Validate.positive_number(auto_shutoff_max, "auto_shutoff_max")
            self._set_parameter("auto shutoff max", auto_shutoff_max, "float")

    def set_down_sample_time(self, down_sample_time: int) -> None:
        """
        Set the down sample time for checking auto shutoff conditions.

        This method specifies the interval at which the simulation checks
        the auto shutoff conditions. The simulation will evaluate whether
        to terminate based on energy levels every `down_sample_time`
        number of `dT` time steps.

        Setting a down sample time allows for efficient monitoring of the
        simulation's energy status without requiring continuous checks,
        which can improve performance.

        Parameters:
        - down_sample_time: An integer representing the number of time
          steps (dT) between each evaluation of the auto shutoff conditions.
          A value of 1 means that the conditions will be checked at every
          time step, while a larger value will reduce the frequency of checks.

        Usage:
        - Call this method to configure how often the simulation evaluates
          the auto shutoff conditions, allowing for better performance tuning
          in long simulations.

        Raises:
        - ValueError: If down_sample_time is not a positive integer.
        """

        Validate.positive_integer(down_sample_time, "down_sample_time")
        self._set_parameter("down sample time", down_sample_time, "int")

    def _get_active_parameters(self) -> _Settings:

        settings = self._Settings.initialize_empty()

        settings.use_early_shutoff = self._get_parameter("use early shutoff", "bool")
        settings.use_divergence_checking = self._get_parameter("use divergence checking", "bool")
        settings.down_sample_time = self._get_parameter("down sample time", "int")

        if settings.use_early_shutoff:
            settings.auto_shutoff_min = self._get_parameter("auto shutoff min", "float")

        if settings.use_divergence_checking:
            settings.auto_shutoff_max = self._get_parameter("auto shutoff max", "float")

        settings.fill_hash_fields()
        return settings


class FDTDParalellEngineSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        set_process_grid: bool
        nx: int
        ny: int
        nz: int

    __slots__ = SettingTab.__slots__

    def set_process_grid(self, true_or_false: bool, nx: int = None, ny: int = None, nz: int = None) -> None:
        """
        Configure the process grid for dividing the simulation volume into
        sub-regions for parallel computation.

        This method allows users to set up a grid that divides the
        simulation volume into multiple processes, which can improve
        computational efficiency and performance during simulation runs.
        By specifying the number of subdivisions in the x, y, and z
        directions, users can tailor the processing setup to better
        utilize available computational resources.

        Parameters:
        - true_or_false: A boolean indicating whether to enable
          (True) or disable (False) the process grid configuration.
        - nx: An optional integer specifying the number of divisions
          along the x-axis. This parameter is only relevant if
          true_or_false is set to True.
        - ny: An optional integer specifying the number of divisions
          along the y-axis. This parameter is only relevant if
          true_or_false is set to True.
        - nz: An optional integer specifying the number of divisions
          along the z-axis. This parameter is only relevant if
          true_or_false is set to True.

        Usage:
        - This method should be called to configure the process grid
          for the simulation. Properly setting up the grid can lead to
          better performance and more efficient resource usage.

        Raises:
        - ValueError: If any of nx, ny, or nz are provided as
          negative integers.
        """

        self._set_parameter("set process grid", true_or_false, "bool")

        if true_or_false:
            if nx is not None:
                Validate.positive_integer(nx, "nx")
                self._set_parameter("nx", nx, "int")
            if ny is not None:
                Validate.positive_integer(ny, "ny")
                self._set_parameter("ny", ny, "int")
            if nz is not None:
                Validate.positive_integer(nz, "nz")
                self._set_parameter("nz", nz, "int")

    def _get_active_parameters(self) -> _Settings:

        settings = self._Settings.initialize_empty()

        settings.set_process_grid = self._get_parameter("set process grid", "bool")
        if settings.set_process_grid:
            settings.__getattribute__("_update")({"nx": self._get_parameter("nx", "int"),
                                                  "ny": self._get_parameter("ny", "int"),
                                                  "nz": self._get_parameter("nz", "int")})
        settings.fill_hash_fields()
        return settings


class FDTDCheckpointSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        checkpoint_during_simulation: bool
        checkpoint_period: int
        checkpoint_at_shutoff: bool

    __slots__ = SettingTab.__slots__

    def set_checkpoint_during_simulation(self, true_or_false: bool, checkpoint_period: int = None) -> None:
        """
        Configure the creation of checkpoints during the simulation.

        This method allows users to enable or disable the creation of
        checkpoints at specified intervals during the simulation run.
        Checkpoints are useful for saving the state of the simulation
        at regular intervals, which can help in recovering from
        unexpected interruptions or failures. The frequency of these
        checkpoints is determined by the checkpoint_period parameter.

        Parameters:
        - true_or_false: A boolean indicating whether to enable
          (True) or disable (False) checkpointing during the simulation.
        - checkpoint_period: An optional integer specifying the
          interval (in time steps) at which checkpoints should be
          created. This parameter is only relevant if
          true_or_false is set to True.

        Usage:
        - This method should be called to configure checkpointing for
          the simulation, ensuring that critical progress is saved
          at regular intervals.

        Raises:
        - ValueError: If checkpoint_period is provided as a negative
          integer.
        """

        self._set_parameter("set checkpoint during simulation", true_or_false, "bool")

        if true_or_false and checkpoint_period is not None:
            Validate.positive_integer(checkpoint_period, "checkpoint_period")
            self._set_parameter("checkpoint period", checkpoint_period, "int")

    def set_checkpoint_at_shutoff(self, true_or_false: bool) -> None:
        """
        Configure the creation of checkpoints at simulation shutoff.

        This method allows users to enable or disable the creation of
        checkpoints whenever the simulation ends, except in cases
        where the "Quit and Don't Save" option is selected.
        This feature is useful for preserving the state of the
        simulation for future analysis or review, ensuring that data
        is not lost when the simulation concludes.

        Parameters:
        - true_or_false: A boolean indicating whether to enable
          (True) or disable (False) checkpoint creation at the
          simulation shutoff.

        Usage:
        - This method should be called to configure whether a
          checkpoint should be created automatically upon
          simulation completion.

        Note:
        - The checkpoint will only be created if the simulation ends
          normally and does not include the "Quit and Don't Save"
          option.
        """

        Validate.boolean(true_or_false, "true_or_false")
        self._set_parameter("set checkpoint at shutoff", true_or_false, "bool")

    def _get_active_parameters(self) -> _Settings:

        settings = self._Settings.initialize_empty()

        settings.checkpoint_during_simulation = self._get_parameter("checkpoint during simulation", "bool")
        settings.checkpoint_at_shutoff = self._get_parameter("checkpoint at shutoff", "bool")

        if settings.checkpoint_during_simulation:
            settings.checkpoint_period = self._get_parameter("checkpoint period", "int")

        settings.fill_hash_fields()
        return settings


class FDTDBFASTSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        bfast_alpha: float
        bfast_dt_multiplier: float

    __slots__ = SettingTab.__slots__

    def set_BFAST_alpha(self, bfast_alpha: float) -> None:
        """
        Set the BFAST alpha parameter for the simulation.

        The BFAST alpha parameter represents the smallest dielectric
        refractive index in the simulation region. It is generally
        recommended to set this value to 1; however, if a different
        background index is used (for example, 1.33 for water), this
        value should reflect that instead of the default of 1.

        This parameter is crucial for accurately modeling the
        electromagnetic behavior in the simulation, particularly
        in regions where the dielectric properties significantly
        affect the results.

        Parameters:
        - bfast_alpha: A float representing the smallest dielectric
          refractive index in the simulation region.

        Usage:
        - This method should be called to configure the BFAST alpha
          value based on the dielectric properties of the medium
          being simulated.

        Raises:
        - ValueError: If bfast_alpha is less than or equal to 0,
          which would be an invalid refractive index.
        """

        Validate.positive_number(bfast_alpha, "bfast_alpha")
        self._set_parameter("bfast alpha", bfast_alpha, "float")

    def set_BFAST_dt_multiplier(self, dt_multiplier: float) -> None:
        """
        Set the BFAST time step multiplier for the simulation.

        The BFAST time step multiplier is used to further reduce the
        time step ("dt") in the mesh settings, complementing the
        existing "dt factor." The maximum value for this multiplier
        is 1, indicating no change to the time step. When the
        multiplier is set to a value smaller than 1, it effectively
        reduces the actual time step "dt." This can be particularly
        useful for mitigating diverging problems that cannot be
        resolved by modifying other simulation settings.

        Parameters:
        - dt_multiplier: A float representing the BFAST time step
          multiplier. Must be in the range (0, 1] to effectively
          reduce the time step.

        Raises:
        - ValueError: If dt_multiplier is not greater or equal to zero.
        """

        Validate.positive_number(dt_multiplier, "dt_multiplier")
        self._set_parameter("bfast dt multiplier", dt_multiplier, "float")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.bfast_alpha = self._get_parameter("bfast alpha", "float")
        settings.bfast_dt_multiplier = self._get_parameter("bfast dt multiplier", "float")
        settings.fill_hash_fields()
        return settings


class FDTDMiscellaneousSubsettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        always_use_complex_fields: bool
        max_source_time_signal_length: int

    __slots__ = SettingTab.__slots__

    def set_always_use_complex_fields(self, true_or_false: bool) -> None:
        """
        Set the option to always use complex fields during simulation.

        This method enables or disables the use of complex fields
        for the simulation. When enabled, the algorithm will utilize
        complex fields throughout the simulation process, which may
        lead to slower simulation times and increased memory usage.
        This setting is generally recommended only when necessary.
        By default, complex fields are utilized only when Bloch
        boundary conditions are applied.

        As of version 2024 R2, this setting is compatible with the
        FDTD GPU solver, allowing for improved performance with
        complex fields on compatible hardware. It's important to
        note that if Bloch boundary conditions are selected, complex
        fields will be utilized regardless of the state of this
        checkbox.

        Parameters:
        - true_or_false: A boolean value indicating whether to
          always use complex fields (True) or not (False).
        """

        Validate.boolean(true_or_false, "true_or_false")
        self._set_parameter("always use complex fields", true_or_false, "bool")

    def set_max_source_time_signal_length(self, length: int) -> None:
        """
        Set the maximum length of data used by sources to store the
        "time" and "time_signal" properties.

        This method allows advanced users to specify the maximum
        length for the data related to time and time signals in
        sources. Reducing this length can save memory, especially
        in simulations that utilize a large number of sources or
        when the simulation time is on the order of 100 picoseconds
        (ps), which is uncommon. However, caution should be taken
        when adjusting this parameter, as the "time" and "time_signal"
        properties are crucial for calculating source power, source
        normalization, and the normalization for transmission functions.

        Parameters:
        - length: An integer representing the maximum length of data
          for the "time" and "time_signal" properties. Should be a positive integer greater
          than or equal to 32.
        """

        Validate.integer_in_range(length, "length", (32, float('inf')))
        self._set_parameter("max source time length signal", length, "int")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.always_use_complex_fields = self._get_parameter("always use complex fields", "bool")
        settings.max_source_time_signal_length = self._get_parameter("max source time signal length", "int")
        settings.fill_hash_fields()
        return settings


class FDTDAdvancedSettings(SettingTab):
    @dataclass
    class _Settings(Settings):
        simulation_bandwidth: FDTDSimulationBandwidthSubsettings._Settings
        mesh_settings: FDTDAdvancedMeshSubsettings._Settings
        auto_shutoff: FDTDAutoShutoffSubsettings._Settings
        paralell_engine_options: FDTDParalellEngineSubsettings._Settings
        checkpoint_options: FDTDCheckpointSubsettings._Settings
        bfast_settings: FDTDBFASTSubsettings._Settings
        miscellaneous: FDTDMiscellaneousSubsettings._Settings

    # Helper lists for initialization/refreshing
    _settings = [FDTDSimulationBandwidthSubsettings, FDTDAdvancedMeshSubsettings, FDTDAutoShutoffSubsettings,
                 FDTDParalellEngineSubsettings, FDTDCheckpointSubsettings, FDTDBFASTSubsettings,
                 FDTDMiscellaneousSubsettings]
    _settings_names = ["simulation_bandwidth_settings", "mesh_settings", "auto_shutoff_settings",
                       "paralell_engine_settings", "checkpoint_settings", "bfast_settings", "misc_settings"]

    simulation_bandwidth_settings: FDTDSimulationBandwidthSubsettings
    mesh_settings: FDTDAdvancedMeshSubsettings
    auto_shutoff_settings: FDTDAutoShutoffSubsettings
    paralell_engine_settings: FDTDParalellEngineSubsettings
    checkpoint_settings: FDTDCheckpointSubsettings
    bfast_settings: FDTDBFASTSubsettings
    misc_settings: FDTDMiscellaneousSubsettings
    __slots__ = SettingTab.__slots__ + _settings_names

    def set_express_mode(self, true_or_false: bool) -> None:
        """Enables the express mode, which has something to do with running FDTD on GPU."""

        self._set_parameter("express mode", true_or_false, "bool")

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.simulation_bandwidth = self.simulation_bandwidth_settings.__getattribute__("_get_active_parameters")()
        settings.mesh_settings = self.mesh_settings.__getattribute__("_get_active_parameters")()
        settings.auto_shutoff = self.auto_shutoff_settings.__getattribute__("_get_active_parameters")()
        settings.paralell_engine_options = self.paralell_engine_settings.__getattribute__("_get_active_parameters")()
        settings.checkpoint_options = self.checkpoint_settings.__getattribute__("_get_active_parameters")()
        settings.bfast_settings = self.bfast_settings.__getattribute__("_get_active_parameters")()
        settings.miscellaneous = self.misc_settings.__getattribute__("_get_active_parameters")()
        settings.fill_hash_fields()
        return settings


#============================ FDTD Region Simulation Object ============================
class FDTDRegion(SimulationObject, TrippleSpansProperties, MinMaxDirectProperties):
    class _SettingsCollection(SimulationObject._SettingsCollection):

        _settings = [FDTDGeneralSettings, TrippleSpannableGeometryAbsolute, FDTDMeshSettings,
                     FDTDBoundaryConditionsSettings, FDTDAdvancedSettings]
        _settings_names = ["general", "geometry", "mesh",
                           "boundary_conditions", "advanced"]

        general: FDTDGeneralSettings
        geometry: TrippleSpannableGeometryAbsolute
        mesh: FDTDMeshSettings
        boundary_conditions: FDTDBoundaryConditionsSettings
        advanced: FDTDAdvancedSettings
        __slots__ = SimulationObject._SettingsCollection.__slots__ + _settings_names

    class _Kwargs(PositionKwargs, total=False):
        x_span: float
        y_span: float
        z_span: float

    @dataclass
    class _MeshGrid(Settings):
        x_grid: np.ndarray
        y_grid: np.ndarray
        z_grid: np.ndarray
        x_min_bc_pml_thickness: float
        x_max_bc_pml_thickness: float
        y_min_bc_pml_thickness: float
        y_max_bc_pml_thickness: float
        z_min_bc_pml_thickness: float
        z_max_bc_pml_thickness: float

        def get_meshed_grid(self) -> np.ndarray:
            X, Y, Z = np.meshgrid(self.x_grid, self.y_grid, self.z_grid, indexing="ij")
            grid = np.stack((X, Y, Z), axis=-1)
            return grid

    @dataclass
    class _Settings(Settings):
        general_settings: FDTDGeneralSettings._Settings
        geometry_settings: TrippleSpannableGeometryRelative._Settings
        mesh_settings: FDTDMeshSettings._Settings
        boundary_conditions: FDTDBoundaryConditionsSettings._Settings
        advanced_settings: FDTDAdvancedSettings._Settings

    _settings = [_SettingsCollection]
    _settings_names = ["settings"]

    settings: _SettingsCollection
    __slots__ = SimulationObject.__slots__ + _settings_names

    def __init__(self, simulation: TSimulation, **kwargs: Unpack[FDTDRegion._Kwargs]) -> None:
        super().__init__(name="FDTD", simulation=simulation, **kwargs)

    def _get_mesh_grid_and_pml_thickness(self) -> _MeshGrid:
        """
        Returns a dataclass with the mesh grids in all directions and the thickness of each pml-boundary.
        """
        mesh_grid = self._MeshGrid.initialize_empty()

        boundary_settings = (
            self.settings.boundary_conditions.boundary_settings.__getattribute__("_get_active_parameters")())
        pml_settings = self.settings.boundary_conditions.pml_settings.__getattribute__("_get_active_parameters")()

        grids = {"x": np.round(self._simulation.__getattribute__("_lumapi").getresult("FDTD", "x").flatten(),
                               decimals=DECIMALS),
                 "y": np.round(self._simulation.__getattribute__("_lumapi").getresult("FDTD", "y").flatten(),
                               decimals=DECIMALS),
                 "z": np.round(self._simulation.__getattribute__("_lumapi").getresult("FDTD", "z").flatten(),
                               decimals=DECIMALS)}

        for boundary in ["x_min_bc", "x_max_bc", "y_min_bc", "y_max_bc", "z_min_bc", "z_max_bc"]:
            if boundary_settings.__getattribute__(boundary) == "PML":
                if "min" in boundary:
                    first_mesh_delta = grids[boundary[0]][1] - grids[boundary[0]][0]
                    thickness = first_mesh_delta * pml_settings.__getattribute__(boundary).pml_layers
                    mesh_grid.__setattr__(boundary + "_pml_thickness", thickness)
                else:
                    last_mesh_delta = grids[boundary[0]][-1] - grids[boundary[0]][-2]
                    thickness = last_mesh_delta * pml_settings.__getattribute__(boundary).pml_layers
                    mesh_grid.__setattr__(boundary + "_pml_thickness", thickness)

        mesh_grid.x_grid = grids["x"]
        mesh_grid.y_grid = grids["y"]
        mesh_grid.z_grid = grids["z"]

        return mesh_grid

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.general_settings = self.settings.general.__getattribute__("_get_active_parameters")()
        settings.geometry_settings = self.settings.geometry.__getattribute__("_get_active_parameters")()
        settings.mesh_settings = self.settings.mesh.__getattribute__("_get_active_parameters")()
        settings.boundary_conditions = self.settings.boundary_conditions.__getattribute__("_get_active_parameters")()
        settings.advanced_settings = self.settings.advanced.__getattribute__("_get_active_parameters")()
        settings.fill_hash_fields()
        return settings
