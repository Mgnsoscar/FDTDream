from __future__ import annotations

# Standard library imports
from typing import Literal, Any, TypedDict, Optional, Unpack
from warnings import warn
import os

# Third-party imports
import numpy as np
from lumapi_import import lumapi

# Local import
from type_hint_resources import LENGTH_UNITS
from local_resources import Validate, convert_length
from local_resources import DECIMALS


########################################################################################################################
#                                             CONSTANTS AND LITERALS
########################################################################################################################

PARAMETER_TYPES = Literal["float", "int", "str", "bool", "list"]

########################################################################################################################
#                                               TYPED DICTIONARIES
########################################################################################################################


class SimulationBaseKwargs(TypedDict, total=False):
    hide: bool
    load_file: bool
    new_file: bool
    save_path: str


########################################################################################################################
#                                                  BASE CLASSES
########################################################################################################################

class CommonFDTDObjectClass:

    class _SettingsDict(TypedDict):
        """
        A TypedDict subclass that encapsulates all configuration settings specific to the
        FDTD environment for instances of this class. This dictionary contains parameters
        that control simulation characteristics, spatial dimensions, and other relevant
        settings, ensuring structured and type-checked data storage across inherited child classes.
        When data should be stored to a database, this class is used to fetch the settings nicely.

        Attributes:
            This dict contains key-value pairs representing each setting parameter relevant
            to the FDTD environment configuration for the given class, and is inherited
            and customized by each child class to represent its unique set of settings.
        """
        pass

    # Declare variables
    _simulation: lumapi.FDTD

    # Add the '_simulation' variable to a list and then add it to the __slots__ to avoid the variable
    # showing up in autocompletion hints across all child classes. It may be bad practice, I don't know,
    # but it makes it cleaner for the end user when only the options they should be able to use show up in
    # auto-completion hints.
    _placeholder_list = ["_simulation"]

    # Declare slots
    __slots__ = _placeholder_list

    def __init__(self, simulation: lumapi.FDTD) -> None:
        """
        Initializes the CommonFDTDObjectClass with the provided FDTD simulation instance.

        Parameters:
        -----------
        simulation : FDTDSimulationBase
            An instance of the FDTD simulation environment that will be used for retrieving and
            setting object parameters.
        """
        # Initialize variables
        self._simulation = simulation

    def _get_parameter(
            self, parameter_name: str, type_: PARAMETER_TYPES, object_name: str = None, getter_function=None) -> Any:


        # Retrieve the parameter from the simulation enviroment either using the getnamed() method
        # or using the provided getter method.
        if getter_function is None:
            fetched = self._simulation.getnamed(object_name, parameter_name)
        else:
            if object_name is None:
                fetched = getter_function(parameter_name)
            else:
                fetched = getter_function(object_name, parameter_name)

        # If the parameter is of type float, round it to 12 decimal places
        if type_ == "float":
            fetched = np.round(float(fetched), decimals=DECIMALS)
        elif type_ == "int":
            fetched = int(fetched)
        elif type_ == "bool":
            fetched = fetched != 0.0
        elif type_ == "list":
            fetched = list(fetched)

        return fetched

    def _set_parameter(
            self, parameter_name: str, value: Any, type_: PARAMETER_TYPES, object_name: str = None,
            getter_function=None, setter_function=None) -> Any:

        # Check that if a custom setter/getter method has been provided, both are provided.
        if ((setter_function is None and getter_function is not None) or
                (getter_function is None and setter_function is not None)):
            raise ValueError("Both setter and getter function must either be provided or not provided.")

        # If the value to be set is a float, round it to the given number of decimals
        if isinstance(value, float):
            value = np.round(value, decimals=DECIMALS)

        # If no object name is provided, set the parameter for the main simulation object
        if setter_function is None:
            self._simulation.setnamed(object_name, parameter_name, value)
        else:
            if object_name is None:
                setter_function(parameter_name, value)
            else:
                setter_function(object_name, parameter_name, value)

        # Retrieve the new value of the parameter after setting it
        if getter_function is None:
            new_parameter = self._get_parameter(
                object_name=object_name, parameter_name=parameter_name, type_=type_)
        else:
            new_parameter = self._get_parameter(parameter_name=parameter_name, type_=type_, object_name=object_name,
                                                getter_function=getter_function)

        # If the parameter value has changed, raise a warning indicating the difference
        if type_ == "list":
            new_equals_old = np.array_equal(np.array(value), np.array(new_parameter))
        else:
            new_equals_old = value == new_parameter

        if not new_equals_old:
            warn(
                f"The value of '{parameter_name}' set to '{value}' was adjusted by the simulation environment. "
                f"The accepted value is '{new_parameter}', which differs from the input."
            )
        return new_parameter

    def _init_empty_settings_dict(self) -> _SettingsDict:
        return self.__class__._SettingsDict(**{
            parameter: None for parameter in self.__class__._SettingsDict.__required_keys__})

    # def get_currently_active_simulation_parameters(self) -> CommonFDTDObjectClass._SettingsDict:
    #     """
    #     Retrieves and returns the currently active simulation parameters associated with this simulation
    #     object or settings module.
    #
    #     This method fetches various configuration parameters from the simulation environment for a specific
    #     object or settings module. It initializes all required parameters with `None` and populates them
    #     based on the simulation's current state.
    #
    #     Returns:
    #     --------
    #     TypedDict:
    #         A type-hinted dictionary with all the parameters of the object/settings module. The keys of the
    #         dictionary is the same as the name of the parameters in the FDTD simulation enviroment, with spaces
    #         exchanged for underscores (i.e 'min wavelength' -> 'min_wavelength').
    #     """
    #     pass


class SettingTab(CommonFDTDObjectClass):
    """
    A base class that represents a settings tab in a simulation environment.
    This class manages subsettings, initializes parameters, and provides methods for
    getting and setting simulation parameters for a parent object.

    Attributes:
    -----------
    _sub_settings : list
        List of subclasses representing additional sub-settings for the object.
    _sub_settings_names : list
        List of names corresponding to the subsettings classes.
    _parent : SimulationObject
        The parent simulation object that this settings tab is associated with.

    __slots__ : list
        Memory optimization by restricting dynamic attribute creation.
        Includes attributes inherited from CommonFDTDObjectClass.
    """

    # Refference to subsettings classes
    _sub_settings = []

    # Names of the subsettings classes
    _sub_settings_names = []

    # Define variables
    _parent: SimulationObjectBase

    __slots__ = CommonFDTDObjectClass.__slots__ + ["_parent"]

    def __init__(self, parent: Optional[SimulationObjectBase], simulation: lumapi.FDTD) -> None:
        """
        Initializes the SettingTab instance by assigning parent, initializing subclasses, and inheriting
        parameters from the parent class.

        Parameters:
        -----------
        parent : Optional[SimulationObject]
            The parent simulation object that this setting tab is associated with.
        simulation : FDTDSimulationBase
            The simulation environment that the setting tab interacts with.
        """

        # Initialize all parameters as None, just so they are initialized in some way
        for parameter in self.__slots__:
            setattr(self, parameter, None)

        # Initialize from parent class
        super().__init__(simulation)

        # Assign variables
        self._parent = parent

        # Initialize subclasses
        for subclass_name, subclass in zip(self.__class__._sub_settings_names, self.__class__._sub_settings):
            setattr(self, subclass_name, subclass(self, simulation))

    def _get_parameter(
            self, parameter_name: str, type_: PARAMETER_TYPES, object_name: str = None, getter_function=None) -> Any:

        if object_name is None:
            if self._parent is not None:
                object_name = self._parent.name

        return super()._get_parameter(object_name=object_name, parameter_name=parameter_name, type_=type_,
                                      getter_function=getter_function)

    def _set_parameter(
            self, parameter_name: str, value: Any, type_: PARAMETER_TYPES, object_name: str = None,
            getter_function=None, setter_function=None) -> Any:
        """
        Sets a parameter in the parent object in the simulation environment.

        The method will check if the value assigned to the parameter in the simulation matches
        the one passed to this function. If not, a warning is issued. The value accepted by the simulation
        enviroment is returned regardless.

        Parameters:
        -----------
        parameter_name : str
            The name of the parameter to set.
        value : Any
            The value to assign to the parameter.
        type_ : Literal["float", "int", "str", "bool", "list"]
            The data type of the parameter.
        object_name : str, optional
            The name of the object for which the parameter is set.
            Defaults to the name of the parent object.

        Returns:
        --------
        Any:
            The new value of the parameter as accepted by the simulation environment.
        """

        if object_name is None:
            if self._parent is not None:
                object_name = self._parent.name

        return super()._set_parameter(object_name=object_name, parameter_name=parameter_name, value=value, type_=type_,
                                      setter_function=setter_function, getter_function=getter_function)


class SubsettingTab(SettingTab):
    __slots__ = SettingTab.__slots__

    def __init__(self, parent_setting: SettingTab, simulation: lumapi.FDTD):
        super().__init__(parent_setting._parent, simulation)


class SimulationObjectBase(CommonFDTDObjectClass):
    """Class representing a simulation object with associated settings."""

    # Helper lists for easy initialization
    _settings = []
    _settings_names = []

    # Declare variables
    _name: str

    __slots__ = CommonFDTDObjectClass.__slots__ + ["_name"]

    def __init__(self, name: str, simulation: lumapi.FDTD) -> None:
        """Initialize the SimulationObject with a name and a simulation base.

        Args:
            name (str): The name of the simulation object.
            simulation (FDTDSimulationBase): The simulation base associated with this object.
        """

        if name == "FDTD":
            raise ValueError("The 'FDTD' name is reserved for the FDTD Simulation Region.")

        # Initialize from parent class
        super().__init__(simulation)

        # Assign variables
        self._name = name

        # Initialize potential settings classes
        for object_name, object_ in zip(self.__class__._settings_names, self.__class__._settings):
            setattr(self, object_name, object_(parent=self, simulation=simulation))

    @property
    def name(self) -> str:
        """Get the name of the simulation object."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        """Set the name of the simulation object.

        Args:
            name (str): The new name to set for the simulation object.
        """
        if name == "FDTD":
            raise ValueError("The 'FDTD' name is reserved for the FDTD Simulation Region.")
        accepted_name = self._set_parameter("name", name, "str")
        self._name = accepted_name

    @property
    def x(self: CommonFDTDObjectClass) -> float:
        return convert_length(self._get_parameter(
            "x", "float"), "m", self._simulation.global_units)

    @x.setter
    def x(self: CommonFDTDObjectClass, x: float) -> None:
        Validate.number(x, "x")
        x = convert_length(x, self._simulation.global_units, "m")
        self._set_parameter("x", x, "float")

    @property
    def y(self: CommonFDTDObjectClass) -> float:
        return convert_length(self._get_parameter(
            "y", "float"), "m", self._simulation.global_units)

    @y.setter
    def y(self: CommonFDTDObjectClass, y: float) -> None:
        Validate.number(y, "y")
        y = convert_length(y, self._simulation.global_units, "m")
        self._set_parameter("y", y, "float")

    @property
    def z(self: CommonFDTDObjectClass) -> float:
        return convert_length(self._get_parameter(
            "z", "float"), "m", self._simulation.global_units)

    @z.setter
    def z(self: CommonFDTDObjectClass, z: float) -> None:
        Validate.number(z, "z")
        z = convert_length(float(z), self._simulation.global_units, "m")
        self._set_parameter("z", z, "float")

    def _get_parameter(
            self, parameter_name: str, type_: PARAMETER_TYPES, object_name: str = None, getter_function=None) -> Any:

        if object_name is None:
            object_name = self.name

        return super()._get_parameter(object_name=object_name, parameter_name=parameter_name, type_=type_)

    def _set_parameter(
            self, parameter_name: str, value: Any, type_: PARAMETER_TYPES, object_name: str = None,
            setter_function=None, getter_function=None) -> Any:

        if object_name is None:
            object_name = self.name

        return super()._set_parameter(object_name=object_name, parameter_name=parameter_name, value=value, type_=type_)


class FDTDSimulationBase(lumapi.FDTD):

    # Declare variables
    global_units: str

    # "Private" variables
    _names = []
    _monitors = []
    _structures = []
    _meshes = []
    _sources = []
    _save_path: str

    def __init__(self, global_units: LENGTH_UNITS = "nm", **kwargs: Unpack[SimulationBaseKwargs]) -> None:

        # Validate and assign variables
        Validate.in_literal(global_units, "global_units", LENGTH_UNITS)
        self.global_units = global_units

        # Initialize empty lists
        self._names = []
        self._monitors = []
        self._structures = []
        self._meshes = []
        self._sources = []

        # Raise an error of not loaded from file or new file is specified
        if kwargs.get("load_file", None) is None and kwargs.get("new_file", None) is None:
            raise ValueError(
                "You need to specify wether the instance of the class should be made as a new .fsp file (new_file=True), "
                "or if it should be loaded from an existing .fsp file (load_file=True). "
                "This class should best be initialized using the .load_file() class method or the "
                ".new_file() class method."
            )
        elif kwargs.get("load_file", None) is not None and kwargs.get("new_file", None) is not None:
            raise ValueError(
                "You have specified both load_file=True, and new_file=True. This is ambigous. Specify only one."
            )

        # Fetch the path to the loaded/new .fsp file
        filename = kwargs.get("save_path", None)
        if filename is None:
            raise ValueError("No path to .fsp file was provided.")

        # Load/initialize the FDTD simulation
        if not kwargs.get("load_file", False):
            super().__init__(**kwargs)
        else:
            super().__init__(filename, **kwargs)

        self.save(filename)  # Save the file and assign the _save_path variable through save() method

    @classmethod
    def new_file(cls, path: str, global_units: LENGTH_UNITS = "nm",
                 **kwargs: Unpack[SimulationBaseKwargs]) -> FDTDSimulationBase:

        # Check if the .fsp suffix is included. If not, add it
        if not path.endswith(".fsp"):
            path += ".fsp"

        path = os.path.abspath(path)

        # Get the directory path
        dir_path = os.path.dirname(path)

        # Ensure the directory exists
        if dir_path and not os.path.exists(dir_path):
            raise ValueError(f"Path '{path}' doesn't exist.")

        return cls(global_units, new_file=True, save_path=path, **kwargs)

    @classmethod
    def load_file(cls, path: str, global_units: LENGTH_UNITS = "nm",
                  **kwargs: Unpack[SimulationBaseKwargs]) -> FDTDSimulationBase:

        # Check if the .fsp suffix is included. If not, add it
        if not path.endswith(".fsp"):
            path += ".fsp"

        path = os.path.abspath(path)

        # Check if the file exists
        if not os.path.exists(path):
            raise ValueError(f"Path '{path}' doesn't exist.")

        instance = cls(global_units, load_file=True, save_path=path, **kwargs)
        instance._create_objects_from_file()

        return instance

    def _get_objects_and_types(self) -> tuple[list, list]:
        # Get a list of all object types
        self.selectall()
        num_objects = int(self.getnumber())
        object_names = []
        object_types = []

        # Iterate through each object
        for i in range(num_objects):
            # Get the name of the object by its index
            object_name = self.get("name", i + 1)
            object_names.append(object_name)

            # Get the type of the object
            object_type = self.getnamed(object_name, "type")
            object_types.append(object_type)

        return object_names, object_types

    def _create_objects_from_file(self) -> None:
        pass  # Override in child class

    def _print_variable_declarations(self, simulation_variable_name: str, exit_after_printing: bool) -> None:
        pass  # Override this in child class

    @classmethod
    def from_base_enviroment(cls, base_enviroment_path: str) -> FDTDSimulationBase:
        pass

    def save(self, filename: Optional[str] = None) -> None:
        if getattr(self, "_save_path", None) is None:
            if filename is None:
                raise ValueError(
                    "If your simulation enviroment is not loaded from a previously existing .fsp file, you must "
                    "specify a filename to save the new .fsp file as."
                )
            self._save_path = filename

        super().save(os.path.abspath(self._save_path))

    def _create_base_enviroment(self):
        pass
