from __future__ import annotations

# Standard library imports
import json
import os.path
import hashlib

# Third-party library imports
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, TypedDict
import numpy as np
from scipy import constants
from scipy.signal import find_peaks

# Local imports
from Simulation_database import DatabaseHandler

# Import the Lumerical python API. This is not in the site-packages directory, so importing it is a bit of a hassle.
# The location here is the default install location, but it might be that with newer FDTD releases, the \v241\
# is changed to a different number. If you get errors related to the import, try to change the location in the
# code snippet below to the actual location of you lumapi.py file.
import importlib.util
spec_win = importlib.util.spec_from_file_location(
    name='lumapi',  # Name of the .py file we want to import
    location=r'C:\\Program Files\\Lumerical\\v241\\api\\python\\lumapi.py'  # The directory of the lumapi file
)
lumapi = importlib.util.module_from_spec(spec_win)
spec_win.loader.exec_module(lumapi)


class StructureDoesNotExistError(Exception):
    """Exception raised when a structure does not exist."""

    def __init__(self, struct_nr: str):
        self.struct_nr = struct_nr
        self.message = f"Structure {self.struct_nr} does not exist."
        super().__init__(self.message)


class StructureDimensionsError(Exception):
    """Exception raised when the structure dimensions exceed the unit cell of the grid."""

    def __init__(self, unit_cell_x: float, unit_cell_y: float, structure_spans, shape: str):
        self.unit_cell_x = unit_cell_x
        self.unit_cell_y = unit_cell_y
        self.structure_spans = structure_spans

        # Adjust structure spans for circular shapes
        if shape == "circle":
            self.structure_spans = (structure_spans[0] * 2, structure_spans[1] * 2)

        self.message = (
            f"The structure dimensions are bigger than the unit cell dimensions.\n"
            f"Unit cell: ({self.unit_cell_x}, {self.unit_cell_y}) nm.\n"
            f"Structure dimensions: ({self.structure_spans[0]}, {self.structure_spans[1]}) nm."
        )
        super().__init__(self.message)


class StructureNotUniqueError(Exception):
    """Exception raised when a function requires a unique instance of a structure type, but there are multiple."""

    def __init__(self, structure_type_id: str):
        self.message = (
            f"The result is ambiguous, as there are more than one structure of the structure type id "
            f"'{structure_type_id}'."
        )
        super().__init__(self.message)


class InsufficientMonitorsError(Exception):
    """Exception raised when attempting to run a simulation without necessary monitors turned on."""

    def __init__(self):
        self.message = (
            "The reflection and/or transmission power monitor(s) are turned off. These are the only necessary "
            "monitors to include in each simulation. If there already exists a simulation in the "
            "database with the same parameters that has results for these monitors, this is okay. However, "
            "if you wish to run the simulation without these monitors, you can call the run() "
            "method directly on a SimulationBase object. This will return the result dictionary but will not "
            "save it to the database."
        )
        super().__init__(self.message)


class NoActiveStructuresError(Exception):
    """Exception raised when attempting to run a simulation with no active structures."""

    def __init__(self):
        self.message = (
            "The simulation has no active structures and will thus not be saved to the database. If you insist on "
            "running the simulation with no active structures, call the run() function directly on the "
            "SimulationBase object. This will return the result dictionary but will not save it to the database."
        )
        super().__init__(self.message)


class SimulationData(TypedDict):
    """Data structure for the simulation results saved to the database."""

    # Basic columns
    name: str

    # Geometry of the simulation
    struct1_xspan: np.float16
    struct1_yspan: np.float16
    struct1_zspan: np.float16
    struct1_material: str
    unit_cell1_x: Optional[np.float16]
    unit_cell1_y: Optional[np.float16]

    struct2_xspan: Optional[np.float16]
    struct2_yspan: Optional[np.float16]
    struct2_zspan: Optional[np.float16]
    struct2_material: str
    unit_cell2_x: Optional[np.float16]
    unit_cell2_y: Optional[np.float16]

    struct3_xspan: Optional[np.float16]
    struct3_yspan: Optional[np.float16]
    struct3_zspan: Optional[np.float16]
    struct3_material: str
    unit_cell3_x: Optional[np.float16]
    unit_cell3_y: Optional[np.float16]

    # Simulation mesh parameters
    mesh_dx: np.float16
    mesh_dy: np.float16
    mesh_dz: np.float16
    fdtd_xspan: np.float16
    fdtd_yspan: np.float16
    fdtd_zspan: np.float16
    boundary_symmetries: str

    # Source parameters
    polarization_angle: np.float16
    incidence_angle: np.float16
    lambda_start: np.float16
    lambda_stop: np.float16

    # Monitors
    ref_power_monitor_z: np.float16
    ref_profile_monitor_z: np.float16
    trans_power_monitor_z: np.float16
    trans_profile_monitor_z: np.float16
    frequency_points: np.float16

    # Results
    lambdas: np.ndarray
    ref_powers: np.ndarray
    ref_power_res_lambda: Optional[np.float16]
    ref_power_res: Optional[np.float16]
    trans_powers: np.ndarray
    trans_power_res_lambda: Optional[np.float16]
    trans_power_res: Optional[np.float16]
    profile_x: np.ndarray
    profile_y: np.ndarray
    ref_magnitudes: np.ndarray
    trans_magnitudes: np.ndarray
    ref_mag_max_pr_lambda: np.ndarray
    trans_mag_max_pr_lambda: np.ndarray
    ref_mag_res: Optional[np.float16]
    ref_mag_res_lambda: np.float16
    trans_mag_res: np.float16
    trans_mag_res_lambda: np.float16
    xz_E_magnitudes: np.ndarray
    xz_P_vectors: np.ndarray
    xz_x_coord: np.ndarray
    xz_z_coord: np.ndarray
    yz_E_magnitudes: np.ndarray
    yz_P_vectors: np.ndarray
    yz_y_coord: np.ndarray
    yz_z_coord: np.ndarray

    # Metadata
    simulation_hash: str
    active_monitors: str

    # Custom comment
    comment: str


class SimulationBase(lumapi.FDTD):
    """
    A base class for managing FDTD simulations using the Lumerical API.

    This class handles the setup of the simulation environment, manages a database for storing results,
    and processes data such as reflection and transmission power, electric field profiles, and resonance wavelengths.

    The default configuration includes:
        - Wavelength Range: 400-1500 nm with 1000 simulation points.
        - Mesh Stepsize: 10 nm in all directions.
        - FDTD Region: 350 nm x 350 nm x 1600 nm.
        - Substrate: Defined dielectric with a refractive index of 1.45, dimensions of 350 nm x 350 nm x 800 nm,
          with the top surface at z = 0 nm.
        - Monitors for recording power and electric field profiles at specified positions.

    Attributes:
        ResultDataType (dict): A type hint for the dictionary structure used to store and retrieve
                               simulation results, such as power and field magnitudes, resonance wavelengths, etc.
        materials_explorer (Literal): A predefined set of materials that can be used in the simulation,
                                      including various metals, semiconductors, and dielectrics.
        list_of_monitor_names (list): A list containing the names of the monitors in the simulation.
        monitor_result_types (dict): A dictionary that tracks the result types fetched from Lumerical FDTD.

    Class Attributes:
        __slots__ (list): A list of attribute names that restricts the attributes to the specified list,
                          optimizing memory usage and performance.

    Example Usage:
        - This class serves as a base for setting up FDTD simulations.
        - Users can define structures, materials, and simulation parameters, and save results to a database.
    """

    # Type hint for the result dictionary structure
    ResultDataType = Dict[
        Literal[
            "lambdas", "ref_powers", "ref_power_res_lambda", "ref_power_res",
            "trans_power_res_lambda", "trans_power_res", "trans_powers",
            "profile_x", "profile_y", "ref_magnitudes", "trans_magnitudes",
            "ref_mag_max_pr_lambda", "trans_mag_max_pr_lambda", "ref_mag_res",
            "ref_mag_res_lambda", "trans_mag_res", "trans_mag_res_lambda",
            "xz_E_magnitudes", "xz_P_vectors", "xz_x_coord", "xz_z_coord",
            "yz_E_magnitudes", "yz_P_vectors", "yz_y_coord", "yz_z_coord"
        ],
        Union[np.ndarray, np.float16]
    ]

    # Predefined set of materials for simulations
    materials_explorer = Literal[
        "Au (Gold) - Ciesielski", "PZT", "Al2O3 - Palik", "SiO2 (Glass) - Palik",
        "Ta (Tantalum) - CRC", "Ge (Germanium) - Palik", "etch", "InAs - Palik",
        "Cr (Chromium) - CRC", "Ni (Nickel) - CRC", "TiN - Palik", "In (Indium) - Palik",
        "Ni (Nickel) - Palik", "Cr (Chromium) - Palik", "Au (Gold) - Palik",
        "Ge (Germanium) - CRC", "PEC (Perfect Electrical Conductor)", "W (Tungsten) - CRC",
        "InP - Palik", "Ag (Silver) - Palik(0 - 2um)", "Ag (Silver) - Palik",
        "Pt (Platinum) - Palik", "Au (Gold) - CRC", "Cu (Copper) - Palik",
        "W (Tungsten) - Palik", "Ti (Titanium) - CRC", "Cu (Copper) - CRC",
        "Ag (Silver) - Johnson and Christy", "GaAs - Palik", "Fe (Iron) - Palik",
        "Ag (Silver) - Palik(1 - 10um)", "Al (Aluminium) - CRC", "Rh (Rhodium) - Palik",
        "Sn (Tin) - Palik", "Au (Gold) - Johnson and Christy", "Pd (Palladium) - Palik",
        "V (Vanadium) - CRC", "Ag (Silver) - CRC", "Si (Silicon) - Palik",
        "Al (Aluminium) - Palik", "Fe (Iron) - CRC", "Ti (Titanium) - Palik",
        "H2O (Water) - Palik"
    ]

    # Predefined monitor literals
    monitor_literal = Literal[
        "ref_power_monitor", "ref_profile_monitor",
        "trans_power_monitor", "trans_profile_monitor",
        "xz_profile_monitor", "yz_profile_monitor"
    ]

    # List of monitor names in the simulation
    list_of_monitor_names: List[str] = [
        "ref_power_monitor", "ref_profile_monitor",
        "trans_power_monitor", "trans_profile_monitor",
        "xz_profile_monitor", "yz_profile_monitor"
    ]

    # Result types for each monitor
    monitor_result_types: Dict[str, List[str]] = {
        "ref_power_monitor": ["T"],  # T for transmitted power
        "trans_power_monitor": ["T"],  # T for transmitted power
        "ref_profile_monitor": ["E"],  # E for electric field profiles
        "trans_profile_monitor": ["E"],  # E for electric field profiles
        "xz_profile_monitor": ["E", "P"],  # E and P for electric field and Poynting vectors
        "yz_profile_monitor": ["E", "P"]  # E and P for electric field and Poynting vectors
    }

    # Monitor results corresponding to the monitors
    monitor_results: Dict[str, List[str]] = {
        "ref_profile_monitor": [
            "profile_x", "profile_y", "ref_profile_vectors",
            "ref_mag_max_pr_lambda", "ref_mag_res_lambda", "ref_mag_res"
        ],
        "trans_profile_monitor": [
            "profile_x", "profile_y", "trans_profile_vectors",
            "trans_mag_max_pr_lambda", "trans_mag_res_lambda", "trans_mag_res"
        ],
        "xz_profile_monitor": [
            "xz_profile_E_vectors", "xz_profile_P_vectors",
            "xz_profile_x_coord", "xz_profile_z_coord"
        ],
        "yz_profile_monitor": [
            "yz_profile_E_vectors", "yz_profile_P_vectors",
            "yz_profile_y_coord", "yz_profile_z_coord"
        ]
    }

    # Attribute slots for optimized memory usage
    __slots__ = [
        "save_path", "db", "name", "_active_meshes", "_active_structures",
        "_global_mesh_stepsizes", "_db_save_path", "_unit_cells", "_film_thickness", "_comment"
    ]

    def __init__(self,
                 simulation_name: str,
                 folder_name: str,
                 db_name: str,
                 from_base: bool = True,
                 hide: bool = True,
                 *args, **kwargs
                 ) -> None:
        """
        Initializes the simulation class.

        Args:
            simulation_name (str): The name of the simulation.
            folder_name (str): The name of the folder for base file and saving simulations.
            db_name (str): The name of the database for storing simulation results.
            from_base (bool): Whether to initialize from a base environment file or start fresh.
            save_path (str, optional): Path where the simulation file will be saved. Defaults to None.
            hide (bool): Whether to hide the simulation window. Defaults to True.
            *args: Additional positional arguments for the parent class.
            **kwargs: Additional keyword arguments for the parent class.

        Attributes:
            save_path (str): The path where the simulation file will be saved.
            db (DatabaseHandler): The database handler for managing simulation data.
            name (str): The name of the simulation.
            _global_mesh_stepsizes (list of np.float16): Global mesh step sizes in nanometers.
            _active_meshes (list): List of active meshes in the simulation.
            _active_structures (dict): Dictionary of active structures with details on shape, uniqueness, and grid status.
            _comment (str): A custom comment about the simulation that will be saved to the database. Can be whatever
                as long as it's a string.
        """

        # Check if the base environment file exists, and initialize from it if so.
        if os.path.exists(os.path.abspath("../Base Enviroment/base.fsp")) and from_base:
            print("Initializing simulation from base environment...")
            super().__init__(os.path.abspath("../Base Enviroment/base.fsp"), hide=hide, *args, **kwargs)
        elif from_base:
            print("Base environment file not found, initializing and saving it...")
            super().__init__(hide=hide, *args, **kwargs)
            from_base = False
        else:
            print("Initializing fresh simulation environment...")
            super().__init__(hide=hide, *args, **kwargs)

        # Set up the database handler for managing simulation results
        self.db = DatabaseHandler(db_name)

        # Define the path for saving simulations and ensure the directories exist
        saving_simulations_path = os.path.abspath("../Simulations")
        if not os.path.exists(saving_simulations_path):
            os.makedirs(saving_simulations_path)

        folder_path = os.path.join(saving_simulations_path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Set up database save path and ensure the folder exists
        self._db_save_path = os.path.abspath(f"../Database/Savefiles/{self.db.db_name}")
        if not os.path.exists(self._db_save_path):
            os.makedirs(self._db_save_path)

        # Set the full save path for the simulation file
        self.save_path = os.path.join(folder_path, f"{simulation_name}.fsp")

        # Assign the name of the simulation
        self.name = simulation_name

        # Initialize global mesh stepsizes (default 10 nm for x, y, z) and active meshes
        self._global_mesh_stepsizes = [np.float16(10), np.float16(10), np.float16(10)]
        self._active_meshes = []

        # Set up unit cell dimensions as a dictionary with placeholders for values
        self._unit_cells = {
            "unit_cell_1_x": None,
            "unit_cell_1_y": None,
            "unit_cell_2_x": None,
            "unit_cell_2_y": None,
            "unit_cell_3_x": None,
            "unit_cell_3_y": None,
        }

        # Keep track of edge meshes (sizes and steps) for different structures
        self._edge_meshes = {
            "struct_1_edge_mesh_size": None,
            "struct_1_edge_mesh_step": None,
            "struct_2_edge_mesh_size": None,
            "struct_2_edge_mesh_step": None,
            "struct_3_edge_mesh_size": None,
            "struct_3_edge_mesh_step": None,
        }

        # Initialize the custom simulation comment as None
        self._comment = None

        # Dictionary for tracking active structures in the simulation and their properties
        self._active_structures = {}

        # Switch simulation to layout mode
        self.switchtolayout()

        # Load custom materials from the 'Material_data' folder
        print("\tLoading custom materials...")
        self._load_all_custom_materials()
        print("\tCustom materials loaded.")

        # Set default film thickness to 100 nm
        self._film_thickness = 100

        # If not initialized from base, create and save the base configuration
        if not from_base:
            print("\tCreating base simulation environment...")
            self._init_default_configuration()
            print("\tBase environment created.")
            self.save(os.path.abspath("../Base Enviroment/base.fsp"))

        # Save the simulation in the designated folder
        self.save()

        # Indicate that the simulation has been initialized
        print("Simulation initialized.\n")

    def _get_active_monitors(self) -> str:
        """
        Fetches the names of all enabled monitors for the current simulation and returns them as a
        comma-separated string.

        This function yields a string that later lets you check if you're running a simulation with the
        same parameters as a previously stored one but with additional monitors enabled.
        In this case only the results of those extra monitors will be stored. All monitors that were already
        enabled in the previous simulation will be turned off to avoid redundant simulations.

        The returned string, containing the active monitor names, will be combined with the unique hash to
        ensure that no unnecessary simulations are executed.

        Returns:
            str: A comma-separated string of the names of all active monitors.
        """
        active_monitors = ""
        for monitor_name in SimulationBase.list_of_monitor_names:
            if self.getnamed(monitor_name, "enabled"):
                active_monitors += f",{monitor_name}"
        active_monitors = active_monitors[1:]  # Remove the leading comma

        return active_monitors

    def _init_default_configuration(self):
        """
        Initializes the default configuration for the FDTD simulation environment.

        This method sets up the essential components required for a steep-angle simulation with symmetric
        boundary conditions, optimized for x-polarized light. The configuration includes:

        - **Substrate**: A rectangular structure representing the substrate, centered along the z-axis, with a defined
          refractive index and dimensions.
        - **FDTD Region**: The main simulation region with anti-symmetric boundary conditions along the x-axis and symmetric
          conditions along the y-axis. The background material and PML settings are also configured.
        - **Power Monitors**: Two power monitors, one above and one below the substrate, to measure reflected and transmitted
          power. Unnecessary field components are disabled to reduce computation load.
        - **Profile Monitors**: Four profile monitors—two in the xy-plane, one in the xz-plane, and one in the yz-plane—configured
          to measure the electric field and Poynting vector profiles at different positions.
        - **Source**: A plane wave source that injects along the z-axis in the backward direction, set to work with x-polarized
          light.

        Key configurations:
        - Anti-symmetric boundary conditions for the x-direction and symmetric for the y-direction.
        - Mesh and monitor spans set for a 350x350 nm simulation area.
        - Power and profile monitors configured with unnecessary field outputs disabled to optimize performance.

        Returns:
            None
        """

        # Define common configuration for x and y span dimensions (350 nm x 350 nm)
        x_y_plane_span = {
            "x span": (350 * 1.1) * 1e-9,
            "y span": (350 * 1.1) * 1e-9
        }

        # === Add Substrate ===
        # Define the substrate with specific index and span, positioned symmetrically along the z-axis
        super().addrect(
            **x_y_plane_span,
            **{
                "name": "substrate",
                "z span": 750e-9,  # Thickness of the substrate
                "z": -750e-9 / 2,  # Center the substrate along the z-axis
                "index": 1.45,  # Refractive index of the substrate material
                "index units": "m",  # Units for refractive index
                "override mesh order from material database": True,
                "mesh order": 3  # Mesh priority for the substrate
            }
        )

        # === Add FDTD Region ===
        # Set up the main simulation region with boundary conditions for steep-angle, x-polarized light.
        # The background material is set to "etch".
        self.addfdtd(
            **{
                "x span": 350e-9,  # The x-span of the simulation region
                "y span": 350e-9,  # The y-span of the simulation region
                "z": (self._film_thickness / 2) * 1e-9,  # Position FDTD region centered in film
                "z span": 3000e-9,  # Span along the z-axis
                "background material": "etch",  # Background material
                "allow symmetry on all boundaries": True,  # Enable boundary symmetry where applicable
                "x min bc": "Anti-Symmetric",  # Anti-symmetric boundary on x-min
                "x max bc": "Anti-Symmetric",  # Anti-symmetric boundary on x-max
                "y min bc": "Symmetric",  # Symmetric boundary on y-min
                "y max bc": "Symmetric",  # Symmetric boundary on y-max
                "pml profile": 3,  # Set to steep angle
                "auto scale pml parameters": False,  # Disable auto-scaling for PML parameters
                "snap pec to yee cell boundary": False  # Disable snapping PEC to Yee cell boundary
            }
        )

        # === Add Power Monitors ===
        # Common configuration for power monitors: disable unnecessary field outputs to save computation.
        power_monitor_config = {
            f"output {field}{direction}": False for field in ["E", "H"] for direction in ["x", "y", "z"]
        }

        # Add reflection power monitor above the substrate
        self.addpower(
            **x_y_plane_span,
            **power_monitor_config,
            **{
                "name": "ref_power_monitor",  # Reflection power monitor
                "z": 700e-9  # Position 700 nm above the substrate
            }
        )

        # Add transmission power monitor below the substrate
        self.addpower(
            **x_y_plane_span,
            **power_monitor_config,
            **{
                "name": "trans_power_monitor",  # Transmission power monitor
                "z": -700e-9  # Position 700 nm below the substrate
            }
        )

        # === Add Profile Monitors (for field vector measurements) ===
        # Common configuration for profile monitors: disable H-field and power outputs.
        profile_monitor_config = {
            f"output H{direction}": False for direction in ["x", "y", "z"]
        }
        profile_monitor_config["output power"] = False

        # Add a profile monitor above the substrate for E-field vector measurement in the xy-plane
        self.addpower(
            **x_y_plane_span,
            **profile_monitor_config,
            **{
                "name": "ref_profile_monitor",
                "z": (self._film_thickness + 10) * 1e-9  # Position 10 nm above the film
            }
        )

        # Add a profile monitor below the substrate for E-field vector measurement in the xy-plane
        self.addpower(
            **x_y_plane_span,
            **profile_monitor_config,
            **{
                "name": "trans_profile_monitor",
                "z": -10e-9  # Position 10 nm below the substrate
            }
        )

        # Enable Poynting vector output for xz- and yz-profile monitors
        for direction in ["x", "y", "z"]:
            profile_monitor_config[f"output p{direction}"] = True

        # Add a profile monitor for the xz-plane
        self.addpower(
            **profile_monitor_config,
            **{
                "name": "xz_profile_monitor",
                "monitor type": "2D Y-normal",  # Monitor perpendicular to the y-axis
                "x span": 350e-9,  # Span along the x-axis
                "z span": 120e-9,  # Span along the z-axis
                "z": (self._film_thickness * 1e-9) / 2  # Position in the middle of the film
            }
        )
        self.set("enabled", False)  # Initially disabled

        # Add a profile monitor for the yz-plane
        self.addpower(
            **profile_monitor_config,
            **{
                "name": "yz_profile_monitor",
                "monitor type": "2D X-normal",  # Monitor perpendicular to the x-axis
                "y span": 350e-9,  # Span along the y-axis
                "z span": 120e-9,  # Span along the z-axis
                "z": (self._film_thickness * 1e-9) / 2  # Position in the middle of the film
            }
        )
        self.set("enabled", False)  # Initially disabled

        # === Add Plane Wave Source ===
        # Define the plane wave source for injecting along the z-axis with a backward direction.
        self.addplane(
            **x_y_plane_span,
            **{
                "name": "source",  # Name of the source
                "z": 800e-9 - 200e-9,  # Position the source above the simulation region
                "direction": "Backward",  # Injection direction is backward along the z-axis
                "injection axis": "z-axis",  # Inject along the z-axis
                "polarization definition": "P",  # Set polarization as x-polarized (P-polarization)
                "override global source settings": False,  # Do not override global source settings
                "use relative coordinates": False  # Use absolute coordinates
            }
        )

        # === Set Wavelength Range and Frequency Points ===
        # Set the global wavelength range for the simulation, from 400 nm to 1500 nm, with 1000 frequency points.
        self.set_global_wavelength_range(
            wavelength_start=400,  # Start wavelength: 400 nm
            wavelength_stop=1500,  # Stop wavelength: 1500 nm
            frequency_points=1000  # Number of frequency points
        )

    def _get_results(self, to_db: bool = False, prev_profile_results: dict = None) -> dict:
        """
        Fetches and processes simulation results from reflection, transmission, and profile monitors.

        Converts all spatial data (coordinates, wavelengths) from meters to nanometers
        and stores them as 16-bit floats for memory efficiency.

        Args:
            to_db (bool): Flag indicating whether to store certain results in the database.
            prev_profile_results (dict): Previous profile results to utilize in current processing, if available.

        Returns:
            dict: A dictionary containing the processed simulation data with specific keys:
                  - lambdas: Wavelengths in nanometers.
                  - ref_powers: Reflection powers.
                  - trans_powers: Transmission powers.
                  - ref_power_res_lambda: Resonance wavelengths for reflection power.
                  - ref_power_res: Resonance values for reflection power.
                  - trans_power_res_lambda: Resonance wavelengths for transmission power.
                  - trans_power_res: Resonance values for transmission power.
                  - profile_x: X-coordinates from profile monitors.
                  - profile_y: Y-coordinates from profile monitors.
                  - ref_profile_vectors: Reflection profile vectors.
                  - trans_profile_vectors: Transmission profile vectors.
                  - ref_mag_max_pr_lambda: Maximum magnitude resonance wavelengths for reflection profile.
                  - trans_mag_max_pr_lambda: Maximum magnitude resonance wavelengths for transmission profile.
                  - ref_mag_res_lambda: Resonance wavelengths for reflection profile magnitudes.
                  - ref_mag_res: Resonance values for reflection profile magnitudes.
                  - trans_mag_res_lambda: Resonance wavelengths for transmission profile magnitudes.
                  - trans_mag_res: Resonance values for transmission profile magnitudes.
                  - xz_profile_E_vectors: Electric field vectors for xz profiles.
                  - xz_profile_P_vectors: Power vectors for xz profiles.
                  - xz_profile_x_coord: X-coordinates for xz profiles.
                  - xz_profile_z_coord: Z-coordinates for xz profiles.
                  - yz_profile_E_vectors: Electric field vectors for yz profiles.
                  - yz_profile_P_vectors: Power vectors for yz profiles.
                  - yz_profile_y_coord: Y-coordinates for yz profiles.
                  - yz_profile_z_coord: Z-coordinates for yz profiles.
        """
        # Fetch active monitors once
        active_monitors = self._get_active_monitors().split(",")

        # Fetch wavelengths from the first monitor and convert to nanometers
        lambdas = (super().getresult(active_monitors[0],
                                     SimulationBase.monitor_result_types[active_monitors[0]][0])[
                       "lambda"] * 1e9).astype(np.float16).flatten()

        # Initialize result placeholders
        results = {
            "lambdas": lambdas,
            "ref_powers": None,
            "trans_powers": None,
            "ref_power_res_lambda": None,
            "ref_power_res": None,
            "trans_power_res_lambda": None,
            "trans_power_res": None,
            "profile_x": None,
            "profile_y": None,
            "ref_profile_vectors": None,
            "trans_profile_vectors": None,
            "ref_mag_max_pr_lambda": None,
            "trans_mag_max_pr_lambda": None,
            "ref_mag_res_lambda": None,
            "ref_mag_res": None,
            "trans_mag_res_lambda": None,
            "trans_mag_res": None,
            "xz_profile_E_vectors": None,
            "xz_profile_P_vectors": None,
            "xz_profile_x_coord": None,
            "xz_profile_z_coord": None,
            "yz_profile_E_vectors": None,
            "yz_profile_P_vectors": None,
            "yz_profile_y_coord": None,
            "yz_profile_z_coord": None
        }

        # Helper to fetch powers and resonances
        def fetch_powers(monitor_name, power_type, resonance_key):
            """Fetches powers from a specified monitor and computes resonances."""
            if monitor_name in active_monitors:
                powers = super(SimulationBase, self).getresult(monitor_name, power_type)["T"].astype(np.float16)
                resonance_lambda, resonance = self._get_resonance(lambdas, powers, resonance_type=resonance_key)
                if monitor_name == "trans_power_monitor":
                    powers *= (-1)  # Adjust for transmission powers
                return powers, resonance_lambda, resonance
            return None, None, None

        # Fetch reflection and transmission powers
        results["ref_powers"], results["ref_power_res_lambda"], results["ref_power_res"] = fetch_powers(
            "ref_power_monitor", "T", "reflection")
        results["trans_powers"], results["trans_power_res_lambda"], results["trans_power_res"] = fetch_powers(
            "trans_power_monitor", "T", "transmission")

        # Function to fetch profile vectors and resonances
        def fetch_profile_vectors(monitor_name, resonance_type):
            """Fetches profile vectors and computes resonances for a given monitor."""
            if monitor_name in active_monitors:
                profile_vectors = np.real(
                    super(SimulationBase, self).getresult(monitor_name, "E")["E"][:, :, 0, :]
                ).astype(np.float16)

                # Compute maximum electric field magnitude and resonances
                mag_max_pr_lambda = self._get_max_e_pr_lambda(
                    np.linalg.norm(profile_vectors, axis=-1).T.astype(np.float16))
                mag_res_lambdas, mag_ress = self._get_resonance(lambdas, mag_max_pr_lambda,
                                                                resonance_type=resonance_type, allow_multiple=True)
                main_idx = np.argmax(mag_ress)
                mag_res_lambda, mag_res = mag_res_lambdas[main_idx], mag_ress[main_idx]

                # Optionally filter for database storage
                if to_db:
                    mask = np.isin(lambdas, mag_res_lambdas)
                    profile_vectors = profile_vectors[:, :, mask]

                return profile_vectors, mag_max_pr_lambda, mag_res_lambda, mag_res

            return None, None, None, None

        # Fetch reflection and transmission profile vectors
        results["ref_profile_vectors"], results["ref_mag_max_pr_lambda"], results["ref_mag_res_lambda"], results[
            "ref_mag_res"] = fetch_profile_vectors("ref_profile_monitor", "reflection")
        results["trans_profile_vectors"], results["trans_mag_max_pr_lambda"], results["trans_mag_res_lambda"], results[
            "trans_mag_res"] = fetch_profile_vectors("trans_profile_monitor", "reflection")

        # Fetch coordinates for profile monitors
        if "ref_profile_monitor" in active_monitors:
            results["profile_x"] = (super().getresult("ref_profile_monitor", "E")["x"] * 1e9).astype(
                np.float16).flatten()
            results["profile_y"] = (super().getresult("ref_profile_monitor", "E")["y"] * 1e9).astype(
                np.float16).flatten()
        elif "trans_profile_monitor" in active_monitors:
            results["profile_x"] = (super().getresult("trans_profile_monitor", "E")["x"] * 1e9).astype(
                np.float16).flatten()
            results["profile_y"] = (super().getresult("trans_profile_monitor", "E")["y"] * 1e9).astype(
                np.float16).flatten()

        # Helper to fetch and filter profile data for xz and yz monitors
        def fetch_xy_profile_vectors(profile_type):
            """Fetches electric field and power vectors for specified profile type."""
            if f"{profile_type}_profile_monitor" in active_monitors:
                # Fetch electric field (E) and power (P) vectors
                E_results = super(SimulationBase, self).getresult(f"{profile_type}_profile_monitor", "E")
                P_results = super(SimulationBase, self).getresult(f"{profile_type}_profile_monitor", "P")
                E_vectors = np.real(E_results["E"][:, 0, :, :]).astype(np.float16)
                P_vectors = np.real(P_results["P"][:, 0, :, :]).astype(np.float16)

                # Handle previous results if provided
                if prev_profile_results is not None:
                    results["ref_mag_max_pr_lambda"] = prev_profile_results.get("ref_mag_max_pr_lambda", None)
                    results["trans_mag_max_pr_lambda"] = prev_profile_results.get("trans_mag_max_pr_lambda", None)

                # Fetch resonances for both transmission and reflection
                trans_mag_res_lambdas, _ = self._get_resonance(
                    lambdas,
                    results["trans_mag_max_pr_lambda"],
                    resonance_type="reflection",
                    allow_multiple=True
                )
                ref_mag_res_lambdas, _ = self._get_resonance(
                    lambdas,
                    results["ref_mag_max_pr_lambda"],
                    resonance_type="reflection",
                    allow_multiple=True
                )

                # Optionally filter for database storage
                if to_db:
                    ref_mask = np.isin(lambdas, ref_mag_res_lambdas)
                    trans_mask = np.isin(lambdas, trans_mag_res_lambdas)
                    combined_mask = trans_mask | ref_mask  # Combine masks to filter data
                    E_vectors = E_vectors[:, :, combined_mask]
                    P_vectors = P_vectors[:, :, combined_mask]

                return E_vectors, P_vectors, (E_results["x"] * 1e9).astype(np.float16).flatten(), (
                        E_results["z"] * 1e9).astype(np.float16).flatten()

            return None, None, None, None

        # Fetch xz and yz profile data
        results["xz_profile_E_vectors"], results["xz_profile_P_vectors"], results["xz_profile_x_coord"], results[
            "xz_profile_z_coord"] = fetch_xy_profile_vectors("xz")
        results["yz_profile_E_vectors"], results["yz_profile_P_vectors"], results["yz_profile_y_coord"], results[
            "yz_profile_z_coord"] = fetch_xy_profile_vectors("yz")

        return results

    def _save_results_to_database(self, results_dict: SimulationBase.ResultDataType) -> None:
        """
        Processes the simulation results and saves relevant parameters to the database.

        Retrieves parameters such as structure spans, materials, FDTD spans, mesh step sizes,
        monitor positions, and polarization angle, and constructs a data object for insertion into the database.

        Args:
            results_dict (SimulationBase.ResultDataType): A dictionary containing the simulation results.
                This is the dictionary created in the _get_results() function and ultimately returned by the run() function.

        Returns:
            None
        """
        # Retrieve structure spans and materials for three structures
        spans = [self.get_structure_spans(i) for i in range(1, 4)]
        materials = [self._get_structure_material(i) for i in range(1, 4)]

        # Get FDTD spans and the global wavelength range
        fdtd_spans = self.get_FDTD_spans()
        lambda_start, lambda_stop, frequency_points = self._get_global_wavelength_range()

        # Prepare the data for database insertion
        to_db = SimulationData(
            **results_dict,
            name=self.name,
            **{f"struct{i}_{axis}span": spans[i - 1][j] for i in range(1, 4) for j, axis in enumerate(['x', 'y', 'z'])},
            **{f"struct{i}_material": materials[i - 1] for i in range(1, 4)},
            fdtd_xspan=fdtd_spans[0],
            fdtd_yspan=fdtd_spans[1],
            fdtd_zspan=fdtd_spans[2],
            **self._unit_cells,
            mesh_dx=self._global_mesh_stepsizes[0],
            mesh_dy=self._global_mesh_stepsizes[1],
            mesh_dz=self._global_mesh_stepsizes[2],
            polarization_angle=self._get_polarization_angle(),
            lambda_start=lambda_start,
            lambda_stop=lambda_stop,
            frequency_points=frequency_points,
            simulation_hash=self.__hash__(),
            active_monitors=self._get_active_monitors(),
            **self._edge_meshes,
            incidence_angle=self._get_incidence_angle(),
            boundary_symmetries=self._get_boundary_symmetry_conditions(),
            comment=self._comment
        )

        # Save the prepared data to the database
        self.db.save_simulation_data(to_db)

    def _structure_exists(self, structure_type_id: str | int):
        """
        Checks if the structure with the given structure number exists in the active structures.

        Args:
            structure_type_id (int): The unique identifier for the structure.

        Returns:
            bool: True if the structure exists, False otherwise.
        """
        return True if f"structure_{structure_type_id}" in self._active_structures.keys() else False

    def _possibly_raise_structure_doesnt_exist_error(self, structure_type_id: str | int) -> None:
        """
        Checks if the structure with the given structure number exists and raises an error if it does not.

        Args:
            structure_type_id (int): The unique identifier for the structure.

        Raises:
            StructureDoesNotExistError: If the structure with the specified structure number does not exist.
        """
        if not self._structure_exists(structure_type_id):
            raise StructureDoesNotExistError(structure_type_id)

    def _get_structure_positions(self, structure_type_id: str | int) \
            -> tuple[np.float16 | None, np.float16 | None, np.float16 | None]:
        """
        Retrieves the x, y, and z coordinates of the center of the structure identified by the given structure type ID.

        Args:
            structure_type_id (str | int): The unique identifier for the structure.

        Returns:
            tuple[np.float16 | None, np.float16 | None, np.float16 | None]:
            A tuple containing the x, y, and z coordinates of the structure's center. Each coordinate is represented as a np.float16.
            If the structure does not exist, an error is raised before retrieval.

        Raises:
            StructureNotUniqueError: If there is more than one structure with the given structure type ID.

        Notes:
            The coordinates are returned in nanometers.
        """
        # Check if the structure exists and raise an error if not
        self._possibly_raise_structure_doesnt_exist_error(structure_type_id)

        # Fetch the coordinates
        x = np.float16(
            self.getnamed(
                f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
                "x"
            ) * 1e9  # Convert from meters to nanometers
        )

        y = np.float16(
            self.getnamed(
                f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
                "y"
            ) * 1e9  # Convert from meters to nanometers
        )

        z = np.float16(
            self.getnamed(
                f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
                "z"
            ) * 1e9  # Convert from meters to nanometers
        )

        return x, y, z

    def _get_structure_material(self, structure_type_id: str | int) -> str | None:
        """
        Retrieves the material of the specified structure type.

        Args:
            structure_type_id (int): The unique number identifying the structure type.

        Returns:
            str | None: The material of the structure type if it exists; otherwise, None.

        Notes:
            If the structure does not exist, this method returns None without raising an error.
        """
        # Check if the structure exists
        if not self._structure_exists(structure_type_id):
            return None

        # Get the active structure's details
        structure_info = self._active_structures[f"structure_{structure_type_id}"]
        hole_in = structure_info.get("hole in")

        # If the structure is implanted in another structure
        if hole_in is not None:
            material = self.getnamed(
                f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
                "material"
            )
            hole_material = self.getnamed(
                f"structure_{hole_in}_group::structure_{hole_in}_1::structure_{hole_in}",
                "material"
            )
            return f"{material} in {hole_material}"

        # Return the material of the structure
        return self.getnamed(
            f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
            "material"
        )

    def _add_structure(
            self,
            structure_type_id: str | int,
            part_of_grid: bool = False,
            hole_in: str | int | None = None
    ) -> None:
        """
        Checks if a structure type with the given ID already exists. If it does not exist,
        it creates a mesh for the structure type and assigns it the specified parameters. Additionally,
        it creates a group for the structure type.

        This method is intended to be called before any function that adds a structure with a specific
        shape. It ensures that the necessary mesh and group are created for the structure type.

        Args:
            structure_type_id (int): The unique number identifying the structure type.
            part_of_grid (bool, optional): Indicates whether the structure is part of a grid. Defaults to False.
            hole_in (str | int | None, optional): The ID of the structure it is a hole in, if applicable.

        Side Effects:
            If the structure does not exist, it modifies the internal state by adding the structure and
            mesh to the active lists and setting relevant parameters.
        """
        # Construct the key for the active structures dictionary
        structure_key = f"structure_{structure_type_id}"

        # Check if the structure already exists in the active structures
        if structure_key not in self._active_structures:
            # Create a new entry for the structure with initial parameters
            self._active_structures[structure_key] = {
                "grid": part_of_grid,  # Whether the structure is part of a grid
                "unique": True,  # Indicates if this structure type is unique
                "hole in": hole_in,  # Reference to a parent structure if it is a hole
                "nr": 1  # Initial count for this structure type
            }

            # Add the mesh identifier to the list of active meshes
            self._active_meshes.append(f"mesh_{structure_type_id}")

            # Create a new group for this structure type
            self.addgroup(name=f"{structure_key}_group")

            # Set mesh parameters
            self.set("use relative coordinates", False)  # Use absolute coordinates
            self.addmesh()  # Create the mesh
            self.set("name", f"mesh_{structure_type_id}")  # Name the mesh
            self.set("based on a structure", True)  # Indicate this mesh is based on a structure

            # Set mesh sizes in nanometers (conversion factor applied)
            self.set("dx", float(self._global_mesh_stepsizes[0]) * 1e-9)  # X dimension
            self.set("dy", float(self._global_mesh_stepsizes[1]) * 1e-9)  # Y dimension
            self.set("dz", float(self._global_mesh_stepsizes[2]) * 1e-9)  # Z dimension

            # Associate the mesh with the structure
            self.set("structure", structure_key)

            # Add the mesh to the structure's group
            self.addtogroup(f"{structure_key}_group")
        else:
            # If the structure already exists, update its properties
            self._active_structures[structure_key]["unique"] = False  # Mark it as not unique
            self._active_structures[structure_key]["nr"] += 1  # Increment the count for this structure type

    def _get_global_wavelength_range(self) -> Tuple[np.float16, np.float16, np.float16]:
        """
        Fetches the simulation's global source wavelength range and the number of frequency points in the monitors.

        Returns:
            Tuple[np.float16, np.float16, np.float16]:
                - The start wavelength (in nanometers).
                - The stop wavelength (in nanometers).
                - The number of frequency points used in the simulation.
        """
        # Fetch the start wavelength from the global source and convert to nanometers (1 meter = 1e9 nanometers)
        start = np.float16(self.getglobalsource("wavelength start") * 1e9)

        # Fetch the stop wavelength from the global source and convert to nanometers
        stop = np.float16(self.getglobalsource("wavelength stop") * 1e9)

        # Fetch the number of frequency points used in the global monitor
        points = np.float16(self.getglobalmonitor("frequency points"))

        # Return the start wavelength, stop wavelength, and number of frequency points as a tuple
        return start, stop, points

    def _load_all_custom_materials(self) -> None:
        """
        Loads all custom materials from .txt files in the Material_data directory.

        This method scans the 'Material_data' directory for all .txt files,
        loads each material's data, and adds the materials to the simulation environment.

        Returns:
            None
        """
        material_data_folder = "../Material_data"  # Path to the material data directory
        for file_name in os.listdir(material_data_folder):
            # Process only .txt files in the directory
            if file_name.endswith(".txt"):
                data_path = os.path.join(material_data_folder, file_name)
                self._load_material(data_path)  # Load each material

    def _load_material(self, data_path: str) -> None:
        """
        Loads material data from a specified .txt file and corresponding .json file.

        This method reads material data, checks for existing materials to avoid duplicates,
        and adds new materials to the simulation. It also loads fit parameters from a .json file.

        Args:
            data_path (str): The path to the material data .txt file.

        Raises:
            ValueError: If the first column of the material dataset is not wavelength (lambda) or frequency (Hz),
                         or if neither permittivity nor refractive index is provided in the material data.
        """
        # Open the material data file and read the name
        with open(data_path, "r") as material_data:
            material_name = material_data.readline().strip()  # Read the material name

            # Skip the material if it already exists
            if material_name in self.getmaterial():
                return

            types = material_data.readline().strip().split(",")  # Read the types from the second line

            # Read the rest of the data into a NumPy array
            data = np.loadtxt(material_data)

            # Process the first column to determine frequencies
            if "lambda" in types[0]:  # If the first column is wavelength
                if "nm" in types[0]:
                    frequencies = (1 / (data[:, 0] * 1e-9)) * constants.c
                elif "angstrom" in types[0]:
                    frequencies = (1 / (data[:, 0] * 1e-10)) * constants.c
                elif "um" in types[0]:
                    frequencies = (1 / (data[:, 0] * 1e-6)) * constants.c
                elif "mm" in types[0]:
                    frequencies = (1 / (data[:, 0] * 1e-3)) * constants.c
                elif "m" in types[0]:
                    frequencies = (1 / data[:, 0]) * constants.c
            elif "Hz" not in types[0]:  # If the first column is not in Hz, raise an error
                raise ValueError(
                    "The first column in the material dataset must be either wavelength (lambda) or frequency (Hz)."
                )

            # Check if permittivity or refractive index is specified
            if "e" in types[1] and "e" in types[2]:
                complex_permittivity = data[:, 1] + 1j * data[:, 2]
            elif "index" in types[1] and "index" in types[2]:
                complex_permittivity = np.sqrt(data[:, 1]) + 1j * np.sqrt(data[:, 2])
            else:
                raise ValueError("Either permittivity or refractive index must be given in the material data.")

            # Collect the sampled data into a NumPy array
            sampled_data = np.array([frequencies, complex_permittivity]).T

            # Create a new material and add it to the simulation environment
            default_name = self.addmaterial("Sampled 3D data")
            self.setmaterial(default_name, "name", material_name)  # Set the material name
            self.setmaterial(material_name, "sampled data", sampled_data)  # Add sampled data

            # Load the fit parameters from a .json file with the same name as the material data file
            with open(os.path.splitext(data_path)[0] + '.json', "r") as file:
                fit_parameters = json.load(file)

            # Set the fit parameters for the material
            for parameter, value in fit_parameters.items():
                self.setmaterial(material_name, parameter, value)

    def _get_film_thickness(self) -> int:
        """
        Retrieves the thickness of the film.

        Returns:
            int: The thickness of the film in nanometers.
        """
        return self._film_thickness

    def _create_edge_meshes(
            self, mesh_size: int, structure_type_id: int | str, step_size: float, struct_nr: int
    ) -> None:
        """
        Creates edge mesh cubes at the corners of the given structure and adds them to the simulation group.

        This function calculates the corner positions of a structure and places small cubic meshes (edge cubes) at each
        corner. The edge cubes are created based on the given cube size, step size for the mesh, and material properties.
        The edge cubes are added to the same group as the structure so that they move and scale together.

        Args:
            mesh_size (int): The size of each edge cube (in nanometers).
            structure_type_id (int | str): The unique identifier of the structure type to which the edge cubes are associated.
            step_size (float): The mesh step size (in nanometers) used for creating the mesh for the edge cubes.
            struct_nr (int): The instance number of the structure of the structure type for which the edge mesh is being created.

        Returns:
            None: The function modifies the simulation by adding edge mesh cubes and updating the mesh, but does not return a value.

        Additional Notes:
            - The edge cubes are created at the corners of the structure based on its calculated bounding box dimensions.
            - The edge mesh will follow the structure if it is moved or resized.
        """
        edge_mesh_name = f"edge_mesh_{structure_type_id}_{struct_nr}"
        structure_name = f"structure_{structure_type_id}"
        mesh_size = float(mesh_size * 1e-9)
        step_size = float(step_size * 1e-9)

        # Set the structure in the active structures dictionary to have edge mesh enabled
        self._edge_meshes[f"struct_{structure_type_id}_edge_mesh_size"] = np.float16(mesh_size)
        self._edge_meshes[f"struct_{structure_type_id}_edge_mesh_step"] = np.float16(step_size)

        # Fetch structure bounding box dimensions
        xmin = round(
            self.getnamed(f"{structure_name}_group::{structure_name}_{struct_nr}::{structure_name}", "x min"), 10
        )
        xmax = round(
            self.getnamed(f"{structure_name}_group::{structure_name}_{struct_nr}::{structure_name}", "x max"), 10
        )
        ymin = round(
            self.getnamed(f"{structure_name}_group::{structure_name}_{struct_nr}::{structure_name}", "y min"), 10
        )
        ymax = round(
            self.getnamed(f"{structure_name}_group::{structure_name}_{struct_nr}::{structure_name}", "y max"), 10
        )
        zmin = round(
            self.getnamed(f"{structure_name}_group::{structure_name}_{struct_nr}::{structure_name}", "z min"), 10
        )
        zmax = round(
            self.getnamed(f"{structure_name}_group::{structure_name}_{struct_nr}::{structure_name}", "z max"), 10
        )

        # Calculate corner positions automatically
        corner_positions = [
            (xmin, ymin, zmin),
            (xmin, ymin, zmax),
            (xmin, ymax, zmin),
            (xmin, ymax, zmax),
            (xmax, ymin, zmin),
            (xmax, ymin, zmax),
            (xmax, ymax, zmin),
            (xmax, ymax, zmax),
        ]

        # Create mesh cubes at each corner
        for i, (x, y, z) in enumerate(corner_positions):
            super().addmesh(
                name=f"{edge_mesh_name}_{i + 1}", x=float(x), y=float(y), z=float(z),
                x_span=float(mesh_size), y_span=float(mesh_size), z_span=float(mesh_size)
            )
            self.set("dx", step_size), self.set("dy", step_size), self.set("dz", step_size)
            self.addtogroup(f"{structure_name}_group::{structure_name}_{struct_nr}")

    def _get_polarization_angle(self) -> np.float16:
        """
        Retrieves the polarization angle (phi) of the source in the simulation.

        Returns:
            np.float16: The current polarization angle in degrees as a 16-bit floating-point number.
        """
        return np.float16(self.getnamed("source", "angle phi"))

    def _get_mesh_stepsizes(self) -> Tuple[np.float16, np.float16, np.float16]:
        """
        Retrieves the current mesh step sizes for the x, y, and z directions.

        Returns:
            Tuple[np.float16, np.float16, np.float16]: A tuple containing the step sizes in nanometers for
                                                       the x, y, and z directions as 16-bit floating-point values.
        """
        # Return the current global mesh step sizes
        return (
            self._global_mesh_stepsizes[0],
            self._global_mesh_stepsizes[1],
            self._global_mesh_stepsizes[2]
        )

    def _get_boundary_symmetry_conditions(self) -> str:
        """
        Fetches a string with the boundary symmetry conditions for all axes.

        Retrieves the boundary conditions for the x, y, and z axes from the FDTD simulation region
        and returns them in a comma-separated string.

        Returns:
            str: A comma-separated string containing the boundary conditions in the order:
                 x min, x max, y min, y max, z min, z max.
        """
        # Define the boundary directions to fetch
        boundaries = ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]

        # Fetch all boundary conditions from FDTD and join them into a comma-separated string
        boundary_conditions = [self.getnamed("FDTD", bc) for bc in boundaries]

        return ",".join(boundary_conditions)

    def _get_incidence_angle(self) -> np.float16:
        """
        Retrieves the current angle of incidence of the source in the FDTD simulation.

        Returns
        -------
        np.float16
            The angle of incidence in degrees, cast to NumPy's float16 format for memory efficiency.
        """
        # Fetch the 'angle theta' from the source configuration and return it as a NumPy float16
        return np.float16(self.getnamed("source", "angle theta"))

    @staticmethod
    def _get_resonance(
            wavelengths: np.ndarray, powers: np.ndarray, resonance_type: str, allow_multiple: bool = False) \
            -> tuple[None, None] | tuple[np.ndarray, np.ndarray]:
        """
        Locates the main resonance peak in the result signals based on the specified resonance type.

        Args:
            wavelengths (np.ndarray): The array of wavelengths corresponding to the powers.
            powers (np.ndarray): The array of power values from the simulation.
            resonance_type (str): The type of resonance to locate, either "reflection" or "transmission".
            allow_multiple (bool): Flag indicating whether to return all resonance peaks (default is False).

        Returns:
            tuple[None, None] | tuple[np.ndarray, np.ndarray]:
                If `allow_multiple` is False, returns a tuple containing the main resonance wavelength and power.
                If `allow_multiple` is True, returns arrays of wavelengths and powers for all detected resonances.
                If no peaks are found, returns (None, None).

        Raises:
            ValueError: If `resonance_type` is not "reflection" or "transmission".
        """

        # Identify the peaks in the power data based on the specified resonance type
        if resonance_type == "reflection":
            peaks, _ = find_peaks(powers)
        elif resonance_type == "transmission":
            peaks, _ = find_peaks(powers)  # Use negative for transmission to find minima
        else:
            raise ValueError("Invalid resonance_type specified. Must be 'reflection' or 'transmission'.")

        # If no peaks are found, return None, None.
        if peaks.size == 0:
            return None, None

        # Create a mask to filter out the identified peaks
        mask = np.zeros_like(powers, dtype=bool)
        mask[peaks] = True

        # Filter powers based on resonance type; reflectance uses raw, transmission uses negative values
        filtered_powers = powers[mask] if resonance_type == "reflection" else -powers[mask]
        filtered_wavelengths = wavelengths[mask]

        if allow_multiple:
            # Return all resonance wavelengths and powers if requested
            return filtered_wavelengths, filtered_powers

        # Determine the main resonance peak based on the specified type
        main_res_idx = np.argmax(filtered_powers) if resonance_type == "reflection" else np.argmin(filtered_powers)

        # Extract the main resonance wavelength and power
        main_res_power = filtered_powers[main_res_idx]
        main_res_wavelength = filtered_wavelengths[main_res_idx]

        return main_res_wavelength, main_res_power

    @staticmethod
    def _get_max_e_pr_lambda(magnitudes: np.ndarray) -> np.ndarray:
        """
        Finds the greatest E-field magnitude in the profile plane for each simulated wavelength.

        Args:
            magnitudes (np.ndarray): A 3D array of E-field magnitudes where each slice along the first axis
                                     corresponds to a different wavelength and the remaining two axes represent
                                     the spatial dimensions (x, y).

        Returns:
            np.ndarray: An array of the maximum E-field magnitudes for each wavelength, with the length equal
                        to the number of wavelengths.
        """

        # Find the maximum E-field magnitude across the (x, y) positions for each wavelength
        max_magnitudes = np.max(magnitudes, axis=(1, 2))

        return max_magnitudes

    def __hash__(self) -> str:
        """
        Generates a unique hash string based on the simulation parameters.

        This hash is derived from various attributes of the simulation, including structure spans,
        materials, polarization angle, and monitor positions. If two simulations have identical parameters,
        their hash strings will be equal.

        Important: Changing the order of the attributes will result in a different unique hash string.

        Returns:
            str: A hexadecimal string representing the unique hash of the simulation parameters.
        """

        # Collect edge meshes and unit cells from the respective dictionaries
        edge_meshes = (mesh_val for param, mesh_val in self._edge_meshes.items())
        unit_cells = (cell_val for param, cell_val in self._unit_cells.items())

        # Gather all relevant attributes to form the unique hash
        attributes = (
            *self.get_structure_spans(1),  # Structure spans for structure 1
            self._get_structure_material(1),  # Material for structure 1
            *self.get_structure_spans(2),  # Structure spans for structure 2
            self._get_structure_material(2),  # Material for structure 2
            *self.get_structure_spans(3),  # Structure spans for structure 3
            self._get_structure_material(3),  # Material for structure 3
            self._get_polarization_angle(),  # Polarization angle
            *self.get_FDTD_spans(),  # FDTD spans
            *self._get_mesh_stepsizes(),  # Mesh step sizes
            *self._get_global_wavelength_range(),  # Global wavelength range
            *unit_cells,  # Unit cells
            *edge_meshes,  # Edge meshes
            self._get_boundary_symmetry_conditions(),  # Symmetry conditions on all boundaries
            self._get_incidence_angle()  # Source angle of incidence
        )

        # Create a string representation of all attributes and encode it to bytes
        attributes_string = ','.join([str(attr) for attr in attributes]).encode('utf-8')

        # Generate and return the SHA-256 hash of the attributes string as a hexadecimal string
        return hashlib.sha256(attributes_string).hexdigest()

    def __eq__(self, other_hash: str) -> bool:
        """
        Compares the hash string of the current simulation instance with another hash.

        This method overrides the equality operator to enable comparison based on hash values.

        Args:
            other_hash (str): The hash string of another simulation to compare against.

        Returns:
            bool: True if the hash strings are equal; otherwise, False.
        """
        # Compare the hash of the current instance with the provided hash
        return self.__hash__() == other_hash

    def get_structure_spans(self, structure_type_id: str | int) \
            -> tuple[np.float16 | None, np.float16 | None, np.float16 | None]:
        """
        Retrieves the x, y, and z spans of all structures identified by the given structure type ID.

        Args:
            structure_type_id (str | int): The unique identifier for the structure type.

        Returns:
            tuple[np.float16 | None, np.float16 | None, np.float16 | None]:
            A tuple containing the x, y, and z spans of the structures. Each span is represented as a np.float16.
            If the structure does not exist, None values are returned for each span.

        Notes:
            The spans are returned in nanometers.
        """
        # Check if the structure exists
        if not self._structure_exists(structure_type_id):
            return None, None, None

        # Retrieve the spans from the structure
        x_span = np.float16(
            self.getnamed(
                f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
                "x span"
            ) * 1e9  # Convert from meters to nanometers
        )

        y_span = np.float16(
            self.getnamed(
                f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
                "y span"
            ) * 1e9  # Convert from meters to nanometers
        )

        z_span = np.float16(
            self.getnamed(
                f"structure_{structure_type_id}_group::structure_{structure_type_id}_1::structure_{structure_type_id}",
                "z span"
            ) * 1e9  # Convert from meters to nanometers
        )

        return x_span, y_span, z_span

    def set_simulation_comment(self, comment: Optional[str], custom_parameter: str | None = None) -> None:
        """
        Sets a comment that will be saved to the database along with the simulation results.

        Parameters:
        -----------
        comment : str or None
            The comment to be saved. Pass None to nullify the comment.
        custom_parameter : str or None
            Can be anything as long as it's a string. This will be displayed in the "Custom parameter" collumn in
            the database.

        Raises:
        -------
        AttributeError:
            If the provided comment is not of type 'str' or None.
        """
        # Check if comment is either a string or None
        if comment is not None and not isinstance(comment, str):
            raise AttributeError("The comment must be of type 'str' or None.")

        # Store the comment for later use
        self._comment = f"{comment};:;{custom_parameter}"

    def delete_structure(self, structure_type_id: int | str) -> None:
        """
        Deletes all structures with the given structure type id from the simulation environment.

        This method checks if the structure exists, deletes it from the simulation,
        resets related variables, and removes any associated meshes from active lists.

        Args:
            structure_type_id (int | str): The structure type Id of the structure(s) to be deleted.

        Raises:
            ValueError: If the specified structure does not exist in the simulation environment.
        """
        # Check if the structure exists
        self._possibly_raise_structure_doesnt_exist_error(structure_type_id)

        # Select and delete all structures with this ID in the simulation environment
        self.select(f"structure_{structure_type_id}_group")
        self.delete()

        # Reset all variables related to this structure type, if applicable
        if structure_type_id in (1, 2, 3):
            # Clear unit cell values for the specified structure type
            self._unit_cells[f"unit_cell_{structure_type_id}_x"] = None
            self._unit_cells[f"unit_cell_{structure_type_id}_y"] = None

            # Clear edge mesh parameters for the specified structure type
            self._edge_meshes[f"struct_{structure_type_id}_edge_mesh_size"] = None
            self._edge_meshes[f"struct_{structure_type_id}_edge_mesh_step"] = None

        # Remove the structure from the active structures dictionary
        del self._active_structures[f"structure_{structure_type_id}"]

        # Remove the corresponding mesh from the active meshes list
        self._active_meshes = [
            mesh for mesh in self._active_meshes if mesh != f"mesh_{structure_type_id}"
        ]

    def flip_polarization_and_boundary_symmetries(self, allow_symmetry: bool = True) -> None:
        """
        Flips the polarization angle of the source by 90° counterclockwise and adjusts the boundary symmetry conditions
        based on the new polarization angle, incidence angle, and the `allow_symmetry` flag.

        The method checks the current polarization angle of the source:
        - If the polarization is along the x-axis (0° or 180°), it rotates the polarization angle by 90° to align it
          with the y-axis (90° or 270°). The boundary conditions are then set as follows:
            - x min bc: Symmetric
            - x max bc: Symmetric
            - y min bc: Anti-Symmetric
            - y max bc: Anti-Symmetric

        - If the polarization is along the y-axis (90° or 270°), it rotates the polarization angle by 90° to align it
          with the x-axis (0° or 180°). The boundary conditions are set to:
            - x min bc: Anti-Symmetric
            - x max bc: Anti-Symmetric
            - y min bc: Symmetric
            - y max bc: Symmetric

        If the polarization angle does not align exactly with the x-axis or y-axis, or if the incidence angle is not
        zero and `allow_symmetry` is True, Bloch boundary conditions are applied to all sides.

        - If `allow_symmetry` is False, PML boundary conditions are applied.

        Parameters
        ----------
        allow_symmetry : bool, optional
            Whether to allow symmetry in the boundary conditions (default is True). I false PML boundaries are applied.

        Returns
        -------
        None
        """
        previous_polarization = self.getnamed("source", "angle phi") % 360  # Fetch the current polarization angle

        self.set_polarization_angle(previous_polarization - 90, allow_symmetry)  # Set the new polarization angle

    def run(self, to_db: bool = False, prev_profile_results: dict | None = None) -> dict:
        """
        Executes the FDTD simulation and returns the results.

        This method runs the simulation and, upon completion, extracts the results as a dictionary.
        The optional `prev_profile_results` dictionary can be provided to enhance the result extraction
        process with additional context from a previous simulation run.

        Args:
            to_db (bool): A flag indicating whether the results are going to be saved to the database. Default is False.
            prev_profile_results (dict | None): A dictionary containing relevant results from a previous simulation
                                                 with the same parameters already saved to the database, or None
                                                 if not applicable. This can be used to enhance the result extraction.

        Returns:
            dict: A dictionary containing the results of the simulation, including relevant data extracted
                  after execution.

        Raises:
            None
        """
        print("\nSimulation started running...")

        # Execute the simulation by calling the parent class's run method
        super().run()

        # Save the simulation state or results to a file
        self.save()

        # Indicate that the simulation has finished running
        print("Simulation finished running.")

        # Extract the results from the simulation and, if applicable, save them to the database
        return self._get_results(to_db=to_db, prev_profile_results=prev_profile_results)

    def save(self, save_path: str = None):
        """
        Saves the Lumerical FDTD simulation file.

        This method allows saving the simulation file to a specified path. If no path is provided,
        it saves the file to the default save path.

        Parameters:
            save_path (str, optional): The path where the simulation file should be saved.
                                        If None, the default save path is used.

        Returns:
            None
        """
        # Check if a custom save path is provided
        if save_path is None:
            # Save the simulation file to the default save path
            super().save(self.save_path)
        else:
            # Save the simulation file to the specified path
            super().save(save_path)

    def set_mesh_enabled_for_structure(self, structure_type_id: str | int, enabled: bool) -> None:
        """
        Enables or disables the mesh for every structure with the given structure type ID.

        Args:
            structure_type_id (int): The ID of the structure type for which to enable or disable the mesh.
            enabled (bool): A boolean indicating whether to enable (True) or disable (False) the mesh.

        Raises:
            StructureDoesNotExistError: If the structure with the given structure_type_id does not exist.
        """
        # Check if the structure exists; raise an error if it does not
        self._possibly_raise_structure_doesnt_exist_error(structure_type_id)

        # Iterate through active meshes to find the one associated with the specified structure type ID
        for mesh in self._active_meshes:
            if mesh == f"mesh_{structure_type_id}":
                # Enable or disable the mesh based on the provided boolean value
                self.setnamed(f"structure_{structure_type_id}_group::mesh_{structure_type_id}", "enabled", enabled)

    def set_global_wavelength_range(self,
                                    wavelength_start: float | int | np.float16,
                                    wavelength_stop: float | int | np.float16,
                                    frequency_points: int) -> None:
        """
        Sets the global source wavelength range and the number of frequency points for the simulation monitors.

        This method automatically adjusts the z-span of the FDTD region, as well as the positions of the source
        and power monitors based on the specified wavelength range and the thickness of the simulated film.
        There will be a distance of λ_max from each side of the film to the respective FDTD z boundary.
        The monitors and sources are positioned at appropriate distances from both the film and the z PML boundaries.

        Args:
            wavelength_start (float | int | np.float16): The start wavelength (in nanometers).
            wavelength_stop (float | int | np.float16): The stop wavelength (in nanometers).
            frequency_points (int): The number of frequency points to set for the monitors.

        Returns:
            None
        """
        # Set the global source's start wavelength in meters (1 nanometer = 1e-9 meters)
        self.setglobalsource("wavelength start", float(wavelength_start) * 1e-9)

        # Set the global source's stop wavelength in meters
        self.setglobalsource("wavelength stop", float(wavelength_stop) * 1e-9)

        # Set the number of frequency points for the simulation monitors
        self.setglobalmonitor("frequency points", frequency_points)

        # Retrieve the current FDTD simulation span dimensions
        fdtd_xspan, fdtd_yspan, fdtd_zspan = self.get_FDTD_spans()

        # Update the FDTD spans to account for the new wavelength range and film thickness
        self.set_FDTD_spans((fdtd_xspan, fdtd_yspan, wavelength_stop * 2  + self._get_film_thickness()))

    def set_film_thickness(self, thickness: int) -> None:
        """
        Sets the thickness of the film (nm) and updates the FDTD spans accordingly.

        This method updates the film thickness and recalculates the z-span of the FDTD region
        to accommodate the new thickness. The z-span is adjusted based on the maximum wavelength
        from the global wavelength range and the updated film thickness.

        Args:
            thickness (int): The new thickness of the film to be set (in nanometers).

        Returns:
            None
        """
        # Update the film thickness
        self._film_thickness = thickness

        # Get the maximum wavelength from the global wavelength range
        max_wavelength = self._get_global_wavelength_range()[1]

        # Update the FDTD spans to account for the new wavelength range and film thickness
        self.set_FDTD_spans((None, None, max_wavelength * 2 + self._get_film_thickness()))

    def run_and_save_to_db(self) -> None:
        """
        Runs the simulation and saves the results to the database.

        This method checks if a simulation with the same parameters already exists in the database.
        - If it exists and no new monitors are active in the current simulation, it prints a message and exits
          without running the simulation.
        - If new monitors are present, it disables redundant monitors and runs the simulation with only the new ones,
          then updates the existing database entry with the new results.

        If the simulation does not exist:
        - It validates that active structures and necessary monitors (reflection and transmission power monitors)
          are present before attempting to run the simulation.

        In either case, the simulation is retried up to 3 times upon failure, with error messages printed
        after each failed attempt.

        Raises:
            NoActiveStructuresError: If no active structures are present in the simulation.
            InsufficientMonitorsError: If either the reflection or transmission power monitors are missing when they shouldn't.

        Returns:
            None
        """

        # Check if the simulation exists and retrieve previous active monitors
        simulation_exists, prev_active_monitors, simulation = self.db.simulation_exists(self.__hash__())
        prev_active_monitors = set(prev_active_monitors or [])

        # Get current active monitors and identify new ones
        current_active_monitors = set(self._get_active_monitors().split(","))
        new_monitors = current_active_monitors - prev_active_monitors

        # Check for active structures
        if not self._active_structures:
            raise NoActiveStructuresError

        # Check for necessary monitors; enable them if they are not already enabled
        if not {"ref_power_monitor", "trans_power_monitor"} <= current_active_monitors:
            if not {"ref_power_monitor", "trans_power_monitor"} <= prev_active_monitors:
                print(InsufficientMonitorsError)
                print("Enabling 'ref_power_monitor' and 'trans_power_monitor'.")
                self.set_monitor_enabled("ref_power_monitor", True)
                self.set_monitor_enabled("trans_power_monitor", True)
                current_active_monitors.update({"ref_power_monitor", "trans_power_monitor"})
                new_monitors.update({"ref_power_monitor", "trans_power_monitor"})

        # Ensure ref/trans profile monitors are enabled if xz/yz profile monitors are active
        if {"xz_profile_monitor", "yz_profile_monitor"} & current_active_monitors:
            if not {"ref_profile_monitor", "trans_profile_monitor"} & (current_active_monitors | prev_active_monitors):
                print("Enabling 'ref_profile_monitor' and 'trans_profile_monitor'.")
                self.set_monitor_enabled("ref_profile_monitor", True)
                self.set_monitor_enabled("trans_profile_monitor", True)
                current_active_monitors.update({"ref_profile_monitor", "trans_profile_monitor"})
                new_monitors.update({"ref_profile_monitor", "trans_profile_monitor"})

        # Skip running if the simulation exists but no new monitors are found
        if simulation_exists and not new_monitors:
            print("\nSimulation already exists and will not be simulated.")
            return

        # Disable redundant monitors that are not needed for the current simulation
        redundant_monitors = current_active_monitors - new_monitors
        if redundant_monitors:
            self.switchtolayout()  # Switch to the layout for monitor updates
            for monitor in redundant_monitors:
                self.setnamed(monitor, "enabled", False)
                print(f"Monitor '{monitor}' disabled.")

        # Attempt to run the simulation, retrying up to 3 times if it fails
        for i in range(3):
            try:
                # Run the simulation with appropriate parameters
                result = self.run(
                    to_db=True,
                    prev_profile_results={
                        "ref_mag_max_pr_lambda": simulation.ref_mag_max_pr_lambda,
                        "trans_mag_max_pr_lambda": simulation.trans_mag_max_pr_lambda,
                    }
                ) if simulation_exists else self.run(to_db=True)

                # Update existing simulation results in the database if applicable
                if simulation_exists:
                    prev_active_monitors_str = getattr(simulation, "active_monitors")
                    for monitor, parameters in SimulationBase.monitor_results.items():
                        if monitor in new_monitors:
                            for parameter in parameters:
                                setattr(simulation, parameter, result[parameter])
                                prev_active_monitors_str += f",{monitor}"
                    setattr(simulation, "active_monitors", prev_active_monitors_str)
                    self.db.sessions["simulation_exists"].commit()
                    self.switchtolayout()
                    self.save(
                        os.path.abspath(
                            os.path.join(
                                self._db_save_path, f"{self.db.db_name}_{simulation.id}.fsp"
                            )
                        )
                    )
                    # Save the file in the apropriate folder in the /Simulations folder. If we don't do this,
                    # the results of the next simulation will be saved to the .fsp file saved in the line of code
                    # above for some reason. This makes the save files huge (350 Mb pr.). We want to make sure we only
                    # save the simulation enviroment, not the results, as these are saved to the database.
                    self.save()

                else:
                    # Save results to the database if this is a new simulation
                    self._save_results_to_database(result)
                    self.switchtolayout()
                    self.save(
                        os.path.abspath(
                            os.path.join(
                                self._db_save_path, f"{self.db.db_name}_{self.db.get_last_id()}.fsp"
                            )
                        )
                    )
                    # See comment in the if-block above
                    self.save()

                # Restore the layout after running the simulation
                self.switchtolayout()
                for monitor in redundant_monitors:
                    self.setnamed(monitor, "enabled", True)  # Re-enable previously disabled monitors
                return

            except Exception as e:
                print(f"Simulation attempt {i + 1} failed: '{e}'. Retrying...")

        # Switch to layout and print a message saying the simulation was aborted
        self.switchtolayout()
        print("\nSimulation aborted after 3 attempts.")

    def set_structure_spans(self, structure_type_id: str | int, spans: Tuple[Any, Any, Any]) -> None:
        """
        Sets the x-, y-, and z-spans of all instances of the specified structure type id in the simulation.

        For rectangular structures, the method updates the spans for all dimensions (x, y, and z). For circular structures,
        it sets the radius values in the x and y directions and adjusts the z-span. Additionally, if the structure includes
        edge meshes, their positions and sizes will be recalculated and updated automatically to fit the new dimensions.

        Args:
            structure_type_id (str | int): The identifier for the structure type whose spans are to be updated.
            spans (Tuple[Any, Any, Any]): A tuple containing the spans for the x, y, and z dimensions.
                - For rectangular structures, these values correspond to the x-span, y-span, and z-span.
                - For circular structures, the x-span represents the radius in the x-direction, the y-span represents the
                  radius in the y-direction (for a perfect circle, these should be equal), and the z-span represents the
                  height of the structure.
                - If `None` is passed for any span, that span will remain unchanged.

        Raises:
            StructureDoesNotExistError: If the specified structure does not exist in the simulation.

        Returns:
            None: The function does not return a value but modifies the simulation by updating the spans of the structures.

        Additional Behavior:
            - If the structure has an associated edge mesh (e.g., smaller mesh cubes placed around the edges for finer meshing),
              the positions of these mesh cubes are updated automatically based on the new spans. This ensures that the
              edge mesh adapts to changes in the larger structure's dimensions without needing manual repositioning.
            - The method first checks if the structure exists by its `structure_type_id`. If not, an error is raised.
            - For rectangular structures, it updates the `x span`, `y span`, and `z span` for all instances of the structure.
            - For circular structures, it updates the `radius`, `radius 2`, and `z span` accordingly.
        """
        # Check if the specified structure exists in the simulation
        self._possibly_raise_structure_doesnt_exist_error(structure_type_id)

        # Retrieve the current spans for the specified structure type
        prev_xspan, prev_yspan, prev_zspan = self.get_structure_spans(structure_type_id)
        x_span, y_span, z_span = spans

        # If None is provided for any span, retain the previous value
        if x_span is None:
            x_span = prev_xspan
        if y_span is None:
            y_span = prev_yspan
        if z_span is None:
            z_span = prev_zspan

        # Determine the shape of the structure to apply the appropriate updates
        structure_shape = self._active_structures[f"structure_{structure_type_id}"]["shape"]
        if structure_shape == "rect":
            # Update spans for all instances of rectangular structures
            for i in range(1, self._active_structures[f"structure_{structure_type_id}"]["nr"] + 1):
                # Set the x, y, and z spans for the current instance
                self.setnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_{i}"
                    f"::structure_{structure_type_id}",
                    "x span",
                    float(x_span) * 1e-9  # Convert to meters
                )
                self.setnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_{i}"
                    f"::structure_{structure_type_id}",
                    "y span",
                    float(y_span) * 1e-9  # Convert to meters
                )
                self.setnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_{i}"
                    f"::structure_{structure_type_id}",
                    "z span",
                    float(z_span) * 1e-9  # Convert to meters
                )

                # Recreate the edge mesh cubes at new appropriate positions
                try:
                    edge_mesh_name = (
                        f"structure_{structure_type_id}_group"
                        f"::structure_{structure_type_id}_{i}"
                        f"::edge_mesh_{structure_type_id}_{i}"
                    )
                    # Retrieve the size of the edge mesh cube for correct placement
                    cube_size = round(self.getnamed(f"{edge_mesh_name}_1", "x span"), 10) * 1e9
                    step_size = round(self.getnamed(f"{edge_mesh_name}_1", "dx"), 10) * 1e9

                    # Delete existing edge mesh cubes
                    for j in range(8):
                        self.select(f"{edge_mesh_name}_{j + 1}")
                        self.delete()

                    # Create new edge mesh cubes based on updated dimensions
                    self._create_edge_meshes(
                        cube_size, structure_type_id, step_size, i
                    )
                except Exception as e:
                    # Handle exceptions gracefully
                    pass

        elif structure_shape == "circle":
            # Update spans for all instances of circular structures
            for i in range(1, self._active_structures[f"structure_{structure_type_id}"]["nr"] + 1):
                # Set the radius in the x and y directions and the z span
                self.setnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_{i}"
                    f"::structure_{structure_type_id}",
                    "radius",
                    float(spans[0]) * 1e-9  # Convert to meters
                )
                self.setnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_{i}"
                    f"::structure_{structure_type_id}",
                    "radius 2",
                    float(spans[1]) * 1e-9  # Convert to meters
                )
                self.setnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_{i}"
                    f"::structure_{structure_type_id}",
                    "z span",
                    float(spans[2]) * 1e-9  # Convert to meters
                )

    def set_structure_material(self, structure_type_id: str | int, material: materials_explorer) -> None:
        """
        Sets the material of all instances of the structure with the specified structure type id.

        Args:
            structure_type_id (int): The identifier for the structure type whose structures' material is to be set.
            material (materials_explorer): The material to be assigned to the structure, specified by the materials_explorer.

        Raises:
            StructureDoesNotExistError: If the specified structure does not exist in the simulation.

        Returns:
            None: This function does not return any value; it modifies the material of the specified structure within the simulation.
        """
        # Check if the specified structure exists in the simulation
        self._possibly_raise_structure_doesnt_exist_error(structure_type_id)

        # Retrieve the number of instances for the specified structure type
        num_instances = self._active_structures[f"structure_{structure_type_id}"]["nr"]

        # Iterate over each instance of the structure to set the material
        for i in range(1, num_instances + 1):
            # Construct the name for the current structure instance based on its ID
            structure_name = (
                f"structure_{structure_type_id}_group"
                f"::structure_{structure_type_id}_{i}"
                f"::structure_{structure_type_id}"
            )

            # Set the specified material for the current structure instance
            self.setnamed(
                structure_name,
                "material",
                material  # Assign the new material to the structure
            )

    def set_structure_position(self, structure_type_id: str | int, position: Tuple[Any, Any, Any]) -> None:
        """
        Sets the position of the specified structure in the simulation.

        Args:
            structure_type_id (int): The identifier for the structure whose position is to be set.
            position (Tuple[Any, Any, Any]): A tuple containing the new x, y, and z coordinates for the structure's position, expressed in nanometers.

        Raises:
            StructureDoesNotExistError: If the specified structure does not exist in the simulation.
            StructureNotUniqueError: If there are more than one structure of the given structure type.

        Returns:
            None: This function does not return any value; it modifies the position of the specified structure within the simulation.

        Additional Notes:
            - If more than one structure with the same structure type id exists, all the different instances will be moved to the same position.
            - Be careful when using this method, as it should only be used when there is one unique instance of the specified structure type.
        """
        # Check if the specified structure exists in the simulation
        self._possibly_raise_structure_doesnt_exist_error(structure_type_id)

        # Retrieve the number of instances for the specified structure type
        num_instances = self._active_structures[f"structure_{structure_type_id}"]["nr"]

        # Iterate over each instance of the structure to set its position
        for i in range(1, num_instances + 1):
            # Construct the name for the current structure instance based on its ID
            structure_name = (
                f"structure_{structure_type_id}_group"
                f"::structure_{structure_type_id}_{i}"
            )

            # Set the new x-coordinate for the current structure instance
            self.setnamed(
                structure_name,
                "x",
                float(position[0]) * 1e-9  # Convert position to meters (from nanometers)
            )

            # Set the new y-coordinate for the current structure instance
            self.setnamed(
                structure_name,
                "y",
                float(position[1]) * 1e-9  # Convert position to meters (from nanometers)
            )

            # Set the new z-coordinate for the current structure instance
            self.setnamed(
                structure_name,
                "z",
                float(position[2]) * 1e-9  # Convert position to meters (from nanometers)
            )

    def addrect(
            self,
            structure_type_id: str | int,
            hole_in: int | str | None,
            spans: Tuple[int | float | np.float16, int | float | np.float16, int | float | np.float16] | None,
            position: Tuple[int | float | np.float16, int | float | np.float16, int | float | np.float16] | None,
            material: materials_explorer,
            edge_mesh_stepsize: int | float | None = None,
            edge_mesh_size: int | float = None,
            bulk_mesh_enabled: bool = True) -> None:
        """
        Adds a rectangular object to the simulation with the specified structure type id.

        Args:
            structure_type_id (int): The identifier for the structure type being added to the simulation.
            hole_in (int | str | None): If the structure is a hole in another structure, specify the structure type
                id for the other structure. If not, use None.
            spans (Tuple[int | float, int | float, int | float] | None): A tuple containing the spans for the
                x, y, and z dimensions. If None, the spans will not be set.
            position (Tuple[int | float, int | float, int | float] | None): A tuple containing the new x, y,
                and z coordinates for the structure's position, expressed in nanometers. If None, the position
                will not be set.
            material (materials_explorer | None): The material to be assigned to the structure. If None,
                the material will not be set.
            edge_mesh_stepsize (int | float | None): If an int or a float is specified, a custom mesh with this stepsize is
                added to each edge of the rectangle. Used to acquire more accurate results around the edges without
                having to have a fine mesh stepsize around the entire object.
            edge_mesh_size (int | float | None): The size of the mesh cube added to each edge.
            bulk_mesh_enabled (bool): Flag to enable or disable bulk mesh generation for the structure.

        Returns:
            None: This function does not return any value; it modifies the simulation state by adding a rectangular structure.

        Additional Notes:
            - The position and spans will be set based on the provided tuples. If either is None, the corresponding attribute will not be set.
            - If multiple structures of the same type already exist, this function will add the new rectangle to the existing group without duplication.
        """
        # Add the structure to the simulation
        self._add_structure(structure_type_id, hole_in=hole_in)

        structure_nr = self._active_structures[f"structure_{structure_type_id}"]["nr"]

        # Fetch parameters
        rect_name = f"structure_{structure_type_id}"
        x, y, z = position
        x_span, y_span, z_span = spans

        # Create the rectangle structure
        super().addrect(
            name=rect_name, x=float(x) * 1e-9, y=float(y) * 1e-9, z=float(z) * 1e-9,
            x_span=float(x_span) * 1e-9, y_span=float(y_span) * 1e-9, z_span=float(z_span) * 1e-9, material=material
        )

        # Create a group and add structure to it
        self.addgroup(name=f"structure_{structure_type_id}_{structure_nr}")
        self.select(rect_name)
        self.addtogroup(f"structure_{structure_type_id}_{structure_nr}")
        self.select(f"structure_{structure_type_id}_{structure_nr}")
        self.addtogroup(f"structure_{structure_type_id}_group")

        self._active_structures[f"structure_{structure_type_id}"]["shape"] = "rect"

        # Set relative coordinates False
        self.setnamed(
            f"structure_{structure_type_id}_group::structure_{structure_type_id}_{structure_nr}",
            "use relative coordinates",
            False
        )

        if edge_mesh_stepsize is not None:
            self._create_edge_meshes(edge_mesh_size, structure_type_id, edge_mesh_stepsize, structure_nr)

        if not bulk_mesh_enabled:
            self.setnamed(f"structure_{structure_type_id}_group::mesh_{structure_type_id}", "enabled", False)

    def addcircle(
            self,
            structure_type_id: str | int,
            hole_in: int | str = None,
            spans: Tuple[int | float, int | float, int | float] | None = None,
            position: Tuple[int | float, int | float, int | float] | None = None,
            material: materials_explorer = None) -> None:
        """
        Adds a circular object to the simulation with the specified structure type id.

        Args:
            structure_type_id (int): The identifier for the structure type being added to the simulation.
            hole_in (int | str | None): If the structure is a hole in another structure, specify the structure type
                id for the other structure. If not use None.
            spans (Tuple[int | float, int | float, int | float] | None): A tuple containing the spans for the
                radius and optional second radius. If None, the spans will not be set.
            position (Tuple[int | float, int | float, int | float] | None): A tuple containing the new x, y,
                and z coordinates for the structure's position, expressed in nanometers. If None, the position
                will not be set.
            material (materials_explorer | None): The material to be assigned to the structure. If None,
                the material will not be set.

        Returns:
            None: This function does not return any value; it modifies the simulation state by adding a circular structure.
        """

        # Add the structure to the simulation
        self._add_structure(structure_type_id, hole_in=hole_in)

        circle_name = f"structure_{structure_type_id}"
        structure_nr = self._active_structures[circle_name]["nr"]

        # Fetch and convert parameters
        if position is None:
            raise ValueError("Position must be provided.")
        if spans is None:
            raise ValueError("Spans must be provided.")

        x, y, z = position
        x_span, y_span, z_span = spans

        # Create the circular structure
        super().addcircle(
            name=circle_name,
            x=float(x) * 1e-9,
            y=float(y) * 1e-9,
            z=float(z) * 1e-9,
            x_span=float(x_span) * 1e-9,
            y_span=float(y_span) * 1e-9,
            z_span=float(z_span) * 1e-9,
            material=material
        )

        # Set as ellipsoid (circular structure)
        self.setnamed(circle_name, "make ellipsoid", True)

        # Update the active structures dictionary
        self._active_structures[f"structure_{structure_type_id}"]["shape"] = "circle"

        # Group management
        self.addgroup(name=f"structure_{structure_type_id}_{structure_nr}")
        self.select(circle_name)
        self.addtogroup(f"structure_{structure_type_id}_{structure_nr}")
        self.select(f"structure_{structure_type_id}_{structure_nr}")
        self.addtogroup(f"structure_{structure_type_id}_group")

        # Set relative coordinates
        self.setnamed(
            f"structure_{structure_type_id}_group::structure_{structure_type_id}_{structure_nr}",
            "use relative coordinates",
            False
        )

    def get_structure_min_max(self, structure_type_id: str | int) \
            -> Tuple[Tuple[np.float16, np.float16], Tuple[np.float16, np.float16], Tuple[np.float16, np.float16]]:
        """
        Retrieves the minimum and maximum coordinates of the specified structure in nanometers. This function does not
        work properly if the structure is part of a grid, or if there are more than one structure with the same structure type id,
        as it requires there to be a single structure with the given structure type id.

        Args:
            structure_type_id (int): The identifier for the structure whose coordinates are to be retrieved.

        Returns:
            Tuple[Tuple[np.float16, np.float16], Tuple[np.float16, np.float16], Tuple[np.float16, np.float16]]:
                A tuple containing three tuples:
                - The first tuple contains the minimum and maximum x-coordinates.
                - The second tuple contains the minimum and maximum y-coordinates.
                - The third tuple contains the minimum and maximum z-coordinates.

        Raises:
            StructureDoesNotExistError: If the specified structure does not exist in the simulation.
            StructureNotUniqueError: If there are more than one structure of the given structure type.

        Warning:
            This function does not work if the structure is part of a grid, as it requires there to be a single
            structure in the simulation with a unique name.
        """

        # Verify that the specified structure exists in the simulation
        self._possibly_raise_structure_doesnt_exist_error(structure_type_id)

        # Check if the structure is unique; raise an error if there are multiple structures with the same type
        if not self._active_structures[f"structure_{structure_type_id}"]["unique"]:
            raise StructureNotUniqueError(structure_type_id)

        # Retrieve the minimum and maximum x-coordinates of the structure, converted to nanometers
        x_min_max = (
            np.float16(
                self.getnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_1"
                    f"::structure_{structure_type_id}",
                    "x min"
                ) * 1e9
            ),
            np.float16(
                self.getnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_1"
                    f"::structure_{structure_type_id}",
                    "x max"
                ) * 1e9
            )
        )

        # Retrieve the minimum and maximum y-coordinates of the structure, converted to nanometers
        y_min_max = (
            np.float16(
                self.getnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_1"
                    f"::structure_{structure_type_id}",
                    "y min"
                ) * 1e9
            ),
            np.float16(
                self.getnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_1"
                    f"::structure_{structure_type_id}",
                    "y max"
                ) * 1e9
            )
        )

        # Retrieve the minimum and maximum z-coordinates of the structure, converted to nanometers
        z_min_max = (
            np.float16(
                self.getnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_1"
                    f"::structure_{structure_type_id}",
                    "z min"
                ) * 1e9
            ),
            np.float16(
                self.getnamed(
                    f"structure_{structure_type_id}_group"
                    f"::structure_{structure_type_id}_1"
                    f"::structure_{structure_type_id}",
                    "z max"
                ) * 1e9
            )
        )

        # Return the retrieved coordinates as tuples
        return x_min_max, y_min_max, z_min_max

    def get_FDTD_min_max(self) \
            -> Tuple[Tuple[np.float16, np.float16], Tuple[np.float16, np.float16], Tuple[np.float16, np.float16]]:
        """
        Retrieves the minimum and maximum coordinates for the FDTD (Finite-Difference Time-Domain) region in nanometers.

        Returns:
            Tuple[Tuple[np.float16, np.float16], Tuple[np.float16, np.float16], Tuple[np.float16, np.float16]]:
                A tuple containing three tuples:
                - The first tuple contains the minimum and maximum x-coordinates.
                - The second tuple contains the minimum and maximum y-coordinates.
                - The third tuple contains the minimum and maximum z-coordinates.
        """

        # Retrieve the minimum and maximum x-coordinates of the FDTD region, converted to nanometers
        x_min_max = (
            np.float16(self.getnamed(f"FDTD", "x min") * 1e9),  # Minimum x-coordinate
            np.float16(self.getnamed(f"FDTD", "x max") * 1e9)  # Maximum x-coordinate
        )

        # Retrieve the minimum and maximum y-coordinates of the FDTD region, converted to nanometers
        y_min_max = (
            np.float16(self.getnamed(f"FDTD", "y min") * 1e9),  # Minimum y-coordinate
            np.float16(self.getnamed(f"FDTD", "y max") * 1e9)  # Maximum y-coordinate
        )

        # Retrieve the minimum and maximum z-coordinates of the FDTD region, converted to nanometers
        z_min_max = (
            np.float16(self.getnamed(f"FDTD", "z min") * 1e9),  # Minimum z-coordinate
            np.float16(self.getnamed(f"FDTD", "z max") * 1e9)  # Maximum z-coordinate
        )

        # Return the coordinates as tuples for x, y, and z
        return x_min_max, y_min_max, z_min_max

    def create_structure_grid(self,
                              structure_type_id: str | int,
                              shape: Literal["rect", "circle"],
                              structure_spans: Tuple[int | float, int | float, int | float],
                              structure_material: materials_explorer,
                              hole_in: str | int | None,
                              min_max_x: Tuple[int | float | np.float16, int | float | np.float16],
                              min_max_y: Tuple[float | int | np.float16, int | float | np.float16],
                              num_x: int,
                              num_y: int,
                              edge_mesh_step_size: int | float | None = None,
                              edge_mesh_size: int | float | None = None,
                              min_x_solid_boundary: bool = False,
                              max_x_solid_boundary: bool = False,
                              min_y_solid_boundary: bool = False,
                              max_y_solid_boundary: bool = False,
                              bulk_mesh_enabled: bool = True) -> None:
        """
        Creates a grid of structures with specified dimensions and materials within defined boundaries.

        A solid boundary is defined as a boundary that is not a symmetric FDTD boundary. The distance between
        the structure closest to the solid boundary (e.g., x_max solid boundary) and the boundary is twice the
        distance between the structure closest to the x_min FDTD boundary and the boundary. Since FDTD symmetric
        boundaries are repeating, this ensures that the unit cells are uniform across the infinite grid created
        by the FDTD region.

        Args:
            structure_type_id (int): The identifier for the structure type all the structures in the grid will be.
            shape (Literal["rect", "circle"]): The shape of the structure, either "rect" for rectangle or "circle" for circular.
            structure_spans (Tuple[int | float, int | float, int | float]): The spans of the structure in x, y, and z directions.
            structure_material (materials_explorer): The material to be assigned to the structure.
            hole_in (str | int | None): Optional; specifies if the structure will have a hole and its identifier.
            min_max_x (Tuple[int | float | np.float16, int | float | np.float16]): The minimum and maximum x-coordinates for placing structures.
            min_max_y (Tuple[float | int | np.float16, int | float | np.float16]): The minimum and maximum y-coordinates for placing structures.
            num_x (int): The number of structures to create in the x-direction.
            num_y (int): The number of structures to create in the y-direction.
            edge_mesh_step_size (int | float | None): Optional; size of the edge mesh step.
            edge_mesh_size (int | float | None): Optional; size of the edge mesh.
            min_x_solid_boundary (bool): Whether to consider a solid boundary at the minimum x-coordinate.
            max_x_solid_boundary (bool): Whether to consider a solid boundary at the maximum x-coordinate.
            min_y_solid_boundary (bool): Whether to consider a solid boundary at the minimum y-coordinate.
            max_y_solid_boundary (bool): Whether to consider a solid boundary at the maximum y-coordinate.
            bulk_mesh_enabled (bool): Wheter the mesh around the entire structure should be active or not.

        Raises:
            AttributeError: If the number of structures in either direction is zero or if the minimum coordinates exceed the maximum coordinates.
            StructureDimensionsError: If the structure dimensions exceed the unit cell dimensions based on the specified shape.

        Returns:
            None
        """
        # Check if the input arguments are valid
        if any([num_x == 0, num_y == 0]):
            raise AttributeError(
                f"The number of structures in the x- and y-direction cannot be zero. "
                f"The input values were: num_x = {num_x}, num_y = {num_y}."
            )
        elif any([min_max_x[0] > min_max_x[1], min_max_y[0] > min_max_y[1]]):
            raise AttributeError(
                f"The min. x/y coordinate cannot be greater than the max. x/y coordinate."
                f"The input values were: (min.x, max. x) = {min_max_x} and (min. y, max. y) = {min_max_y}."
            )

        # Find available space between min and max positions and calculate the unit cell lengths
        available_x = min_max_x[1] - min_max_x[0]
        unit_cell_x = (
                (
                        (available_x - num_x * structure_spans[0])
                        /
                        (num_x + 0.5 * (min_x_solid_boundary + max_x_solid_boundary))
                ) + structure_spans[0]
        )

        available_y = min_max_y[1] - min_max_y[0]
        unit_cell_y = (
                (
                        (available_y - num_y * structure_spans[1])
                        /
                        (num_y + 0.5 * (min_y_solid_boundary + max_y_solid_boundary))
                ) + structure_spans[1]
        )

        # Save the unit cell values to the dictionary
        self._unit_cells[f"unit_cell_{structure_type_id}_x"] = np.float16(unit_cell_x)
        self._unit_cells[f"unit_cell_{structure_type_id}_y"] = np.float16(unit_cell_y)

        # Check if the unit cell is smaller than the structure dimensions
        if shape == "rect" and any([unit_cell_x <= structure_spans[0], unit_cell_y <= structure_spans[1]]):
            raise StructureDimensionsError(unit_cell_x, unit_cell_y, structure_spans, "rectangle")
        elif shape == "circle" and any([unit_cell_x <= structure_spans[0] * 2, unit_cell_y <= structure_spans[1] * 2]):
            raise StructureDimensionsError(unit_cell_x, unit_cell_y, structure_spans, "circle")

        # Find the center coordinates of the bottom left unit cell
        first_x = min_max_x[0] + unit_cell_x / 2 + ((unit_cell_x - structure_spans[0]) / 2) * min_x_solid_boundary
        first_y = min_max_y[0] + unit_cell_y / 2 + ((unit_cell_y - structure_spans[1]) / 2) * min_y_solid_boundary

        # Iterate over the shapes to be added and add them at the correct positions
        for i in range(num_x):
            # Calculate the given structure's x-coordinate
            x = first_x + unit_cell_x * i

            for j in range(num_y):
                # Calculate the given structure's y-coordinate
                y = first_y + unit_cell_y * j
                # Add the structure based on the specified shape
                if shape == "rect":
                    self.addrect(
                        structure_type_id,
                        hole_in,
                        structure_spans,
                        (x, y, structure_spans[2] / 2),
                        structure_material,
                        edge_mesh_step_size,
                        edge_mesh_size,
                        bulk_mesh_enabled=bulk_mesh_enabled
                    )
                elif shape == "circle":
                    self.addcircle(
                        structure_type_id,
                        hole_in,
                        structure_spans,
                        (x, y, structure_spans[2] / 2),
                        structure_material
                    )

    def set_polarization_angle(self, angle: int | float | np.float16, allow_symmetry: bool = True) -> None:
        """
        Set the polarization angle (phi) for the source in the simulation and adjust boundary conditions accordingly.

        This method sets the polarization angle of the source and configures the simulation boundaries based on the
        angle and the `allow_symmetry` flag. For angles aligned along the x-axis (0° or 180°) or y-axis (90° or 270°),
        symmetric and anti-symmetric boundary conditions are applied if symmetry is allowed and the incidence angle is
        zero. If symmetry is allowed, but either the incidence angle is not 0° or the polarization angle is not along
        the x- or y-axis, bloch boundary conditions are applied. If symmetry is not allowed, Perfectly Matched Layer
        (PML) boundaries are applied.

        Parameters
        ----------
        angle : int | float | np.float16
            The polarization angle (phi) in degrees. It can be provided as an integer, float, or 16-bit float.
        allow_symmetry : bool, optional
            A flag to enable or disable symmetric boundary conditions. Defaults to True.

        Notes
        -----
        - For polarization angles aligned with the x-axis (0° or 180°) or y-axis (90° or 270°), symmetric boundary
          conditions are used when `allow_symmetry` is True and the incidence angle is zero.
        - If symmetry is not allowed, PML boundary conditions are applied.
        - For non-aligned polarization angles, Bloch boundary conditions can be used if symmetry is allowed.

        Raises
        ------
        None

        Returns
        -------
        None
        """
        # Normalize the angle to the range [0, 360) for consistency
        angle = angle % 360

        # Set the polarization angle (phi) for the source in the FDTD simulation
        self.setnamed("source", "angle phi", float(angle))

        # Assume that PML boundaries will be applied unless symmetry or Bloch boundaries are configured
        pml = True

        # Fetch the current incidence angle of the source to determine symmetry eligibility
        incidence_angle = self._get_incidence_angle()

        # Case 1: Polarization angle along the x-axis (0° or 180°)
        if angle in (0, 180) and incidence_angle == 0:
            if allow_symmetry:
                # Apply symmetric boundary conditions along the x-axis and anti-symmetric along the y-axis
                self.setnamed("FDTD", "allow symmetry on all boundaries", True)  # Allow symmetric boundaries
                self.setnamed("FDTD", "x min bc", "Symmetric")
                self.setnamed("FDTD", "x max bc", "Symmetric")
                self.setnamed("FDTD", "y min bc", "Anti-Symmetric")
                self.setnamed("FDTD", "y max bc", "Anti-Symmetric")
                pml = False  # Symmetry applied, no need for PML
                print("Symmetric boundary conditions applied along x-axis.")

        # Case 2: Polarization angle along the y-axis (90° or 270°)
        elif angle in (90, 270) and incidence_angle == 0:
            if allow_symmetry:
                # Apply symmetric boundary conditions along the y-axis and anti-symmetric along the x-axis
                self.setnamed("FDTD", "allow symmetry on all boundaries", True)  # Allow symmetric boundaries
                self.setnamed("FDTD", "x min bc", "Anti-Symmetric")
                self.setnamed("FDTD", "x max bc", "Anti-Symmetric")
                self.setnamed("FDTD", "y min bc", "Symmetric")
                self.setnamed("FDTD", "y max bc", "Symmetric")
                pml = False  # Symmetry applied, no need for PML
                print("Symmetric boundary conditions applied along y-axis.")

        # Case 3: Polarization angle is not aligned along the primary axes (x or y)
        else:
            if allow_symmetry:
                # Apply Bloch boundary conditions for non-axis aligned polarization angles
                self.setnamed("FDTD", "allow symmetry on all boundaries", False)
                self.setnamed("FDTD", "x min bc", "Bloch")
                self.setnamed("FDTD", "x max bc", "Bloch")
                self.setnamed("FDTD", "y min bc", "Bloch")
                self.setnamed("FDTD", "y max bc", "Bloch")
                self.setnamed("FDTD", "set based on source angle", True)
                self.setnamed("FDTD", "bloch units", "bandstructure")
                print("Bloch boundary conditions applied for non-aligned angle.")
                pml = False  # Bloch boundary applied, no need for PML

        # Case 4: If no symmetry or Bloch conditions are applied, default to PML boundary conditions
        if pml:
            self.setnamed("FDTD", "allow symmetry on all boundaries", False)  # Disable symmetric boundaries
            self.setnamed("FDTD", "x min bc", "PML")
            self.setnamed("FDTD", "x max bc", "PML")
            self.setnamed("FDTD", "y min bc", "PML")
            self.setnamed("FDTD", "y max bc", "PML")
            print("PML boundary conditions applied.")

    def set_incidence_angle(self, incidence_angle: float, allow_symmetry: bool = True) -> None:
        """
        Configures the simulation boundaries based on the specified incidence angle.

        For non-normal incidence, Bloch boundary conditions are applied. For normal incidence (0°),
        symmetry conditions are applied if `allow_symmetry` is True and the polarization allows for it.
        Symmetry is not applied for non-normal incidence.

        Parameters
        ----------
        incidence_angle : float
            The angle of incidence in degrees. Must be within the range -89.9 to 89.9.
        allow_symmetry : bool, optional
            Whether to allow symmetry for normal incidence (default is True). Symmetry is disabled for non-normal incidence.

        Raises
        ------
        ValueError
            If the incidence angle is outside the allowed range of -89.9 to 89.9 degrees.

        Returns
        -------
        None
        """
        # Validate the incidence angle is within the allowed range
        if not -89.9 <= incidence_angle <= 89.9:
            raise ValueError("The incidence angle must be between -89.9 and 89.9 degrees.")

        # Fetch the polarization angle only once
        polarization_angle = self._get_polarization_angle()

        # Configure Bloch or PML boundary conditions for non-normal incidence
        if incidence_angle != 0:
            # Set the source angle for non-normal incidence
            self.setnamed("source", "angle theta", float(incidence_angle))

            # Apply Bloch or PML boundary conditions
            boundary_condition = "Bloch" if allow_symmetry else "PML"
            for axis in ["x min", "x max", "y min", "y max"]:
                self.setnamed("FDTD", f"{axis} bc", boundary_condition)

            # Additional settings for Bloch boundaries
            if allow_symmetry:
                self.setnamed("FDTD", "allow symmetry on all boundaries", False)
                self.setnamed("FDTD", "set based on source angle", True)
                self.setnamed("FDTD", "bloch units", "bandstructure")

            print(f"{boundary_condition} boundary conditions applied.")  # Print what boundary conditions were applied

        # Apply symmetry for normal incidence
        else:
            self.setnamed("source", "angle theta", incidence_angle)  # Set the incidence angle 0
            self.set_polarization_angle(polarization_angle, allow_symmetry=allow_symmetry)  # Set boundary conditions

    def set_mesh_stepsizes(
            self, stepsizes: Tuple[int | float | np.float16, int | float | np.float16, int | float | np.float16]) \
            -> None:
        """
        Sets the mesh step sizes in all three directions (x, y, z) for all the non-edge meshes in the simulation.

        This method updates the global mesh step sizes and applies the new values to all active meshes in the simulation.
        The step sizes are internally converted from nanometers to meters when applied to each mesh.

        Args:
            stepsizes (Tuple[int | float | np.float16]): A tuple containing the step sizes in nanometers for
                                                         the x, y, and z directions. The values can be of type
                                                         int, float, or 16-bit floating-point.

        Returns:
            None
        """

        # Update global mesh step sizes with provided values
        self._global_mesh_stepsizes[0] = stepsizes[0]
        self._global_mesh_stepsizes[1] = stepsizes[1]
        self._global_mesh_stepsizes[2] = stepsizes[2]

        # Apply the new step sizes to each active mesh
        for mesh in self._active_meshes:
            # Convert step sizes from nanometers to meters (1 nm = 1e-9 m)
            self.setnamed(mesh, "dx", float(stepsizes[0] * 1e-9))
            self.setnamed(mesh, "dy", float(stepsizes[1] * 1e-9))
            self.setnamed(mesh, "dz", float(stepsizes[2] * 1e-9))

    def get_FDTD_spans(self) -> Tuple[np.float16, np.float16, np.float16]:
        """
        Retrieves the spans of the simulation region in the x, y, and z directions.

        The spans are obtained from the FDTD settings and are converted from meters to nanometers before
        being returned as 16-bit floating-point values.

        Returns:
            Tuple[np.float16, np.float16, np.float16]: A tuple containing the spans of the FDTD region
                                                       in nanometers for the x, y, and z directions
                                                       as 16-bit floating-point values.
        """
        # Retrieve the spans from the FDTD settings and convert them to nanometers
        return (
            np.float16(self.getnamed("FDTD", "x span") * 1e9),  # Convert x span from meters to nanometers
            np.float16(self.getnamed("FDTD", "y span") * 1e9),  # Convert y span from meters to nanometers
            np.float16(self.getnamed("FDTD", "z span") * 1e9)  # Convert z span from meters to nanometers
        )

    def set_FDTD_spans(self, spans: Tuple[int | float | None, int | float | None, int | float | None]) -> None:
        """
        Sets the spans of the simulation region in the x, y, and z directions.
        Updates the positions and spans of all monitors and sources to ensure they are correctly placed
        within the simulation region. If any span is passed as None, its value will remain unchanged.

        Args:
            spans (Tuple[int | float | np.float16 | None]): A tuple containing the desired spans
                                                             for the x, y, and z directions in nanometers.
        """
        # Retrieve the current spans for x, y, and z directions
        prev_xspan, prev_yspan, prev_zspan = self.get_FDTD_spans()

        # Unpack the new spans, setting to previous values if None
        FDTD_xspan, FDTD_yspan, fdtd_zspan = spans

        # Update spans to retain previous values if None
        if FDTD_xspan is None:
            FDTD_xspan = prev_xspan
        if FDTD_yspan is None:
            FDTD_yspan = prev_yspan
        if fdtd_zspan is None:
            fdtd_zspan = prev_zspan

        # Set the new FDTD-region spans in meters
        self.setnamed("FDTD", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("FDTD", "y span", float(FDTD_yspan) * 1e-9)
        self.setnamed("FDTD", "z span", float(fdtd_zspan) * 1e-9)
        self.setnamed("FDTD", "z", float(self._film_thickness/2) * 1e-9)  # Center the FDTD in the middle of the film

        # Fetch the min. and max. z-coordinated of the FDTD-region
        _, _, FDTD_z_min_max = self.get_FDTD_min_max()
        FDTD_z_min, FDTD_z_max = FDTD_z_min_max

        # Set the new spans of all the simulation objects to be 1.1 times the FDTD span. This is to avoid
        # edge mesh issues when using Bloch boundary conditions
        FDTD_xspan *= 1.1
        FDTD_yspan *= 1.1

        # Update the dimensions of the substrate to match the new FDTD region
        self.setnamed("substrate", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("substrate", "y span", float(FDTD_yspan) * 1e-9)
        self.setnamed("substrate", "z max", 0)  # Set the maximum z of the substrate to 0
        self.setnamed("substrate", "z min", float(FDTD_z_min * 1.1) * 1e-9)  # Update the minimum z of the substrate

        # Position the source within the FDTD region
        self.setnamed("source", "z", float((FDTD_z_max - self._film_thickness) * 0.8) * 1e-9)
        self.setnamed("source", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("source", "y span", float(FDTD_yspan) * 1e-9)

        # Update the dimensions of the reflection power monitor to span the FDTD region
        self.setnamed("ref_power_monitor", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("ref_power_monitor", "y span", float(FDTD_yspan) * 1e-9)

        # Update the dimensions of the reflection profile monitor
        self.setnamed("ref_profile_monitor", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("ref_profile_monitor", "y span", float(FDTD_yspan) * 1e-9)
        self.setnamed("ref_profile_monitor", "z", float(self._film_thickness + 10) * 1e-9)  # Position in z

        # Update the dimensions of the transmission power monitor
        self.setnamed("trans_power_monitor", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("trans_power_monitor", "y span", float(FDTD_yspan) * 1e-9)

        # Update the dimensions of the transmission profile monitor
        self.setnamed("trans_profile_monitor", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("trans_profile_monitor", "y span", float(FDTD_yspan) * 1e-9)

        # Update the dimensions of the xz and yz profile monitors
        self.setnamed("xz_profile_monitor", "x span", float(FDTD_xspan) * 1e-9)
        self.setnamed("yz_profile_monitor", "y span", float(FDTD_yspan) * 1e-9)

        # Move the reflection power monitor above the source
        self.setnamed("ref_power_monitor", "z", float((FDTD_z_max - self._film_thickness) * (14 / 15)) * 1e-9)

        # Move the transmission power monitor to the corresponding negative z-position
        self.setnamed("trans_power_monitor", "z", float(
            -((FDTD_z_max - self._film_thickness) * (14 / 15)) + self._film_thickness) * 1e-9
                      )

    def set_monitor_enabled(self, monitor_name: monitor_literal, enabled: bool) -> None:
        """
        Enables or disables the specified monitor in the simulation.

        Args:
            monitor_name (monitor_literal): The name of the monitor to enable or disable.
            enabled (bool): A boolean value indicating whether to enable (True) or disable (False) the monitor.

        This method updates the monitor's status by setting the "enabled" property to the specified value.
        """
        # Set the "enabled" property of the specified monitor
        self.setnamed(monitor_name, "enabled", enabled)
