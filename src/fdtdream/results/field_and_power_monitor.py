from __future__ import annotations
from dataclasses import dataclass
from numpy.typing import NDArray
import numpy as np
from typing import Self, Literal, List, Tuple, cast
from abc import ABC, abstractmethod
from matplotlib import pyplot as plt
import trimesh
from ..resources.functions import convert_length
from ..resources import errors
from ..resources.literals import LENGTH_UNITS


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
    plane_normal: Tuple[int, int, int]

    @classmethod
    @abstractmethod
    def _extract_results(cls, object_name: str, plane_normal: Tuple[int, int, int],
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
    def _extract_results(cls, object_name: str, lumapi, *args) -> Self:

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
        e = Field._extract_results(object_name, plane_normal, lumapi, "E")
        h = Field._extract_results(object_name, plane_normal, lumapi, "H")
        p = Field._extract_results(object_name, plane_normal, lumapi, "P")

        return cls(object_name, plane_normal, t, e, h, p)


@dataclass
class T(ResultBase):

    wavelengths: NDArray[np.float64]
    data: NDArray[np.float64]

    @classmethod
    def _extract_results(cls, object_name: str, plane_normal: Tuple[int, int, int], lumapi, *args) -> Self:

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
        return cls(object_name, plane_normal, wavelengths, data)

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

    @staticmethod
    def _get_projection_outline(structures: List[trimesh.Trimesh],
                                plane: Literal["xy", "xz", "yz"]) -> List[List[NDArray]]:
        """Calculates the projection of the structure onto one of the axis planes and returns the outline as
        an array of 2D vectors representing either the x and y, x and z, or y and z coordinates, depending
        on the plane.

        Args:
            structures (List[trimesh.Trimesh]]: A list of trimesh objects corresponing to the structures the projection
                outline should be calculated for.
            plane (Literal["xy", "xz", "yz"]): The plane the structure should be projected onto.
            units (str), what units the projection outline should be fetched in.

        """

        structure_outlines: List[List[NDArray]] = []

        for structure in structures:

            # Move all coordinates to the plane and find the intersection.
            outlines = []
            if plane == "xy":
                projection = structure.projected(normal=(0, 0, 1))
            elif plane == "xz":
                projection = structure.projected(normal=(0, 1, 0))
            elif plane == "yz":
                projection = structure.projected(normal=(1, 0, 0))
            else:
                raise ValueError(f"Invalid value for argument 'plane'. Expected one of 'xy', 'xz', 'yz', got {plane}")

            for entity in projection.entities:
                discrete = entity.discrete(projection.vertices)
                outlines.append(discrete)

            structure_outlines.append(outlines)

        return structure_outlines

    def has_results(self) -> bool:
        return any([field is not None for field in [self.x_field, self.y_field, self.z_field]])

    def has_component(self, component: Literal["x", "y", "z"]) -> bool:
        return getattr(self, component + "_field", None) is not None

    @classmethod
    def _extract_results(cls, object_name: str, plane_normal: Tuple[int, int, int], lumapi,
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

        return cls(object_name, plane_normal, field_name.capitalize(), wavelengths, x, y, z, **axes)  # type: ignore

    def _get_plane_results(self, plane: Literal["xy", "xz", "yz"] | str,
                           coordinate_indices: Tuple[slice, slice, slice] =
                           (slice(None, None), slice(None, None), slice(None, None)),
                           wavelength_index: int = 0,
                           units: LENGTH_UNITS = None) -> Tuple[Tuple[NDArray], Tuple[NDArray | None], int]:
        """
        Fetches the field map in a plane slice across the monitor.

        Args:
            plane: The plane in which the field map should be taken ("xy", "xz", or "yz").
            coordinate_indices: A tuple of three slices representing x, y, and z indices.
            wavelength_index: The index corresponding to the wavelength.

        Returns:
            A tuple containing the x, y, and z coordinate, and a tuple containing the
                field components corresponding to the corrdinates.
        """
        x_slice, y_slice, z_slice = coordinate_indices

        # Determine fixed and variable indices based on the plane

        if plane == "xy":
            fixed_index = z_slice.start if z_slice.start is not None else 0
            indices = (x_slice, y_slice, fixed_index, wavelength_index)
        elif plane == "xz":
            fixed_index = y_slice.start if y_slice.start is not None else 0
            indices = (x_slice, fixed_index, z_slice, wavelength_index)
        elif plane == "yz":
            fixed_index = x_slice.start if x_slice.start is not None else 0
            indices = (fixed_index, y_slice, z_slice, wavelength_index)
        else:
            raise ValueError(f"Invalid plane '{plane}'. Choose from 'xy', 'xz', or 'yz'.")

        # Fetch coordinates
        x = self.x_coords[indices[0]]
        y = self.y_coords[indices[1]]
        z = self.z_coords[indices[2]]

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

        return (x, y, z), (x_field, y_field, z_field), wavelength_index  # type: ignore

    def plot(self, plane: Literal["xy", "xz", "yz"] = None,
             components: Literal["x", "y", "z", "xy", "xz", "yz", "xyz"] = "xyz",
             coordinates: Tuple[slice, slice, slice] =
             (slice(None, None), slice(None, None), slice(None, None)),
             wavelength: float = 400,
             structures: List[trimesh.Trimesh] = None) -> None:
        """
        Plots the intensity field map of the results.

        Args:


        """

        if plane is None:
            if self.plane_normal == (0, 0, 1):
                plane = "xy"
            elif self.plane_normal == (0, 1, 0):
                plane = "xz"
            elif self.plane_normal == (1, 0, 0):
                plane = "yz"
            else:
                plane = "xy"

        # Manage coordinate indices


        wavelength_idx = np.argmin(np.abs(self.wavelengths - wavelength))
        coordinates, field_components, lambda_idx = self._get_plane_results(
            plane, (slice(None, None), slice(None, None), slice(0, 1)), wavelength_idx)

        # Create a meshgrid for plotting
        if plane == "xy":
            X, Y = np.meshgrid(coordinates[0], coordinates[1], indexing="ij")
            fixed = f"z = {coordinates[2]}"
        elif plane == "xz":
            X, Y = np.meshgrid(coordinates[0], coordinates[2], indexing="ij")
            fixed = f"y = {coordinates[1]}"
        elif plane == "yz":
            X, Y = np.meshgrid(coordinates[1], coordinates[2], indexing="ij")
            fixed = f"x = {coordinates[0]}"
        else:
            raise ValueError(f"Expected 'xy', 'xz', or 'yz' for 'plane', got '{plane}'.")

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
            raise ValueError(f"Expected 'x', 'y', 'z', 'xy', 'xz', 'yz', or 'xyz' for 'components', got '{plane}'.")

        # Create figure
        fig, ax = plt.subplots(figsize=(6, 5))

        # Plot the contour field
        contour = ax.contourf(X, Y, data, levels=1000, cmap="viridis")
        fig.colorbar(contour, label=label)

        # Determine in-plane field components
        if plane == "xy":
            U, V = field_components[0], field_components[1]  # Ex, Ey
        elif plane == "xz":
            U, V = field_components[0], field_components[2]  # Ex, Ez
        elif plane == "yz":
            U, V = field_components[1], field_components[2]  # Ey, Ez
        else:
            U, V = None, None

        # Plot quiver (vector field) if applicable
        if U is not None and V is not None:
            stride = 1  # Adjust this to control vector density
            ax.quiver(
                X[::stride, ::stride], Y[::stride, ::stride],
                U[::stride, ::stride], V[::stride, ::stride],
                color="white", scale=40, width=0.002, alpha=0.5
            )

        # Set axis limits to min and max of X and Y
        ax.set_xlim([np.min(X), np.max(X)])
        ax.set_ylim([np.min(Y), np.max(Y)])

        # Labels and title
        ax.set_xlabel("x (nm)")
        ax.set_ylabel("y (nm)")
        ax.set_title(f"{label} at {fixed} for $\\lambda = {self.wavelengths[lambda_idx]}$")

        # Overlay **only the outer boundary** of the trimesh object
        outlines = self._get_projection_outline(structures, plane)  # type: ignore
        for outline in outlines:
            for line in outline:
                plt.plot(*line.T, "black", alpha=0.8)

        # Show the combined plot
        plt.show()
