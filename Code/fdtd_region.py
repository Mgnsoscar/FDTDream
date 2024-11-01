from __future__ import annotations

# Standard library imports
from typing import Literal, Union, List, TypedDict, get_args, Unpack, Optional

# Third-party imports
import numpy as np
from lumapi_import import lumapi

# Local imports
from base_classes import SettingTab, SubsettingTab
from simulation_object import SimulationObject
from local_resources import Validate
from local_resources import convert_length
from type_hint_resources import MATERIALS, AXES, LENGTH_UNITS
from geometry import CartesianGeometry

########################################################################################################################
#                                         LITERALS AND CONSTANTS
########################################################################################################################

DIMENSION = Literal["2D", "3D"]
BOUNDARY_TYPES = Literal["PML", "Metal", "Periodic", "Symmetric", "Anti-Symmetric", "Bloch", "PMC"]
BOUNDARIES = Literal["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]
PML_PARAMETERS = Literal["profile", "layers", "kappa", "sigma", "polynomial", "alpha", "alpha_polynomial",
                         "min_layers", "max_layers"]
PML_PROFILES = Literal["standard", "stabilized", "steep angle", "custom"]
PML_TYPES = Literal["stretched coordinate PML", "uniaxial anisotropic PML (legacy)"]
BLOCH_UNITS = Literal["bandstructure", "SI"]
DEFINE_MESH_BY = Literal["mesh cells per wavelength", "maximum mesh step",
                         "max mesh step and mesh cells per wavelength", "number of mesh cells"]
MESH_REFINEMENT = Literal["staircase", "conformal variant 0", "conformal variant 1", "conformal variant 2",
                          "dielectric volume average", "volume average", "Yu-Mittra method 1", "Yu-Mittra method 2",
                          "precise volume average"]
MESH_TYPE = Literal["auto non-uniform", "custom non-uniform", "uniform"]

########################################################################################################################
#                                              GEOMETRY CLASSES
########################################################################################################################


class MeshGeometry(CartesianGeometry):

    class _SettingsDict(CartesianGeometry._SettingsDict):
        buffer: float

    __slots__ = CartesianGeometry.__slots__

    def set_based_on_a_structure(self, structure: 'StructureBase', buffer: float = None,
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
            structure (StructureBase): The structure to base the mesh override parameters on.
                                       This must be an instance of StructureBase or a subclass
                                       that includes a valid name.
            buffer (float, optional): A positive value indicating the buffer distance to extend
                                      the mesh override region in all directions. If None, no
                                      buffer will be applied.
            length_units (LENGTH_UNITS, optional): The units of the provided buffer distance.
                                                    If None, the global units of the simulation
                                                    will be used.

        Raises:
            ValueError: If the provided buffer is negative or if the length_units is not valid.
        """
        self._set_parameter("based on a structure", True, "bool")
        self._set_parameter("structure", structure.name, "str")

        # Assign the structure this mesh and the structure to the mesh
        if not hasattr(structure, "_bulk_mesh"):  # Check correct type without importing. All structures have this.
            raise ValueError("The 'structure' parameter must be an instance of StructureBase or a subclass.")
        structure._bulk_mesh = self._parent
        self._parent._structure = structure

        if buffer is not None:
            if length_units is None:
                length_units = self._simulation.global_units
            else:
                Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

            buffer = convert_length(buffer, from_unit=length_units, to_unit="m")
            self._set_parameter("buffer", buffer, "float")

    def set_directly_defined(self) -> None:
        """
        Enable direct definition of the mesh geometry.

        This method must be called to allow users to define the geometry of the mesh directly
        using coordinates and spans, similar to standard mesh definition practices.
        """
        self._parent._structure = None
        self._set_parameter("directly defined", True, "bool")

    def set_spans(
            self, x_span: Optional[Union[int, float]] = None, y_span: Optional[Union[int, float]] = None,
            z_span: Optional[Union[int, float]] = None, units: LENGTH_UNITS = None) -> None:
        if self._get_parameter("based on a structure", "bool"):
            raise ValueError("You cannot set the spans of the mesh when 'based on a structure' is enabled. "
                             "Enable 'directly defined' first.")
        super().set_spans(x_span, y_span, z_span, units)

    def set_position(
            self, x: Optional[Union[int, float]] = None, y: Optional[Union[int, float]] = None,
            z: Optional[Union[int, float]] = None, units: LENGTH_UNITS = None) -> None:
        if self._get_parameter("based on a structure", "bool"):
            raise ValueError("You cannot set the position of the mesh when 'based on a structure' is enabled. "
                             "Enable 'directly defined' first.")

    def get_currently_active_simulation_parameters(self) -> MeshGeometry._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        if self._get_parameter("based on a structure", "bool"):

            structure = self._parent._structure
            settings["x"] = self._get_parameter(
                object_name=structure.name, parameter_name="x", type_="float")
            settings["y"] = self._get_parameter(
                object_name= structure.name, parameter_name="y", type_="float")
            settings["z"] = self._get_parameter(
                object_name= structure.name, parameter_name="z", type_="float")
            settings["x_span"] = convert_length(structure.x_max - structure.x_min,
                                                self._simulation.global_units, "m")
            settings["y_span"] = convert_length(structure.y_max - structure.y_min,
                                                self._simulation.global_units, "m")
            settings["z_span"] = convert_length(structure.z_max - structure.z_min,
                                                self._simulation.global_units, "m")
            settings["use_relative_coordinates"] = self._get_parameter(
                object_name=structure.name, parameter_name="use relative coordinates", type_="bool")
            settings["buffer"] = self._get_parameter("buffer", "float")

        else:
            settings.update(super().get_currently_active_simulation_parameters())

        return settings


########################################################################################################################
#                     CLASSES FOR SUBSETTINGS (SHOULD BE MEMBER VARIABLES OF THE SETTING CLASSES)
########################################################################################################################


# FDTD Region Mesh subsettings
class MeshType(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        mesh_type: MESH_TYPE
        mesh_accuracy: int
        define_x_mesh_by: DEFINE_MESH_BY
        define_y_mesh_by: DEFINE_MESH_BY
        define_z_mesh_by: DEFINE_MESH_BY
        allow_grading_in_x: bool
        allow_grading_in_y: bool
        allow_grading_in_z: bool
        grading_factor: float
        dx: float
        dy: float
        dz: float
        mesh_cells_per_wavelength: Union[int, float]
        mesh_cells_x: int
        mesh_cells_y: int
        mesh_cells_z: int

    __slots__ = SubsettingTab.__slots__

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
        self._set_parameter("mesh accuracy", mesh_accuracy, "str")

    def define_mesh_by(self, axis: AXES, definition: DEFINE_MESH_BY) -> None:
        """
        Define the mesh generation criteria for a specified axis.

        Parameters:
        - axis: The axis for which the mesh definition is being set. Valid options include
          'x', 'y', or 'z'.

        - definition: Specifies how the mesh will be defined. Options include:
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

        Validate.axis(axis)
        Validate.in_literal(definition, "definition", DEFINE_MESH_BY)
        self._set_parameter(f"define {axis} mesh by", definition, "str")

    def allow_mesh_grading(self, axis: AXES, allow: bool) -> None:
        """
        Enable or disable mesh grading for a specified axis.

        Parameters:
        - axis: The axis for which mesh grading is being set. Valid options include
          'x', 'y', or 'z'.

        - allow: A boolean value indicating whether mesh grading is allowed (True)
          or not (False).

        Raises:
        - ValueError: If the axis is not valid, if the current mesh type is not
          'custom non-uniform', or if the 'define {axis} mesh by' parameter is set
          to 'number of mesh cells'.

        Enabling mesh grading allows for more flexible mesh adjustments, improving
        simulation accuracy but may increase computation time.
        """
        # Check the current mesh type
        current_mesh_type = self._get_parameter("mesh type", "str")

        # Ensure the mesh type is 'custom non-uniform'
        if current_mesh_type != "custom non-uniform":
            raise ValueError("Mesh type must be 'custom non-uniform' to allow mesh grading.")

        # Fetch the 'define {axis} mesh by' parameter
        define_mesh_by = self._get_parameter(f"define {axis} mesh by", "str")

        # Raise an error if it is set to 'number of mesh cells'
        if define_mesh_by == "number of mesh cells":
            raise ValueError(
                f"Mesh grading cannot be allowed when 'define {axis} mesh by' is set to 'number of mesh cells'.")

        Validate.axis(axis)
        self._set_parameter(f"allow grading in {axis}", allow, "bool")

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

    def set_maximum_mesh_step(
            self, axis: AXES, max_step: Union[int, float], units: LENGTH_UNITS = None) -> None:
        """
        Set the maximum mesh step size for the specified axis.

        Parameters:
        - axis: The axis along which to set the maximum mesh step (e.g., 'x', 'y', 'z').
        - max_step: An integer or float value representing the maximum mesh step size.
        - units: The units for max_step. If None, the global units will be used.

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

        if units is None:
            units = self._simulation.global_units
        else:
            Validate.in_literal(units, "units", LENGTH_UNITS)

        max_step = convert_length(max_step, units, "m")
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

    def set_number_of_mesh_cells_without_override_regions(self, axis: AXES, nr: int) -> None:
        """
        Set the number of mesh cells for the specified axis without override regions.

        Parameters:
        - axis: The axis for which the number of mesh cells is being set (e.g., 'x', 'y', 'z').
        - nr: An integer value representing the number of mesh cells.

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

        Validate.axis(axis)

        # Fetch the current definition for the specified axis
        definition = self._get_parameter(f"define {axis} mesh by", "str")

        # Ensure the definition is 'number of mesh cells'
        if definition != "number of mesh cells":
            raise ValueError(
                f"The definition for '{axis}' mesh must be 'number of mesh cells', "
                f"but it is currently '{definition}'."
            )

        Validate.positive_integer(nr, "nr")
        self._set_parameter(f"mesh cells {axis}", nr, "int")

    def get_currently_active_simulation_parameters(self) -> MeshType._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        # Check the mesh type
        if settings["mesh_type"] == "auto non-uniform":
            settings["mesh_accuracy"] = self._get_parameter("mesh accuracy", "int")

        else:

            for axis in get_args(AXES):
                settings[f"define_{axis}_mesh_by"] = self._get_parameter(
                    f"define {axis} mesh by", "str")

                if (settings[f"define_{axis}_mesh_by"] in
                        ["maximum mesh step", "max mesh step and mesh cells per wavelength"]):

                    settings[f"d{axis}"] = self._get_parameter(f"d{axis}", "float")

                elif settings[f"define_{axis}_mesh_by"] == "number of mesh cells":

                    settings[f"mesh_cells_{axis}"] = self._get_parameter(
                        f"mesh cells {axis}", "int")

            if settings["mesh_type"] == "custom non-uniform":

                settings["mesh_cells_per_wavelength"] = self._get_parameter(
                    "mesh cells per wavelength", "float")

                for axis in get_args(AXES):
                    settings[f"allow_grading_in_{axis}"] = self._get_parameter(
                        f"allow grading in {axis}", "bool")

                settings["grading_factor"] = self._get_parameter("grading factor", "float")

        return settings


class MeshRefinement(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        mesh_refinement: MESH_REFINEMENT
        meshing_refinement: int

    __slots__ = SubsettingTab.__slots__

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

    def set_dielectric_volume_average(self, meshing_refinement: float) -> None:
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

    def set_precise_volume_average(self, meshing_refinement: float) -> None:
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
        self._set_parameter("meshing refinement", meshing_refinement, "float")

    def get_currently_active_simulation_parameters(self) -> MeshRefinement._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["mesh_refinement"] = self._get_parameter("mesh refinement", "str")
        if settings["mesh_refinement"] in ["volume average", "precise volume average"]:
            settings["meshing_refinement"] = self._get_parameter("meshing refinement", "int")
        return settings


# FDTD Region Advanced Options subsettings
class SimulationBandwidth(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        set_simulation_bandwidth: bool
        simulation_wavelength_min: float
        simulation_wavelength_max: float

    __slots__ = SubsettingTab.__slots__

    def set_simulation_bandwidth(
            self, true_or_false: bool, min_wavelength: float = None,
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
            units = self._simulation.global_units

        if true_or_false:
            if min_wavelength is not None:
                min_wavelength = convert_length(float(min_wavelength), units, "m")
                self._set_parameter("simulation wavelength min", min_wavelength, "float")
            if max_wavelength is not None:
                max_wavelength = convert_length(float(max_wavelength), units, "m")
                self._set_parameter("simulation wavelength max", max_wavelength, "float")

    def get_currently_active_simulation_parameters(self) -> SimulationBandwidth._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        if settings["set_simulation_bandwidth"]:
            settings["simulation_wavelength_min"] = self._get_parameter(
                "simulation wavelength min", "float")
            settings["simulation_wavelength_max"] = self._get_parameter(
                "simulation wavelength max", "float")

        return settings


class AdvancedMeshSettings(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        force_symmetric_x_mesh: bool
        force_symmetric_y_mesh: bool
        force_symmetric_z_mesh: bool
        override_simulation_bandwidth_for_mesh_generation: bool
        mesh_wavelength_min: float
        mesh_wavelength_max: float
        snap_pec_to_yee_cell_boundary: bool

    __slots__ = SubsettingTab.__slots__

    def force_symmetric_mesh(self, axis: AXES, force: bool) -> None:
        """
        Force a symmetric mesh about the specified axis (x, y, or z) in the simulation.

        When this option is enabled, the meshing algorithm only considers objects in the
        positive half of the simulation region. The mesh in the negative half is generated
        as a direct copy of the positive half mesh. Consequently, any physical structures
        and mesh override regions in the negative half will not be considered by the
        meshing algorithm. Additionally, this option ensures a mesh point is placed at
        the center of the simulation region.

        This method is particularly useful for ensuring consistent mesh behavior when
        transitioning between simulations with and without symmetry.

        Parameters:
        - axis: The axis (x, y, or z) about which to enforce symmetry. Must be one of
          the defined axes in the AXES enumeration.

        - force: A boolean value indicating whether to enable (True) or disable (False)
          the symmetric meshing. When enabled, it ensures that the mesh structure
          remains unchanged regardless of symmetry configurations in the simulation.

        Raises:
        - ValueError: If the provided axis is not valid according to the AXES enumeration.

        Usage:
        - Call this method when you want to simplify the meshing process for simulations
          that exhibit symmetry, ensuring computational efficiency and consistency in the
          generated mesh structure.
        """
        Validate.axis(axis)
        Validate.boolean(force, "force")
        self._set_parameter(f"force symmetric {axis} mesh", force, "bool")

    def override_simulation_bandwidth_for_mesh_generation(
            self, override: bool, min_wavelength: float = None,
            max_wavelength: float = None, units: LENGTH_UNITS = None) -> None:
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
            units = self._simulation.global_units

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

    def get_currently_active_simulation_parameters(self) -> AdvancedMeshSettings._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update({
            "snap_pec_to_yee_cell_boundary": self._get_parameter("snap pec to yee cell boundary",
                                                                 "bool"),
            "force_symmetric_x_mesh": self._get_parameter("force symmetric x mesh", "bool"),
            "force_symmetric_y_mesh": self._get_parameter("force symmetric y mesh", "bool"),
            "force_symmetric_z_mesh": self._get_parameter("force symmetric z mesh", "bool"),
            "override_simulation_bandwidth_for_mesh_generation": self._get_parameter(
                "override simulation bandwidth for mesh generation", "bool")
        })
        if settings["override_simulation_bandwidth_for_mesh_generation"]:
            settings["mesh_wavelength_min"] = self._get_parameter("mesh wavelength min", "float")
            settings["mesh_wavelength_max"] = self._get_parameter("mesh wavelength max", "float")
        return settings


class AutoShutoff(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        use_early_shutoff: bool
        auto_shutoff_min: float
        use_divergence_checking: bool
        auto_shutoff_max: float
        down_sample_time: int

    __slots__ = SubsettingTab.__slots__

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

    def get_currently_active_simulation_parameters(self) -> AutoShutoff._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update({
            "use_early_shutoff": self._get_parameter("use early shutoff", "bool"),
            "use_divergence_checking": self._get_parameter("use divergence checking", "bool"),
            "down_sample_time": self._get_parameter("down sample time", "int")
        })
        if settings["use_early_shutoff"]:
            settings["auto_shutoff_min"] = self._get_parameter("auto shutoff min", "float")
        if settings["use_divergence_checking"]:
            settings["auto_shutoff_max"] = self._get_parameter("auto shutoff max", "float")

        return settings


class ParalellEngineOptions(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        set_process_grid: bool
        nx: int
        ny: int
        nz: int

    __slots__ = SubsettingTab.__slots__

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

    def get_currently_active_simulation_parameters(self) -> ParalellEngineOptions._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["set_process_grid"] = self._get_parameter("set process grid", "bool")
        if settings["set_process_grid"]:
            settings.update({
                "nx": self._get_parameter("nx", "int"),
                "ny": self._get_parameter("ny", "int"),
                "nz": self._get_parameter("nz", "int")
            })
        return settings


class CheckpointOptions(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        checkpoint_during_simulation: bool
        checkpoint_period: int
        checkpoint_at_shutoff: bool

    __slots__ = SubsettingTab.__slots__

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

    def get_currently_active_simulation_parameters(self) -> CheckpointOptions._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update({
            "checkpoint_during_simulation": self._get_parameter("checkpoint during simulation",
                                                                "bool"),
            "checkpoint_at_shutoff": self._get_parameter("checkpoint at shutoff", "bool")
        })
        if settings["checkpoint_during_simulation"]:
            settings["checkpoint_period"] = self._get_parameter("checkpoint period", "int")

        return settings


class BFASTSettings(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        bfast_alpha: float
        bfast_dt_multiplier: float

    __slots__ = SubsettingTab.__slots__

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

    def get_currently_active_simulation_parameters(self) -> BFASTSettings._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update({
            "bfast_alpha": self._get_parameter("bfast alpha", "float"),
            "bfast_dt_multiplier": self._get_parameter("bfast dt multiplier", "float")
        })
        return settings


class Miscellaneous(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        always_use_complex_fields: bool
        max_source_time_signal_length: int

    __slots__ = SubsettingTab.__slots__

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

    def get_currently_active_simulation_parameters(self) -> Miscellaneous._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["always_use_complex_fields"] = self._get_parameter("always use complex fields",
                                                                    "bool")
        settings["max_source_time_signal_length"] = self._get_parameter("max source time signal length",
                                                                        "int")
        return settings


# FDTD Region Boundary subsettings
class PMLSettings(SubsettingTab):

    class _PMLBoundarySettings(TypedDict):
        pml_type: PML_TYPES
        pml_profile: PML_PROFILES
        pml_layers: int
        pml_kappa: Union[int, float]
        pml_sigma: Union[int, float]
        pml_polynomial: Union[int, float]
        pml_alpha: Union[int, float]
        pml_alpha_polynomial: Union[int, float]
        pml_min_layers: int
        pml_max_layers: int

    class _SettingsDict(SubsettingTab._SettingsDict):
        same_settings_on_all_boundaries: bool
        x_min_bc: PMLSettings._PMLBoundarySettings
        x_max_bx: PMLSettings._PMLBoundarySettings
        y_min_bc: PMLSettings._PMLBoundarySettings
        y_max_bc: PMLSettings._PMLBoundarySettings
        z_min_bc: PMLSettings._PMLBoundarySettings
        z_max_bc: PMLSettings._PMLBoundarySettings
        extend_structure_through_pml: bool
        auto_scale_pml_parameters: bool

    __slots__ = SubsettingTab.__slots__

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

    def _set_value(
            self, parameter: str, value, type_: Literal["str", "float", "int", "str", "list"],
            boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """Helper function to set pml boundary settings."""

        if isinstance(boundary, list):
            for boundary in boundary:
                Validate.in_literal(boundary, "boundary", BOUNDARIES)
        elif boundary is None:
            boundary = get_args(BOUNDARIES)
        else:
            Validate.in_literal(boundary, "boundary", BOUNDARIES)

        boundary_to_index_map = {boundary: i for i, boundary in enumerate(get_args(BOUNDARIES))}

        if self._get_parameter("same settings on all boundaries", "bool"):

            self._set_parameter(parameter, value, type_)

        else:

            if boundary is None:
                raise ValueError(f"When 'same settings on all boundaries' is False, you must specify a boundary.")

            prev_values = np.array(self._get_parameter(parameter, "list")).flatten().tolist()

            if isinstance(boundary, list):
                for b in boundary:
                    prev_values[boundary_to_index_map[b]] = value

            else:
                prev_values[boundary_to_index_map[boundary]] = value

            # Convert to numpy array and transpose to match the format we fetch from the simulation
            new_values = np.array([np.array([value]) for value in prev_values])

            self._set_parameter(parameter, new_values, "list")

    def set_profile(
            self, profile: PML_PROFILES,
            boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
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

        Parameters:
            profile (PML_PROFILES): The PML profile to set.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the profile to.
                If None, the profile will be applied to all PML boundaries.

        Raises:
            ValueError: If the specified profile is not valid.
        """
        Validate.in_literal(profile, "profile", PML_PROFILES)

        profile_to_index_map = {profile: i + 1 for i, profile in enumerate(get_args(PML_PROFILES))}

        self._set_value("pml profile", profile_to_index_map[profile], "str", boundary)

    def set_layers(self, layers: int, boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the number of PML layers for the specified boundary.

        PML boundaries occupy a finite volume surrounding the simulation region and are divided into layers
        for discretization. The number of layers can significantly affect the absorption properties of the PML.
        Generally, increasing the number of layers leads to lower reflections but may also increase simulation time.

        Parameters:
            layers (int): The number of PML layers to set.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the layer setting to.
                If None, the layer setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the provided boundary is invalid.
        """
        self._set_value("pml layers", layers, "int", boundary)

    def set_kappa(self, kappa: float, boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the kappa parameter for PML boundaries.

        Kappa is a unitless parameter that controls the absorption properties of the PML regions.
        It is graded inside the PML using polynomial functions. The effective range of kappa should
        be carefully chosen to ensure optimal absorption without compromising numerical stability.

        Parameters:
            kappa (float): The kappa value to set. It should be a normalized unitless value.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the kappa setting to.
                If None, the kappa setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the specified boundary is invalid
        """
        self._set_value("pml kappa", kappa, "float", boundary)

    def set_sigma(self, sigma: float, boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the sigma parameter for PML boundaries.

        Sigma is another unitless parameter that contributes to the absorption properties of PML regions.
        It must be entered as a normalized unitless value. Increasing sigma can enhance absorption but
        may also impact stability, particularly when combined with the alpha parameter.

        Parameters:
            sigma (float): The sigma value to set. It should be a normalized unitless value.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the sigma setting to.
                If None, the sigma setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the specified boundary is invalid.
        """
        self._set_value("pml sigma", sigma, "float", boundary)

    def set_polynomial(self, polynomial: int, boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the polynomial order for grading kappa and sigma in PML boundaries.

        The polynomial order specifies how kappa and sigma are graded inside the PML regions.
        Higher-order polynomials can improve the absorption characteristics of the PML but may
        also complicate the numerical stability.

        Parameters:
            polynomial (int): The polynomial order to set.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the polynomial setting to.
                If None, the polynomial setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the specified boundary is invalid.
        """
        self._set_value("pml polynomial", polynomial, "float", boundary)

    def set_alpha(self, alpha: float, boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the alpha parameter for PML boundaries.

        Alpha is a unitless parameter that influences the absorption properties of the PML regions.
        This parameter can only be set if the PML type is "stretched coordinate PML."

        Parameters:
            alpha (float): The alpha value to set. It should be a normalized unitless value.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the alpha setting to.
                If None, the alpha setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the PML type is not "stretched coordinate PML" or if the specified alpha value is invalid.
            ValueError: If the specified boundary is invalid.
        """
        pml_type = self._get_parameter("pml type", "str")
        if pml_type != "stretched coordinate PML":
            raise ValueError("Alpha can only be set when PML type is 'stretched coordinate PML'.")
        self._set_value("pml alpha", alpha, "float", boundary)

    def set_alpha_polynomial(self, alpha_polynomial: float,
                             boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the alpha polynomial order for PML boundaries.

        The alpha polynomial order specifies how alpha is graded inside the PML regions.
        This parameter can only be set if the PML type is "stretched coordinate PML."

        Parameters:
            alpha_polynomial (float): The alpha polynomial order to set.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the alpha polynomial setting to.
                If None, the alpha polynomial setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the PML type is not "stretched coordinate PML" or if the specified alpha polynomial order is
                        invalid.
            ValueError: If the specified boundary is invalid.
        """
        pml_type = self._get_parameter("pml type", "str")
        if pml_type != "stretched coordinate PML":
            raise ValueError("Alpha polynomial can only be set when PML type is 'stretched coordinate PML'.")
        self._set_value("pml alpha polynomial", alpha_polynomial, "float", boundary)

    def set_min_layers(self, min_layers: int, boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the minimum number of PML layers for the specified boundaries.

        The minimum number of layers enforces a lower limit on how many layers
        are used in the PML region, which can influence the absorption performance.
        Setting a sensible minimum is important to ensure that the PML can effectively
        absorb outgoing waves without significant reflections.

        Parameters:
            min_layers (int): The minimum number of PML layers to set.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the minimum layer setting to.
                If None, the minimum layer setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the specified minimum layers value is invalid (e.g., negative).
            ValueError: If the specified boundary is invalid.
        """
        Validate.positive_integer(min_layers, "min_layers")
        self._set_value("pml min layers", min_layers, "int", boundary)

    def set_max_layers(self, max_layers: int, boundary: Union[List[BOUNDARIES], BOUNDARIES] = None) -> None:
        """
        Sets the maximum number of PML layers for the specified boundaries.

        The maximum number of layers enforces an upper limit on how many layers
        can be used in the PML region. This can help manage simulation performance,
        as excessively high layer counts may lead to longer simulation times without
        significant improvements in absorption.

        Parameters:
            max_layers (int): The maximum number of PML layers to set.
            boundary (Union[List[BOUNDARIES], BOUNDARIES], optional):
                The specific boundary or boundaries to apply the maximum layer setting to.
                If None, the maximum layer setting will be applied to all PML boundaries.

        Raises:
            ValueError: If the specified maximum layers value is invalid (e.g., negative).
            ValueError: If the specified boundary is invalid.
        """
        Validate.positive_integer(max_layers, "max_layers")
        self._set_value("pml max layers", max_layers, "int", boundary)

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

    def get_currently_active_simulation_parameters(self) -> PMLSettings._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        settings["same_settings_on_all_boundaries"] = self._get_parameter("same settings on all boundaries", "bool")

        int_to_profile = {1: "standard", 2: "stabilized", 3: "steep angle", 4: "custom"}
        boundary_to_index = {
            "x_min_bc": 0, "x_max_bc": 1, "y_min_bc": 2, "y_max_bc": 3, "z_min_bc": 4, "z_max_bc": 5
        }

        pml_type = self._get_parameter("pml type", "str")

        for boundary in get_args(BOUNDARIES):
            if self._get_parameter(boundary, "str") == "PML":
                if settings["same_settings_on_all_boundaries"]:
                    pml_settings = PMLSettings._PMLBoundarySettings(**{
                        parameter: None for parameter in PMLSettings._PMLBoundarySettings.__required_keys__})
                    pml_settings.update({
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
                        pml_settings["pml_alpha"] = self._get_parameter("pml alpha", "float")
                        pml_settings["pml_alpha_polynomial"] = self._get_parameter(
                            "pml alpha polynomial", "float")

                else:
                    pml_settings = PMLSettings._PMLBoundarySettings(**{
                        parameter: None for parameter in PMLSettings._PMLBoundarySettings.__required_keys__})

                    pml_settings.update({
                        "pml_type": pml_type,
                        "pml_profile": int_to_profile[int(self._get_parameter(
                            "pml profile", "list")[
                                                              boundary_to_index[boundary.replace(" ", "_")]])],
                        "pml_layers": int(self._get_parameter("pml layers", "list")[
                                              boundary_to_index[boundary.replace(" ", "_")]]),
                        "pml_kappa": float(self._get_parameter("pml kappa", "list")[
                                               boundary_to_index[boundary.replace(" ", "_")]]),
                        "pml_sigma": float(self._get_parameter(
                            "pml sigma", "list")[boundary_to_index[boundary.replace(" ", "_")]]),
                        "pml_polynomial": float(self._get_parameter("pml polynomial", "list")[
                                                    boundary_to_index[boundary.replace(" ", "_")]]),
                        "pml_min_layers": int(self._get_parameter("pml min layers", "list")[
                                                  boundary_to_index[boundary.replace(" ", "_")]]),
                        "pml_max_layers": int(self._get_parameter("pml max layers", "list")[
                                                  boundary_to_index[boundary.replace(" ", "_")]]),
                    })
                    if pml_type == "stretched coordinate PML":
                        pml_settings["pml_alpha"] = float(self._get_parameter(
                            "pml alpha", "list")[
                                                              boundary_to_index[boundary.replace(" ", "_")]])
                        pml_settings["pml_alpha_polynomial"] = float(self._get_parameter(
                            "pml alpha polynomial", "list")[
                                                                         boundary_to_index[boundary.replace(" ", "_")]])

                settings[boundary.replace(" ", "_")] = pml_settings

        return settings


class BlochSettings(SubsettingTab):

    class _SettingsDict(SubsettingTab._SettingsDict):
        set_based_on_source_angle: bool
        bloch_units: BLOCH_UNITS
        kx: float
        ky: float
        kz: float

    __slots__ = SubsettingTab.__slots__

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

    def set_k(self, axis: AXES, value: float) -> None:
        """
        Sets the wavevector for the Bloch boundary in the specified direction (x, y, or z).

        The wavevector values (kx, ky, kz) are set based on the specified axis and the value provided.

        Parameters:
            axis (AXES):
                The direction in which the wavevector is to be set. This should be one of the
                predefined values in the AXES enumeration, which typically includes
                AXES.X for kx, AXES.Y for ky, and AXES.Z for kz.

            value (float):
                The value of the wavevector in the specified direction. This value should
                correspond to the units defined by the currently set Bloch units (either
                bandstructure or SI units).

        Raises:
            ValueError: If the provided axis.
        """
        Validate.axis(axis)
        self._set_parameter(f"k{axis}", value, "float")

    def get_currently_active_simulation_parameters(self) -> BlochSettings._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        boundaries = [self._get_parameter(boundary, "str") for boundary in get_args(BOUNDARIES)]
        bloch_boundaries = [boundary for boundary in boundaries if boundary == "Bloch"]
        if bloch_boundaries:
            settings.update({
                "set_based_on_source_angle": self._get_parameter("set based on source angle",
                                                                 "bool"),
                "bloch_units": self._get_parameter("bloch units", "str"),
            })
            for axis in get_args(AXES):
                if any([axis in boundary for boundary in bloch_boundaries]):
                    settings[f"k{axis}"] = self._get_parameter(f"k{axis}", "float")

        return settings


class Boundaries(SubsettingTab):
    """Class representing boundary settings for an FDTD simulation region."""

    class _SettingsDict(SubsettingTab._SettingsDict):
        x_min_bc: BOUNDARY_TYPES
        x_max_bc: BOUNDARY_TYPES
        y_min_bc: BOUNDARY_TYPES
        y_max_bc: BOUNDARY_TYPES
        z_min_bc: BOUNDARY_TYPES
        z_max_bc: BOUNDARY_TYPES
        allow_symmetry_on_all_boundaries: bool

    __slots__ = SubsettingTab.__slots__

    def set_boundary_type(
            self, axis: AXES, min_max: Literal["min", "max"], boundary_type: BOUNDARY_TYPES) -> None:
        """
        Set the boundary type for a specified axis and minimum or maximum boundary.

        This method allows you to configure different boundary conditions (such as PML, Metal, PMC, etc.)
        for the simulation based on the desired axis and the boundary condition type.

        Args:
            axis (AXES):
                The axis for which the boundary type is being set.
                This should be one of the predefined values in the AXES enumeration
                (e.g., AXES.X, AXES.Y, AXES.Z).

            min_max (Literal["min", "max"]):
                Specifies whether to set the minimum or maximum boundary for the given axis.

            boundary_type (BOUNDARY_TYPES):
                The type of boundary condition to apply. This should be one of the predefined values in
                the BOUNDARY_TYPES enumeration (e.g., BOUNDARY_TYPES.PML, BOUNDARY_TYPES.Metal, etc.).

                Supported boundary types:
                - **PML (Perfectly Matched Layer)**: Absorbs electromagnetic waves to model open boundaries.
                  Best when structures extend through the boundary.
                - **Metal (Perfect Electric Conductor)**: Reflects all electromagnetic waves, with zero electric
                  field component parallel to the boundary.
                - **PMC (Perfect Magnetic Conductor)**: Reflects magnetic fields, with zero magnetic field component
                  parallel to the boundary.
                - **Periodic**: Used for structures that are periodic in one or more directions, simulating infinite
                  repetition.
                - **Bloch**: Used for periodic structures with a phase shift, suitable for plane waves at angles or
                  bandstructure calculations.
                - **Symmetric**: Mirrors electric fields and anti-mirrors magnetic fields; requires symmetric sources.
                - **Anti-Symmetric**: Anti-mirrors electric fields and mirrors magnetic fields; requires anti-symmetric sources.

        Raises:
            ValueError:
                If the provided axis, min_max, or boundary_type arguments are invalid. Ensure that
                the axis is one of 'x', 'y', or 'z', min_max is either 'min' or 'max',
                and boundary_type is a valid boundary type.
            ValueError:
                If you are trying to set a max bc to "Symmetric" or "Anti-Symmetric" when 'allow symmetry on all
                boundaries' are disabled.
        """
        Validate.axis(axis)
        Validate.in_literal(min_max, "min_max", Literal["min", "max"])
        Validate.in_literal(boundary_type, "boundary_type", BOUNDARY_TYPES)

        if min_max == "max":
            symmetry_allowed = self._get_parameter("allow symmetry on all boundaries", "bool")
            if symmetry_allowed and boundary_type in ["Symmetric", "Anti-Symmetric"]:
                raise ValueError(
                    f"Cannot set a max boundary condition to '{boundary_type}' when 'allow symmetry on all boundaries' "
                    "is disabled. Please enable this option or choose a different boundary type."
                )

        self._set_parameter(f"{axis} {min_max} bc", boundary_type, "str")

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

    def get_currently_active_simulation_parameters(self) -> Boundaries._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        for boundary in get_args(BOUNDARIES):
            settings[boundary.replace(" ", "_")] = self._get_parameter(boundary, "str")
        settings["allow_symmetry_on_all_boundaries"] = self._get_parameter(
            "allow symmetry on all boundaries", "bool")
        return settings


########################################################################################################################
#                                       CLASSES FOR SETTINGS CATEGORIES
########################################################################################################################


# FDTD Region Settings
class General(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
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
        # Validate that the material is one of the allowed materials
        Validate.in_literal(material, "material", MATERIALS)

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

    def get_currently_active_simulation_parameters(self) -> General._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        settings.update({
            "dimension": self._get_parameter("dimension", "str"),
            "simulation_time": self._get_parameter("simulation time", "float"),
            "simulation_temperature": self._get_parameter("simulation temperature", "float"),
            "background_material": self._get_parameter("background material", "str"),
            "index": self._get_parameter("index", "float")
        })

        return settings


class MeshSettings(SettingTab):

    class _SettingsDict(MeshRefinement._SettingsDict, MeshType._SettingsDict):
        dt_stability_factor: float
        min_mesh_step: float

    # Helper lists for initialization/refreshing
    _sub_settings = [MeshType, MeshRefinement]
    _sub_settings_names = ["mesh_type_settings", "mesh_refinement_settings"]

    # Declare variables
    mesh_type_settings: MeshType
    mesh_refinement_settings: MeshRefinement

    __slots__ = SettingTab.__slots__ + _sub_settings_names

    def get_currently_active_simulation_parameters(self) -> MeshSettings._SettingsDict:
        # Initialize a settings typed dict with all values None
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update(self.mesh_type_settings.get_currently_active_simulation_parameters())
        settings.update(self.mesh_refinement_settings.get_currently_active_simulation_parameters())
        settings.update({
            "dt_stability_factor": self._get_parameter("dt stability factor", "float"),
            "min_mesh_step": self._get_parameter("min mesh step", "float")
        })
        return settings

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
            units = self._simulation.global_units
        else:
            Validate.in_literal(units, "units", LENGTH_UNITS)

        min_step = convert_length(min_step, units, "m")
        self._set_parameter("min mesh step", min_step, "float")


class AdvancedOptions(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        simulation_bandwidth: SimulationBandwidth._SettingsDict
        mesh_settings: AdvancedMeshSettings._SettingsDict
        auto_shutoff: AutoShutoff._SettingsDict
        paralell_engine_options: ParalellEngineOptions._SettingsDict
        checkpoint_options: CheckpointOptions._SettingsDict
        bfast_settings: BFASTSettings._SettingsDict
        miscellaneous: Miscellaneous._SettingsDict

    # Helper lists for initialization/refreshing
    _sub_settings = [
        SimulationBandwidth, AdvancedMeshSettings, AutoShutoff, ParalellEngineOptions,
        CheckpointOptions, BFASTSettings, Miscellaneous
    ]
    _sub_settings_names = [
        "simulation_bandwidth_settings", "mesh_settings", "auto_shutoff_settings", "paralell_enginge_settings",
        "checkpoint_settings", "bfast_settings", "misc_settings"
    ]

    # Declare variables
    simulation_bandwidth_settings: SimulationBandwidth
    mesh_settings: AdvancedMeshSettings
    auto_shutoff_settings: AutoShutoff
    paralell_engine_settings: ParalellEngineOptions
    checkpoint_settings: CheckpointOptions
    bfast_settings: BFASTSettings
    misc_settings: Miscellaneous

    __slots__ = SettingTab.__slots__ + _sub_settings_names

    def set_express_mode(self, true_or_false: bool) -> None:
        """Enables the express mode, which has something to do with running FDTD on GPU."""
        self._set_parameter("express mode", true_or_false, "bool")

    def get_currently_active_simulation_parameters(self) -> AdvancedOptions._SettingsDict:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["simulation_bandwidth"] = (self.simulation_bandwidth_settings.
                                            get_currently_active_simulation_parameters())
        settings["mesh_settings"] = self.mesh_settings.get_currently_active_simulation_parameters()
        settings["auto_shutoff"] = self.auto_shutoff_settings.get_currently_active_simulation_parameters()
        settings["paralell_engine_options"] = self.paralell_engine_settings.get_currently_active_simulation_parameters()
        settings["checkpoint_options"] = self.checkpoint_settings.get_currently_active_simulation_parameters()
        settings["bfast_settings"] = self.bfast_settings.get_currently_active_simulation_parameters()
        settings["miscellaneous"] = self.misc_settings.get_currently_active_simulation_parameters()
        return settings


class BoundaryConditions(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        pml_settings: PMLSettings._SettingsDict
        boundary_settings: Boundaries._SettingsDict
        bloch_settings: BlochSettings._SettingsDict

    _sub_settings = [PMLSettings, BlochSettings, Boundaries]
    _sub_settings_names = ["pml_settings", "bloch_settings", "boundary_settings"]
    __slots__ = SettingTab.__slots__ + _sub_settings_names

    # Declare variables
    pml_settings: PMLSettings
    bloch_settings: BlochSettings
    boundary_settings: Boundaries

    def get_currently_active_simulation_parameters(self) -> BoundaryConditions._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["boundary_settings"] = self.boundary_settings.get_currently_active_simulation_parameters()
        settings["bloch_settings"] = self.bloch_settings.get_currently_active_simulation_parameters()
        settings["pml_settings"] = self.pml_settings.get_currently_active_simulation_parameters()

        return settings


# Mesh Settings
class MeshGeneral(SettingTab):

    class _SettingsDict(SettingTab._SettingsDict):
        dx: float
        dy: float
        dz: float
        equivalent_x_index: float
        equivalent_y_index: float
        equivalent_z_index: float

    __slots__ = SettingTab.__slots__

    def override_axis_mesh(self, axis: AXES, override: bool) -> None:
        """
        Enable or disable mesh size overrides for a specified axis.

        This method allows users to set whether mesh size constraints should be overridden
        for a specific axis (x, y, or z). If multiple mesh override regions are present,
        the meshing algorithm will use the override region that results in the smallest mesh
        for that volume of space. Constraints from mesh override regions always take precedence
        over the default automatic mesh, even if they result in a larger mesh size.

        Args:
            axis (AXES): The axis for which to override the mesh size (x, y, or z).
            override (bool): True to enable the override, or False to disable it.

        Raises:
            ValueError: If the axis is not valid.
        """
        Validate.in_literal(axis, "axis", AXES)
        self._set_parameter(f"override {axis} mesh", override, "bool")

    def set_equivalent_index(self, x_index: float = None, y_index: float = None, z_index: float = None) -> None:
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
            x_index (float, optional): The equivalent refractive index in the x direction.
                                        If None, the x mesh will not be overridden.
            y_index (float, optional): The equivalent refractive index in the y direction.
                                        If None, the y mesh will not be overridden.
            z_index (float, optional): The equivalent refractive index in the z direction.
                                        If None, the z mesh will not be overridden.

        Raises:
            ValueError: If there are issues in setting the parameters.
        """
        self._set_parameter("set equivalent index", True, "bool")
        if x_index is not None:
            self._set_parameter("override x mesh", True, "bool")
            self._set_parameter(f"equivalent x index", x_index, "float")
        if y_index is not None:
            self._set_parameter("override y mesh", True, "bool")
            self._set_parameter(f"equivalent y index", y_index, "float")
        if z_index is not None:
            self._set_parameter("override z mesh", True, "bool")
            self._set_parameter(f"equivalent z index", z_index, "float")

    def set_maximum_mesh_step(self, dx: float = None, dy: float = None, dz: float = None,
                              length_units: LENGTH_UNITS = None) -> None:
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
            length_units (LENGTH_UNITS, optional): The units of the provided mesh sizes. If None,
                                                    the global units of the simulation will be used.

        Raises:
            ValueError: If the provided length_units is not valid.
        """
        if length_units is None:
            length_units = self._simulation.global_units
        else:
            Validate.in_literal(length_units, "length_units", LENGTH_UNITS)

        self._set_parameter("set maximum mesh step", True, "bool")
        if dx is not None:
            dx = convert_length(dx, from_unit=length_units, to_unit="m")
            self._set_parameter("dx", dx, "float")
        if dy is not None:
            dy = convert_length(dy, from_unit=length_units, to_unit="m")
            self._set_parameter("dy", dy, "float")
        if dz is not None:
            dz = convert_length(dz, from_unit=length_units, to_unit="m")
            self._set_parameter("dz", dz, "float")

    def get_currently_active_simulation_parameters(self) -> MeshGeneral._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())

        if self._get_parameter("set maximum mesh step", "bool"):
            for axis in get_args(AXES):
                if self._get_parameter(f"override {axis} mesh", "bool"):
                    settings[f"d{axis}"] = self._get_parameter(f"d{axis}", "float")
        else:
            for axis in get_args(AXES):
                if self._get_parameter(f"override {axis} mesh", "bool"):
                    settings[f"equivalent {axis} index"] = self._get_parameter(
                        f"equivalent {axis} index", "float")

        return settings


########################################################################################################################
#                                       CLASSES FOR ACTUAL SIMULATION OBJECTS
########################################################################################################################


class FDTDRegion(SimulationObject):
    """Class representing a finite-difference time-domain (FDTD) simulation region."""

    class _Kwargs(SimulationObject._Kwargs):
        x_span: float
        y_span: float
        z_span: float

    class _SettingsDict(SimulationObject._SettingsDict):
        general_settings: General._SettingsDict
        mesh_settings: MeshSettings._SettingsDict
        boundary_conditions: BoundaryConditions._SettingsDict
        advanced_settings: AdvancedOptions._SettingsDict

    # Lists to aid in initialization
    _settings = SimulationObject._settings + [General, MeshSettings, BoundaryConditions, AdvancedOptions]
    _settings_names = SimulationObject._settings_names + [
        "general_settings", "mesh_settings", "boundary_conditions_settings", "advanced_settings"
    ]

    # Declare variables
    general_settings: General
    mesh_settings: MeshSettings
    boundary_conditions_settings: BoundaryConditions
    advanced_settings: AdvancedOptions

    def __init__(self, simulation: lumapi.FDTD, **kwargs: Unpack[FDTDRegion._Kwargs]) -> None:
        """Initialize the FDTDRegion with the specified simulation.

        Args:
            simulation (FDTDSimulationBase): The simulation base associated with this FDTD region.
        """
        simulation._names.append("FDTD")
        super().__init__(name="FDTD", simulation=simulation, **kwargs)
        self.boundary_conditions_settings.boundary_settings.set_allow_symmetry_on_all_boundaries(True)

    def get_currently_active_simulation_parameters(self) -> FDTDRegion._SettingsDict:

        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings.update({
            "general_settings": self.general_settings.get_currently_active_simulation_parameters(),
            "mesh_settings": self.mesh_settings.get_currently_active_simulation_parameters(),
            "boundary_conditions": self.boundary_conditions_settings.get_currently_active_simulation_parameters(),
            "advanced_settings": self.advanced_settings.get_currently_active_simulation_parameters()
        })
        return settings

    def __repr__(self) -> str:
        return "FDTDRegion"


class Mesh(SimulationObject):

    class _Kwargs(SimulationObject._Kwargs, FDTDRegion._Kwargs):
        based_on_a_structure: SimulationObject
        dx: float
        dy: float
        dz: float

    class _SettingsDict(SimulationObject._SettingsDict):
        general_settings: MeshGeneral._SettingsDict
        geometry_settings: MeshGeometry._SettingsDict

    _settings = [MeshGeometry if _setting == CartesianGeometry
                 else _setting for _setting in SimulationObject._settings] + [MeshGeneral]
    _settings_names = SimulationObject._settings_names + ["general_settings"]
    general_settings: MeshGeneral
    geometry_settings: MeshGeometry
    _structure: 'StructureBase'

    __slots__ = SimulationObject.__slots__ + _settings_names + ["_structure"]

    def __init__(self, name: str, simulation: lumapi.FDTD, **kwargs: Unpack[Mesh._Kwargs]) -> None:
        self._structure = None
        super().__init__(name, simulation, **kwargs)
        simulation._meshes.append(self)

    @property
    def dx(self) -> float:
        return convert_length(self._get_parameter(
            "dx", "float"), from_unit="m", to_unit=self._simulation.global_units)

    @dx.setter
    def dx(self, dx: float):
        self.general_settings.set_maximum_mesh_step(dx=dx)

    @property
    def dy(self) -> float:
        return convert_length(self._get_parameter(
            "dy", "float"), from_unit="m", to_unit=self._simulation.global_units)

    @dy.setter
    def dy(self, dy: float):
        self.general_settings.set_maximum_mesh_step(dy=dy)

    @property
    def dz(self) -> float:
        return convert_length(self._get_parameter(
            "dz", "float"), from_unit="m", to_unit=self._simulation.global_units)

    @dz.setter
    def dz(self, dz: float):
        self.general_settings.set_maximum_mesh_step(dz=dz)

    def get_currently_active_simulation_parameters(self) -> Mesh._SettingsDict | None:
        settings = self.__class__._SettingsDict(**self._init_empty_settings_dict())
        settings["general_settings"] = self.general_settings.get_currently_active_simulation_parameters()
        settings["geometry_settings"] = self.geometry_settings.get_currently_active_simulation_parameters()
        if all([value is None for _, value in settings["general_settings"].items()]):
            return None  # No meshes are overridden, and the mesh therefore has no effect
        return settings

    def __repr__(self) -> str:
        return "Mesh"
