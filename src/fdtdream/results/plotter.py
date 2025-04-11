import matplotlib.pyplot as plt
import numpy as np
import trimesh
from typing import Literal, Unpack, TypedDict, Tuple, List, Union
from .field_and_power_monitor import Field
import shapely
from ..resources import validation
from .plotted_structure import PlottedStructure


class ProfilePlotter:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.quiver_artists = []
        self.structures: List[PlottedStructure]
        self.current_result: Union[Field, None] = None
        self.plane: Literal["x-normal", "y-normal", "z-normal"] = "z-normal"
        self.fixed_index = 0
        self.components: Literal["x", "y", "z", "xy", "xz", "yz", "xyz"] = "xyz"
        self.wavelength: float = -float('inf')
        self.indices = None

    def set_new_result(self, new_result: Field) -> None:
        self.quiver_artists = []
        prev_structure_names = [struct[0] for struct in self.structure_artists]

        self.current_result: Union[Field, None] = new_result
        self.indices = None
        self.plot()


    def plot(self) -> None:
        """
        Plots the intensity field map of the results.
        """

        if self.current_result is None:
            raise ValueError(f"No monitor result is currently selected.")

        # Your existing code for handling wavelengths, coordinates, and field components...
        X, Y, fixed_axis, fixed_coordinate, indices = self.current_result._get_coordinate_mesh(
            self.fixed_index, self.plane
        )

        # Store the indices
        self.indices = indices

        # Create a meshgrid for plotting
        data, label, wavelength = self.current_result._get_field_data(indices, self.wavelength, self.components)

        # Plot the contour field
        self.ax.clear()  # Clears previous plot elements (contours)
        contour = self.ax.contourf(X, Y, data, levels=1000, cmap="viridis")
        self.fig.colorbar(contour, label=label)

        # # Determine in-plane field components for the quiver plot
        # U, V = self._get_inplane_components(plane, field_components)
        #
        # # Plot quiver (vector field) if applicable
        # if U is not None and V is not None:
        #     self._update_quiver(U, V, X, Y)
        #
        # # Overlay **only the outer boundary** of the trimesh object
        # self._update_structure_outlines(structures, plane)

        self._update_structure_outlines(self.structure_artists)

        # Show the combined plot
        plt.plot()
        plt.draw()
        plt.pause(0.01)  # If running in interactive mode

    def _update_quiver(self, U, V, X, Y):
        """Update the quiver plot without redrawing the entire figure."""
        if self.quiver_artists:
            # Remove old quiver plot
            for artist in self.quiver_artists:
                artist.remove()

        stride = 1  # Adjust this to control vector density
        quiver = self.ax.quiver(
            X[::stride, ::stride], Y[::stride, ::stride],
            U[::stride, ::stride], V[::stride, ::stride],
            color="white", scale=40, width=0.002, alpha=0.5
        )
        self.quiver_artists.append(quiver)

    def _update_structure_outlines(self, structures, plane):
        """Update the structure boundaries without redrawing the entire figure."""
        if self.structure_artists:
            # Remove previous structures
            for artist in self.structure_artists:
                if artist[0] not in [struct[0] for struct in structures]:
                    artist.remove()

        self.structure_artists = structures

        # Add new structure outlines
        for structure in structures:
            structure_outline = self.current_result._get_projection_outline(self.ax, structure, plane)
            self.structure_artists.append(structure_outline)

    def _get_projection_outline(self, ax, structure, plane):
        """Extracts and returns the boundary projection outline for a trimesh structure."""
        # Logic to extract and plot the structure outline
        # This is similar to your original _get_projection_outline function
        pass
