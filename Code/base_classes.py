from __future__ import annotations

# Standard library imports
from typing import (Any, TypedDict, Optional, Unpack, Dict, Type, List, get_type_hints, TypeVar, Union, Generic,
                    Literal, ClassVar, Tuple)
from dataclasses import dataclass, fields, is_dataclass, asdict
from abc import ABC, abstractmethod
from warnings import warn
import hashlib

# Third-party imports
from scipy.spatial.transform import Rotation as R
from Code.Resources.lumapi_import import lumapi
import numpy as np

# Local import
from Code.Resources.literals import PARAMETER_TYPES, LENGTH_UNITS, AXES, MATERIALS, INDEX_UNITS
from Code.Resources.local_resources import (Validate, convert_length, get_parameter, set_parameter, euler_to_axis_angle)

########################################################################################################################
#                                                     TYPEVARS
########################################################################################################################
TMaterialDatabase = TypeVar("TMaterialDatabase", bound="MaterialDatabaseBase")
TSimulationObject = TypeVar("TSimulationObject", bound="SimulationObject")
TGlobalSettingTab = TypeVar("TGlobalSettingTab", bound="GlobalSettingTab")
TCommonBaseClass = TypeVar("TCommonBaseClass", bound="CommonBaseClass")
TSimulation = TypeVar("TSimulation", bound="SimulationBase")
TSettingTab = TypeVar("TSettingTab", bound="SettingTab")
TStructure = TypeVar("TStructure", bound="Structure")
TMaterial = TypeVar("TMaterial", bound="MaterialBase")
TGeometry = TypeVar("TGeometry", bound="BaseGeometry")
TSettings = TypeVar("TSettings", bound="Settings")
TGroup = TypeVar("TGroup", bound="Group")


########################################################################################################################
#                                                     TYPED DICTS
########################################################################################################################
class RelPositionKwargs(TypedDict, total=False):
    use_relative_coordinates: bool
    x: float
    y: float
    z: float


class PositionKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float


class AxesBoolKwargs(TypedDict, total=False):
    x: bool
    y: bool
    z: bool


class AxesFloatKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float


class AxesIntKwargs(TypedDict, total=False):
    x: int
    y: int
    z: int


########################################################################################################################
#                                                  BASE SETTINGS DATACLASSES
########################################################################################################################
@dataclass
class Settings:
    hash: Optional[str]

    @classmethod
    def initialize_empty(cls: Type[TSettings]) -> TSettings:
        """
        Recursively initializes all fields of the dataclass to `None`,
        unless a field is another dataclass, in which case it is recursively initialized.

        Returns:
            cls: An instance of the dataclass with all fields initialized to `None`.

        Example:
            @dataclass
            class MySettings(SettingsInterface):
                field1: int
                field2: AnotherSettings

            instance = MySettings.initialize_dataclass_with_none()
            print(instance)  # MySettings(field1=None, field2=AnotherSettings(...))
        """
        # Create an instance with all fields initialized
        instance_data = {}
        type_hints = get_type_hints(cls)  # Get resolved type hints for the dataclass

        for field in fields(cls):
            field_type = type_hints[field.name]  # Use resolved type hint
            if is_dataclass(field_type):  # If the field is a dataclass, recursively initialize it
                instance_data[field.name] = field_type.initialize_empty()
            else:  # Otherwise, initialize it to None
                instance_data[field.name] = None

        return cls(**instance_data)

    def fill_hash_fields(self):
        """
        Computes a unique hash for the dataclass by concatenating the string representations
        of all fields, including nested dataclasses and NumPy arrays.

        For nested dataclasses:
            - Calls `fill_hash_fields` on the nested dataclass.
            - Uses the `hash` of the nested dataclass as part of the computation.

        For NumPy arrays:
            - Computes a hash of the array's byte representation.

        This method updates the `hash` attribute of the instance.

        Example:
            instance = MySettings(field1=42, field2=AnotherSettings(...))
            instance.fill_hash_fields()
            print(instance.hash)  # Computed hash string
        """

        attr_string = ""

        for field in fields(self.__class__):
            field_name = field.name
            field_value = self.__getattribute__(field_name)

            if isinstance(field_value, np.ndarray):
                field_value = hashlib.sha256(field_value.tobytes()).hexdigest()
            elif isinstance(field_value, Settings):
                # Check if the nested dict has a hash. If so, return it, else create it
                field_hash = field_value.__getattribute__("hash")
                if not field_hash:
                    field_value.fill_hash_fields()
                    field_value = field_value.hash
            elif isinstance(field_value, list):
                list_hash_string = ""
                for list_item in field_value:
                    if is_dataclass(list_item):
                        # Check if the nested dict has a hash. If so, return it, else create it
                        list_item_hash = list_item.__getattribute__("hash")
                        if not list_item_hash:
                            list_item.fill_hash_fields()
                            list_hash_string += list_item.hash
                field_value = list_hash_string
            elif field_value is None:
                field_value = str(field_value)

            attr_string += field_name + str(field_value)

        hash_object = hashlib.sha256(attr_string.encode())
        self.hash = hash_object.hexdigest()

    def as_dict(self) -> dict:
        return asdict(self)

    def _update(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise KeyError(f"{key} is not a valid field of {self.__class__.__name__}")

    def _print(self, nested_name: str, tabulation: int, include_hash: bool = False) -> str:
        tab = "\t"
        string = tab * tabulation + nested_name
        if include_hash:
            string += f"(hash: {self.hash})\n"
        else:
            string += "\n"

        for parameter, hint in get_type_hints(self.__class__).items():
            if self.__getattribute__(parameter) is None:
                string += tab * (tabulation + 1) + parameter + ": None"
            elif not is_dataclass(hint):
                if parameter != "hash":
                    if hint == np.ndarray:
                        attr = self.__getattribute__(parameter)
                        if attr is not None and len(attr) > 3:
                            attr = "[...]"
                    else:
                        attr = self.__getattribute__(parameter)
                    string += tab * (tabulation + 1) + f"{parameter}: {attr}\n"
            else:
                string += self.__getattribute__(parameter)._print(nested_name=parameter, tabulation=tabulation + 1)
        return string

    def __hash__(self):
        return str(self.hash)

    def __eq__(self, other: TSettings):
        return self.hash == other.hash

    def __str__(self):
        return self._print(f"", 0)

    def __setattr__(self, name, value):

        if name not in {field.name for field in fields(self)}:
            raise AttributeError(f"Cannot add attribute '{name}' to '{self.__class__.__name__}' "
                                 f"as it is not a part of this class' defined variables.")
        super().__setattr__(name, value)


@dataclass
class Vertex(Settings):
    x: float
    y: float


@dataclass
class Position(Vertex):
    z: float


@dataclass
class BaseGeometrySettings(Settings):
    position: Position


@dataclass
class StructureSettings(Settings):
    geometry_settings: BaseGeometrySettings
    material_settings: MaterialBase.Settings
    rotation_settings: Rotation._Settings


@dataclass
class MaterialAdvancedParameters(Settings):
    tolerance: float
    max_coefficients: int
    make_fit_passive: bool
    improve_numerical_stability: bool
    imaginary_weight: float
    wavelength_min: float
    wavelength_max: float
    frequency_min: float
    frequency_max: float


@dataclass
class MaterialCommonParameters(Settings):
    anisotropy: str
    mesh_order: int


########################################################################################################################
#                                                  PROPERTY CLASSES
########################################################################################################################
class BaseMixinClass(ABC):
    class _SettingsCollection(ABC):
        geometry: TGeometry

    _simulation: TSimulation

    @abstractmethod
    def _get_parameter(self, *args):
        ...

    @abstractmethod
    def _set_parameter(self, *args):
        ...


class PositionProperties(BaseMixinClass, ABC):

    @property
    def x(self) -> float:
        return convert_length(self._get_parameter("x", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @x.setter
    def x(self, x: float) -> None:
        Validate.number(x, "x")
        x = convert_length(x, self._simulation.__getattribute__("_global_units"), "m")
        self._set_parameter("x", x, "float")

    @property
    def y(self) -> float:
        return convert_length(self._get_parameter("y", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @y.setter
    def y(self, y: float) -> None:
        Validate.number(y, "y")
        y = convert_length(y, self._simulation.__getattribute__("_global_units"), "m")
        self._set_parameter("y", y, "float")

    @property
    def z(self) -> float:
        return convert_length(self._get_parameter("z", "float"),
                              "m", self._simulation.__getattribute__("_global_units"))

    @z.setter
    def z(self, z: float) -> None:
        Validate.number(z, "z")
        z = convert_length(z, self._simulation.__getattribute__("_global_units"), "m")
        self._set_parameter("z", z, "float")


class MinMaxBoundingBoxProperties(BaseMixinClass, ABC):

    settings: TStructure._SettingsCollection

    @abstractmethod
    def _get_bounding_box(self):
        ...

    def _get_min_max(self, axis: Literal["x", "y", "z"], min_max: Literal["min", "max"]) -> float:
        is_rotated = self.settings.rotations.is_rotated()
        min_max_map = {"min": 0, "max": 1}
        axis_map = {"x": 0, "y": 1, "z": 2}
        structure = self.__class__.__name__
        if structure in ["Rectangle", "Custom", "Surface"]:
            if is_rotated:
                value = float(self._get_bounding_box()[min_max_map[min_max][axis_map[axis]]])
            else:
                value = self._get_parameter(axis + " " + min_max, "float")
        elif structure in ["Circle", "Polygon", "EquilateralPolygon", "Pyramid", "Ring"]:
            if axis != "z":
                value = float(self._get_bounding_box()[min_max_map[min_max]][axis_map[axis]])
            else:
                if is_rotated:
                    value = float(self._get_bounding_box()[min_max_map[min_max]][axis_map[axis]])
                else:
                    value = self._get_parameter("z " + min_max, "float")
        elif structure in ["Waveguide", "Sphere", "2D polygon"]:
            value = float(self._get_bounding_box()[min_max_map[min_max]][axis_map[axis]])
        elif structure in ["2D rectangle"]:
            if axis != "z":
                if is_rotated:
                    value = float(self._get_bounding_box()[min_max_map[min_max]][axis_map[axis]])
                else:
                    value = self._get_parameter(axis + " " + min_max, "float")
            else:
                value = self._get_parameter("z", "float")
        else:
            raise ValueError(f"Structure '{structure}' is not recognized.")

        return convert_length(value, "m", self._simulation.__getattribute__("_global_units"))

    @property
    def x_max(self) -> float:
        return self._get_min_max("x", "max")

    @property
    def x_min(self) -> float:
        return self._get_min_max("x", "min")

    @property
    def y_max(self) -> float:
        return self._get_min_max("y", "max")

    @property
    def y_min(self) -> float:
        return self._get_min_max("y", "min")

    @property
    def z_max(self) -> float:
        return self._get_min_max("z", "max")

    @property
    def z_min(self) -> float:
        return self._get_min_max("z", "min")


class MinMaxDirectProperties(BaseMixinClass, ABC):

    @property
    def x_max(self) -> float:
        return convert_length(float(self._get_parameter("x max", "float")), "m", self._simulation._global_units)

    @property
    def x_min(self) -> float:
        return convert_length(float(self._get_parameter("x min", "float")), "m", self._simulation._global_units)

    @property
    def y_max(self) -> float:
        return convert_length(float(self._get_parameter("y max", "float")), "m", self._simulation._global_units)

    @property
    def y_min(self) -> float:
        return convert_length(float(self._get_parameter("y min", "float")), "m", self._simulation._global_units)

    @property
    def z_max(self) -> float:
        return convert_length(float(self._get_parameter("z max", "float")), "m", self._simulation._global_units)

    @property
    def z_min(self) -> float:
        return convert_length(float(self._get_parameter("z min", "float")), "m", self._simulation._global_units)


########################################################################################################################
#                                                  GENERAL BASE CLASS
########################################################################################################################
class CommonBaseClass(ABC):
    class _Settings(Settings):
        ...

    _simulation: SimulationBase
    _placeholder_list = ["_simulation", "_settings_buffer"]
    __slots__ = _placeholder_list

    def __init__(self, simulation: TSimulation) -> None:
        # Initialize all parameters as None, just so they are initialized in some way
        for parameter in self.__slots__:
            setattr(self, parameter, None)

        self._simulation = simulation

    def __hash__(self) -> str:
        return self._get_active_parameters().hash

    def __eq__(self, other: TCommonBaseClass) -> bool:
        return self.__hash__() == other.__hash__()

    @abstractmethod
    def _get_parameter(self, parameter_name: str, parameter_type: PARAMETER_TYPES, object_name: str = None) -> Any:
        ...

    @abstractmethod
    def _set_parameter(self, parameter_name: str, value: Any, parameter_type: PARAMETER_TYPES,
                       object_name: str = None) -> Any:
        ...

    @abstractmethod
    def _get_active_parameters(self) -> _Settings:
        """
        Retrieves and returns the currently active simulation parameters associated with this simulation
        object or settings module.

        This method fetches various configuration parameters from the simulation environment for a specific
        object or settings module. It initializes all required parameters with `None` and populates them
        based on the simulation's current state.

        Returns:
        --------
        TypedDict:
            A type-hinted dictionary with all the parameters of the object/settings module. The keys of the
            dictionary is the same as the name of the parameters in the FDTD simulation enviroment, with spaces
            exchanged for underscores (i.e 'min wavelength' -> 'min_wavelength').
        """
        ...


########################################################################################################################
#                                               SETTING TABS BASE CLASSES
########################################################################################################################
class Tab(CommonBaseClass, ABC):
    __slots__ = CommonBaseClass.__slots__


class GlobalSettingTab(Tab, ABC):
    _settings: ClassVar[List[GlobalSettingTab]]
    _settings_names: ClassVar[List[str]]

    __slots__ = Tab.__slots__

    def __init__(self, simulation: TSimulation) -> None:
        super().__init__(simulation)

        # Initialize subclasses
        if getattr(self.__class__, "_settings", None):
            # Initialize subclasses
            for subclass_name, subclass in zip(self.__class__._settings_names, self.__class__._settings):
                setattr(self, subclass_name, subclass(simulation=simulation))

    def _create_or_get_existing_database_table(self, session=None, db_handler=None) -> None:
        raise UserWarning("This method should not be used by global settings tabs.")


class SettingTab(Tab, ABC):

    _settings: ClassVar[List[SettingTab]]
    _settings_names: ClassVar[List[str]]
    _parent: SimulationObject
    __slots__ = Tab.__slots__ + ["_parent"]

    def __init__(self, parent: TSimulationObject, simulation: TSimulation) -> None:
        super().__init__(simulation)
        self._parent = parent
        if getattr(self.__class__, "_settings", None):
            # Initialize subclasses
            for subclass_name, subclass in zip(self._settings_names, self._settings):
                setattr(self, subclass_name, subclass(parent=parent, simulation=simulation))

    def _get_parameter(self, parameter_name: str, parameter_type: PARAMETER_TYPES, object_name: str = None) -> Any:
        return get_parameter(simulation=self._simulation._lumapi, object_name=self._parent.name,
                             parameter_name=parameter_name, parameter_type=parameter_type)

    def _set_parameter(self, parameter_name: str, value: Any, parameter_type: PARAMETER_TYPES,
                       object_name: str = None) -> Any:
        return set_parameter(simulation=self._simulation._lumapi, object_name=self._parent.name,
                             parameter_name=parameter_name, value=value, parameter_type=parameter_type)


class Collection(SettingTab):

    __slots__ = SettingTab.__slots__

    def _get_active_parameters(self) -> None:
        return None


########################################################################################################################
#                                         GENERAL SIMULATION OBJECT BASE CLASSES
########################################################################################################################
class SimulationObject(CommonBaseClass, PositionProperties, ABC):
    class _SettingsCollection(Collection):
        geometry: RelativeBaseGeometry
        __slots__ = Collection.__slots__

    class _Kwargs(RelPositionKwargs, total=False):
        pass

    _settings: ClassVar[List[SettingTab]]
    _settings_names: ClassVar[List[str]]
    _name: str
    _group: Optional[Group]
    settings: _SettingsCollection

    __slots__ = CommonBaseClass.__slots__ + ["_name", "_group"]

    def __init__(self: TSimulationObject, name: str, simulation: TSimulation,
                 **kwargs: Unpack[_Kwargs]) -> None:

        # Initialize from parent class
        super().__init__(simulation)

        # Assign variables
        self._name = name.replace(" ", "_")
        self._group = None

        # Initialize potential settings classes
        for object_name, object_ in zip(self._settings_names, self._settings):
            setattr(self, object_name, object_(parent=self, simulation=simulation))

        self._apply_kwargs(**kwargs)

    def _apply_kwargs(self, **kwargs) -> None:
        """
        Applies keyword arguments (kwargs) to attributes or methods of the current instance or its subclasses
        in a predefined order, based on the field order in the TypedDict used as input.

        This method uses the ordered field names from `kwargs.__class__.__annotations__` to ensure that the
        keyword arguments are applied in the sequence defined in the `TypedDict`. For each argument, the method
        checks if the corresponding key matches an attribute or method in the main class or, if not found, in one
        of the specified subclasses. The key is applied by either setting an attribute or calling a method with
        the provided value.

        Parameters:
        -----------
        kwargs :
            Keyword arguments as a `TypedDict`, where the field names represent parameters to be applied to
            the current instance or its subclasses. The method assumes each field is either an attribute to set
            or a method to call.
        """

        def find_and_call_kwarg_method(inst_class: TCommonBaseClass, parameter: str, value: Any) -> bool:

            # Check if the key is a method or variable in the main class
            if hasattr(inst_class, parameter) and not isinstance(getattr(inst_class, parameter), Tab):

                if callable(getattr(inst_class, parameter)):
                    method = getattr(inst_class, parameter)
                    method(value)
                else:
                    setattr(inst_class, parameter, value)
                return True

            elif hasattr(inst_class, f"set_{parameter}") and callable(getattr(inst_class, f"set_{parameter}")):
                method = getattr(inst_class, f"set_{parameter}")
                method(value)
                return True

            else:
                # Check each subclass for the key
                subsettings_names = getattr(inst_class, "_settings_names", None)
                if subsettings_names:
                    for subsetting_name in subsettings_names:
                        subsetting = getattr(inst_class, subsetting_name)
                        found_method = find_and_call_kwarg_method(subsetting, parameter, value)
                        if found_method:
                            return True
            return False

        keys = list(self._Kwargs.__annotations__.keys())
        unordered_kwargs = [kwarg for kwarg in kwargs.keys() if kwarg not in keys]
        ordered_keys = unordered_kwargs + keys
        for key in ordered_keys:
            arg = kwargs.get(key, None)
            if arg is None:
                continue

            find_and_call_kwarg_method(self, key, arg)

    def _get_parameter(self, parameter_name: str, parameter_type: PARAMETER_TYPES, object_name: str = None) -> Any:
        return get_parameter(self._simulation.__getattribute__("_lumapi"), parameter_name, parameter_type, self.name)

    def _set_parameter(self, parameter_name: str, value: Any, parameter_type: PARAMETER_TYPES,
                       object_name: str = None) -> Any:
        return set_parameter(self._simulation.__getattribute__("_lumapi"), parameter_name, value,
                             parameter_type, self.name)

    def _get_relative_scope(self) -> str:
        """
        Determines the relative scope of the current object within an FDTD simulation, returning a string
        representing the object's position in the simulation's hierarchy from the perspective of the global
        scope.

        The function builds the absolute scope path of the object by traversing its hierarchy, from the
        object itself up through any parent groups until reaching the top-level group. This scope path is
        then adjusted relative to the simulation's global scope, providing a concise relative representation.

        Returns:
        --------
        str
            A string representing the relative scope of the object within the FDTD simulation hierarchy,
            scoped from the current simulation context. This scope reflects the object’s position relative
            to the global scope.
        """

        def get_absolute_scope(simulation_object: TSimulationObject) -> str:
            def get_hierarchy(current_object: TSimulationObject, current_object_scope: str) -> str:

                current_object_scope = "::" + current_object._name + current_object_scope
                if current_object._group is None:
                    if current_object_scope.startswith("::"):
                        current_object_scope = current_object_scope[2:]
                    return current_object_scope
                else:
                    return get_hierarchy(current_object._group, current_object_scope)

            absolute_scope = get_hierarchy(simulation_object, "")

            return absolute_scope

        global_scope = self._simulation.__getattribute__("_lumapi").groupscope()
        if "::" in global_scope:
            global_scope = global_scope.rsplit("::", 1)[1]

        scope = "::model::" + get_absolute_scope(self)
        scope = scope.rsplit(f"{global_scope}::", 1)[1]

        return scope

    @property
    def name(self) -> str:
        return self._get_relative_scope()

    @property
    def group(self) -> TGroup:
        return self._group

    @property
    def enabled(self) -> bool:
        if self._group is None:
            return self._get_parameter("enabled", "bool")
        else:
            return self._group.enabled

    @enabled.setter
    def enabled(self, true_or_false: bool) -> None:
        self.set_enabled(true_or_false)

    def set_enabled(self, true_or_false: bool) -> None:
        """
        Sets the enabled state of the simulation object within the FDTD simulation environment.

        This function modifies the simulation object's "enabled" parameter, determining whether the
        object is active in the simulation. When `enabled` is set to `True`, the object participates
        in the simulation; when `False`, it is ignored during the simulation run. This is useful for
        enabling or disabling specific components without needing to remove them from the simulation.

        Parameters:
        -----------
        true_or_false : bool
            A boolean value indicating the desired enabled state of the simulation object:
            - `True` to enable the object.
            - `False` to disable the object.

        Example:
        --------
        To enable the object:
            `simulation_object.set_enabled(True)`

        To disable the object:
            `simulation_object.set_enabled(False)`
        """
        self._set_parameter("enabled", true_or_false, "bool")


class RotateableSimulationObject(SimulationObject, MinMaxBoundingBoxProperties, ABC):
    class _SettingsCollection(SimulationObject._SettingsCollection):
        rotations: Rotation
        __slots__ = SimulationObject._SettingsCollection.__slots__

    settings: _SettingsCollection
    __slots__ = SimulationObject.__slots__

    @abstractmethod
    def _get_corners(self) -> List[np.ndarray]:
        """
        Calculates and returns the positions of all corners of a structure in 3D space,
        sorted by specific ordering criteria.

        The method computes the coordinates for each corner of the structure and returns them
        as a list of numpy arrays in the format `(x, y, z)`. The ordering of the corners follows a
        deterministic rule:
        1. Corners are sorted by the z-coordinate in ascending order, with those at the lowest
           z-coordinate appearing first.
        2. For corners with the same z-coordinate, the ordering proceeds counterclockwise around
           the z-axis, starting from the positive x-axis direction.

        Returns:
        --------
        List[np.ndarray]
            A list of tuples representing the 3D coordinates of the structure's corners, ordered
            by the lowest z-coordinate and counterclockwise positioning around the z-axis for
            corners at the same z-level.
        """
        ...

    def _get_bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the bounding box of the object based on its corner positions, including any rotations
        specified by the object's rotation parameters.

        This method first retrieves the corner positions using `_get_corners` and applies a series of
        rotations as defined by the object's rotation parameters on the x, y, and z axes. Once rotated,
        the bounding box is calculated by finding the minimum and maximum coordinates along each axis,
        returning these as the bounding box's corner coordinates.

        Returns:
        --------
        tuple[np.ndarray, np.ndarray]
            A tuple containing two numpy arrays:
            - `min_coords`: A 1D array of shape (3,) representing the minimum x, y, and z coordinates
              of the bounding box after applying rotations.
            - `max_coords`: A 1D array of shape (3,) representing the maximum x, y, and z coordinates
              of the bounding box after applying rotations.

        Function Process:
        -----------------
        1. Retrieve the corner coordinates using `_get_corners`.
        2. Determine rotation axes and angles:
           - Define axes as unit vectors based on parameters `"first axis"`, `"second axis"`, and
             `"third axis"`.
           - Retrieve corresponding rotation angles.
        3. Apply each rotation in sequence:
           - Start with an initial rotation of 0 degrees.
           - For each specified axis and angle, compute the rotation and apply it to all corner points.
        4. Calculate the bounding box by taking the minimum and maximum coordinates along each axis.
        """
        rotated_corners = self._get_corners()
        axis_to_array = {"x": np.array([1, 0, 0]), "y": np.array([0, 1, 0]), "z": np.array([0, 0, 1]), "none": None}
        axes = [axis_to_array[self._get_parameter(f"{nr} axis", "str")]
                for nr in ["first", "second", "third"]]
        angles = [self._get_parameter(f"rotation {i + 1}", "float") for i in range(3)]

        # Initial 0 degree rotation
        rotation = R.from_rotvec(0 * axis_to_array["x"])
        rotated_corners = rotation.apply(rotated_corners)

        for axis, angle in zip(axes, angles):
            if not isinstance(axis, np.ndarray):
                continue
            rotation = R.from_rotvec(np.radians(angle) * axis)
            rotated_corners = rotation.apply(rotated_corners)

        min_coords = rotated_corners.min(axis=0)
        max_coords = rotated_corners.max(axis=0)
        return min_coords, max_coords


########################################################################################################################
#                                                 MESH BASE CLASS
########################################################################################################################
class MeshBase(SimulationObject, ABC):
    @dataclass
    class _Settings(Settings):
        general_settings: Settings
        geometry_settings: BaseGeometrySettings

    _structure: Optional[TStructure]
    __slots__ = SimulationObject.__slots__ + ["_structure"]

    @property
    @abstractmethod
    def based_on_structure(self) -> Optional[TStructure]:
        ...

    @based_on_structure.setter
    @abstractmethod
    def based_on_structure(self, structure: Optional[TStructure]) -> None:
        ...


########################################################################################################################
#                                                 STRUCTURE BASE CLASS
########################################################################################################################
class Structure(RotateableSimulationObject, ABC):
    class _SettingsCollection(RotateableSimulationObject._SettingsCollection):
        material: MaterialSettingsBase
        __slots__ = RotateableSimulationObject._SettingsCollection.__slots__

    class _Kwargs(RelPositionKwargs, total=False):
        material: MATERIALS
        index: Optional[Union[str, float]]

    @dataclass
    class _Settings(StructureSettings):
        ...

    _bulk_mesh: Optional[MeshBase]
    settings: _SettingsCollection
    __slots__ = RotateableSimulationObject.__slots__ + ["_bulk_mesh"]

    def place_on_top_of(self, obj: TSimulationObject, offset: float = 0) -> None:
        """
        Places the current structure directly on top of another structure.

        This method adjusts the z-coordinate of the current structure such that its `z_min`
        aligns with the `z_max` of the specified `structure`. An optional `offset` can be
        applied to introduce additional spacing between the two structures.

        Args:
            obj (TStructure): The structure on top of which the current structure
                                    will be placed.
            offset (float, optional): Additional spacing to apply between the two structures
                                      along the z-axis. Defaults to 0.

        Raises:
            AttributeError: If the provided `structure` does not have a `z_max` property.

        Behavior:
            - Calculates the `z_min` position of the current structure based on the `z_max`
              of the provided `structure`.
            - Updates the z-coordinate of the current structure such that it sits on top of
              the provided `structure`, with the specified `offset` applied.
            - The x and y coordinates of the current structure remain unchanged.

        Example:
            If `structure` has a `z_max` of 100, and the current structure has a `z_span`
            (z_max - z_min) of 20, calling:
                `place_on_top_of(structure, offset=5)`
            will position the current structure such that its `z_min` is at 105 (100 + 5),
            and its `z_max` is at 125.
        """
        self.z = obj.z_max + ((self.z_max - self.z_min) / 2) + offset

    def place_next_to(self, obj: TSimulationObject,
                      boundary: Literal["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"],
                      offset: float = 0) -> None:
        """
        Places the current structure adjacent to the specified boundary of another simulation object.

        This method adjusts the position of the current structure such that its designated boundary
        (e.g., x_min, x_max, etc.) is placed adjacent to the specified boundary of the given simulation
        object (`obj`). The `offset` argument can be used to introduce additional spacing between the
        two objects. The coordinates along the axes not specified in the `boundary` argument will remain
        unchanged.

        Args:
            obj (TSimulationObject): The simulation object to position this structure next to.
            boundary (Literal["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]):
                The boundary of the current structure to align with the corresponding boundary of
                the target object (`obj`). For example:
                    - "x_min": Align this structure's minimum x-boundary.
                    - "x_max": Align this structure's maximum x-boundary.
                    - Similar behavior for "y_min", "y_max", "z_min", "z_max".
            offset (Optional[float]):
                            The additional distance to place between the two objects along the
                            specified axis. Positive values increase the spacing, while negative
                            values overlap the objects. Default value is zero.

        Raises:
            ValueError: If the provided `boundary` is not a valid boundary literal.

        Behavior:
            - Determines the position of the specified `boundary` of the target object (`obj`).
            - Calculates the new position of the current structure based on its span along the
              specified axis and the given offset.
            - Updates the position of the current structure to ensure it is adjacent to the
              target object's boundary, without altering its coordinates on the other axes.

        Example:
            If `obj` is positioned such that its `x_max` is at 100, and the current structure's
            `x_span` is 20, calling this method with:
                `place_next_to(obj, "x_max", offset=5)`
            will place the current structure such that its `x_min` is at 105 (100 + 5).
            The `y` and `z` coordinates of the current structure will remain unchanged.
        """

        Validate.in_literal(boundary, "boundary", Literal["x_min", "x_max", "y_min", "y_max", "z_min", "z_max"])
        axis = boundary[0]
        min_ = -1 if boundary[2:] == "min" else 1

        obj_extreme = obj.__getattribute__(boundary)
        new_position = obj_extreme + (min_ * self.__getattribute__(f"{axis}_span") / 2) + offset
        self.__setattr__(f"{axis}", new_position)

    @property
    def bulk_mesh(self) -> Optional[MeshBase]:
        return self._bulk_mesh

    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.geometry_settings = self.settings.geometry.__getattribute__("_get_active_parameters")()
        settings.material_settings = self.settings.material.__getattribute__("_get_active_parameters")()
        settings.rotation_settings = self.settings.rotations.__getattribute__("_get_active_parameters")()
        settings.fill_hash_fields()
        return settings


########################################################################################################################
#                                                 GROUP BASE CLASS
########################################################################################################################
class Group(SimulationObject, ABC):
    class _Kwargs(RelPositionKwargs, total=False):
        pass

    geometry: RelativeBaseGeometry
    _grouped_objects: List[SimulationObject]

    __slots__ = SimulationObject.__slots__ + ["_grouped_objects"]

    def __init__(self, name: str, simulation: TSimulation, **kwargs: Unpack[Group._Kwargs]) -> None:

        kwargs = dict(**kwargs)
        for k, v in kwargs.items():
            if k == "use_relative_coordinates" and v is None:
                kwargs["use_relative_coordinates"] = False
            elif v is None:
                kwargs[k] = 0

        super().__init__(name, simulation, **kwargs)
        self._grouped_objects = []

    # def _get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
    #
    #     params = {**{f"min_{axis}": float('inf') for axis in ["x", "y", "z"]},
    #               **{f"max_{axis}": -float('inf') for axis in ["x", "y", "z"]}}
    #
    #     for obj in self._grouped_objects:
    #         for axis in ["x", "y", "z"]:
    #             min_ = getattr(obj, f"{axis}_min")
    #             if min_ < params[f"min_{axis}"]:
    #                 params[f"min_axis"] = min_
    #             max_ = getattr(obj, f"{axis}_max")
    #             if max_ > params[f"max_{axis}"]:
    #                 params[f"max_{axis}"] = max_
    #
    #     min_ = np.array([params["min_x"], params["min_y"], params["min_z"]])
    #     max_ = np.array([params["max_x"], params["max_y"], params["max_z"]])
    #
    #     return min_, max_
    #
    # def _get_min_max(self, axis: Literal["x", "y", "z"], min_max: Literal["min", "max"]) -> float:
    #     min_max_map = {"min": 0, "max": 1}
    #     axis_map = {"x": 0, "y": 1, "z": 2}
    #     value = float(self._get_bounding_box()[min_max_map[min_max]][axis_map[axis]])
    #     return value

    def add(self, simulation_object: TSimulationObject, use_relative_coordinates: bool = None) -> None:

        if getattr(simulation_object, "_group", None):
            raise ValueError(f"The simulation object with name '{simulation_object.name}' is already assigned "
                             f"to a group and can therefore not be assigned to the group '{self.name}'.")

        self._simulation.__getattribute__("_lumapi").select(simulation_object.name)
        if use_relative_coordinates is not None:
            self._simulation.__getattribute__("_lumapi").set("use relative coordinates", use_relative_coordinates)
        self._simulation.__getattribute__("_lumapi").addtogroup(self.name)
        self._grouped_objects.append(simulation_object)
        setattr(simulation_object, "_group", self)


########################################################################################################################
#                                                GEOMETRY BASE CLASS
########################################################################################################################
class BaseGeometry(SettingTab, ABC):
    class _SetPositionKwargs(PositionKwargs, total=False):
        units: Optional[LENGTH_UNITS]

    @dataclass
    class _Settings(BaseGeometrySettings):
        ...

    __slots__ = SettingTab.__slots__

    def set_position(self, **kwargs: Unpack[_SetPositionKwargs]) -> None:
        """
        Set the position of the simulation object.

        If the 'units' argument is not provided, it defaults to the simulation's 'global_units' parameter.
        """
        if not kwargs:
            raise ValueError("You must provide arguments for this method.")

        units = kwargs.pop("units", None)
        if units is None:
            units = self._simulation.__getattribute__("_global_units")
        else:
            Validate.in_literal(units, "units", LENGTH_UNITS)

        for axis, value in kwargs.items():
            if value is None:
                continue
            Validate.number(value, axis)
            value = convert_length(value, units, "m")  # type: ignore
            self._set_parameter(axis, value, "float")

    def set_position_cylindrically(self, origin: Union[Tuple[float, float], TSimulationObject],
                                   theta: float, radius: float, z: Optional[float] = None) -> None:
        """
        Sets the new position of the object by cylindrical coordinates with origin in the specified point.

        Parameters:
            origin (Tuple[float, float] | TSimulationObject): Can either be a 2D tuple with the x and y coordinate, or
                a simulation object. If the latter, the object's center coordinate will be used as the origin.
            theta (float): The counterclockwise angle from the positive x-axis in degrees.
            radius (float): The radial displacement from the origin.
            z (Optional[float]): The displacement along the z-axis. If None is provided, it defaults to 0.
        """
        # Extract origin coordinates
        if isinstance(origin, SimulationObject):
            origin_x, origin_y = origin.x, origin.y
        else:
            origin_x, origin_y = origin

        # Convert theta to radians and calculate new position
        theta_rad = np.deg2rad(theta)
        displacement = radius * np.array([np.cos(theta_rad), np.sin(theta_rad)])

        x = float(origin_x + displacement[0])
        y = float(origin_y + displacement[1])
        z = self._parent.z + z if z is not None else None
        self.set_position(x=x, y=y, z=z)

    def set_position_spherically(self, origin: Union[Tuple[float, float, float], TSimulationObject],
                                 radius: float, theta: float, phi: float) -> None:
        """
        Sets the new position of the object by spherical coordinates with origin in the specified point.

        Parameters:
            origin (Tuple[float, float, float] | TSimulationObject): Can either be a 3D tuple with the x, y, and z
                coordinates or a simulation object. If the latter, the object's center coordinate will be used as the
                origin.
            radius (float): The radial distance from the origin.
            theta (float): The counterclockwise angle from the positive x-axis in the xy-plane in degrees.
            phi (float): The angle from the positive z-axis in degrees.
        """

        # Extract origin coordinates
        if isinstance(origin, SimulationObject):
            origin_x, origin_y, origin_z = origin.x, origin.y, origin.z
        else:
            origin_x, origin_y, origin_z = origin

        # Convert theta and phi to radians
        theta_rad = np.deg2rad(theta)
        phi_rad = np.deg2rad(phi)

        # Calculate new position using spherical coordinate formulas
        x_displacement = radius * np.sin(phi_rad) * np.cos(theta_rad)
        y_displacement = radius * np.sin(phi_rad) * np.sin(theta_rad)
        z_displacement = radius * np.cos(phi_rad)

        x = origin_x + x_displacement
        y = origin_y + y_displacement
        z = origin_z + z_displacement
        self.set_position(x=x, y=y, z=z)

    @abstractmethod
    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        settings.position.x = self._get_parameter("x", "float")
        settings.position.y = self._get_parameter("y", "float")
        settings.position.z = self._get_parameter("x", "float")
        settings.fill_hash_fields()
        return settings


class RelativeBaseGeometry(BaseGeometry):
    @dataclass
    class _Settings(BaseGeometrySettings):
        ...

    __slots__ = BaseGeometry.__slots__

    @property
    def use_relative_coordinates(self) -> bool:
        """
        Gets the 'use relative coordinates' parameter in the FDTD simulation.
        """
        ...
        return self._get_parameter("use relative coordinates", "bool")

    @use_relative_coordinates.setter
    def use_relative_coordinates(self, true_or_false: bool) -> None:
        """
        Sets the 'use relative coordinates' parameter in the FDTD simulation.

        Parameters:
        -----------
        true_or_false : bool
            If True, the object's 'use relative coordinates' parameter is enabled, else it's disabled.
        """
        self._set_parameter("use relative coordinates", true_or_false, "bool")

    @abstractmethod
    def _get_active_parameters(self) -> _Settings:

        settings = super()._get_active_parameters()
        settings.hash = None

        def get_absolute_coordinates(sim_object: TSimulationObject, pos: Position) -> Position:
            if sim_object.settings.geometry.use_relative_coordinates and sim_object.group is not None:
                pos = get_absolute_coordinates(sim_object.group, pos)
                pos.x += sim_object.group.__getattribute__("_get_parameter")("x", "float")
                pos.y += sim_object.group.__getattribute__("_get_parameter")("y", "float")
                pos.z += sim_object.group.__getattribute__("_get_parameter")("z", "float")
            return pos

        lpi = self._simulation.__getattribute__("_lumapi")

        # Fetch the current scope, store it, and set the scope to global
        current_groupscope = lpi.groupscope()
        lpi.groupscope("::model")

        # Alter the position recursively basen on parent groups
        settings.position = get_absolute_coordinates(self._parent, settings.position)
        settings.fill_hash_fields()

        # Reset scope
        lpi.groupscope(current_groupscope)

        return settings


########################################################################################################################
#                                              ROTATION SETTING BASE CLASS
########################################################################################################################
class Rotation(SettingTab):
    @dataclass
    class _Settings(Settings):
        axis: np.ndarray
        angle: float
        first_axis: str
        rotation_1: float
        second_axis: str
        rotation_2: float
        third_axis: str
        rotation_3: float

    _parent: Structure
    __slots__ = SettingTab.__slots__

    def set_first_axis(self, axis: AXES) -> None:
        """Set the first rotation axis.

        Args:
            axis (x, y, or z): The axis for the first rotation.
        """
        self._set_parameter("first axis", axis, "str")

    def set_second_axis(self, axis: AXES) -> None:
        """Set the second rotation axis.

        Args:
            axis (x, y, or z): The axis for the second rotation.
        """
        self._set_parameter("second axis", axis, "str")

    def set_third_axis(self, axis: AXES) -> None:
        """Set the third rotation axis.

        Args:
            axis (x, y, or z): The axis for the third rotation.
        """
        self._set_parameter("third axis", axis, "str")

    def set_first_axis_rotation(self, rotation_degrees: float) -> None:
        """Set the counter-clockwise rotation angle for the first axis.

        Args:
            rotation_degrees (float): The rotation angle in degrees for the first axis.
        """
        self._set_parameter("rotation 1", rotation_degrees, "float")

    def set_second_axis_rotation(self, rotation_degrees: float) -> None:
        """Set the counter-clockwise rotation angle for the second axis.

        Args:
            rotation_degrees (float): The rotation angle in degrees for the second axis.
        """
        self._set_parameter("rotation 2", rotation_degrees, "float")

    def set_third_axis_rotation(self, rotation_degrees: float) -> None:
        """Set the counter-clockwise rotation angle for the third axis.

        Args:
            rotation_degrees (float): The rotation angle in degrees for the third axis.
        """
        self._set_parameter("rotation 3", rotation_degrees, "float")
    
    def is_rotated(self) -> bool:
        first_rotation = self._get_parameter("rotation 1", "float") % 360
        second_rotation = self._get_parameter("rotation 2", "float") % 360
        third_rotation = self._get_parameter("rotation 3", "float") % 360
        if all([rotation == 0 for rotation in [first_rotation, second_rotation, third_rotation]]):
            return False
        return True
        
    def _get_active_parameters(self) -> _Settings:
        settings = self._Settings.initialize_empty()
        
        first_axis = self._get_parameter("first axis", "str")
        first_rotation = self._get_parameter("rotation 1", "float")
        second_axis = self._get_parameter("second axis", "str")
        second_rotation = self._get_parameter("rotation 2", "float")
        third_axis = self._get_parameter("third axis", "str")
        third_rotation = self._get_parameter("rotation 3", "float")

        if first_rotation != "none" and first_rotation != 0:
            settings.first_axis = first_axis
            settings.rotation_1 = first_rotation
        if second_rotation != "none" and second_rotation != 0:
            settings.second_axis = second_axis
            settings.rotation_2 = second_rotation
        if third_rotation != "none" and third_rotation != 0:
            settings.third_axis = third_axis
            settings.rotation_3 = third_rotation

        axis, angle = euler_to_axis_angle(first_axis, second_axis, third_axis,
                                          first_rotation, second_rotation, third_rotation)
        settings.axis = axis
        settings.angle = angle
        settings.fill_hash_fields()
        return settings


########################################################################################################################
#                                         SIMULATION BASE CLASS
########################################################################################################################

class SimulationBase(ABC):
    class _Kwargs(TypedDict, total=False):
        hide: bool

    class _ActiveObjects(Settings):
        structures: List[TStructure]
        monitors: List[TSimulationObject]
        sources: List[TSimulationObject]
        meshes: List[MeshBase]
        # layout_groups: List[LayoutGroup]
        # structure_groups: List[StructureGroupInterface]
        # analysis_groups: List[GroupInterface]
        used_names: List[str] = []

    _active_objects: _ActiveObjects
    _type_to_class_map: ClassVar[Dict[str, Type[SimulationObject]]]
    _material_database: TMaterialDatabase
    _global_units: LENGTH_UNITS
    _lumapi: lumapi.FDTD
    _save_path: str

    @abstractmethod
    def save(self, open_explorer: bool = False, save_path: str = None) -> None:
        ...

    def _get_parameter(self, object_name: str, parameter_name: str, parameter_type: PARAMETER_TYPES) -> Any:
        return get_parameter(self._lumapi, parameter_name, parameter_type, object_name)

    def _get_results(self, object_name: str, result_name: str, result_type: PARAMETER_TYPES) -> Any:
        return get_parameter(self._lumapi, result_name, result_type, object_name,
                             getter_function=self._lumapi.getresult)

    def _set_parameter(self, object_name: str, parameter_name: str, value: Any, parameter_type: PARAMETER_TYPES) -> Any:
        return set_parameter(self._lumapi, parameter_name, value, parameter_type, object_name)


########################################################################################################################
#                                         MATERIAL RELATED ABSTRACT CLASSES
########################################################################################################################
class MaterialSettingsBase(SettingTab, ABC):

    def set_material(self, material: MATERIALS = None, index: Optional[Union[float, str]] = None) -> None:
        """
        Set the material of the object, validating the selection against available materials.

        The index can be specified as:
            - Isotropic: A single float > 1
            - Anisotropic: A semicolon-separated string of three float values for xx, yy,
                           and zz indices, e.g., "1;1.5;1"
            - Spatially Varying: A spatial equation in terms of x, y, and z, e.g., "2+0.1*x"

        Args:
            material (MATERIALS): The material to assign to the object, validated from a predefined list.
            index (float or str, optional): The refractive index for "<Object defined dielectric>".
                Must be a float > 1 for isotropic, a semicolon-separated string for anisotropic,
                or an equation for spatially varying index.

        Raises:
            ValueError: If the index is invalid for the selected material type.
        """

        if material is None and index is None:
            return
        elif material is None:
            material = self._get_parameter("material", "str")
        else:
            self._set_parameter("material", material, "str")

        # Check for required index when using "<Object defined dielectric>"
        if material == "<Object defined dielectric>" and index is not None:

            # Validate isotropic index
            if isinstance(index, float):
                if index <= 1:
                    raise ValueError("Isotropic index must be a float greater than or equal to one.")
                self._set_parameter("index", str(index), "str")

            # Validate anisotropic index (semicolon-separated values)
            elif isinstance(index, str) and ';' in index:
                components = index.split(';')
                if len(components) != 3 or not all(float(comp) > 0 for comp in components):
                    raise ValueError(
                        "Anisotropic index must contain three positive float values separated by semicolons.")
                self._set_parameter("index", str(index), "str")

            # Validate spatially varying index (equation)
            else:
                # Additional checks can be implemented here if a specific format is required for equations.
                self._set_parameter("index", str(index), "str")

        elif index is not None:
            # If the material is not "<Object defined dielectric>", ignore the index value and warn the user
            warn("Warning: 'index' parameter is only applicable for '<Object defined dielectric>'. "
                 "Ignoring the provided index.")

    def set_index(self, index: float, index_units: INDEX_UNITS = "m") -> None:
        """
        Set the refractive index for the material when the material type is "<Object defined dielectric>".

        For structures with material type "<Object defined dielectric>", this method assigns a refractive index.
        The index can be a single float value greater than 1 or a spatially varying equation using x, y, z variables
        (e.g., "2 + 0.1 * x"). When specifying an equation, `index_units` is used to define the units for x, y, z.

        Args:
            index (Union[float, str]): The refractive index of the structure. Must be either:
                - A float greater than 1 for isotropic materials, or
                - A string representing a spatial equation (e.g., "2 + 0.1 * x") for spatially varying indices.
            index_units (INDEX_UNITS, optional): Units for x, y, z variables when `index` is an equation. Default is
                "m" (meters).

        Raises:
            ValueError: If the material is not set to "<Object defined dielectric>".
            ValueError: If a numeric `index` value is not greater than 1.
        """

        if index is None:
            return

        # Retrieve and verify material type
        material = self._get_parameter("material", "str")
        if material != "<Object defined dielectric>":
            raise ValueError(
                f"Structure name: '{self._parent.name}'.\n"
                "The index can only be set when the material is '<Object defined dielectric>', "
                f"not '{material}'."
            )

        # Validate the type and value of the index
        if isinstance(index, float):
            if index <= 1:
                raise ValueError("Index must be greater than or equals 1 for '<Object defined dielectric>' "
                                 "material type.")
        elif isinstance(index, str):
            # Ensure valid spatial equation format
            if not any(var in index for var in ('x', 'y', 'z')):
                raise ValueError(
                    "Index equation must contain spatial variables x, y, or z for spatially varying indices."
                )
        else:
            raise TypeError("Index must be either a float or a spatial equation string.")

        # Validate index_units
        Validate.in_literal(index_units, "index_units", INDEX_UNITS)

        # Set parameters
        self._set_parameter("index", index, "float" if isinstance(index, float) else "str")
        self._set_parameter("index units", index_units, "str")

    def override_mesh_order_from_material_database(self, override: bool, mesh_order: int = None) -> None:
        """
        Overrides the mesh order setting from the material database and allows manual setting of a mesh order.

        When `override` is set to True, the `mesh_order` parameter can be specified to determine priority
        during material overlap in the simulation engine. Higher-priority materials (lower mesh order values)
        will override lower-priority materials in overlap regions.

        Args:
            override (bool): If True, enables manual mesh order setting; otherwise, uses the database's mesh order.
            mesh_order (int, optional): Mesh order to assign if overriding the database setting. Only allowed if `override` is True.

        Raises:
            ValueError: If `override` is False and `mesh_order` is provided.
            ValueError: If `mesh_order` is set but does not fall within an acceptable range (e.g., >= 1).
        """

        # Set the override parameter
        self._set_parameter("override mesh order from material database", override, "bool")

        # Validate and set mesh order if overriding is enabled
        if not override:
            if mesh_order is not None:
                raise ValueError("Cannot set 'mesh_order' when 'override' is False.")
        else:
            if mesh_order is not None:
                if mesh_order < 1:
                    raise ValueError("Mesh order must be 1 or higher when overriding the database.")
                Validate.integer(mesh_order, "mesh_order")
                self._set_parameter("mesh order", mesh_order, "int")

    def set_grid_attribute_name(self, name: str) -> None:
        """
        Sets the name of the grid attribute that applies to this object.

        The grid attribute name is used to identify specific grid configurations
        relevant to the object's simulation. It is relevant when creating anisotropic optical materials.

        Args:
            name (str): The grid attribute name for this object.

        Raises:
            ValueError: If `name` is an empty string or only whitespace.
        """

        # Validate that the name is a non-empty string
        if not name.strip():
            raise ValueError("Grid attribute name cannot be empty or only whitespace.")

        # Set the grid attribute name
        self._set_parameter("grid attribute name", name, "str")


class MaterialBase(ABC):
    @dataclass
    class AdvancedParameters(MaterialAdvancedParameters):
        ...

    @dataclass
    class CommonParameters(MaterialCommonParameters):
        ...

    @dataclass
    class SpecificParameters(Settings):
        type: str

    @dataclass
    class Settings(Settings):
        name: str
        common_parameters: MaterialBase.CommonParameters
        specific_parameters: MaterialBase.SpecificParameters
        advanced_parameters: MaterialBase.AdvancedParameters

    material_database: MaterialDatabaseBase
    name: str
    __slots__ = ["name", "material_database"]

    def __init__(self, name: str, material_database: TMaterialDatabase) -> None:
        self.name = name
        self.material_database = material_database

    def get_parameter(self, parameter_name: str, parameter_type: PARAMETER_TYPES) -> Any:
        return self.material_database.__getattribute__("_get_parameter")(self.name, parameter_name, parameter_type)

    def set_parameter(self, parameter_name: str, value: Any, parameter_type: PARAMETER_TYPES) -> None:
        self.material_database.__getattribute__("_set_parameter")(self.name, parameter_name, value, parameter_type)

    def get_common_parameters(self) -> CommonParameters:
        settings = self.CommonParameters.initialize_empty()
        settings.anisotropy = self.get_parameter("anisotropy", "str")
        settings.mesh_order = self.get_parameter("mesh order", "int")
        settings.fill_hash_fields()
        return settings

    def get_advanced_parameters(self) -> AdvancedParameters:
        settings = self.AdvancedParameters.initialize_empty()
        settings.__getattribute__("_update")({
            "hash": None,
            "tolerance": self.get_parameter("tolerance", "float"),
            "max_coefficients": self.get_parameter("max coefficients", "int"),
            "make_fit_passive": self.get_parameter("make fit passive", "bool"),
            "improve_numerical_stability": self.get_parameter("improve numerical stability", "bool"),
            "imaginary_weight": self.get_parameter("imaginary weight", "float"),
            "wavelength_min": self.get_parameter("wavelength min", "float"),
            "wavelength_max": self.get_parameter("wavelength max", "float"),
            "frequency_min": self.get_parameter("frequency min", "float"),
            "frequency_max": self.get_parameter("frequency max", "float")})
        settings.fill_hash_fields()
        return settings

    @abstractmethod
    def get_material_parameters(self) -> Settings:
        ...

    @abstractmethod
    def get_base_material(self) -> Settings:
        ...


class MaterialDatabaseBase(GlobalSettingTab):

    def _set_parameter(self, material_name: str, parameter_name: str, value: Any,
                       parameter_type: PARAMETER_TYPES = None) -> Any:
        if parameter_type is None:
            raise ValueError("You must provide the expected 'parameter_type'. Got 'None'")

        lpi = self._simulation.__getattribute__("_lumapi")
        set_parameter(lpi, parameter_name, value, parameter_type, object_name=material_name,
                      getter_function=lpi.getmaterial, setter_function=lpi.setmaterial)

    def _get_parameter(self, material_name: str, parameter_name: str, parameter_type: PARAMETER_TYPES = None) -> Any:
        if parameter_type is None:
            raise ValueError("You must provide the expected 'parameter_type'. Got 'None'")

        lpi = self._simulation.__getattribute__("_lumapi")
        return get_parameter(lpi, parameter_name, parameter_type, object_name=material_name,
                             getter_function=lpi.getmaterial)

    @abstractmethod
    def get_material_parameters(self, material_name: str) -> TMaterial.SettingsDict:
        ...
