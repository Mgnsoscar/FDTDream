import os.path
import sys
from abc import ABC

from PyQt6.QtWidgets import QApplication, QFileDialog

from . import fdtd
from . import mesh
from . import monitors
from . import sources
from .structures.scripted_structures import *
from .structures.scripted_structures.scripted_structure_group import ScriptedStructureGroup
from . import structures
from .lumapi import Lumapi
from .resources import validation
from .resources.literals import LENGTH_UNITS
from .simulation import Simulation


# region Object Interfaces

# region Structure Interfaces

class Rectangle(structures.Rectangle, ABC):
    ...


class Circle(structures.Circle, ABC):
    ...


class Sphere(structures.Sphere, ABC):
    ...


class Pyramid(structures.Pyramid, ABC):
    ...


class Ring(structures.Ring, ABC):
    ...


class Polygon(structures.Polygon, ABC):
    ...


class RegularPolygon(structures.RegularPolygon, ABC):
    ...


class Lattice(structures.Lattice, ABC):
    ...


class StructureGroup(structures.StructureGroup, ABC):
    ...


class PlanarSolid(structures.PlanarSolid, ABC):
    ...


# endregion Structure Interfaces

# region Scripted Structure Interfaces

class SCircle(ScriptedCircle, ABC):
    ...


class SPolygon(ScriptedPolygon, ABC):
    ...


class SPyramid(ScriptedPyramid, ABC):
    ...


class SRectangle(ScriptedRectangle, ABC):
    ...


class SRegularPolygon(ScriptedRegularPolygon, ABC):
    ...


class SRing(ScriptedRing, ABC):
    ...


class SSphere(ScriptedSphere, ABC):
    ...


class SStructureGroup(ScriptedStructureGroup, ABC):
    ...


class STriangle(ScriptedTriangle, ABC):
    ...


class SPlanarSolid(ScriptedPlanarSolid, ABC):
    ...


# endregion

# region Source Interfaces

class PlaneWave(sources.PlaneWave, ABC):
    ...


class GaussianBeam(sources.GaussianBeam, ABC):
    ...


class CauchyLorentzian(sources.CauchyLorentzianBeam, ABC):
    ...


# endregion Source Interfaces

# region Monitor Interfaces

class IndexMonitor(monitors.IndexMonitor, ABC):
    ...


class FreqDomainFieldAndPowerMonitor(monitors.FreqDomainFieldAndPowerMonitor, ABC):
    ...


# endregion Monitor Interfaces

# region FDTD Interfaces

class Mesh(mesh.Mesh, ABC):
    ...


class FDTDRegion(fdtd.FDTDRegion, ABC):
    ...


# endregion FDTD Interfaces

# endregion Object Interfaces


class FDTDream:
    """The FDTDream class is basically a class used to initialize simulations."""

    class i:
        """Class containing references to simulation object interfaces."""
        Rectangle: Rectangle = Rectangle
        Circle: Circle = Circle
        Sphere: Sphere = Sphere
        Pyramid: Pyramid = Pyramid
        Ring: Ring = Ring
        Polygon: Polygon = Polygon
        RegularPolygon: RegularPolygon = RegularPolygon
        Lattice: Lattice = Lattice
        StructureGroup: StructureGroup = StructureGroup
        PlanarSolid: PlanarSolid = PlanarSolid
        SRectangle: SRectangle = SRectangle
        SCircle: SCircle = SCircle
        SSphere: SSphere = SSphere
        SPyramid: SPyramid = SPyramid
        SRing: SRing = SRing
        SPolygon: SPolygon = SPolygon
        SRegularPolygon: SRegularPolygon = SRegularPolygon
        SStructureGroup: SStructureGroup = SStructureGroup
        STriangle: STriangle = STriangle
        SPlanarSolid: SPlanarSolid = SPlanarSolid
        PlaneWave: PlaneWave = PlaneWave
        GaussianBeam: GaussianBeam = GaussianBeam
        CauchyLorentzian: CauchyLorentzian = CauchyLorentzian
        IndexMonitor: IndexMonitor = IndexMonitor
        FreqDomainFieldAndPowerMonitor: FreqDomainFieldAndPowerMonitor = FreqDomainFieldAndPowerMonitor
        Mesh: Mesh = Mesh
        FDTDRegion: FDTDRegion = FDTDRegion

    @staticmethod
    def _update_materials(new_materials: str):
        """Loads the list of available materials from the provided .fsp file and hard rewrites the materials literal
        from the resources package to ensure up to date material hints."""

        # Fetch the current directory:
        current_dir = os.path.dirname(__file__)

        # Fetch the path to the materials_literal.py file
        file_path = os.path.join(current_dir, "resources/materials_literal.py")

        # Initialize the new contents of the .py file
        new_contents = ("from typing import Literal\n"
                        "# This file will be erased and rewritten every time a new Lumerical FDTD project file "
                        "is created or loaded.\n\n"
                        "Materials = Literal[\n")

        # Split the input string into lines
        materials = new_materials.splitlines()

        # Insert the new materials:
        for material in materials:
            new_contents += "    '" + material + "',\n"

        new_contents += "    '" + "<Object defined dielectric>" + "',\n"

        # Close out the string properly
        new_contents += "\t]"

        # Write the updated content back to the file
        with open(file_path, "w") as file:
            file.write(new_contents)

    @staticmethod
    def _select_load_path() -> str:
        """Opens a file explorer that allows the user to select a .fsp file."""
        # Ensure a QApplication instance exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Open a file dialog to choose an existing file
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select Simulation File",
            "",
            "FDTD Simulation Files (*.fsp)"
        )

        if file_path:
            return os.path.abspath(file_path)
        else:
            raise ValueError("No file selected.")

    @staticmethod
    def _select_save_path(filename: str = None) -> str:
        """
        Opens a file explorer that allows the user to select a location where to save a .fsp file.

        Args:
            filename (str): Name of the .fsp file. Does not need to include the .fsp suffix.

        Returns:
            str: Absolute path and filename of the new .fsp file.
        """
        # Ensure a QApplication instance exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Provide a default filename if none is given
        default_filename = filename if filename else "new_simulation.fsp"
        if not default_filename.endswith(".fsp"):
            default_filename += ".fsp"

        # Open a file dialog to choose a save location
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Simulation File",
            default_filename,
            "FDTD Simulation Files (*.fsp)"
        )

        if file_path:
            # Ensure the file name ends with the .fsp suffix
            if not file_path.endswith(".fsp"):
                file_path += ".fsp"
            return os.path.abspath(file_path)
        else:
            raise ValueError("No save location selected.")

    @classmethod
    def new_simulation(cls, filename: str = None, units: LENGTH_UNITS = "nm", variable_name: str = "sim",
                       hide: bool = False) -> Simulation:
        """
        Creates a new Lumerical FDTD simulation file and saves it to the provided save path.

        Args:
            filename (str): The name of the new simulation file. Does not need to include the .fsp suffix. If not
                provided, a file explorer window appears.
            units (str): The units all lengths units will default to. Default is nanometers.
            variable_name (str): The name of the variable created by calling this method. Will be important when
                printing declarations to console.
            hide (bool): If True, Lumerical FDTD runs in the background without opening, if False it opens.
        """

        # Validate correct units
        validation.in_literal(units, "units", LENGTH_UNITS)

        # Create an absolute path.
        if filename:
            print_declarations = False

            # Check that the filename argument is a string
            if not isinstance(filename, str):
                raise TypeError(f"Expected filename as type(str), got {type(filename)}.")

            # Make sure the filename ends with the .fsp suffix
            if not filename.endswith(".fsp"):
                filename += ".fsp"

            filename = os.path.abspath(filename)

        else:
            print_declarations = True
            filename = cls._select_save_path(filename)

        # Create a new lumapi instance:
        lumapi = Lumapi(hide=hide)

        # Fetch materials and update available materials
        cls._update_materials(lumapi.getmaterial())

        # Initialize a simulation object and pass the initialized API and filename to it, along with the units.
        sim = Simulation(lumapi, filename, units)

        # Print alternative method call to console.
        if print_declarations:
            print(f"\033[4mReplace the new_simulation() call with this to do exactly the same without "
                  f"calling the file explorer.\033[0m\n\n"
                  f"{variable_name} = FDTDream.new_simulation(r'{filename}',\n"
                  f"{len(variable_name + ' = FDTDream.new_simulation(') * ' '}units='{units}', hide={hide})\n\n")

        # Save
        # sim.save(print_confirmation=False)

        # Return the initialized simulation
        return sim

    @classmethod
    def load_simulation(cls, path: str = None, units: LENGTH_UNITS = "nm", variable_name: str = "sim",
                        hide: bool = False) -> Simulation:
        """
        Loads an existing .fsp file from the specified path. If the path is not provided, an explorer appears, promting
        the user to select a .fsp file to load.

        When loading a .fsp file using the file explorer, the .fsp file
        is scanned for contained object. Variable declarations with type hints are printed to the console. These
        should be copy/pasted into you code, replacing this method. That way the user gets full autocompletion and
        control over the objects in the .fsp file. This way, the list of available materials are also updated.

        Args:
            path (str): Location of the .fsp file. If None, a file explorer window appears.
            units (str): The units all lengths units will default to. Default is nanometers.
            variable_name (str): The name of the variable created by calling this method. Will be important when
                printing declarations to console.
            hide (bool): If True, Lumerical FDTD runs in the background without opening, if False it opens.

        Returns:
            A Simulation object containing the loaded simulation.
        """

        # Validate correct units
        validation.in_literal(units, "units", LENGTH_UNITS)

        # Create an absolute path.
        if not path:
            path = cls._select_load_path()
            print_declarations = True
            hide = True

        else:
            print_declarations = False

            # Check that the filename argument is a string
            if not isinstance(path, str):
                raise TypeError(f"Expected filename as type(str), got {type(path)}.")

            # Make sure the filename ends with the .fsp suffix
            if not path.endswith(".fsp"):
                path += ".fsp"

            # Make sure the file exists
            if not os.path.exists(path):
                raise IOError(f"The specified path does not exist. Path: '{path}'")
            else:
                path = os.path.abspath(path)

        # Create a new lumapi instance:
        lumapi = Lumapi(path, hide=hide)

        # Fetch materials and update available materials
        cls._update_materials(lumapi.getmaterial())

        # Initialize a simulation object and pass the initialized API and filename to it, along with the units.
        sim = Simulation(lumapi, path, units)

        if print_declarations:
            # Print alternative method call to console.
            print(f"\033[4mReplace the load_simulation() call with this to do exactly the same without "
                  f"calling the file explorer.\033[0m\n\n"
                  f"{variable_name} = FDTDream.load_simulation(r'{path}', \n"
                  f"{len(variable_name + ' = FDTDream.load_simulation(') * ' '}units='{units}', hide={hide})\n")

        # Load objects and print variable declarations
        sim._load_objects_from_file()
        if print_declarations:
            sim._print_variable_declarations("sim", True)

        # Save
        # sim.save(print_confirmation=False)

        # Return the initialized simulation
        return sim

    @classmethod
    def load_base(cls, base_path: str = None, save_path: str = None, units: LENGTH_UNITS = "nm",
                  variable_name: str = "sim", hide: bool = False) -> Simulation:
        """
        Loads an existing .fsp file from the specified path, but saves it to the specified save path, not overriding
        the original. If either the base_path or the filename arguments are not provided, a file explorer window will
        pop up, prompting the user to either select a file to load, or a location to save.

        When loading a .fsp file using the file explorer, the .fsp file
        is scanned for contained object. Variable declarations with type hints are printed to the console. These
        should be copy/pasted into you code, replacing this method. That way the user gets full autocompletion and
        control over the objects in the .fsp file. This way, the list of available materials are also updated.

        Args:
            base_path (str): Location of the .fsp file to load. If None, a file explorer window appears.
            save_path (str): Filename and path to where the file should be saved. If None, a file explorer
                window appears.
            units (str): The units all lengths units will default to. Default is nanometers.
            variable_name (str): The name of the variable created by calling this method. Will be important when
                printing declarations to console.
            hide (bool): If True, Lumerical FDTD runs in the background without opening, if False it opens.

        Returns:
            A Simulation object containing the loaded simulation.

        """
        # Validate correct units
        validation.in_literal(units, "units", LENGTH_UNITS)

        # Create an absolute path.
        if not base_path:
            base_path = cls._select_load_path()
            print_declarations = True
            hide = True

        else:
            print_declarations = False
            # Check that the base path argument is a string
            if not isinstance(base_path, str):
                raise TypeError(f"Expected filename as type(str), got {type(base_path)}.")

            # Make sure the base_path ends with the .fsp suffix
            if not base_path.endswith(".fsp"):
                base_path += ".fsp"

            # Make sure the file exists
            if not os.path.exists(base_path):
                raise IOError(f"The specified path does not exist. Path: '{base_path}'")
            else:
                base_path = os.path.abspath(base_path)

        # Create an absolute path to the save path.
        if save_path:

            # Check that the filename argument is a string
            if not isinstance(save_path, str):
                raise TypeError(f"Expected filename as type(str), got {type(save_path)}.")

            # Make sure the filename ends with the .fsp suffix
            if not save_path.endswith(".fsp"):
                save_path += ".fsp"

            save_path = os.path.abspath(save_path)

        else:
            save_path = cls._select_save_path(save_path)

        # Create a new lumapi instance:
        lumapi = Lumapi(base_path, hide=hide)

        # Fetch materials and update available materials
        cls._update_materials(lumapi.getmaterial())

        # Initialize a simulation object and pass the initialized API and filename to it, along with the units.
        sim = Simulation(lumapi, save_path, units)

        # Load objects and print type annotations
        sim._load_objects_from_file()
        if print_declarations:
            # Print alternative method call to console.
            print(f"\033[4mReplace the load_base() call with this to do exactly the same without "
                  f"calling the file explorer.\033[0m\n\n"
                  f"{variable_name} = FDTDream.load_base(\n\tr'{base_path}',\n\tr'{save_path}',\n"
                  f"{len(variable_name + ' = FDTDream.load_base(') * ' '}units='{units}', "
                  f"variable_name='{variable_name}', hide={hide})\n\n")
            sim._print_variable_declarations(variable_name, True)

        # Save
        # sim.save(print_confirmation=False)

        # Return the initialized simulation
        return sim
