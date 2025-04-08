from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Self
from numpy.typing import NDArray
import numpy as np
from matplotlib import pyplot as plt
from ..resources.functions import convert_length


@dataclass
class SavedSimulation:

    category: str
    subcategory: str
    parameters: dict
    structures: list
    results: list
    units: str


@dataclass
class ResultBase(ABC):
    """Abstract base class for any dataclass containing results from simulation objects."""

    monitor_name: str

    @classmethod
    @abstractmethod
    def _extract_results(cls, object_name: str, lumapi, result_name: str, *args) -> Self:
        """
        Fetches the results from the simulation, and returns the results as a dataclass.

        Args:
            object_name (str): Name of the object results will be fetched from.
            lumapi: The initialized API connected to the simulation.
            result_name (str): Name of the result/field to be extracted.

        Returns:
            Dataclass with the results.
        """


@dataclass
class T(ResultBase):
    wavelengths: NDArray[np.float64]
    data: NDArray[np.float64]

    @classmethod
    def _extract_results(cls, object_name: str, lumapi, *args) -> Self:

        # Fetch the T results
        results = lumapi.getresult(object_name, "T")

        # Extract wavelengths and data. These must be reversed.
        wavelengths = results["lambda"].flatten()
        data = results["T"].flatten()

        # Create the dataclass and return
        return cls(object_name, wavelengths, data)


@dataclass
class Field(ResultBase):
    wavelengths: NDArray[np.float64]
    x_coords: NDArray[np.float64]
    y_coords: NDArray[np.float64]
    z_coords: NDArray[np.float64]
    x_field: NDArray[np.float64]
    y_field: NDArray[np.float64]
    z_field: NDArray[np.float64]

    @classmethod
    def _extract_results(cls, object_name: str, lumapi, field_name: str, *args) -> Self:

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
            x = lumapi.getresult(object_name, "x").flatten()
            y = lumapi.getresult(object_name, "y").flatten()
            z = lumapi.getresult(object_name, "z")
            if isinstance(z, float):
                z = np.array([z], dtype=np.float64)
            else:
                z = z.flatten()
            wavelengths = lumapi.getresult(object_name, field_name.capitalize())["lambda"].flatten()[::-1]
            wavelengths = convert_length(wavelengths, "m", "um")

        return cls(object_name, wavelengths, x, y, z, **axes)

    def plot(self, struct=None):
        z_index = 0  # Assuming single z-coordinate
        time_index = 0  # Selecting first time step

        # Extract the 2D slice of the Ex field
        Ex_slice = self.x_field[:, :, z_index, time_index]

        # Convert to real values (magnitude) to avoid complex number issues
        Ex_slice = np.abs(Ex_slice)  # Use .real if you prefer the real part only

        # Convert coordinates from meters to nanometers
        x = convert_length(self.x_coords, "m", "nm")
        y = convert_length(self.y_coords, "m", "nm")

        # Create a meshgrid for plotting
        X, Y = np.meshgrid(x, y, indexing="ij")

        # Create figure
        fig, ax = plt.subplots(figsize=(6, 5))

        # Plot the contour field
        contour = ax.contourf(X, Y, Ex_slice, levels=1000, cmap="viridis")
        fig.colorbar(contour, label="Ex field value")

        # Labels and title
        ax.set_xlabel("x (nm)")
        ax.set_ylabel("y (nm)")

        plt.plot(*struct._get_projection_outline("xy").T)

        # Show the combined plot
        plt.show()