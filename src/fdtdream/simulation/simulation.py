from __future__ import annotations

import sys
import os
import warnings
from typing import List, Any, ClassVar, Type, TypeVar, Tuple, Dict, Union
import re
from itertools import product
import pickle

from .add import Add
from ..interfaces import SimulationInterface, SimulationObjectInterface
from ..lumapi import Lumapi
from ..resources import errors
from ..resources.functions import get_unique_name, convert_length
from ..resources.literals import LENGTH_UNITS
from .. import structures
from .. import monitors
from .. import sources
from ..fdtd import FDTDRegion
from ..structures import structure_group
from ..structures.scripted_structures import *
from ..mesh import Mesh
from ..results.simulation import Structure as SavedStructure
from ..results.simulation import Simulation as SimulationResults
from ..results.saved_simulation import SavedSimulation
from ..database import DatabaseHandler
import numpy as np
from trimesh.boolean import intersection
import trimesh
from ..results.plotted_structure import PlottedStructure

T = TypeVar("T")

# Type to Class Map for loading simulation objects
_type_to_class_map: dict[str, type] = {

    # Structure types
    "Rectangle": structures.Rectangle,
    "Circle": structures.Circle,
    "Sphere": structures.Sphere,
    "Ring": structures.Ring,
    "Pyramid": structures.Pyramid,
    "Polygon": structures.Polygon,
    "RegularPolygon": structures.RegularPolygon,
    "Triangle": structures.Triangle,
    "PlanarSolid": structures.PlanarSolid,

    # Source types
    "GaussianSource": sources.GaussianBeam,
    "Cauchy-Lorentzian": sources.CauchyLorentzianBeam,
    "PlaneSource": sources.PlaneWave,

    # Monitor Types
    "IndexMonitor": monitors.IndexMonitor,
    "DFTMonitor": monitors.FreqDomainFieldAndPowerMonitor,

    # FDTD Types
    "FDTD": FDTDRegion,
    "Mesh": Mesh,

    # Group types:

}


class Simulation(SimulationInterface):
    # region Class Body
    global_source: sources.GlobalSource
    global_monitor: monitors.GlobalMonitor
    _loaded_objects: List[SimulationObjectInterface]
    _structures: List
    _sources: List
    _monitors: List
    _meshes: List
    _fdtd: Any
    _save_path: str
    add: Add
    __slots__ = ["_global_units", "_objects", "add", "_monitors", "_meshes", "_fdtd", "_loaded_objects",
                 "globa_source", "global_monitor"]

    # endregion Class Body

    # region Dev methods

    def __init__(self, lumapi: Lumapi, save_path: str, units: LENGTH_UNITS):

        # Assign the global source and monitor
        self.global_source = sources.GlobalSource(self)
        self.global_monitor = monitors.GlobalMonitor(self)  # type: ignore

        self._save_path = os.path.abspath(save_path)
        self._global_lumapi = lumapi
        self._global_units = units
        self._structures = []
        self._sources = []
        self._monitors = []
        self._meshes = []
        self._loaded_objects = []

        # Initialize FDTD Region variable
        self._fdtd = None

        # Assign module collections
        self.add = Add(self, self._lumapi, self._units, self._check_name)

    def _get_all_objects(self) -> list[SimulationObjectInterface]:
        """Fetches a list of all objects in the current simulation."""
        all_objects = []
        all_objects.extend(self._structures)
        all_objects.extend(self._sources)
        all_objects.extend(self._monitors)
        all_objects.extend(self._meshes)
        all_objects.extend(self._fdtd)
        return all_objects

    def _get_used_names(self) -> list[str]:
        """Fetches a list with the names of all objects in the current simulation."""
        names = [obj._name for obj in self._get_all_objects()]
        return names

    def _get_simulation_objects_in_scope(self, groupscope: str, autoset_new_unique_names: bool,
                                         iterated: List[dict[str, str]] = None) -> List[dict[str, str]]:
        """
        Recursively retrieves all simulation objects within a specified scope, including nested groups,
        returning a list of dictionaries with object details. Each dictionary contains the object's name,
        type, and scope information, providing a structured representation of the simulation hierarchy.

        Parameters:
        -----------
        groupscope : str
            The name of the group scope to explore, starting with the provided scope and iterating through
            nested groups if present.

        autoset_new_unique_names : bool
            If `True`, assigns unique names to objects by automatically adjusting names to avoid duplicates
            within the scope. This is helpful in complex simulations with potentially overlapping object names.

        iterated : List[Dict[str, str]], optional
            A list of dictionaries representing objects that have already been processed. This list is used
            during recursion to aggregate results across nested group scopes.

        Returns:
        --------
        List[Dict[str, str]]
            A list of dictionaries, each containing:
            - "name": The unique name of the object within the simulation.
            - "type": A string representing the object type as identified by the FDTD simulation program.
            - "scope": The name of the group or scope in which the object resides.

        """
        if iterated is None:
            iterated = []

        # Fetch reference to the lumerical API for reuse
        lumapi = self._lumapi()

        # Select the provided group as the groupscope and select all objects in it
        lumapi.groupscope(groupscope)
        lumapi.selectall()
        num_objects = int(lumapi.getnumber())

        # Iterate through all the objects in the group
        for i in range(num_objects):

            name = lumapi.get("name", i + 1).replace(" ", "_")
            sim_object_type = lumapi.get("type", i + 1)

            used_names = [sim_object["name"].replace(" ", "_") for sim_object in iterated]

            if autoset_new_unique_names and sim_object_type != "FDTD":

                unique_name = get_unique_name(name, used_names)

                lumapi.set("name", unique_name, i + 1)

            else:
                unique_name = name

            iterated.append(
                {"name": unique_name, "type": sim_object_type, "scope": groupscope.split("::")[-1]})

            # Check if the object is another group, run this method recursively
            if sim_object_type == "Structure Group":
                if bool(lumapi.getnamed(name, "construction group")):

                    # Fetch the script
                    script: str = lumapi.getnamed(name, "script")
                    iterated[-1]["script"] = script

                else:
                    warnings.warn(f"Simulation object with name '{name}' is a Structure Group that is not a "
                                  f"construction group. Loading such objects with FDTDream is currently not supported.")
            if sim_object_type == "Layout Group":
                warnings.warn(f"Simulation object with name '{name}' is a Layout Group. "
                              f"Loading such objects with FDTDream is currently not supported.")

        return iterated

    def _load_objects_from_file(self) -> None:
        """
        Reads an `.fsp` simulation file and creates Python objects corresponding to each simulation
        object, enabling programmatic manipulation of the simulation environment. For enhanced
        autocompletion and type hints, call `print_variable_declarations()` after executing this
        function.

        This method retrieves all simulation objects within the "::model" scope, iterates over them,
        and instantiates Python representations for each based on the object type. The created objects
        are assigned as attributes to the current instance, making them accessible as standard Python
        objects for easier manipulation.
        """

        def init_structure_types(obj_dict):
            # Create an instance of the object
            obj = _type_to_class_map[obj_dict["type"]](obj_dict["name"], self)

            # Implement logic based on the object's type.
            if isinstance(obj, structures.Structure):
                self._structures.append(obj)
            elif isinstance(obj, monitors.Monitor):
                self._monitors.append(obj)
            elif isinstance(obj, sources.Source):
                self._sources.append(obj)
            elif isinstance(obj, Mesh):
                self._meshes.append(obj)
            return obj

        objects = []
        lattices = {}

        simulation_objects = self._get_simulation_objects_in_scope("::model", False)
        assign_to_lattice = []
        for sim_object in simulation_objects:

            # Assign the fdtd region to the simulation
            if sim_object["type"] == "FDTD":
                instantiated_object = _type_to_class_map[sim_object["type"]](self)

            elif sim_object["type"] == "Layout Group":
                warnings.warn(f"While loading, Layout Group of name '{sim_object['name']}' was encountered. "
                              f"Currently, only scripted groups created using FDTDream are supported, due to possible "
                              f"ambiguity between objects in non-scripted groups, and complexity of parsing scripts "
                              f"not written by FDTDream. This might be fixed in the future. "
                              f"The Layout Group will be ignored, and other   compatible objects will be loaded.")
                continue

            # Handle different types of construction groups
            elif sim_object["type"] == "Structure Group":

                # Fetch the script
                script = sim_object["script"]

                # Separate into code lines
                code_lines = extract_effective_lines(script)

                if "Lattice" in code_lines[1]:

                    # Create a Lattice object
                    instantiated_object = structures.Lattice(sim_object["name"], self, from_load=True)  # type: ignore

                    # Set rows and cols
                    instantiated_object._rows = int(code_lines[2].split("=")[1].strip().strip(";"))
                    instantiated_object._cols = int(code_lines[3].split("=")[1].strip().strip(";"))

                    # Set alpha beta and gamma
                    instantiated_object._alpha = float(code_lines[4].split("=")[1].strip().strip(";"))
                    instantiated_object._beta = float(code_lines[5].split("=")[1].strip().strip(";"))
                    instantiated_object._gamma = float(code_lines[6].split("=")[1].strip().strip(";"))

                    # Construct the lattice's site matrix
                    instantiated_object._sites = instantiated_object._construct_site_matrix()

                    # Store the lattice with the name of the base structure in a list for later assignment.
                    base_structure_name = str(code_lines[7].split("=")[1].strip().strip("'").strip(";").rstrip("'"))
                    if base_structure_name in lattices:
                        lattices[base_structure_name].append(instantiated_object)
                    else:
                        lattices[base_structure_name] = [instantiated_object]

                elif "Construction group" in code_lines[1]:

                    # Create a structure group object
                    instantiated_object = structures.StructureGroup(sim_object["name"], self,
                                                                    from_load=True)  # type: ignore

                    scripted_objects = read_construction_group(instantiated_object, code_lines, self)

                    instantiated_object._structures = scripted_objects

                else:
                    warnings.warn(f"While loading, Structure Group of name '{sim_object['name']}' was encountered. "
                                  f"The group's script has not been written using FDTDream, and due to possible "
                                  f"mistakes while trying to parse arbitrary Lumerical code, this structure group "
                                  f"will be ignored. Other compatible objects will be loaded. Ignoring this structure "
                                  f"group might lead to other errors. It is recomended to create all objects using "
                                  f"FDTDream.")
                    continue

            elif sim_object["type"] == "Polygon":
                grid_name: str = self._lumapi().getnamed(sim_object["name"], "grid attribute name")

                if grid_name == "Triangle":
                    instantiated_object = structures.Triangle(sim_object["name"], self)

                else:
                    instantiated_object = init_structure_types(sim_object)

            # Handle other structure types:
            else:
                instantiated_object = init_structure_types(sim_object)

            # Handle cases where the object is a part of a parent group
            if sim_object["scope"] != "model":
                group = getattr(self, sim_object["scope"])
                group._children.append(instantiated_object)
                instantiated_object._parents.append(group)

            # Assign a variable to each object.
            if sim_object["name"] == "FDTD":
                setattr(self, "_fdtd", instantiated_object)
            else:
                setattr(self, sim_object["name"], instantiated_object)

            objects.append(instantiated_object)

        # Assign base structures to lattices
        for base_structure_name in lattices:
            matching_names = [obj for obj in objects if obj.name == base_structure_name]
            if len(matching_names) > 1:
                warnings.warn("While loading object, multiple objects with the same name has been identified when "
                              "assigning base structures to lattices. Be aware, this might lead to inexact lattices.")
            elif base_structure_name != "" and not matching_names:
                warnings.warn(f"Loaded Lattice object has a base structure with name "
                              f"'{base_structure_name}', but no structure with this name is found in the simulation "
                              f"file. Be aware of bugs and errors that might happen because of this.")
                break
            if matching_names:
                base_structure = matching_names[0]
                for lattice in lattices[base_structure_name]:
                    lattice._base_structure = base_structure
                    base_structure._updatable_parents.append(lattice)

        # Assign the list of loaded object to the class variable.
        self._loaded_objects = objects

    def _print_variable_declarations(self, simulation_variable_name: str, exit_after_printing: bool) -> None:
        """
        Prints type declarations for all active simulation objects, enabling autocompletion and type hints
        when manipulating a loaded simulation programmatically.

        This method retrieves all simulation objects within the "::model" scope and generates Python variable
        declarations for each object, formatted for easy copy-pasting into code. These declarations provide
        full autocompletion support, allowing for more streamlined development when interacting with a loaded
        `.fsp` file.

        Parameters:
        -----------
        simulation_variable_name : str
            The name to use for the simulation instance variable in the declarations, representing the
            simulation environment.

        exit_after_printing : bool
            If `True`, the program will exit immediately after printing the declarations. Useful for generating
            declarations without running additional code.
        """

        if self._loaded_objects is None:
            raise ValueError("No objects loaded yet.")

        simulation_objects = self._loaded_objects

        # Print the type declarations in the desired format
        print("# region TYPE ANNOTATIONS\n")

        for sim_object in simulation_objects:

            object_class = sim_object.__class__

            if object_class.__name__ == "FDTDRegion":
                object_name = "fdtd"
                line = (
                    f"{object_name}: FDTDream"
                    f".i.{object_class.__name__} "
                    f"= getattr({simulation_variable_name}, '_{object_name}')"
                )
                if len(line) > 116:
                    line = (
                        f"{object_name}: FDTDream"
                        f".i.{object_class.__name__} "
                        f"= (\n\tgetattr({simulation_variable_name}, '_{object_name}'))")

            elif object_class is not None:

                object_name = sim_object._name.replace(" ", "_")
                line = (
                    f"{object_name}: FDTDream"
                    f".i.{object_class.__name__} "
                    f"= getattr({simulation_variable_name}, '{object_name}')")
                if len(line) > 116:
                    line = (
                        f"{object_name}: FDTDream"
                        f".i.{object_class.__name__} "
                        f"= (\n\tgetattr({simulation_variable_name}, '{object_name}'))")
                if object_class.__name__ == "Lattice":
                    if sim_object._base_structure is not None:  # type: ignore
                        line += f"\n#==> Base structure: '{sim_object._base_structure.name}'"  # type: ignore
                elif object_class.__name__ == "StructureGroup":
                    if sim_object._structures:  # type: ignore
                        line += f"\n# region '{object_name}' structures:\n"
                        used_names = []
                        for idx, obj in enumerate(sim_object._structures):  # type: ignore
                            name = get_unique_name(obj.name, used_names)
                            used_names.append(name)
                            scripted_type = obj.__class__.__name__[len("scripted"):]
                            line += (f"{object_name}_{name}: "  # type: ignore
                                     f"FDTDream.i.S{scripted_type} = getattr({object_name}, '_structures')[{idx}]\n")
                        line += "# endregion\n"
            else:
                raise ValueError("Something wierd happened here.")
            print(line)

        print("\n# endregion TYPE ANNOTATIONS")

        if exit_after_printing:
            sys.exit()

    def _units(self) -> LENGTH_UNITS:
        return self._global_units

    def _lumapi(self) -> Lumapi:
        return self._global_lumapi

    def _check_name(self, name: str) -> None:
        """Checks if an object with a given name exists. If it does, a FDTDreamNotUniqueError is raised."""
        if any(getattr(obj, "_name") == name for obj in self._structures):
            message = f"Expected unique name. Object with name '{name}' already exists."
            raise errors.FDTDreamNotUniqueNameError(message)

    # endregion

    # region User Methods
    def _extract_meshes(self) -> List[SavedStructure]:

        # Fetch all structure meshes
        all_structures = []
        etch_structures = []
        for struct in self._structures:
            try:
                if struct._get("material", str) != "etch":
                    if struct.enabled:
                        all_structures.append(struct)
                else:
                    if struct.enabled:
                        etch_structures.append(struct._get_trimesh(absolute=True, units="nm"))
            except ValueError as e:
                if hasattr(struct, "_base_structure"):  # Then it's a lattice
                    if struct._base_structure._get("material", str) != "etch":
                        if struct.enabled:
                            all_structures.append(struct)
                    else:
                        if struct.enabled:
                            lattice_mesh = struct._get_trimesh(absolute=True, units="nm")
                            etch_structures.append(lattice_mesh)
                elif hasattr(struct, "_structures"):  # Then it's a structure group
                    if struct.enabled:
                        etch_substructures = [substruct._get_trimesh(absolute=True, units="nm")
                                           for substruct in struct._structures
                                           if substruct._get("material", str) == "etch" and substruct.enabled]
                        etch_structures.extend(etch_substructures)
                        all_structures.append(struct)
                else:
                    raise e

        meshes = []

        # Get FDTD box mesh and center (in nm)
        fdtd = self._fdtd
        fdtd_mesh = self._fdtd._get_trimesh(absolute=True, units="nm")
        fdtd_position = convert_length(self._fdtd._get_position(absolute=True), "m", "nm")
        fdtd_center = fdtd_position  # assuming this is the centroid of the FDTD region

        # Get boundary conditions
        x_bc = self._fdtd._get("x min bc", str).lower()
        y_bc = self._fdtd._get("y min bc", str).lower()
        z_bc = self._fdtd._get("z min bc", str).lower()

        # Get truth values for what boundaries are symmetric
        x_sym = x_bc in ["symmetric", "anti-symmetric"]
        y_sym = y_bc in ["symmetric", "anti-symmetric"]
        z_sym = z_bc in ["symmetric", "anti-symmetric"]

        # Make the fdtd region only the part that will be mirrored, not the other regions.
        mirrored_regions = []
        epsilon = - 0.1  # Slight buffer to make sure tangenting meshes overlap.
        if x_sym:
            x_span = fdtd.x_span / 2
            m = trimesh.creation.box((x_span + epsilon, fdtd.y_span, fdtd.z_span))
            m.apply_translation(fdtd_position - np.array([x_span / 2, 0, 0]))
            mirrored_regions.append(m)
        if y_sym:
            y_span = fdtd.y_span / 2
            m = trimesh.creation.box((fdtd.x_span, y_span + epsilon, fdtd.z_span))
            m.apply_translation(fdtd_position - np.array([0, y_span / 2, 0]))
            mirrored_regions.append(m)

        if z_sym:
            z_span = fdtd.z_span / 2
            m = trimesh.creation.box((fdtd.x_span, fdtd.y_span, z_span + epsilon))
            m.apply_translation(fdtd_position - np.array([0, 0, z_span / 2]))
            mirrored_regions.append(m)

        if mirrored_regions:
            fdtd_mesh = trimesh.boolean.difference([fdtd_mesh, trimesh.boolean.union(mirrored_regions)])

        # Define mirror directions
        mirror_axes = []
        if x_sym:
            mirror_axes.append([-1, 1])
        else:
            mirror_axes.append([1])
        if y_sym:
            mirror_axes.append([-1, 1])
        else:
            mirror_axes.append([1])
        if z_sym:
            mirror_axes.append([-1, 1])
        else:
            mirror_axes.append([1])

        def mirror_structure(struct, parent_group) -> SavedStructure | None:
            org_mesh = struct._get_trimesh(absolute=True, units="nm")

            # Remove potential etches
            if etch_structures:
                org_mesh = trimesh.boolean.difference([org_mesh] + etch_structures)

            mirrored = []

            try:
                # Get the portion of the structure that is inside the mirrored region
                mirror_part = trimesh.boolean.intersection([org_mesh, fdtd_mesh])

                # Return None if no part of the structure is inside the region.
                if mirror_part.is_empty:
                    return None

                # Mirror across symmetric axes (assumes mirroring around the fdtd_center)
                for scale in product(*mirror_axes):
                    if scale == (1, 1, 1):
                        mirrored.append(mirror_part)
                    else:
                        m = mirror_part.copy()
                        m.apply_translation(-fdtd_center)
                        m.apply_scale(scale)
                        m.apply_translation(fdtd_center)
                        mirrored.append(m)

            except Exception as e:
                print(f"Warning: Mirroring failed for structure '{struct.name}': {e}")

            # Combine original and mirrored pieces
            try:
                recombined_struct = trimesh.boolean.union(mirrored)
            except Exception as e:
                print(f"Warning: Concatenation failed for '{struct.name}': {e}")
                recombined_struct = org_mesh

            saved_structure = SavedStructure(struct.name, recombined_struct)

            return saved_structure

        for structure in all_structures:
            if not structure.enabled:
                continue

            meshes.append(mirror_structure(structure, None))

            if hasattr(structure, "_structures"):
                for substruct in structure._structures:
                    if substruct._get("material", str) != "etch" and substruct.enabled:
                        structure_mesh = mirror_structure(substruct, structure)
                        if structure_mesh:
                            meshes.append(structure_mesh)
            elif hasattr(structure, "_base_structure"):
                if structure._base_structure._get("material", str) != "etch":
                    structure_mesh = mirror_structure(structure, None)
                    if structure_mesh:
                        meshes.append(structure_mesh)

        return meshes

    def run(self,
            database_path: str,
            simulation_category: str,
            simulation_name: str,
            parameters: Dict[str, Union[str, float, int, bool]] = None,
            info_text: str = None) -> SimulationResults:
        """
        Runs the simulation and extracts the result to the database at the database_path.
        The category is a string deciding what "folder" in the database to put the simulation in.
        The simulation name is the name of the simulation in the database.
        The parameter dictionary is an optional set of parameters that can be saved to the database.
        The info_text string is a str you can save to the simulation with additional information.
        """

        # Check if a simulation region has been added
        if self._fdtd is None:
            raise errors.FDTDreamNoSimulationRegionError("Cannot run simulation, as no FDTD Region is defined.")

        # Validate parameters
        if parameters is None:
            parameters = {}
        elif not isinstance(parameters, dict):
            raise TypeError(f"Expected dictionary for 'parameters', got '{type(parameters)}'.")

        if not "__info__" in parameters:
            parameters["__info__"] = info_text if info_text else ""

        # Connect to the database.
        db_handler = DatabaseHandler(database_path)

        # Extract structure meshes
        meshes = self._extract_meshes()

        # Save simulation to temp file
        # Create the temp folder at the same level as the parent directory
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Current script location
        parent_dir = os.path.dirname(script_dir)  # Go one level up
        temp_dir = os.path.join(parent_dir, "temp")  # Path to temp folder

        os.makedirs(temp_dir, exist_ok=True)  # Ensure temp folder exists

        # Create a temporary .fsp file
        temp_fsp_path = os.path.join(temp_dir, "temp_simulation.fsp")
        self.save(temp_fsp_path)  # Save simulation to temp file

        # Run the simulation
        self._lumapi().switchtolayout()
        self._lumapi().run()

        # Fetch results from the monitors
        results = []
        for monitor in self._monitors:
            if not monitor.enabled:
                continue

            res = monitor._get_results()
            if res is not None:
                results.append(res)

        # Create a SavedSim model
        saved_sim = SimulationResults(
            simulation_category,
            simulation_name,
            parameters,
            results,
            meshes
        )

        # Add the model to the database.
        db_handler.add_simulation(saved_sim)

        # Switch back to layout and save the temp file again (to avoid double saving data).
        self._lumapi().switchtolayout()
        self.save(temp_fsp_path)

        # Delete the temp file when it's no longer needed
        try:
            os.remove(temp_fsp_path)
        except OSError as e:
            pass

        # Delete additional log files if they exist
        save_path = temp_fsp_path
        base_name = os.path.splitext(os.path.basename(save_path))[0]  # Get filename without extension
        log_files = [f"{base_name}_p0.log", f"{base_name}_p0.err"]

        for log_file in log_files:
            log_file_path = os.path.join(os.path.dirname(save_path), log_file)
            if os.path.exists(log_file_path):
                try:
                    os.remove(log_file_path)
                except OSError as e:
                    pass

        # Print validation
        print(f"Saved simulation '{simulation_name}' with category '{simulation_category}' "
              f"to database '{db_handler.filename}'.")

        return saved_sim

    def save(self, save_path: str = None, print_confirmation: bool = True) -> None:
        """
        Saves the lumerical simulation file to the default save path or to the speccified save path if provided.

        Args:
            save_path (str): Where to save the file, including the name. Does not need to contain the .fsp suffix.
                If not provided, the original save path is used.
            print_confirmation (bool): If True, prints 'File saved to: r"path"' to console.

        """
        path = os.path.abspath(save_path) if save_path is not None else self._save_path
        self._lumapi().save(path)
        if print_confirmation:
            print("File saved to: r'" + path + "'")

    # endregion


# region Alt Loading

creation_lines = ["addrect();", "addcircle();", "addsphere();", "addring();", "addpyramid();", "addpoly();",
                  "addplanarsolid();"]


def read_set_line(line, current_object: dict | None) -> None:

    if current_object is None:
        #TODO implement catching errors
        ...

    # This regex captures the entire quoted string (including quotes) for each argument.
    pattern = r"set\(\s*((['\"]).*?\2)\s*,\s*(((['\"]).*?\5)|([^'\"\)]+))\s*\);"

    match = re.search(pattern, line)
    if match:

        left_arg = match.group(1)  # always a quoted string (with quotes)
        right_arg = match.group(3)  # either a quoted string (with quotes) or a non-quoted value

        left_arg = left_arg.strip("'").strip('"')
        if "'" in right_arg or '"' in right_arg:
            right_arg = right_arg.strip("'").strip('"')
        elif right_arg == "true":
            right_arg = True
        elif right_arg == "false":
            right_arg = False
        else:
            right_arg = float(right_arg)

        if current_object.get("parameters", None):
            current_object["parameters"].append((left_arg, right_arg))
        else:
            current_object["parameters"] = [(left_arg, right_arg)]


def read_construction_code(line: str, sim) -> ScriptedStructure:
    if line == "addrect();":
        obj = ScriptedRectangle(sim)
    elif line == "addcircle();":
        obj = ScriptedCircle(sim)
    elif line == "addsphere();":
        obj = ScriptedSphere(sim)
    elif line == "addring();":
        obj = ScriptedRing(sim)
    elif line == "addpyramid();":
        obj = ScriptedPyramid(sim)
    elif line == "addpoly();":
        obj = ScriptedPolygon(sim)
    elif line == "addtriangle();":
        obj = ScriptedTriangle(sim)
    elif line == "addregularpolygon();":
        obj = ScriptedRegularPolygon(sim)
    else:
        raise ValueError(f"Construction code '{line}' does not refer to a valid structure type.")

    return obj


def read_construction_group(cg: structures.StructureGroup, code_lines: List[str],
                            sim: SimulationInterface) -> list[ScriptedStructure] | None:
    objects = []
    current_object = None

    if not code_lines:
        return None
    elif code_lines[0] == "deleteall;":
        if len(code_lines) > 1:
            code_lines = code_lines[1:]
        else:
            return None

    for line in code_lines:

        if line in creation_lines:

            current_object = {"constructor": line}
            objects.append(current_object)

        elif line.startswith("set("):

            read_set_line(line, current_object)

    # Create objects and set parameters:
    new_objects = []
    for obj in objects:
        for param, value in obj["parameters"]:

            if param == "grid attribute name":
                if value == "Triangle":
                    obj["constructor"] = "addtriangle();"
                elif value == "RegularPolygon":
                    obj["constructor"] = "addregularpolygon();"
                break

        new_object = read_construction_code(obj["constructor"], sim)
        for param in obj["parameters"]:
            new_object._set(*param)

        new_object._closest_parent = cg
        new_object._parents.append(cg)
        new_objects.append(new_object)

    return new_objects

def extract_effective_lines(code_str: str) -> list[str]:
    """Takes in Lumerical Scripting language and returns a list with each line of code that actually does anything."""

    effective_lines = []
    current_statement = ""

    # Process the code line by line
    for line in code_str.splitlines():

        # Remove any comment (anything after '#' is ignored)
        code_without_comment = line.split('#', 1)[0].strip()
        if not code_without_comment:
            continue  # skip empty lines

        # Accumulate the code, adding a space for separation if needed
        current_statement += code_without_comment + " "

        # Process the accumulated code until all effective lines (terminated by ;) are extracted
        while ';' in current_statement:
            # Split on the first semicolon
            statement, remainder = current_statement.split(';', 1)
            if statement.strip():
                effective_lines.append(statement.strip())
            current_statement = remainder.strip()

        # Add back the ; separators.
    effective_lines = [line + ";" for line in effective_lines]

    return effective_lines

# endregion
