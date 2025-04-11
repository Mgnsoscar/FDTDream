from __future__ import annotations
from dataclasses import dataclass
from numpy.typing import NDArray
import numpy as np
from typing import Self, Literal, List, Tuple, cast, TypedDict, Unpack
from abc import ABC, abstractmethod
from matplotlib import pyplot as plt
import trimesh
from ..resources import validation
from ..resources.functions import convert_length
from ..resources import errors
from ..resources.literals import LENGTH_UNITS
import shapely
from ..results.plotted_structure import PlottedStructure

PLANE_NORMALS = Literal["x-normal", "y-normal", "z-normal"]

@dataclass
class SavedSimulation:
    parameters: dict
    category: str
    structures: List[Tuple[str, trimesh.Trimesh]]
    monitor_results: List[FieldAndPower]


@dataclass
class ResultBase(ABC):
    """Abstract base class for any dataclass containing results from simulation objects."""

    monitor_name: str
    monitor_type: str

    @classmethod
    @abstractmethod
    def _extract_results(cls, object_name: str, monitor_type: str,
                         lumapi, result_name: str, *args, **kwargs) -> Self:
        """
        Fetches the results from the simulation, and returns the results as a dataclass.

        Args:
            object_name (str): Name of the object results will be fetched from.
            lumapi: The initialized API connected to the simulation.
            result_name (str): Name of the result/field to be extracted.

        Returns:
            Dataclass with the results.
        """

    @abstractmethod
    def has_results(self) -> bool:
        """Returns True if there are valid results to display/plot for this result type. If not, returns False."""
        ...


@dataclass
class FieldAndPower(ResultBase):

    T: T
    E: Field
    H: Field
    P: Field

    def has_results(self) -> bool:
        return any([res.has_results() for res in [self.T, self.E, self.H, self.P]])

    @classmethod
    def _extract_results(cls, object_name: str, lumapi, monitor_type: str, *args) -> Self:

        plane_normal = int(lumapi.getresult(object_name, "surface_normal"))
        if plane_normal == 0:
            plane_normal = (1, 1, 1)
        elif plane_normal == 1:
            plane_normal = (1, 0, 0)
        elif plane_normal == 2:
            plane_normal = (0, 1, 0)
        else:
            plane_normal = (0, 0, 1)

        t = T._extract_results(object_name, plane_normal, lumapi)
        e = Field._extract_results(object_name, monitor_type, lumapi, "E")
        h = Field._extract_results(object_name, monitor_type, lumapi, "H")
        p = Field._extract_results(object_name, monitor_type, lumapi, "P")

        return cls(object_name, monitor_type, t, e, h, p)


@dataclass
class T(ResultBase):

    wavelengths: NDArray[np.float64]
    data: NDArray[np.float64]

    @classmethod
    def _extract_results(cls, object_name: str, lumapi, monitor_type: str, *args) -> Self:

        # Fetch the T results
        try:
            results = lumapi.getresult(object_name, "T")
        except errors.LumApiError:
            return cls(object_name, plane_normal, None, None)  # type: ignore

        # Extract wavelengths and data. These must be reversed.
        wavelengths = results.get("lambda", None)
        if wavelengths is not None:
            wavelengths = convert_length(wavelengths.flatten(), "m", "nm").astype(np.float16)

        data = results.get("T", None)
        if data is not None:
            data = data.flatten().astype(np.float16)

        # Create the dataclass and return
        return cls(object_name, monitor_type, wavelengths, data)

    def has_results(self) -> bool:
        return self.wavelengths is not None and self.data is not None

    def plot(self, label: str, ax: plt.Axes = None, reference: T = None) -> plt.Axes:
        if not self.has_results():
            raise ValueError(f"Cannot plot 'T' data for monitor '{self.monitor_name}', as it has no 'T' results.")

        # Create a new figure and axis if none is provided
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 5))

        if reference is not None:
            data = self.data / reference.data
        else:
            data = self.data

        # Plot data
        ax.plot(self.wavelengths, data, linewidth=2, label=label)

        # Labels and title
        # Labels and title with larger fonts
        ax.set_xlabel("Wavelength (nm)", fontsize=16)
        ax.set_ylabel("Reflectance (R)", fontsize=16)
        ax.set_title("Reflectance", fontsize=18)

        ax.set_xlim([400, 1000])
        ax.set_ylim([0, 1])

        # Increase tick label size
        ax.tick_params(axis="both", which="major", labelsize=14)

        # Add grid
        ax.grid(True, linestyle="--", alpha=0.7)

        # Show legend
        ax.legend(fontsize=14)

        return ax  # Return the axis for further customization


class ProjectionKwargs(TypedDict, total=False):
    fill_projection: bool
    fill_alpha: float
    fill_color: str
    projection_outline: bool
    outline_alpha: float
    outline_color: str
    outline_width: float


@dataclass
class Field(ResultBase):

    field_type: Literal["E", "H", "P"]
    wavelengths: NDArray[np.float32]
    x_coords: NDArray[np.float32]
    y_coords: NDArray[np.float32]
    z_coords: NDArray[np.float32]
    x_field: NDArray[np.float32]
    y_field: NDArray[np.float32]
    z_field: NDArray[np.float32]

    def has_results(self) -> bool:
        return any([field is not None for field in [self.x_field, self.y_field, self.z_field]])

    def has_component(self, component: Literal["x", "y", "z"]) -> bool:
        return getattr(self, component + "_field", None) is not None

    @classmethod
    def _extract_results(cls, object_name: str, monitor_type: str, lumapi,
                         field_name: str, *args) -> Self:

        # Fetchable Results
        results = lumapi.getresult(object_name).split("\n")

        # Extract results
        axes = {}
        for axis in ["x", "y", "z"]:
            data = f"{field_name.capitalize()}{axis}"
            if data in results:
                axes[f"{axis}_field"] = lumapi.getresult(object_name, data)
            else:
                axes[f"{axis}_field"] = None

        if all([axes[f"{ax}_field"] is None for ax in ["x", "y", "z"]]):
            return None
        else:
            x = convert_length(lumapi.getresult(object_name, "x"), "m", "nm")
            if isinstance(x, float):
                x = np.array([x], dtype=np.float32)
            else:
                x = x.flatten().astype(np.float32)

            y = convert_length(lumapi.getresult(object_name, "y"), "m", "nm")
            if isinstance(y, float):
                y = np.array([y], dtype=np.float32)
            else:
                y = y.flatten().astype(np.float32)

            z = convert_length(lumapi.getresult(object_name, "z"), "m", "nm")
            if isinstance(z, float):
                z = np.array([z], dtype=np.float32)
            else:
                z = z.flatten().astype(np.float32)

            wavelengths = lumapi.getresult(object_name, field_name.capitalize())["lambda"].flatten()[::-1]
            wavelengths = convert_length(wavelengths, "m", "nm").astype(np.float16)

        return cls(object_name, monitor_type, field_name.capitalize(), wavelengths, x, y, z, **axes)  # type: ignore

    def _get_field_data(self, coordinate_mesh_indices: tuple, wavelength: float,
                        components: Literal["x", "y", "z", "xy", "xz", "yz", "xyz"] = "xyz"
                        ) -> Tuple[NDArray, str, float]:

        wavelength_idx = np.argmin(np.abs(self.wavelengths - wavelength))
        wavelength = float(self.wavelengths[wavelength_idx])
        indices = (*coordinate_mesh_indices, wavelength_idx)

        # Fetch field components using the computed indices
        if self.has_component("x"):
            x_field = self.x_field[indices]
        else:
            x_field = None
        if self.has_component("y"):
            y_field = self.y_field[indices]
        else:
            y_field = None
        if self.has_component("z"):
            z_field = self.z_field[indices]
        else:
            z_field = None

        field_components = (x_field, y_field, z_field)

        if components == "x":
            if field_components[0] is None:
                raise ValueError("No results for field component x.")
            data = field_components[0]
            label = f"{self.field_type}x"
        elif components == "y":
            if field_components[1] is None:
                raise ValueError("No results for field component y.")
            data = field_components[1]
            label = f"{self.field_type}y"
        elif components == "z":
            if field_components[2] is None:
                raise ValueError("No results for field component z.")
            data = field_components[2]
            label = f"{self.field_type}z"
        elif components == "xy":
            if field_components[0] is None:
                raise ValueError("No results for field component x.")
            if field_components[1] is None:
                raise ValueError("No results for field component y.")
            data = np.linalg.norm(np.stack((field_components[0], field_components[1]), axis=0), axis=0)
            label = f"Magnitude of {self.field_type}xy"
        elif components == "xz":
            if field_components[0] is None:
                raise ValueError("No results for field component x.")
            if field_components[2] is None:
                raise ValueError("No results for field component z.")
            data = np.linalg.norm(np.stack((field_components[0], field_components[2]), axis=0), axis=0)
            label = f"Magnitude of {self.field_type}xz"
        elif components == "yz":
            if field_components[1] is None:
                raise ValueError("No results for field component y.")
            if field_components[2] is None:
                raise ValueError("No results for field component z.")
            data = np.linalg.norm(np.stack((field_components[1], field_components[2]), axis=0), axis=0)
            label = f"Magnitude of {self.field_type}yz"
        elif components == "xyz":
            if field_components[0] is None:
                raise ValueError("No results for field component x.")
            if field_components[1] is None:
                raise ValueError("No results for field component y.")
            if field_components[2] is None:
                raise ValueError("No results for field component z.")
            data = np.linalg.norm(np.stack((field_components[0], field_components[1], field_components[2]), axis=0),
                                  axis=0)
            label = f"Magnitude of {self.field_type}"
        else:
            raise ValueError(f"Expected 'x', 'y', 'z', 'xy', 'xz', 'yz', or 'xyz' for 'components', got '{components}'.")

        return data, label, wavelength

    def _get_coordinate_mesh(self, fixed_index: int = 0,
                             plane_normal: PLANE_NORMALS = "z-normal") -> Tuple[NDArray, NDArray, str, float, tuple]:
        """Returns the coordinate mesh for the given monitor, as well as a string label with the fixed axis, and
        a float with the coordinate of the fixed axis."""

        def get_indices(m_type: str, fix_i: int = 0):

            if m_type in "2d z-normal":
                p = "xy"
                i = (slice(None, None), slice(None, None), fix_i)
            elif m_type in "2d y-normal":
                p = "xz"
                i = (slice(None, None), fix_i, slice(None, None))
            elif m_type in "2d x_normal":
                p = "yz"
                i = (fix_i, slice(None, None), slice(None, None))
            elif m_type == "3d":
                validation.in_literal(plane_normal, "plane_normal", PLANE_NORMALS)
                p, i = get_indices(plane_normal, fixed_index)
            else:
                raise ValueError(f"This method does not work for monitors with dimensions less than 2.")

            return p, i

        plane, indices = get_indices(self.monitor_type)

        # Fetch coordinates
        x = self.x_coords[indices[0]]
        y = self.y_coords[indices[1]]
        z = self.z_coords[indices[2]]

        # Create a meshgrid for plotting
        if plane == "xy":
            X, Y = np.meshgrid(x, y, indexing="ij")
            fixed_axis = "z"
            fixed_coordinate = float(z)
        elif plane == "xz":
            X, Y = np.meshgrid(x, z, indexing="ij")
            fixed_axis = "y"
            fixed_coordinate = float(y)
        elif plane == "yz":
            X, Y = np.meshgrid(y, z, indexing="ij")
            fixed_axis = "x"
            fixed_coordinate = float(x)
        else:
            raise ValueError(f"Expected 'xy', 'xz', or 'yz' for 'plane', got '{plane}'.")

        return X, Y, fixed_axis, fixed_coordinate, indices
