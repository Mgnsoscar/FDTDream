from __future__ import annotations
from dataclasses import dataclass
from numpy.typing import NDArray
import itertools
import numpy as np
from typing import Self, Literal, List, Tuple, cast, TypedDict, Unpack, Union, Any, get_args
from abc import ABC, abstractmethod
from matplotlib import pyplot as plt
import trimesh
from ..resources import validation
from ..resources.functions import convert_length
from scipy.constants import c
from ..resources import errors
from ..resources.literals import LENGTH_UNITS
import shapely
from ..results.plotted_structure import PlottedStructure

PLANE_NORMALS = Literal["x-normal", "y-normal", "z-normal"]
RESULTS = Literal["power", "T", "E", "H", "P"]
LINESTYLES = Literal["solid", "dotted", "dashed", "dashdot"]
COMPONENTS = Literal["x", "y", "z", "xy", "xz", "yz", "xyz"]
PLANES = Literal["xy", "xz", "yz"]
FIELDS = Literal["E", "H", "P"]
AXES = Literal["x", "y", "z"]


@dataclass
class SavedSimulation:
    parameters: dict
    category: str
    structures: List[Tuple[str, trimesh.Trimesh]]
    monitor_results: List[FieldAndPower]


@dataclass
class FieldAndPower:
    name: str
    monitor_type: str
    wavelengths: Wavelengths
    x: Union[Coordinates, None]
    y: Union[Coordinates, None]
    z: Union[Coordinates, None]
    power: Union[Result1D, None]
    T: Union[Result1D, None]
    E: Union[Field, None]
    H: Union[Field, None]
    P: Union[Field, None]

    def __init__(self, object_name: str, monitor_type: str, lumapi, available_results: List[str] = None) -> None:

        self.monitor_type = monitor_type

        # Fetch the available results if not passed:
        if available_results is None:
            available_results = lumapi.getresult(object_name).split("\n")

        # Extract wavelengths.
        self.wavelengths = Wavelengths._extract(object_name, lumapi)

        # Extract power and T data if any.
        if "T" in available_results:

            t_data = lumapi.getresult(object_name, "T")
            t_data = t_data["T"].flatten()[::-1].astype(np.float16)
            self.T = Result1D(t_data, self)

            power_data = lumapi.getresult(object_name, "power")
            power_data = power_data.flatten()[::-1]
            self.power = Result1D(power_data, self)

        else:
            self.T = None
            self.power = None

        # Check if any field data is available
        fields = ["E", "H", "P"]
        has_field_data = any(f in available_results for f in fields)

        # Extract coordinates if field data is present
        if has_field_data:
            self.x = Coordinates._extract(object_name, "x", lumapi)
            self.y = Coordinates._extract(object_name, "y", lumapi)
            self.z = Coordinates._extract(object_name, "z", lumapi)
        else:
            self.x = self.y = self.z = None

        # Extract each field or set to None
        for field in fields:
            setattr(self, field,
                    Field._extract(object_name, field, self, lumapi) if field in available_results else None)

    def has_plane(self, plane: PLANES) -> bool:
        """Given a plane, returns if the monitor has data in that plane that can be plotted."""

        for axis in plane:
            if not getattr(self, axis).shape[0] > 1:
                return False
        return True

    def get_planes(self) -> List[PLANES]:
        """Return a list of planes that the monitor can plot data in."""
        planes = []
        for plane in get_args(PLANES):
            if self.has_plane(plane):
                planes.append(plane)
        return planes

    def get_fields(self) -> List[FIELDS]:
        """Returns a list of plottable fields."""
        fields = []
        for field in get_args(FIELDS):
            if getattr(self, field) is not None:
                fields.append(field)
        return fields

    def get_field_components(self, field: FIELDS) -> List[COMPONENTS]:
        """Given a field, retrieve the available field components (and their combinations)."""

        # Fetch the field.
        field: Field = getattr(self, field)

        if field is None:
            return []

        components = []
        for component in get_args(AXES):
            if getattr(field, "_has_" + component):
                components.append(component)

        # Get all combinations
        combinations = []
        for r in range(1, len(components) + 1):
            for combo in itertools.combinations(components, r):
                # For combinations of length 2, join as 'xy', 'xz', etc.
                if len(combo) != 1:
                    combinations.append(''.join(combo))
                else:
                    # For single components, just add them as they are
                    combinations.append(combo[0])

        return combinations

    def wavelength_to_idx(self, wavelength: float, units: LENGTH_UNITS = "nm") -> int:
        return np.argmin(np.abs(self.wavelengths.as_units(units) - wavelength))

    def idx_to_wavelength(self, wavelength_idx: int, units: LENGTH_UNITS = "nm") -> float:
        return float(self.wavelengths.as_units(units)[wavelength_idx])

    def has_result(self, result: RESULTS) -> bool:
        """Given a result type, returns True if the monitor has results for that type."""
        return getattr(self, result) is not None

    @classmethod
    def _extract_results(cls, object_name: str, monitor_type: str, lumapi) -> Union[Self, None]:

        # Get the list of available results
        available_results = lumapi.getresult(object_name).split("\n")

        # Check if any of the data we're interested in is available. Return None if there is no data.
        interesting_data = ["power", "T", "E", "H", "P"]
        if not any([data in available_results for data in interesting_data]):
            return None
        else:
            return cls(object_name, monitor_type, lumapi)

    @staticmethod
    def _generate_meshgrid(coord1: Coordinates, coord2: Coordinates) -> Tuple[NDArray, NDArray]:
        """
        Helper method to generate a meshgrid for any two coordinates.

        Args:
            coord1 (Coordinates): The first coordinate array (e.g., x or y).
            coord2 (Coordinates): The second coordinate array (e.g., y or z).

        Returns:
            tuple: The meshgrid arrays (X, Y).
        """
        X, Y = np.meshgrid(coord1, coord2, indexing="ij")
        return X, Y

    def _get_xy_mesh(self) -> Tuple[NDArray, NDArray]:
        """Returns the mesh grid in the xy plane."""
        return self._generate_meshgrid(self.x, self.y)

    def get_empty_quadmesh(self, ax: plt.Axes, plane: Literal["xy", "xz", "yz"]) -> Tuple[plt.QuadMesh, plt.Colorbar]:
        """Returns a QuadMesh with coordinates and a dummy value array, and also a colorbar."""

        # Get mesh grid coordinates for the specified plane (xy, xz, yz)
        X, Y = getattr(self, f"_get_{plane}_mesh")()

        # Create a QuadMesh object with zero data initially (you can change cmap or data as needed)
        mesh = ax.pcolormesh(X, Y, np.zeros_like(X), cmap="viridis")

        # Create the colorbar and associate it with the mesh
        cbar = plt.colorbar(mesh, ax=ax)

        return mesh, cbar

    def get_empty_quiver_plot(self, ax: plt.Axes, plane: Literal["xy", "xz", "yz"]) -> plt.Quiver:

        # Get mesh grid coordinates for the specified plane (xy, xz, yz)
        X, Y = getattr(self, f"_get_{plane}_mesh")()

        dummy_U = np.zeros_like(X)
        dummy_V = np.zeros_like(Y)

        # Initialize the quiver plot with dummy data
        quiver = ax.quiver(X, Y, dummy_U, dummy_V)

        return quiver

    def _get_xz_mesh(self) -> Tuple[NDArray, NDArray]:
        """Returns the mesh grid in the xz plane."""
        return self._generate_meshgrid(self.x, self.z)

    def _get_yz_mesh(self) -> Tuple[NDArray, NDArray]:
        """Returns the mesh grid in the yz plane."""
        return self._generate_meshgrid(self.y, self.z)


class Result1D(np.ndarray):
    _parent_monitor: FieldAndPower

    def __new__(cls, data: NDArray, parent_monitor: FieldAndPower) -> Result1D:
        # Convert input to ndarray, then view it as Wavelengths
        obj = np.asarray(data).view(cls)
        obj._parent_monitor = parent_monitor
        return obj

    def __array_finalize__(self, obj: Any) -> None:
        if obj is None:
            return
        self._parent_monitor = getattr(obj, '_parent_monitor', None)

    def has_results(self) -> bool:
        """Returns true if there is result data."""
        if self.size == 0:
            return False
        return True

    def plot(self, ax: plt.Axes, reference: Result1D = None,
             units: LENGTH_UNITS = "nm") -> Union[plt.Line2D, None]:
        """Takes in a plt.Axes object, plots the data on that plot, and returns the artist."""

        # Do nothing if there are no results to plot.
        if not self.has_results():
            return

        # Normalize the data to the reference if one is provided.
        if reference is not None:
            if np.array_equal(self._parent_monitor.wavelengths, reference._parent_monitor.wavelengths):
                data = self / reference
            else:
                raise ValueError(f"The wavelengths of the reference does not match the wavelengths of the "
                                 f"results you want to normalize.")
        else:
            data = self

        # Fetch correct wavelengths.
        wavelengths = self._parent_monitor.wavelengths.as_units(units)

        # Plot data.
        artist = ax.plot(wavelengths, data)

        return artist[0]


class Field(np.ndarray):
    _components: COMPONENTS
    _parent_monitor: FieldAndPower
    _has_x: bool
    _has_y: bool
    _has_z: bool

    def __new__(cls, data: NDArray, components: COMPONENTS, parent_monitor: FieldAndPower) -> Field:
        # Convert input to ndarray, then view it as Field
        obj = np.asarray(data).view(cls)
        obj._parent_monitor = parent_monitor
        obj._components = components

        # Set the flags for x, y, z components
        for ax in ["x", "y", "z"]:
            setattr(obj, f"_has_{ax}", False)

        # Fill the map with components and their respective indices
        for comp in components:
            setattr(obj, f"_has_{comp}", True)

        return obj

    def __array_finalize__(self, obj: Any) -> None:
        if obj is None:
            return
        self._parent_monitor = getattr(obj, '_parent_monitor', None)
        self._components = getattr(obj, "_components", None)
        for ax in ["x", "y", "z"]:
            setattr(self, f"_has_{ax}", getattr(obj, f"_has_{ax}", False))

    def __reduce__(self):
        constructor, args, state = super().__reduce__()

        # Convert state to dict if it's not already
        if isinstance(state, dict):
            extended_state = state
        else:
            extended_state = {"_ndarray_state": state}  # wrap original state safely

        # Add your custom attributes
        extended_state.update({
            "_components": self._components,
            "_parent_monitor": self._parent_monitor,
        })

        return constructor, args, extended_state

    def __setstate__(self, state):
        self._components = state.pop("_components", "")
        self._parent_monitor = state.pop("_parent_monitor", None)

        # Restore has_x, has_y, has_z
        for ax in ["x", "y", "z"]:
            setattr(self, f"_has_{ax}", ax in self._components)

        # Restore original ndarray state
        ndarray_state = state.pop("_ndarray_state", None)
        if ndarray_state is not None:
            super().__setstate__(ndarray_state)
        else:
            super().__setstate__(state)

    @property
    def x(self) -> NDArray:
        if self._has_x:
            return self[:, :, :, :, 0]
        else:
            raise ValueError("The monitor has not recorded x-components.")

    @property
    def y(self) -> NDArray:
        if self._has_y:
            return self[:, :, :, :, int(self._has_x)]
        else:
            raise ValueError("The monitor has not recorded y-components.")

    @property
    def z(self) -> NDArray:
        if self._has_z:
            return self[:, :, :, :, int(self._has_x) + int(self._has_y)]
        else:
            raise ValueError("The monitor has not recorded z-components.")

    @property
    def xy(self) -> NDArray:
        if self._has_x and self._has_y:
            return self[:, :, :, :, [0, 1]]
        else:
            if not self._has_x:
                raise ValueError("The monitor has not recorded x-components.")
            else:
                raise ValueError("The monitor has not recorded x-components.")

    @property
    def xy_magnitude(self) -> NDArray:
        if self._has_x and self._has_y:
            return np.linalg.norm(self[:, :, :, :, [0, 1]], axis=-1)
        else:
            if not self._has_x:
                raise ValueError("The monitor has not recorded x-components.")
            else:
                raise ValueError("The monitor has not recorded x-components.")

    @property
    def xz(self) -> NDArray:
        if self._has_x and self._has_z:
            return self[:, :, :, :, [0, int(self._has_y) + 1]]
        else:
            if not self._has_x:
                raise ValueError("The monitor has not recorded x-components.")
            else:
                raise ValueError("The monitor has not recorded z-components.")

    @property
    def xz_magnitude(self) -> NDArray:
        if self._has_x and self._has_z:
            return np.linalg.norm(self[:, :, :, :, [0, int(self._has_y) + 1]], axis=-1)
        else:
            if not self._has_x:
                raise ValueError("The monitor has not recorded x-components.")
            else:
                raise ValueError("The monitor has not recorded z-components.")

    @property
    def yz(self) -> NDArray:
        if self._has_y and self._has_z:
            return self[:, :, :, :, [int(self._has_x), int(self._has_x) + 1]]
        else:
            if not self._has_y:
                raise ValueError("The monitor has not recorded y-components.")
            else:
                raise ValueError("The monitor has not recorded z-components.")

    @property
    def yz_magnitude(self) -> NDArray:
        if self._has_y and self._has_z:
            return np.linalg.norm(self[:, :, :, :, [int(self._has_x), int(self._has_x) + 1]], axis=-1)
        else:
            if not self._has_y:
                raise ValueError("The monitor has not recorded y-components.")
            else:
                raise ValueError("The monitor has not recorded z-components.")

    @property
    def xyz_magnitude(self) -> NDArray:
        if self._has_x and self._has_y and self._has_z:
            return np.linalg.norm(self, axis=-1)
        else:
            if not self._has_x:
                raise ValueError("The monitor has not recorded x-components.")
            if not self._has_y:
                raise ValueError("The monitor has not recorded y-components.")
            else:
                raise ValueError("The monitor has not recorded z-components.")

    @classmethod
    def _extract(cls, object_name: str, field_name: str, parent_monitor: FieldAndPower, lumapi) -> Union[Self, None]:
        # Make sure the field name is capitalized
        print(field_name + "\n")
        field_name = field_name.capitalize()

        # Fetch the field results and make a list of the included components
        results = lumapi.getresult(object_name).split("\n")
        available_fields = set(results)

        # Build components list from expected axes
        axes = ["x", "y", "z"]
        components = [axis for axis in axes if field_name + axis in available_fields]

        # Special handling for P-field
        if field_name == "P" and "P" in available_fields and not components:
            # Get the data
            try:
                data_dict = lumapi.getresult(object_name, 'P')
            except errors.LumApiError as e:
                if "Can not find result 'P' in the result provider" in str(e):
                    return None
                else:
                    raise e

            # Infer components from which E and H fields are present
            e_fields = {axis for axis in axes if "E" + axis in available_fields}
            h_fields = {axis for axis in axes if "H" + axis in available_fields}

            present_axes = sorted(e_fields & h_fields)

            if len(present_axes) == 3:
                component_str = "xyz"
                data = data_dict["P"]
            elif len(present_axes) == 2:
                missing_axis = list(set(axes) - set(present_axes))[0]
                component_str = missing_axis

                data = np.stack([data_dict[field_name + comp] for comp in component_str], axis=-1)

            else:
                # Not enough data to construct P-field
                print("None")
                return None

        else:
            # Turn the components into a string, ie. 'xyz'
            component_str = "".join(components)

            # Extract the result dict for the field.
            data_dict = lumapi.getresult(object_name, field_name)

            # If all components are in a single array
            if field_name in data_dict:
                data = data_dict[field_name]
            else:
                data = np.stack(
                    [data_dict[field_name + axis] for axis in axes if field_name + axis in data_dict],
                    axis=-1
                )

        # Reverse all arrays along the wavelength axis
        try:
            data = data[:, :, :, ::-1, :]
        except Exception as e:
            print(field_name + ": " + str(e))
        return cls(data, component_str, parent_monitor)  # type: ignore


class Coordinates(np.ndarray):
    _base_units: LENGTH_UNITS

    def __new__(cls, data: NDArray, base_units: LENGTH_UNITS) -> Coordinates:
        # Convert input to ndarray, then view it as Wavelengths
        obj = np.asarray(data).view(cls)
        obj._base_units = base_units
        return obj

    def __array_finalize__(self, obj: Any) -> None:
        if obj is None:
            return
        self._base_units = getattr(obj, '_base_units', None)

    def __reduce__(self):
        constructor, args, state = super().__reduce__()
        # Append _base_units to the ndarray's state tuple
        return (constructor, args, (state, self._base_units))

    def __setstate__(self, state):
        ndarray_state, self._base_units = state  # Gives a user warning, but works.
        super().__setstate__(ndarray_state)

    @classmethod
    def _extract(cls, object_name: str, axis: Literal["x", "y", "z"], lumapi) -> Self:

        # Fetch the array of coordinates along the specified axis.
        coordinates = lumapi.getresult(object_name, axis)

        # Convert from meters to nanometers. Allows us to use 32 bit floats in stead of 62 bit floats.
        coordinates = convert_length(coordinates, "m", "nm")

        # If the coordinates is just a single float, convert it to an array.
        if type(coordinates) is float:
            coordinates = np.array([coordinates], dtype=np.float32)

        # If not, flatten the array and convert values to 32 bit floats.
        else:
            coordinates = coordinates.flatten().astype(np.float32)

        return Coordinates(coordinates, "nm")

    def as_units(self, units: LENGTH_UNITS) -> Self:
        """Returns the coordinates in the specified length units."""
        if units == self._base_units:
            return self
        validation.in_literal(units, "units", LENGTH_UNITS)
        data = convert_length(self, self._base_units, units)
        return Coordinates(data, units)


class Wavelengths(np.ndarray):
    _base_units: LENGTH_UNITS

    def __new__(cls, data: NDArray, base_units: LENGTH_UNITS) -> Wavelengths:
        # Convert input to ndarray, then view it as Wavelengths
        obj = np.asarray(data).view(cls)
        obj._base_units = base_units
        return obj

    def __array_finalize__(self, obj: Any) -> None:
        if obj is None:
            return
        self._base_units = getattr(obj, '_base_units', None)

    def __reduce__(self):
        constructor, args, state = super().__reduce__()
        # Append _base_units to the ndarray's state tuple
        return (constructor, args, (state, self._base_units))

    def __setstate__(self, state):
        # `state` is a tuple: (ndarray_state, base_units)
        ndarray_state, self._base_units = state  # Gives a user warning, but works.
        super().__setstate__(ndarray_state)

    @classmethod
    def _extract(cls, object_name: str, lumapi) -> Self:
        # Extract the monitor's frequencies
        frequencies: NDArray = lumapi.getresult(object_name, "f")

        # Convert to wavelengths and reverse so the array is from shortest to longest.
        wavelengths = c / frequencies[::-1]

        # Flatten array and convert to nanometers. Set type to 16 bit float.
        wavelengths = convert_length(wavelengths.flatten(), "m", "nm").astype(np.float32)

        return Wavelengths(wavelengths, "nm")

    def as_units(self, units: LENGTH_UNITS) -> Self:
        """Returns the wavelenghts in the specified length units."""
        if units == self._base_units:
            return self
        validation.in_literal(units, "units", LENGTH_UNITS)
        data = convert_length(self, self._base_units, units)
        return Wavelengths(data, units)
