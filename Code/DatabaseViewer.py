from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QStandardItemModel
)
from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QWidget, QLineEdit, QListWidget,
    QMainWindow, QFormLayout, QHBoxLayout, QPushButton, QGridLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QTableView, QStyledItemDelegate, QSlider
)
from Simulation import SimulationBase
from Simulation_database import (
    ResultModel, DatabaseHandler
)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas
)
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from sqlalchemy import inspect, between, Column, Row
from typing import List, Dict, Literal, Any, Type, Tuple
from scipy.signal import find_peaks
import numpy as np
import sys
import os
import subprocess


class PlotCanvas(FigureCanvas):
    plottable_columns = [
        "Ref. Res. λ",
        "Ref. Res.",
        "Trans. Res. λ",
        "Trans. Res.",
        "Ref. E Max λ",
        "Trans. E Max λ"
    ]
    profilable_columns = [
        "Ref. E Max",
        "Trans. E Max"
    ]
    legend_columns = [
        "Sim. Name",
        "ID",
        "Struct. 1 x-span",
        "Struct. 1 y-span",
        "Unit cell 1 x-span",
        "Unit cell 1 y-span",
        "Struct. 1 material",
        "Struct. 2 x-span",
        "Struct. 2 y-span",
        "Unit cell 2 x-span",
        "Unit cell 2 y-span",
        "Struct 2 material",
        "Mesh dx",
        "Mesh dy",
        "Mesh dz",
        "FDTD x-span",
        "FDTD y-span",
        "Polarization angle",
        "Custom Parameter"
    ]
    type_of_plot: Literal[
        "ref_power_pr_lambda",
        "trans_power_pr_lambda",
        "ref_and_trans_power_pr_lambda",
        "ref_magnitude_max_pr_lambda",
        "trans_magnitude_max_pr_lambda",
        "ref_and_trans_magnitude_max_pr_lambda",
        "normalized_mag_res_and_power",
        "ref_profile",
        "trans_profile",
        "value_pr_legend",
        "xz_poynting_vector",
        "yz_poynting_vector",
        "xz_profile",
        "yz_profile"
    ]
    # Create a mapping between plot types and plot data
    plot_dispatch = {
        "ref_and_trans_power_pr_lambda": lambda result, legend: [
            (
                "Reflectance and Transmittance",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.ref_powers, f"Reflectance {legend}"),
            (result.lambdas, result.trans_powers, f"Transmittance {legend}"),
            (result.lambdas, result.ref_powers + result.trans_powers, f"Reflectance + Transmittance {legend}"),
            ""
        ],
        "ref_power_pr_lambda": lambda result, legend: [
            (
                "Reflectance",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.ref_powers, f"Reflectance {legend}")
        ],
        "trans_power_pr_lambda": lambda result, legend: [
            (
                "Transmittance",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.trans_powers, f"Transmittance {legend}")
        ],
        "ref_and_trans_magnitude_max_pr_lambda": lambda result, legend: [
            (
                "Reflected and Transmitted E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                "$\\frac{{E_{{max}}}}{{E_0}}$"
            ),
            (result.lambdas, result.ref_mag_max_pr_lambda, f"Reflected $\\frac{{E_{{max}} }}{{E_0}}$ {legend}"),
            (result.lambdas, result.trans_mag_max_pr_lambda, f"Transmitted $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "ref_magnitude_max_pr_lambda": lambda result, legend: [
            (
                "Reflected E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                "$\\frac{{E_{{max}}}}{{E_0}}$"
            ),
            (result.lambdas, result.ref_mag_max_pr_lambda[str(5)], f"Reflected $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "trans_magnitude_max_pr_lambda": lambda result, legend: [
            (
                "Transmitted E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                "$\\frac{{E_{{max}}}}{{E_0}}$"
            ),
            (result.lambdas, result.trans_mag_max_pr_lambda[str(5)], f"Transmitted $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "ref_power_and_ref_mag_res_max": lambda result, legend: [
            (
                "Reflectance and Reflected E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.ref_powers, f"Reflectance {legend}"),
            (result.lambdas, result.ref_mag_max_pr_lambda[str(5)], f"Reflected $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "ref_and_trans_power_and_ref_mag_max": lambda result, legend: [
            (
                "Reflectance/Transmittance and Reflected E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.ref_powers, f"Reflectance {legend}"),
            (result.lambdas, result.trans_powers, f"Transmittance {legend}"),
            (result.lambdas, result.ref_mag_max_pr_lambda[str(5)], f"Reflected $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "ref_power_and_trans_mag_res_max": lambda result, legend: [
            (
                "Reflectance and Transmitted E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.ref_powers, f"Reflectance {legend}"),
            (result.lambdas, result.trans_mag_max_pr_lambda[str(5)], f"Transmitted $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "ref_and_trans_power_and_trans_mag_max": lambda result, legend: [
            (
                "Reflectance/Transmittance and Transmitted E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.ref_powers, f"Reflectance {legend}"),
            (result.lambdas, result.trans_powers, f"Transmittance {legend}"),
            (result.lambdas, result.trans_mag_max_pr_lambda[str(5)], f"Transmitted $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "trans_power_and_ref_mag_res_max": lambda result, legend: [
            (
                "Transmittance and Reflected E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.trans_powers, f"Transmittance {legend}"),
            (result.lambdas, result.ref_mag_max_pr_lambda[str(5)], f"Reflected $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "trans_power_and_trans_mag_res_max": lambda result, legend: [
            (
                "Transmittance and Transmitted E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.trans_powers, f"Transmittance {legend}"),
            (result.lambdas, result.trans_mag_max_pr_lambda[str(5)], f"Transmitted $\\frac{{E_{{max}} }}{{E_0}}$ {legend}")
        ],
        "ref_and_trans_power_and_ref_and_trans_mag_max": lambda result, legend: [
            (
                "Reflectance/Transmittance and E$_{max}$/E$_0$",
                "Wavelength (λ) [nm]",
                ""
            ),
            (result.lambdas, result.ref_powers, f"Reflectance {legend}"),
            (result.lambdas, result.trans_powers, f"Transmittance {legend}"),
            (result.lambdas, result.ref_mag_max_pr_lambda[str(5)], f"Reflected $\\frac{{E_{{max}} }}{{E_0}}$ {legend}"),
            (result.lambdas, result.trans_mag_max_pr_lambda[str(5)], f"Transmitted $\\frac{{E_{{max}} }}{{E_0}}$ {legend}"),
        ],
    }

    def __init__(self, parent=None, width: int = 5, height: int = 4, dpi: int = 100) -> None:

        self.fig = Figure(
            figsize=(width, height),
            dpi=dpi
        )
        self.parent = parent
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.annotation = self.axes.annotate(
            "", xy=(0, 0), xytext=(10, 10),
            textcoords="offset points", bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->")
        )
        self.colorbar = None
        self.show_vectors = False
        self.show_wavelength = None
        self.displayed_wavelength = None

    def _plot_profile(self,
                      sim_result: Type[ResultModel],
                      plot_type: type_of_plot,
                      at_wavelength: str | float = "max",


                      update: str | None = None) -> None:

        x_pos = sim_result.profile_x
        y_pos = sim_result.profile_y

        # Fetch the wavelength of the result
        lambdas = sim_result.lambdas

        if update == "update_lambda":
            if self.show_wavelength is None:
                self.show_wavelength = 0
            elif self.displayed_wavelength is None:
                pass

            elif lambdas[np.argmin(np.abs(lambdas - self.show_wavelength))] == self.displayed_wavelength:
                return


        if plot_type == "ref_profile":

            string = "Reflected"
            distance = str(5)
            print(sim_result.ref_profile_vectors.keys())
            wavelengths = np.array(list(sim_result.ref_profile_vectors[str(5)].keys())).astype(np.float16)

            if update != "update_lambda":
                wavelength = sim_result.ref_power_res_lambda
            else:
                wavelength = self.show_wavelength

            wavelength = wavelengths[np.argmin(np.abs(wavelengths - wavelength))]

            profile_vectors = sim_result.ref_profile_vectors[distance][str(wavelength)]
            magnitudes = np.linalg.norm(profile_vectors, axis=-1).T.astype(np.float16)

            V_x = profile_vectors[:, :, 0]
            V_y = profile_vectors[:, :, 1]

        elif plot_type == "trans_profile":
            string = "Reflected"
            distance = str(5)
            wavelengths = np.array(list(sim_result.trans_profile_vectors[str(5)].keys())).astype(np.float16)

            if update != "update_lambda":
                wavelength = sim_result.ref_power_res_lambda
            else:
                wavelength = self.show_wavelength

            wavelength = wavelengths[np.argmin(np.abs(wavelengths - wavelength))]

            profile_vectors = sim_result.trans_profile_vectors[distance][str(wavelength)]
            magnitudes = np.linalg.norm(profile_vectors, axis=-1).T.astype(np.float16)

            V_x = profile_vectors[:, :, 0]
            V_y = profile_vectors[:, :, 1]

        try:
            title = f"{string} Near-Field Magnitudes at $\\lambda$ = {wavelength} nm"
            x_label = "x-position [nm]"
            y_label = "y-position [nm]"
        except:
            pass

        scale = 50
        vector_label='E-field vectors'

        if plot_type == "xz_profile":
            distance = str(5)
            wavelengths = np.array(list(sim_result.xz_profile_E_vectors[str(5)].keys())).astype(np.float16)
            if update != "update_lambda":
                wavelength = sim_result.ref_power_res_lambda
            else:
                wavelength = self.show_wavelength

            wavelength = wavelengths[np.argmin(np.abs(wavelengths - wavelength))]

            profile_vectors = sim_result.xz_profile_E_vectors[distance][str(wavelength)]
            profile_P_vectors = sim_result.xz_profile_P_vectors[distance][str(wavelength)]
            magnitudes = np.linalg.norm(profile_vectors, axis=-1).T.astype(np.float16)

            V_x = profile_P_vectors[:, :, 0]
            V_y = profile_P_vectors[:, :, 2]
            x_label = "x-position [nm]"
            y_label = "z-position [nm]"
            x_pos = sim_result.xz_profile_x_coord
            y_pos = sim_result.xz_profile_z_coord

            vector_label='Poynting vectors'
            scale = 0.05

            title = f"E-Field Magnitude and Poynting Vectors in the XZ-Plane at lambda={wavelength}"

        if plot_type == "yz_profile":
            x_label = "y-position [nm]"
            y_label = "z-position [nm]"
            magnitudes = np.linalg.norm(sim_result.yz_profile_E_vectors, axis=-1).T.astype(np.float16)
            x_pos = sim_result.yz_profile_y_coord
            y_pos = sim_result.yz_profile_z_coord

            vector_label = 'Poynting vectors'
            scale = 0.1

            if update != "update_lambda":
                wavelength = sim_result.ref_power_res_lambda
            else:
                wavelength = self.show_wavelength

            # Fetch resonances for both transmission and reflection
            trans_mag_res_lambdas, _ = SimulationBase._get_resonance(
                lambdas,
                sim_result.trans_mag_max_pr_lambda,
                resonance_type="reflection",
                nr_peaks=3
            )
            ref_mag_res_lambdas, _ = SimulationBase._get_resonance(
                lambdas,
                sim_result.ref_mag_max_pr_lambda,
                resonance_type="reflection",
                nr_peaks=3
            )
            # Find the reflection peaks
            ref_peak_lambdas, _ = SimulationBase._get_resonance(
                lambdas, sim_result.ref_powers, resonance_type="reflection", nr_peaks=3
            )
            # Find the transmission peaks
            trans_peak_lambdas, _ = SimulationBase._get_resonance(
                lambdas, sim_result.trans_powers, resonance_type="transmission", nr_peaks=3
            )

            # Combine all resonance peak wavelengths and ensure uniqueness
            wavelengths = np.unique(np.concatenate((
                trans_mag_res_lambdas, ref_mag_res_lambdas, ref_peak_lambdas, trans_peak_lambdas
            )))

            title = f"E-Field Magnitude and Poynting Vectors in the YZ-Plane at lambda={wavelengths[np.argmin(np.abs(wavelengths - wavelength))]}"

            V_x = sim_result.yz_profile_P_vectors[:, :, np.argmin(np.abs(wavelengths - wavelength)), 1]
            V_y = sim_result.yz_profile_P_vectors[:, :, np.argmin(np.abs(wavelengths - wavelength)), 2]

        # Code to make sure the colorbar is propperly reset between each plot
        self.axes.clear()
        if self.colorbar is not None:
            self.fig.delaxes(self.fig.axes[1])
            self.colorbar = None
        self.fig.delaxes(self.axes)
        self.axes = self.fig.add_subplot(111)

        # Create the heatmap

        # Create a meshgrid for the x and y positions (which might be irregular)
        X, Y = np.meshgrid(x_pos, y_pos)
        self.displayed_wavelength = wavelength

        try:
            # Use pcolormesh instead of imshow to account for non-uniform grid spacing
            c = self.axes.pcolormesh(
                X, Y,  # Meshgrid for non-uniform grid
                magnitudes,  # The heatmap data
                shading='auto',  # Ensure smooth shading
                cmap='viridis'  # Choose a suitable colormap
            )
        except Exception as e:
            print(e)
            # Use pcolormesh instead of imshow to account for non-uniform grid spacing
            c = self.axes.imshow(
                x_pos, y_pos,  # Meshgrid for non-uniform grid
                magnitudes[:][:][np.argmin(np.abs(wavelengths - wavelength))],  # The heatmap data
                shading='auto',  # Ensure smooth shading
                cmap='viridis'  # Choose a suitable colormap
            )

        # Add a new colorbar and store the reference
        self.colorbar = self.axes.figure.colorbar(c, ax=self.axes, label="Magnitude")

        min_dx = np.min(np.diff(np.unique(x_pos)))
        min_dy = np.min(np.diff(np.unique(y_pos)))
        smallest_cell_size = min(min_dx, min_dy)

        step = 1
        X, Y = np.meshgrid(x_pos, y_pos)
        X_sub = X[::step, ::step]
        Y_sub = Y[::step, ::step]
        V_x_sub = V_x.T[::step, ::step]
        V_y_sub = V_y.T[::step, ::step]
        # Create the vector field using quiver for the xz profile (assuming xz plane)
        if self.show_vectors:

            self.axes.quiver(
                X_sub, Y_sub,
                V_x_sub, V_y_sub,  # Subsampled P_x and P_z
                color='white',  # Choose a color that contrasts well with the heatmap
                width=0.0005,
                scale=smallest_cell_size * scale,
                label=vector_label
            )

        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel(y_label)
        self.axes.set_title(title)
        self.axes.legend()
        self.axes.figure.tight_layout()
        self.draw()

    def _plot_lines(self, clicked_data: dict, plot_type: type_of_plot) -> None:
        # Clear previous plots
        self.axes.clear()
        if self.colorbar is not None:
            self.fig.delaxes(self.fig.axes[1])
            self.colorbar = None
        self.fig.delaxes(self.axes)
        self.axes = self.fig.add_subplot(111)

        # Iterate over the rows clicked
        for row, data in clicked_data.items():
            if row == "last_clicked":
                continue

            result = data["result"]
            legend = "".join(
                f" - {name}: {value}"
                for name, value in zip(data["column_names"], data["column_values"])
                if name in PlotCanvas.legend_columns
            )

            try:
                # Fetch plot data using the dispatch table
                if plot_type in PlotCanvas.plot_dispatch:
                    plot_data = PlotCanvas.plot_dispatch[plot_type](result, legend)
                    title, x_axis, y_axis = plot_data[0]
                    for x_data, y_data, label in plot_data[1:]:
                        self.axes.plot(x_data, y_data, label=label)
                else:
                    print(f"Unknown plot type: {plot_type}")
                    return
            except Exception as e:
                print(f"Newwww: {e}")

        # Set title and axis labels with larger font size
        self.axes.set_title(title, fontsize=14)
        self.axes.set_xlabel(x_axis, fontsize=12)
        self.axes.set_ylabel(y_axis, fontsize=12)
        self.axes.legend()

        # Add a grid
        self.axes.grid(True)

        # Increase the font size for tick labels
        self.axes.tick_params(axis='both', which='major', labelsize=10)

        # Set tight layout
        self.axes.figure.tight_layout()

        # Redraw the canvas
        self.draw()

        # Connect the hover event
        self.annotation = self.axes.annotate(
            "", xy=(0, 0), xytext=(10, 10),
            textcoords="offset points", bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->")
        )
        self.annotation.set_visible(False)

        self.mpl_connect("motion_notify_event", self._on_hover1)

    def plot(self, clicked_data: dict, update: str | None = None) -> None:
        # Fetch the clicked columns
        clicked_columns = set()
        for row in clicked_data.keys():
            if row != "last_clicked":
                for column_name in clicked_data[row]["column_names"]:
                    clicked_columns.add(column_name)

        is_plotable_columns = any(column in PlotCanvas.plottable_columns for column in clicked_columns)
        is_profilable_columns = any(column in PlotCanvas.profilable_columns for column in clicked_columns)
        is_legend_columns = any(column in PlotCanvas.legend_columns for column in clicked_columns)

        # Fetch the last clicked column
        last_clicked = clicked_data["last_clicked"]

        # Check if anything should be plotted. If not, return
        if last_clicked["column_name"] == "Struct. 1 x-span":
            self._plot_profile(
                sim_result=last_clicked["result"],
                plot_type="xz_profile", update=update
            )
            return
        elif all([column == noe for column, noe in zip(clicked_columns, ["Struct. 1 y-span", "Struct. 1 z-span"])]):
            self._plot_profile(
                sim_result=last_clicked["result"],
                plot_type="yz_profile", update=update
            )
        elif not is_plotable_columns and not is_profilable_columns:
            return


        # Determine if profiles should be plotted
        if last_clicked["column_name"] == "Ref. E Max":
            self._plot_profile(
                sim_result=last_clicked["result"],
                plot_type="ref_profile", update=update
            )
            return
        elif last_clicked["column_name"] == "Trans. E Max":
            self._plot_profile(
                sim_result=last_clicked["result"],
                plot_type="trans_profile", update=update
            )
            return

        # Fetch some truth statements
        is_ref_power = any(column in clicked_columns for column in ["Ref. Res. λ", "Ref. Res."])
        is_trans_power = any(column in clicked_columns for column in ["Trans. Res. λ", "Trans. Res."])
        is_ref_mag_max = "Ref. E Max λ" in clicked_columns
        is_trans_mag_max = "Trans. E Max λ" in clicked_columns

        # Now determine what type of line plot should be plotted
        if (is_ref_power or is_trans_power) and not (is_ref_mag_max or is_trans_mag_max):
            if is_trans_power and is_ref_power:
                type_of_plot = "ref_and_trans_power_pr_lambda"
            elif is_ref_power:
                type_of_plot = "ref_power_pr_lambda"
            else:
                type_of_plot = "trans_power_pr_lambda"

        elif (is_ref_mag_max or is_trans_mag_max) and not (is_ref_power or is_trans_power):
            if is_ref_mag_max and is_trans_mag_max:
                type_of_plot = "ref_and_trans_magnitude_max_pr_lambda"
            elif is_ref_mag_max:
                type_of_plot = "ref_magnitude_max_pr_lambda"
            else:
                type_of_plot = "trans_magnitude_max_pr_lambda"

        else:
            if (is_ref_power and not is_trans_power) and (is_ref_mag_max and not is_trans_mag_max):
                type_of_plot = "ref_power_and_ref_mag_res_max"
            elif (is_ref_power and is_trans_power) and (is_ref_mag_max and not is_trans_mag_max):
                type_of_plot = "ref_and_trans_power_and_ref_mag_max"
            elif (is_ref_power and not is_trans_power) and (not is_ref_mag_max and is_trans_mag_max):
                type_of_plot = "ref_power_and_trans_mag_res_max"
            elif (is_ref_power and is_trans_power) and (is_ref_mag_max and is_trans_mag_max):
                type_of_plot = "ref_and_trans_power_and_ref_and_trans_mag_max"
            elif (is_ref_power and is_trans_power) and (not is_ref_mag_max and is_trans_mag_max):
                type_of_plot = "ref_and_trans_power_and_trans_mag_max"
            elif (not is_ref_power and is_trans_power) and (is_ref_mag_max and not is_trans_mag_max):
                type_of_plot = "trans_power_and_ref_mag_res_max"
            elif (not is_ref_power and is_trans_power) and (not is_ref_mag_max and is_trans_mag_max):
                type_of_plot = "trans_power_and_trans_mag_res_max"

        self._plot_lines(clicked_data, plot_type=type_of_plot)

    def _on_hover1(self, event):
        # Check if the event occurred inside the axes
        if event.inaxes == self.axes:
            # Get the data coordinates of the mouse pointer
            x, y = event.xdata, event.ydata

            # Update the annotation text and position
            self.annotation.xy = (x, y)
            text = f"Wavelength: {x:.2f} nm\nValue: {y:.2f}"
            self.annotation.set_text(text)
            self.annotation.set_visible(True)
            self.draw()  # Redraw to show the updated annotation
        else:
            self.annotation.set_visible(False)
            self.draw()  # Redraw to hide the annotation


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text: str):
        super().__init__(text)

    def __lt__(self, other: QTableWidgetItem):
        # Try to convert both items to floats for comparison
        try:
            return float(self.text()) < float(other.text())
        except ValueError:
            # If conversion fails, fall back to string comparison
            return self.text() < other.text()


class ResultsTable(QTableWidget):
    default_headers: List[str] = [
        "ID",
        "Sim. Name",
        "Struct. 1 x-span",
        "Struct. 1 y-span",
        "Struct. 1 z-span",
        "FDTD x-span",
        "FDTD y-span",
        "Custom Parameter",
        "Ref. Res. λ",
        "Trans. Res. λ",
        "Ref. E Max λ",
        "Ref. E Max",
        "Trans. E Max λ",
        "Trans. E Max",
        "Polarization angle",
        "Struct. 1 Material"
    ]
    header_to_column_map: Dict[str, str] = {
        "ID": "id",
        "Sim. Name": "name",
        "Polarization angle": "polarization_angle",
        "Ref. Res. λ": "ref_power_res_lambda",
        "Ref. Res.": "ref_power_res",
        "Trans. Res. λ": "trans_power_res_lambda",
        "Trans. Res.": "trans_power_res",
        "Ref. E Max λ": "ref_mag_res_lambda",
        "Ref. E Max": "ref_mag_res",
        "Trans. E Max λ": "trans_mag_res_lambda",
        "Trans. E Max": "trans_mag_res",
        "Struct. 1 x-span": "struct1_xspan",
        "Struct. 1 y-span": "struct1_yspan",
        "Struct. 1 z-span": "struct1_zspan",
        "Struct. 1 unit cell x": "unit_cell1_x",
        "Struct. 1 unit cell y": "unit_cell1_y",
        "FDTD x-span": "fdtd_xspan",
        "FDTD y-span": "fdtd_yspan",
        "Struct. 2 x-span": "struct2_xspan",
        "Struct. 2 y-span": "struct2_yspan",
        "Struct. 2 unit cell x": "unit_cell2_x",
        "Struct. 2 unit cell y": "unit_cell2_y",
        "Mesh dx": "mesh_dx",
        "Mesh dy": "mesh_dy",
        "Mesh dz": "mesh_dz",
        "Struct. 1 Material": "struct1_material",
        "Struct. 2 Material": "struct2_material",
        "Custom Parameter": "comment"
    }
    column_to_header_map: Dict[str, str] = {
        "id": "ID",
        "name": "Sim. Name",
        "polarization_angle": "Polarization angle",
        "ref_power_res_lambda": "Ref. Res. λ",
        "ref_power_res": "Ref. Res.",
        "trans_power_res_lambda": "Trans. Res. λ",
        "trans_power_res": "Trans. Res.",
        "ref_mag_res_lambda": "Ref. E Max λ",
        "ref_mag_res": "Ref. E Max",
        "trans_mag_res_lambda": "Trans. E Max λ",
        "trans_mag_res": "Trans. E Max",
        "struct1_xspan": "Struct. 1 x-span",
        "struct1_yspan": "Struct. 1 y-span",
        "struct1_zspan": "Struct. 1 z-span",
        "unit_cell1_x": "Struct. 1 unit cell x",
        "unit_cell1_y": "Struct. 1 unit cell y",
        "fdtd_xspan": "FDTD x-span",
        "fdtd_yspan": "FDTD y-span",
        "struct2_xspan": "Struct. 2 x-span",
        "struct2_yspan": "Struct. 2 y-span",
        "unit_cell2_x": "Struct. 2 unit cell x",
        "unit_cell2_y": "Struct. 2 unit cell y",
        "mesh_dx": "Mesh dx",
        "mesh_dy": "Mesh dy",
        "mesh_dz": "Mesh dz",
        "struct1_material": "Struct. 1 Material",
        "struct2_material": "Struct. 2 Material",
        "comment": "Custom Paramter"
    }

    def __init__(self, parent: DatabaseViewer, canvas: PlotCanvas, headers: List[str] | int = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make a refference to the plotting canvas
        self.canvas = canvas

        self.parent = parent

        # Add a list for all the fetched results from the database. Will be used for loading
        # addtional results to the table
        self.currently_fetched_data: List[Type[ResultModel]] = []

        # Add a list containing all the id numbers of the results in the above list
        self.indices: List[int] = []

        # Set the header count and labels
        self.headers = ResultsTable.default_headers
        self.setColumnCount(self.headers)
        self.setHorizontalHeaderLabels(self.headers)

        # Enable sorting and ensure header labels are clickable for sorting
        self.setSortingEnabled(True)
        self.horizontalHeader().setSortIndicatorShown(True)

        # Set selection mode to allow extended selection
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Adjust column widths based on content for specific columns
        for column in range(self.columnCount()):
            self.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)

        # Connect the selectionChanged signal
        self.selectionModel().selectionChanged.connect(self.on_cell_click)

        parent.central_layout.addWidget(self)
        self.setMinimumHeight(300)

    def store_results(self, results: list[Row[tuple[ResultModel, int]]]) -> None:
        # Save all the fetched data to a list
        self.currently_fetched_data = {result_id: result for result, result_id in results}

    def display_results(self, result_ids) -> None:
        # Empty the table
        self.reset()

        nr_rows = len(result_ids)
        results = [
            self.currently_fetched_data[result_id] for result_id in result_ids
        ]

        # Insert the number of rows and columns in the list of rows
        self.setRowCount(nr_rows)
        self.setColumnCount(self.headers)

        # Fetch the corresponding column names to what headers are currently displayed
        included_columns = [ResultsTable.header_to_column_map[header] for header in self.headers]

        # Insert the data
        for row_nr, result in enumerate(results):
            for column_nr, value in enumerate(included_columns):
                attribute = getattr(result, value)
                if value == "comment":
                    attribute = attribute.split(";:;")

                    if len(attribute) < 2:
                        attribute = None
                    else:
                        attribute = attribute[1]
                self.setItem(row_nr, column_nr, NumericTableWidgetItem(str(attribute)))

        # Set alternating row colors
        self.setAlternatingRowColors(True)

    def setColumnCount(self, columns: List[str] | int) -> None:
        if isinstance(columns, list):
            super().setColumnCount(len(columns))
        else:
            super().setColumnCount(columns)

    def open_fsp_file(self, simulation_id: int) -> None:
        """
        Opens a .fsp file in Lumerical FDTD by launching the program with the file path.

        Args:
            file_number (int): The number of the .fsp file to open (e.g., 1 for 1.fsp).
            simulations_folder (str): The folder where .fsp files are located.
        """
        # Construct the file path
        folder_path = os.path.abspath(f"../Database/Savefiles/{self.parent.db_handler.db_name}")
        file_path = os.path.join(folder_path, f"{self.parent.db_handler.db_name}_{simulation_id}.fsp")

        # Path to the Lumerical FDTD executable
        # Update this path based on your installation
        fdtd_executable = r"C:\Program Files\Lumerical\v241\bin\fdtd-solutions.exe"  # Example path

        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return

        # Open the .fsp file in Lumerical FDTD
        subprocess.Popen([fdtd_executable, file_path])

    def on_cell_click(self, update: str | None = None) -> None:
        # Fetch the currently selected indices
        selected_indices = self.selectedIndexes()

        # Return nothing if no cells are selected
        if not selected_indices:
            return

        # Make a dictionary that holds all information concerning the clicked data in the table
        clicked_data = {}

        # Assign the corresponding result to each row and make a list of what cells are
        # clicked in that row
        for index in selected_indices:
            row = index.row()

            if row not in clicked_data.keys():
                clicked_data[row] = {
                    "result": self.currently_fetched_data[int(self.item(row, 0).text())],
                    "column_names": [str(self.horizontalHeaderItem(index.column()).text())],
                    "column_values": [str(self.item(row, index.column()).text())]
                }
            else:
                clicked_data[row]["column_names"].append(str(self.horizontalHeaderItem(index.column()).text()))
                clicked_data[row]["column_values"].append(str(self.item(row, index.column()).text()))

        clicked_data["last_clicked"] = {
            "result": self.currently_fetched_data[int(self.item(selected_indices[-1].row(), 0).text())],
            "column_name": self.horizontalHeaderItem(selected_indices[-1].column()).text(),
        }

        if clicked_data["last_clicked"]["column_name"] == "Ref. E Max" or clicked_data["last_clicked"]["column_name"] == "Trans. E Max":
            lambdas = clicked_data["last_clicked"]["result"].lambdas

            self.parent.vector_slider.setRange(0, len(lambdas) - 1)  # Set range based on the list length
            self.parent.vector_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            self.parent.vector_slider.setTickInterval(int(round(len(lambdas)/100, 0)))
            # self.parent.vector_slider.setValue(2)  # Start with the third value in the list

        if clicked_data["last_clicked"]["column_name"] == "ID":
            self.open_fsp_file(clicked_data["last_clicked"]["result"].id)

        try:
            self.canvas.plot(clicked_data, update)
        except Exception as e:
            print(f"Plotting Error: {e}")


class DatabaseViewer(QMainWindow):
    # Some type hints
    grid_layout: QGridLayout
    input_fields: Dict[str, QLineEdit]
    # Default input fields to be included
    default_input_fields: List[str] = [
        "Sim. Name",
        "Struct. 1 Material",
        "Struct. 1 x-span",
        "FDTD x-span",
        "Struct. 1 y-span",
        "FDTD y-span",
        "Polarization angle"
    ]
    column_to_input_field_map = {
        "name": "Sim. Name",
        "ref_power_res_lambda": "Ref. Far-Field. Res. λ",
        "trans_power_res_lambda": "Trans. Far-Field. Res λ",
        "ref_mag_res_lambda": "Ref. Near-Field Res. λ",
        "trans_mag_res_lambda": "Trans. Near-Field Res. λ",
        "struct1_xspan": "Struct. 1 x-span",
        "struct1_yspan": "Struct. 1 y-span",
        "fdtd_xspan": "FDTD x-span",
        "fdtd_yspan": "FDTD y-span",
        "mesh_dx": "Mesh dx",
        "mesh_dy": "Mesh dy",
        "mesh_dz": "Mesh dz",
        "struct1_material": "Struct. 1 Material",
        "polarization_angle": "Polarization angle"
    }
    input_field_to_column_map = {
        "Sim. Name": "name",
        "Ref. Far-Field. Res. λ": "ref_power_res_lambda",
        "Trans. Far-Field. Res λ": "trans_power_res_lambda",
        "Ref. Near-Field Res. λ": "ref_mag_res_lambda",
        "Trans. Near-Field Res. λ": "trans_mag_res_lambda",
        "Struct. 1 x-span": "struct1_xspan",
        "Struct. 1 y-span": "struct1_yspan",
        "FDTD x-span": "fdtd_xspan",
        "FDTD y-span": "fdtd_yspan",
        "Mesh dx": "mesh_dx",
        "Mesh dy": "mesh_dy",
        "Mesh dz": "mesh_dz",
        "Struct. 1 Material": "struct1_material",
        "Polarization angle": "polarization_angle"
    }
    text_type_columns = ["struct1_material", "name"]

    def __init__(self, database: str):
        super().__init__()

        # Set the window title
        self.setWindowTitle("Database Search and Plotter")

        # Fetch the database handler
        self.db_handler = DatabaseHandler(database)

        # Add a central widget and set the main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.central_layout = QVBoxLayout(central_widget)
        self.setLayout(self.central_layout)

        # Generate the input fields
        self._add_parameter_input_fields()

        # Add the search_button
        self.search_button = QPushButton("Search database", self)
        self.search_button.clicked.connect(self.search_database_and_display)
        self.central_layout.addWidget(self.search_button)

        canvas_layout = QHBoxLayout()
        # Matplotlib plot for reflectance
        self.canvas1 = PlotCanvas(self, width=8, height=10)
        canvas_layout.addWidget(self.canvas1)

        # Insert the results table
        self.table = ResultsTable(self, self.canvas1)

        # Slider and button to toggle on and off vectors
        # Horizontal layout for slider and button
        control_layout = QHBoxLayout()

        # Create a slider for adjusting vector size with values from the list
        self.vector_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.vector_slider.valueChanged.connect(self.update_wavelength)
        control_layout.addWidget(self.vector_slider)

        # Create button to toggle vectors on and off
        self.toggle_button = QPushButton("Toggle Vectors", self)
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_vectors)
        control_layout.addWidget(self.toggle_button)

        # Add control layout to the main layout
        self.central_layout.addLayout(control_layout)

        # Do the initial load of the table
        initial_load = self.db_handler.initial_load(print_load_time=True)
        initial_ids = [result[1] for result in initial_load]
        self.table.store_results(initial_load)
        self.table.display_results(initial_ids)

        # Add the canvas to the main layout
        self.central_layout.addLayout(canvas_layout)

    def update_wavelength(self):
        # Update vector size based on slider value
        wavelength = self.vector_slider.value()
        self.canvas1.show_wavelength = wavelength
        self.table.on_cell_click(update="update_lambda")

    def toggle_vectors(self):
        # Toggle visibility of vectors
        if self.toggle_button.isChecked():
            # Show vectors
            self.canvas1.show_vectors = True
        else:
            # Hide vectors
            self.canvas1.show_vectors = False

        self.table.on_cell_click(update="toggle_vectors")

    def _add_parameter_input_fields(self, exceptions: List[str] = None) -> None:

        # Add a grid layout for the input fields
        self.grid_layout = QGridLayout()
        self.input_fields = {}

        # Dynamically generate input fields based on ResultModel columns
        inspector = inspect(ResultModel)

        # Iterate over the columns in the database
        row = 0
        col = 0
        for column in inspector.columns:

            # Fetch the name of the column
            column_name = column.name
            included_collumns = [
                DatabaseViewer.input_field_to_column_map[field] for field in DatabaseViewer.default_input_fields
            ]

            # Go to next collumn if it shouldn't be included
            if column_name not in included_collumns:
                continue

            # Map the column name to a reader friendly name
            column_display_name = DatabaseViewer.column_to_input_field_map[column_name]

            # Create label and input field
            label = QLabel(f"{column_display_name}:")
            input_field = QLineEdit(self)

            # If numeric input field, placeholder should specify nanometers
            if column_name in DatabaseViewer.text_type_columns:
                input_field.setPlaceholderText(f"Enter text")
            else:
                input_field.setPlaceholderText(f"Enter value in nanometers")

            # Connect the return pressed event to the function that loads results from the database
            input_field.returnPressed.connect(self.search_database_and_display)

            # Add the input field to the dictionary of input fields
            self.input_fields[column_name] = input_field

            # Add label and input field to the grid layout
            self.grid_layout.addWidget(label, row, col)
            self.grid_layout.addWidget(input_field, row, col + 1)

            # Move to the next column; if the row has two columns, move to the next row
            col += 2
            if col >= 4:  # Adjust to increase or decrease the number of fields per row
                col = 0
                row += 1

            # Add the grid layout to the main layout
            self.central_layout.addLayout(self.grid_layout)

    @staticmethod
    def generate_filter(input_field: str, value: str) -> Any:
        # Fetch the relevant column from the database model
        column: Column = getattr(ResultModel, input_field, None)

        # Check if it's a text field
        if input_field in DatabaseViewer.text_type_columns:
            return column.ilike(f"%{value}%")

        # If not it's a number field
        else:
            # Check if input is a range (from_value, to_value)
            if "," in value:
                # Try to convert values to tuple of floats. If it doesn't work, go on until the next
                try:
                    from_value, to_value = map(str.strip, value.split(","))

                    # Convert to float
                    from_value = float(from_value)
                    to_value = float(to_value)

                    # Add the filter
                    return between(column, from_value, to_value)

                except ValueError as e:
                    print(e)
                    return None

            else:
                try:
                    return column == np.float16(value)

                # Ignore invalid inputs (non-numeric)
                except ValueError as e:
                    print(e)
                    return None

    def search_database_and_display(self) -> None:
        # Make a list of filters
        filters = []

        # Iterate over the search parameters in the input fields and create filters
        for key, field in self.input_fields.items():
            # Fetch the text from the input field
            value = str(field.text().strip())

            if value:
                filter = self.generate_filter(key, value)

                if filter is not None:
                    filters.append(filter)

        result_ids = self.db_handler.get_filtered_results(filters, only_ids=True)

        # Display the results in the table
        self.table.display_results(result_ids)

    @staticmethod
    def open_db_viewer(database: str) -> None:
        app = QApplication(sys.argv)
        window = DatabaseViewer(database)
        window.show()
        sys.exit(app.exec())


class DatabasePlotter(DatabaseHandler):

    def __init__(self, database_name: str):
        super().__init__(database_name)

    @staticmethod
    def setup_plot_style() -> None:
        """Sets up the plot aesthetics for a scientific publication look."""
        plt.style.use('ggplot')  # You can replace with 'bmh' or others
        plt.rcParams.update({
            'font.family': 'serif',  # Use a serif font like Times New Roman
            'font.size': 12,
            'axes.labelsize': 14,
            'axes.titlesize': 16,
            'legend.fontsize': 12,
            'xtick.labelsize': 12,
            'ytick.labelsize': 12,
            'lines.linewidth': 2,
            'lines.markersize': 6,
            'figure.figsize': (8, 6),
            'savefig.format': 'png',
            'savefig.bbox': 'tight'
        })

    @staticmethod
    def plot_spectrum(ax, lambdas, powers, label, color, linestyle='-', marker=None) -> None:
        """Plots a spectrum on the given axis."""
        ax.plot(lambdas, powers, label=label, color=color, linestyle=linestyle, marker=marker, markersize=4)

    @staticmethod
    def save_plot_if_needed(folder_name: str | None, file_name: str | None) -> None:
        """Saves the plot if folder_name and file_name are provided."""
        if folder_name and file_name:
            folder_path = os.path.join("../Saved_plots", folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"Created folder: {folder_path}")

            file_path = os.path.join(folder_path, file_name)
            if os.path.exists(file_path):
                user_input = input(f"The file '{file_name}' already exists. Overwrite? (y/n): ").lower()
                if user_input != 'y':
                    print("Plot not saved. Overwrite canceled.")
                    plt.show()
                    return

            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved as '{file_path}'")

    def spectrum_plot(self,
                      result_ids: List[int],
                      plot_type: Literal["reflection", "transmission", "reflection and transmission"],
                      folder_name: str | None = None,
                      file_name: str | None = None,
                      open_plot: bool = True,
                      vlines: List[float] | None = None,
                      show_title: bool = True) -> None:
        """
        Plots the spectrum (reflection, transmission, or both) for the specified result IDs.

        Args:
            result_ids (List[int]): List of result IDs to plot.
            plot_type (str): 'reflection', 'transmission', or 'both'.
        """
        results = self.get_entries_by_ids(result_ids)
        self.setup_plot_style()

        fig, ax = plt.subplots()
        colors = plt.cm.tab10(np.linspace(0, 1, len(results)))

        for idx, (result, color) in enumerate(zip(results, colors)):
            lambdas = result.lambdas

            if plot_type == 'reflection':
                self.plot_spectrum(ax, lambdas, result.ref_powers, f'Periodicity: {result.fdtd_xspan/2} nm', color)
            elif plot_type == 'transmission':
                self.plot_spectrum(ax, lambdas, result.trans_powers, f'Periodicity: {result.fdtd_xspan/2} nm', color)
            elif plot_type == 'reflection and transmission':
                self.plot_spectrum(ax, lambdas, result.ref_powers, 'Reflection', color, linestyle='--')
                self.plot_spectrum(ax, lambdas, result.trans_powers, 'Transmission', color, linestyle=':')
                self.plot_spectrum(ax, lambdas, result.ref_powers + result.trans_powers, 'Refl. + Trans.', color)

        if vlines is not None:
            for x in vlines:
                ax.axvline(x=x, color='black', linestyle='--', linewidth=1, label=None)

        ax.set_xlabel(r'Wavelength $\lambda$ [nm]', fontsize=14, labelpad=10)
        ax.set_ylabel(f'{plot_type.capitalize()} Power', fontsize=14, labelpad=10)
        if show_title:
            ax.set_title(f'{plot_type.capitalize()} Spectrum', fontsize=16, pad=15)

        ax.grid(True, which='major', linestyle='-', linewidth=1, alpha=1)
        ax.tick_params(which='major', length=6, width=1, direction='in')
        ax.tick_params(which='minor', length=4, width=0.7, direction='in')
        ax.minorticks_on()
        ax.set_xlim(
            [min(min(result.lambdas) for result in results) - 10, max(max(result.lambdas) for result in results) + 10])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.legend(loc='best', frameon=False)
        plt.tight_layout()

        self.save_plot_if_needed(folder_name, file_name)

        if open_plot:
            plt.show()

        plt.close()

    def plot_profile(self,
                     result_id: int,
                     plot_type: Literal["reflection", "transmission", "xz plane", "yz plane"],
                     distance: float,
                     input_wavelength: float | Literal["ref res", "trans res", "ref mag res", "trans mag res"] | None = None,
                     show_vectors: bool = False,
                     vector_scale: float = 1,
                     vector_steps: int = 1,
                     vector_width: float = 0.0005,
                     folder_name: str | None = None,
                     file_name: str | None = None,
                     open_plot: bool = True,
                     vlines: list[float] = None,
                     vgaps: list[list[tuple]] = None,
                     hlines: list[float] = None,
                     hgaps: list[list[tuple]] = None,
                     show_title: bool = True,
                     legend: bool = True,
                     vector_alpha: float = 1.0,
                     linecolor: str = "black",
                     linealpha: float = 0.5) -> None:

        self.setup_plot_style()

        # Fetch the result
        result = self.get_entries_by_ids([result_id])[0]

        # Positions
        if plot_type == "reflection" or plot_type == "transmission":
            x_pos = result.profile_x
            y_pos = result.profile_y
        elif plot_type == "xz plane":
            x_pos = result.xz_profile_x_coord
            y_pos = result.xz_profile_z_coord
        elif plot_type == "yz plane":
            x_pos = result.yz_profile_y_coord
            y_pos = result.yz_profile_z_coord

        if plot_type == "reflection":

            wavelengths = np.array(  # Fetch the wavelength for which the profile vectors are available
                list(
                    result.ref_profile_vectors[str(distance)].keys()
                )
            ).astype(np.float16)

            if input_wavelength is None:
                wavelength = wavelengths[  # From the list of available wavelength data, fetch the reflection resonance
                    np.argmin(
                        np.abs(
                            wavelengths - result.ref_power_res_lambda
                        )
                    )
                ]
            elif isinstance(input_wavelength, str):

                target = None

                if input_wavelength == "ref res":
                    target = result.ref_power_res_lambda
                elif input_wavelength == "trans res":
                    target = result.trans_power_res_lambda
                elif input_wavelength == "ref mag res":
                    target = result.ref_mag_res_lambda
                elif input_wavelength == "trans mag res":
                    target = result.trans_mag_res_lambda

                if target is None:
                    target = 0

                wavelength = wavelengths[  # Fetch the wavelength closest to the target wavelength
                    np.argmin(
                        np.abs(
                            wavelengths - target
                        )
                    )
                ]
            else:
                wavelength = wavelengths[  # Fetch the wavelength closest to the input wavelength
                    np.argmin(
                        np.abs(
                            wavelengths - input_wavelength
                        )
                    )
                ]

            # Fetch the coorect field profile and calculate magnitudes
            profile_vectors = result.ref_profile_vectors[str(distance)][str(wavelength)]
            magnitudes = np.linalg.norm(profile_vectors, axis=-1).T.astype(np.float16)

            # Get he vector field
            V_x = profile_vectors[:, :, 0]
            V_y = profile_vectors[:, :, 1]

        elif plot_type == "transmission":

            wavelengths = np.array(  # Fetch the wavelength for which the profile vectors are available
                list(
                    result.trans_profile_vectors[str(distance)].keys()
                )
            ).astype(np.float16)

            if input_wavelength is None:
                wavelength = wavelengths[  # From the list of available wavelength data, fetch the reflection resonance
                    np.argmin(
                        np.abs(
                            wavelengths - result.ref_power_res_lambda
                        )
                    )
                ]

            elif isinstance(input_wavelength, str):

                target = None

                if input_wavelength == "ref res":
                    target = result.ref_power_res_lambda
                elif input_wavelength == "trans res":
                    target = result.trans_power_res_lambda
                elif input_wavelength == "ref mag res":
                    target = result.ref_mag_res_lambda
                elif input_wavelength == "trans mag res":
                    target = result.trans_mag_res_lambda

                if target is None:
                    target = 0

                wavelength = wavelengths[  # Fetch the wavelength closest to the target wavelength
                    np.argmin(
                        np.abs(
                            wavelengths - target
                        )
                    )
                ]
            else:
                wavelength = wavelengths[  # Fetch the wavelength closest to the input wavelength
                    np.argmin(
                        np.abs(
                            wavelengths - input_wavelength
                        )
                    )
                ]

            # Fetch the coorect field profile and calculate magnitudes
            profile_vectors = result.trans_profile_vectors[str(distance)][str(wavelength)]
            magnitudes = np.linalg.norm(profile_vectors, axis=-1).T.astype(np.float16)

            # Get he vector field
            V_x = profile_vectors[:, :, 0]
            V_y = profile_vectors[:, :, 1]

        elif plot_type == "xz plane":

            wavelengths = np.array(  # Fetch the wavelength for which the profile vectors are available
                list(
                    result.xz_profile_E_vectors[str(distance)].keys()
                )
            ).astype(np.float16)

            if input_wavelength is None:
                target = result.ref_power_res_lambda
                if target is None: target = 0
                wavelength = wavelengths[  # From the list of available wavelength data, fetch the reflection resonance
                    np.argmin(
                        np.abs(
                            wavelengths - target
                        )
                    )
                ]
            elif isinstance(input_wavelength, str):

                target = None

                if input_wavelength == "ref res":
                    target = result.ref_power_res_lambda
                elif input_wavelength == "trans res":
                    target = result.trans_power_res_lambda
                elif input_wavelength == "ref mag res":
                    target = result.ref_mag_res_lambda
                elif input_wavelength == "trans mag res":
                    target = result.trans_mag_res_lambda

                if target is None:
                    target = 0

                wavelength = wavelengths[  # Fetch the wavelength closest to the target wavelength
                    np.argmin(
                        np.abs(
                            wavelengths - target
                        )
                    )
                ]
            else:
                wavelength = wavelengths[  # Fetch the wavelength closest to the input wavelength
                    np.argmin(
                        np.abs(
                            wavelengths - input_wavelength
                        )
                    )
                ]

            # Fetch the coorect field profile and calculate magnitudes
            profile_vectors = result.xz_profile_P_vectors[str(distance)][str(wavelength)]
            magnitudes = np.linalg.norm(result.xz_profile_E_vectors[str(distance)][str(wavelength)], axis=-1).T.astype(np.float16)

            # Get he vector field
            V_x = profile_vectors[:, :, 0]
            V_y = profile_vectors[:, :, 2]

        if plot_type == "reflection" or plot_type == "transmission":
            title = rf"{plot_type.capitalize()} field-map at $\lambda$ = {wavelength} nm"
            x_label = "x-position [nm]"
            y_label = "y-position [nm]"
            vector_label = "E-field vectors"
        elif plot_type == "xz plane":
            title = rf"{plot_type.capitalize()} field-map at $\lambda$ = {wavelength} nm"
            x_label = "x-position [nm]"
            y_label = "y-position [nm]"
            vector_label = "Poynting vectors"

        # Create a new figure and axis for plotting
        fig, ax = plt.subplots()

        # Create meshgrid for positions
        X, Y = np.meshgrid(x_pos, y_pos)

        # Plot the heatmap using pcolormesh
        heatmap = ax.pcolormesh(X, Y, magnitudes, shading='auto', cmap='viridis')
        cbar = fig.colorbar(heatmap, ax=ax, label="Magnitude")


        # Assuming ax is your axes object
        if vgaps is None:
            vgaps = [[] for _ in vlines]  # Create an empty list for each vline if vgaps is not provided

        if hgaps is None:
            hgaps = [[] for _ in
                     hlines] if hlines is not None else []  # Create an empty list for each hline if hgaps is not provided

        if vlines is not None:
            for x, gaps in zip(vlines, vgaps):  # Loop through each x-coordinate and its corresponding gaps
                ymin, ymax = ax.get_ylim()  # Get the y-limits of the plot

                # If vgaps are provided for the current vline, draw the lines only outside the gaps
                start_y = ymin
                if gaps:  # Ensure that there are gaps to process
                    for gap_start, gap_stop in gaps:
                        # Handle special cases for "min" and "max"
                        if gap_start == "min":
                            gap_start = ymin
                        if gap_stop == "max":
                            gap_stop = ymax

                        # Draw the line from start_y to the beginning of the gap
                        if start_y < gap_start:
                            ax.vlines(x, ymin=start_y, ymax=gap_start, color=linecolor, linestyle='--', linewidth=1,
                                      alpha=linealpha)
                        # Update start_y to the end of the gap
                        start_y = gap_stop

                    # Draw the final line after the last gap
                    if start_y < ymax:
                        ax.vlines(x, ymin=start_y, ymax=ymax, color=linecolor, linestyle='--', linewidth=1, alpha=linealpha)
                else:
                    # If no gaps are provided for this line, just draw the full line
                    ax.vlines(x, ymin=ymin, ymax=ymax, color=linecolor, linestyle='--', linewidth=1, alpha=linealpha)

            # Plotting horizontal lines with gaps
            if hlines is not None:
                for y, gaps in zip(hlines, hgaps):  # Loop through each y-coordinate and its corresponding gaps
                    xmin, xmax = ax.get_xlim()  # Get the x-limits of the plot

                    # If hgaps are provided for the current hline, draw the lines only outside the gaps
                    start_x = xmin
                    if gaps:  # Ensure that there are gaps to process
                        for gap_start, gap_stop in gaps:
                            # Handle special cases for "min" and "max"
                            if gap_start == "min":
                                gap_start = xmin
                            if gap_stop == "max":
                                gap_stop = xmax

                            # Draw the line from start_x to the beginning of the gap
                            if start_x < gap_start:
                                ax.hlines(y, xmin=start_x, xmax=gap_start, color=linecolor, linestyle='--', linewidth=1,
                                          alpha=linealpha)
                            # Update start_x to the end of the gap
                            start_x = gap_stop

                        # Draw the final line after the last gap
                        if start_x < xmax:
                            ax.hlines(y, xmin=start_x, xmax=xmax, color=linecolor, linestyle='--', linewidth=1, alpha=linealpha)
                    else:
                        # If no gaps are provided for this line, just draw the full line
                        ax.hlines(y, xmin=xmin, xmax=xmax, color=linecolor, linestyle='--', linewidth=1, alpha=linealpha)

        # Quiver plot for vectors (if needed)
        if show_vectors:
            scale = vector_scale  # Adjust as needed
            step = vector_steps
            X_sub = X[::step, ::step]
            Y_sub = Y[::step, ::step]
            V_x_sub = V_x.T[::step, ::step]
            V_y_sub = V_y.T[::step, ::step]

            ax.quiver(
                X_sub,
                Y_sub,
                V_x_sub,
                V_y_sub,
                color='white',
                scale=scale,
                width=vector_width,
                label=vector_label,
                alpha=vector_alpha
            )

        # Set labels and title
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        if show_title:
            ax.set_title(title)

        # Add a legend if vectors are shown
        if show_vectors and legend:
            ax.legend()

        # Adjust layout and show the plot
        fig.tight_layout()

        self.save_plot_if_needed(folder_name, file_name)

        if open_plot:
            plt.show()

        plt.close()


