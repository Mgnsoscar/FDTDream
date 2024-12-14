from __future__ import annotations

# Standard library imports
import os
from tkinter import Tk, filedialog

# Local library imports
from simulation import Simulation
from Code.Resources.literals import LENGTH_UNITS
from Code.Resources.lumapi_import import lumapi
from Code.Resources.local_resources import Validate


class FDTDream:

    class SimulationInterface(Simulation):

        def __new__(cls, *args, **kwargs):
            raise UserWarning("This is only an interface object, and should only be used for type hinting and "
                              "autocompletion. It is not meant to be initialized.")

    @staticmethod
    def _update_materials(file_path, new_materials):
        # Read the file content
        with open(file_path, "r") as file:
            lines = file.readlines()

        # Locate the #START_MATERIALS and #END_MATERIALS markers
        start_idx = None
        end_idx = None

        for i, line_ in enumerate(lines):
            if "#START_MATERIALS" in line_:
                start_idx = i
            elif "#END_MATERIALS" in line_:
                end_idx = i

        # Ensure markers were found
        if start_idx is None or end_idx is None:
            raise ValueError("Could not find #START_MATERIALS or #END_MATERIALS markers.")

        # Replace the MATERIALS block
        new_materials_block = (f"MATERIALS = Union[Literal[\n        "
                               f"{', '.join(f'\"{m}\"' for m in new_materials)}\n    ], str]\n")
        lines[start_idx + 1: end_idx] = [new_materials_block]

        # Write the updated content back to the file
        with open(file_path, "w") as file:
            file.writelines(lines)

    @staticmethod
    def _get_save_path(filename: str | None, save_directory: str | None, prompt: str | None, new: bool = False) -> str:
        """
        Returns the absolute save path for the file, ensuring it's valid and handles overwrites via GUI prompts.

        Args:
            filename (str): Name of the file to save, must include the `.fsp` extension.
            save_directory (str | None): Directory to save the file. If None, opens a wizard to choose the save location.

        Returns:
            str: The absolute path where the file will be saved.

        Raises:
            ValueError: If no location is selected or the directory is invalid.
            FileExistsError: If the file exists and the user chooses not to overwrite.
        """

        if filename is None and not new:
            root = Tk()
            root.withdraw()  # Hide the main window
            root.attributes("-topmost", True)  # Ensure the dialog is always on top
            file_path = filedialog.askopenfilename(
                title=prompt,
                defaultextension=".fsp",
                filetypes=[("Lumerical Simulation Files", "*.fsp")]
            )
            root.destroy()
            if not file_path:
                raise ValueError("No file selected. Operation canceled.")
            return file_path

        # Handle the save path logic
        if save_directory is None:
            # Open a wizard to let the user choose the file save location
            root = Tk()
            root.withdraw()  # Hide the main window
            save_path = filedialog.asksaveasfilename(
                title="Select Save Location",
                defaultextension=".fsp",
                filetypes=[("Lumerical Simulation Files", "*.fsp")],
                initialfile=filename
            )
            root.destroy()
            if not save_path:
                raise ValueError("No file location selected. Save operation canceled.")
        else:
            # Validate save_directory and construct the save path
            if not os.path.isdir(save_directory):
                raise ValueError(f"The specified save directory does not exist: {save_directory}")
            save_path = os.path.join(save_directory, filename)

        # Ensure the file has the correct .fsp extension
        if not save_path.endswith(".fsp"):
            save_path += ".fsp"

        return save_path

    @staticmethod
    def new_file(filename: str, save_path: str = None,
                 units: LENGTH_UNITS = "nm", hide: bool = False,
                 simulation_variable_name: str = "sim") -> Simulation:
        """Creates a new .fsp file with the given filename and saves it to the specified directory.
        If a .fsp file in the specified directory exists, a prompt to overwrite it will appear.
        Raises an error if the save directory doesn't exist. If no save directory is provided,
        a wizard will open to let the user choose the directory.

        Args:
            filename (str): Name of the file to create.
            save_path (str, optional): Path where .fsp file will be saved. If None, the file explorer window will
                                       showup and let you choose.
            units (LENGTH_UNITS): Units for the simulation. Defaults to "nm".
            hide (bool): If True, the FDTD application will open. If False it will run in the background. Defaults to
                         False.
            simulation_variable_name (str): Name of the instantiated simulation variable. Defaults to "sim".

        Returns:
            Simulation: A new Simulation instance.
        """

        Validate.in_literal(units, "units", LENGTH_UNITS)

        if save_path is None:
            save_path = FDTDream._get_save_path(filename, save_path, prompt="Select Save Location")
            indent_len = len(f"{simulation_variable_name} = FDTDream.new_file(")
            print(f"Replace the FDTDream.new_file() method with this if you want to save the new file to the same "
                  f"location next time you run the function.\n\n"
                  f"{simulation_variable_name} = FDTDream.new_file('{filename}',"
                  f"\n{' ' * indent_len}save_path='{save_path}',"
                  f"\n{' '*indent_len}units='{units}', hide={hide}, "
                  f"simulation_variable_name='{simulation_variable_name}')")

        lumapi_fdtd = lumapi.FDTD(hide=hide)
        sim = Simulation(lumapi_fdtd, save_path, units)
        materials = sim.__getattribute__("_lumapi").getmaterial().split("\n") + ["<Object defined dielectric>"]
        FDTDream._update_materials(r"C:\Users\mgnso\Desktop\Master thesis\Code\FDTDream\Code\Resources\literals.py",
                                   materials)
        return sim

    @staticmethod
    def load_file(file_path: str = None, units: LENGTH_UNITS = "nm", hide: bool = False,
                  simulation_variable_name: str = "sim") -> Simulation:

        Validate.in_literal(units, "units", LENGTH_UNITS)

        print_declarations = False
        message = ""
        prev_hide = hide
        if file_path is None:
            print_declarations = True
            hide = True
            file_path = FDTDream._get_save_path(filename=None, save_directory=None, prompt="Select File To Load")
            indent_len = len(f"{simulation_variable_name} = FDTDream.load_file(")

            message = (f"{simulation_variable_name} = FDTDream.load_file(file_path='{file_path}',"
                       f"\n{' ' * indent_len}units='{units}', hide={prev_hide}, "
                       f"simulation_variable_name='{simulation_variable_name}')")

        lumapi_fdtd = lumapi.FDTD(file_path, hide=hide)

        sim = Simulation(lumapi_fdtd, file_path, units)

        materials = sim.__getattribute__("_lumapi").getmaterial().split("\n") + ["<Object defined dielectric>"]
        FDTDream._update_materials(r"C:\Users\mgnso\Desktop\Master thesis\Code\FDTDream\Code\Resources\literals.py",
                                   materials)

        sim.__getattribute__("_initialize_objects_from_loaded_simulation")()
        if print_declarations:
            sim.__getattribute__("_print_variable_declarations")(simulation_variable_name, message,
                                                                 exit_after_printing=True)
        return sim

    @staticmethod
    def load_file_as_base(load_path: str = None, save_path: str = None,
                          units: LENGTH_UNITS = "nm", hide: bool = False,
                          simulation_variable_name: str = "sim") -> Simulation:

        Validate.in_literal(units, "units", LENGTH_UNITS)
        prev_hide = hide

        print_declarations = False
        if load_path is None:
            print_declarations = True
            hide = True
            load_path = FDTDream._get_save_path(filename=None, save_directory=None, prompt="Select File To Load")

        if save_path is None:
            save_path = FDTDream._get_save_path(filename=None, save_directory=None, prompt="Select Save Location",
                                                new=True)

        message = ""
        if print_declarations:

            indent_len = len(f"{simulation_variable_name} = FDTDream.load_file_as_base(")

            message = (f"{simulation_variable_name} = FDTDream.load_file_as_base(load_path='{load_path}',"
                       f"\n{' ' * indent_len}save_path='{save_path}',"
                       f"\n{' ' * indent_len}units='{units}', hide={prev_hide}, "
                       f"simulation_variable_name='{simulation_variable_name}')")

        lumapi_fdtd = lumapi.FDTD(load_path, hide=hide)

        sim = Simulation(lumapi_fdtd, save_path, units)

        materials = sim.__getattribute__("_lumapi").getmaterial().split("\n") + ["<Object defined dielectric>"]
        FDTDream._update_materials(r"C:\Users\mgnso\Desktop\Master thesis\Code\FDTDream\Code\Resources\literals.py",
                                   materials)

        sim.__getattribute__("_initialize_objects_from_loaded_simulation")()
        if print_declarations:
            sim.__getattribute__("_print_variable_declarations")(simulation_variable_name, message,
                                                                 exit_after_printing=True)
        return sim

    @staticmethod
    def _init_simulation_enviroment(filename: str, **kwargs) -> lumapi.FDTD:
        """
        Initializes a simulation environment by either creating a new simulation file or loading an
        existing one, based on the specified filename.

        This function checks if a file with the given `filename` exists. If it does, the simulation
        environment is initialized with that file. If not, a new simulation file is created with the
        specified name. Additional settings for the simulation environment can be passed through keyword
        arguments.

        Parameters:
        -----------
        filename : str
            The path to the simulation file to load or create. If the file does not exist, a new file
            with this name is created, given that the directory exists.

        **kwargs : Unpack[SimulationBase._Kwargs]
            Additional keyword arguments that configure settings for the `lumapi.FDTD` simulation
            environment. The specific parameters should match those expected by the `SimulationBase._Kwargs`
            type.

        Returns:
        --------
        lumapi.FDTD
            An instance of the FDTD simulation environment, initialized with the specified file and
            settings.
        """

        if filename:
            directory = os.path.dirname(filename)
            if directory and not os.path.isdir(directory):
                raise FileNotFoundError(f"The directory for '{filename}' does not exist.")

            if not os.path.exists(filename):
                print(f"No file named '{filename}' found. Creating new .fsp file.")

        return lumapi.FDTD(filename, **kwargs)

