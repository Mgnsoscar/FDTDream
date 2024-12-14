from __future__ import annotations

# Standard library imports
import sys
import os
import tkinter as tk
import warnings
from tkinter import ttk
from typing import Unpack, List, ClassVar, Dict, Literal, Tuple, Any, cast
from dataclasses import dataclass, field
from tkinter import Tk, filedialog
from copy import copy as pythoncopy

# Third party library imports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from scipy.ndimage import label
from matplotlib import pyplot as plt
from scipy.spatial import ConvexHull
import gdspy
from PIL import Image
import numpy as np
from numpy import ndarray

# Local library imports
from base_classes import SimulationBase, TSimulationObject, Settings, TStructure, GlobalSettingTab, Structure
from Code.Resources.literals import (LENGTH_UNITS, MATERIALS, MONITOR_TYPES_ALL, MONITOR_TYPES_3D, INJECTION_AXES,
                                     DIRECTIONS, EXTRACTION_TYPES)
from structures import (Rectangle, Circle, Ring, Pyramid, Polygon, EquilateralPolygon, Sphere, LayoutGroup,
                        StructureGroup, Group, TPolygon, PolygonStructureBase, RectangularLattice)
from Code.Resources.lumapi_import import lumapi
from Code.Resources.local_resources import (Validate, get_unique_name, convert_length, reverse_dict_order)
from materials import MaterialDatabase
from fdtd_region import Mesh, FDTDRegion
from monitors import FreqDomainFieldAndPower, IndexMonitor, GlobalMonitorSettings, MonitorBase
from sources import PlaneWaveSource, GaussianSource, CauchyLorentzianSource, GlobalSource, SourceBase


class Plot3DApp:
    def __init__(self, index_model: Simulation._IndexModel):
        self.root = tk.Tk()
        self.index_model = index_model

        # Current selection for what to plot
        self.what_to_plot = tk.StringVar(value="materials")
        self.selected_id = tk.StringVar(value="All Ids")  # Default to show all ids

        # GUI Layout
        self._create_gui()
        self.root.mainloop()

    def _create_gui(self):

        # Dropdown for selecting what to plot
        ttk.Label(self.root, text="Select Plot:").pack(side=tk.TOP, pady=5)
        options = ["materials", "structures", "layers"]
        ttk.OptionMenu(
            self.root,
            self.what_to_plot,
            self.what_to_plot.get(),
            *options,
            command=self._update_id_dropdown
        ).pack(side=tk.TOP, pady=5)

        # Dropdown for selecting an ID
        self.id_dropdown_label = ttk.Label(self.root, text="Select ID:")
        self.id_dropdown_label.pack(side=tk.TOP, pady=5)

        self.id_dropdown = ttk.OptionMenu(self.root, self.selected_id, "All Ids")
        self.id_dropdown.pack(side=tk.TOP, pady=5)

        # Bind selected_id to _update_plot
        self.selected_id.trace("w", lambda *_: self._update_plot())

        # Create a placeholder for the Matplotlib figure
        self.fig = Figure(figsize=(12, 10))
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Add a Matplotlib navigation toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.root)
        self.toolbar.update()
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Initial plot
        self._update_id_dropdown()
        self._plot_3d()

    def _update_id_dropdown(self, *_):
        """Update the ID dropdown based on the selected plot type."""
        # Determine available IDs based on the selected plot type
        if self.what_to_plot.get() == "materials":
            available_ids = [str(i + 1) for i in range(len(self.index_model.materials))]
        elif self.what_to_plot.get() == "structures":
            available_ids = [str(i + 1) for i in range(len(self.index_model.structures))]
        elif self.what_to_plot.get() == "layers":
            available_ids = [str(i + 1) for i in range(len(self.index_model.layers))]
        else:
            available_ids = []

        # Prepend "All Ids" to the list
        available_ids = ["All Ids"] + available_ids

        # Update the ID dropdown
        menu = self.id_dropdown["menu"]
        menu.delete(0, "end")  # Clear the existing options
        for id_value in available_ids:
            menu.add_command(
                label=id_value, command=lambda value=id_value: self.selected_id.set(value)
            )

        # Set default ID to "All Ids"
        self.selected_id.set("All Ids")

        self._plot_3d()

    def _plot_3d(self, spotsize=20, alpha=0.5):
        # Clear the previous plot
        self.ax.clear()

        self.index_model.__getattribute__("_plot_3d")(self.ax,
                                                      self.what_to_plot.get(),
                                                      spotsize=spotsize,
                                                      alpha=alpha,
                                                      id_=self.selected_id.get())

        # Redraw the canvas
        self.canvas.draw()

    def _update_plot(self):
        # Redraw the plot when selection changes
        self._plot_3d()


class Collection(GlobalSettingTab):
    _simulation: Simulation
    __slots__ = GlobalSettingTab.__slots__

    def _get_parameter(self, *args) -> None:
        return None

    def _set_parameter(self, *args) -> None:
        return None

    def _get_active_parameters(self) -> None:
        return None


class SimulationAddMethods(Collection):
    class _Structures(Collection):

        __slots__ = Collection.__slots__

        def rectangle(self, name: str, **kwargs: Unpack[Rectangle._Kwargs]) -> Rectangle:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addrect(name=name)
            rectangle = Rectangle(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").structures.append(rectangle)
            return rectangle

        def circle(self, name: str, **kwargs: Unpack[Circle._Kwargs]) -> Circle:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addcircle(name=name)
            circle = Circle(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").structures.append(circle)
            return circle

        def sphere(self, name: str, **kwargs: Unpack[Sphere._Kwargs]) -> Sphere:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addsphere(name=name)
            sphere = Sphere(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").structures.append(sphere)
            return sphere

        def ring(self, name: str, **kwargs: Unpack[Ring._Kwargs]) -> Ring:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addring(name=name)
            ring = Ring(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").structures.append(ring)
            return ring

        def pyramid(self, name: str, **kwargs: Unpack[Pyramid._Kwargs]) -> Pyramid:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addpyramid(name=name)
            pyramid = Pyramid(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").structures.append(pyramid)
            return pyramid

        def polygon(self, name: str, **kwargs: Unpack[Polygon._Kwargs]) -> Polygon:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addpoly(name=name)
            polygon = Polygon(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").structures.append(polygon)
            return polygon

        def equilateral_polygon(self, name: str, nr_sides: int, **kwargs: Unpack[EquilateralPolygon._Kwargs]
                                ) -> EquilateralPolygon:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addpoly(name=name)
            polygon = EquilateralPolygon(name, self._simulation, nr_sides, **kwargs)
            self._simulation.__getattribute__("_active_objects").structures.append(polygon)
            return polygon

        def substrate(self, name: str, material: MATERIALS, fdtd_multiplier: float = 3) -> Rectangle:
            """
            Adds a rectangular structure that is has spans 'fdtd_multiplier' times the spans of the fdtd_region.
            Places the substrate so the top surface is placed in the middle of the fdtd-region.

            Raises a RuntimeError if no fdtd-region has been added to the simulation.

            Parameters:
                name (str): Name of the substrate object. Must be a unique name.
                material (MATERIALS): The material to assign the substrate.
                fdtd_multiplier (float): How many times larger than the fdtd-spans the substrate's spans will be. Cannot be
                                        smaller than 1.
                                        NB! It should in most cases be bigger than this, as you usually
                                        want the substrate to extend beyond the boundary layers. The PML layer thicknesses
                                        are dependent on the simulation mesh, which might change based on the objects you
                                        add to the simulation. Give yourself a good margin.
            """
            if getattr(self._simulation, "_fdtd", None) is None:
                raise RuntimeError("You can't add a substrate before adding an fdtd-region, as the substrate "
                                   "dimensions are based on the dimensions of the fdtd_region.")
            fdtd = self._simulation.__getattribute__("_fdtd")
            substrate = self.rectangle(name, x_span=fdtd.x_span * fdtd_multiplier, y_span=fdtd.y_span * fdtd_multiplier,
                                       z_span=fdtd.z_span * fdtd_multiplier, z=fdtd.z_min * fdtd_multiplier,
                                       material=material)
            return substrate

    class _Monitors(Collection):

        __slots__ = Collection.__slots__

        def index_monitor(self, name: str, monitor_type: MONITOR_TYPES_3D, **kwargs: Unpack[IndexMonitor._Kwargs]
                          ) -> IndexMonitor:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addindex(name=name)
            kwargs = {"monitor_type": monitor_type, **kwargs}
            index_monitor = IndexMonitor(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").monitors.append(index_monitor)
            return index_monitor

        def power_monitor(
                self, name: str, monitor_type: MONITOR_TYPES_ALL,
                **kwargs: Unpack[FreqDomainFieldAndPower._Kwargs]) -> FreqDomainFieldAndPower:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addpower(name=name)
            kwargs = {"monitor_type": monitor_type, **kwargs}
            power_monitor = FreqDomainFieldAndPower(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").monitors.append(power_monitor)
            return power_monitor

        def profile_monitor(
                self, name: str, monitor_type: MONITOR_TYPES_ALL,
                **kwargs: Unpack[FreqDomainFieldAndPower._Kwargs]) -> FreqDomainFieldAndPower:
            name = name.replace(" ", "_")
            kwargs = {**{"monitor_type": monitor_type}, **kwargs}
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addpower(name=name)
            power_monitor = FreqDomainFieldAndPower(name, self._simulation, **kwargs)
            power_monitor.settings.advanced.set_spatial_interpolation("specified position")
            self._simulation.__getattribute__("_active_objects").monitors.append(power_monitor)
            return power_monitor

    class _Sources(Collection):

        __slots__ = Collection.__slots__

        def plane_wave(self, name: str, injection_axis: INJECTION_AXES, direction: DIRECTIONS,
                       **kwargs: Unpack[PlaneWaveSource._Kwargs]) -> PlaneWaveSource:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addplane(name=name)
            kwargs = {"injection_axis": injection_axis, "direction": direction, **kwargs}
            plane_source = PlaneWaveSource(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").sources.append(plane_source)
            return plane_source

        def gaussian(self, name: str, injection_axis: INJECTION_AXES, direction: DIRECTIONS,
                     **kwargs: Unpack[GaussianSource._Kwargs]) -> GaussianSource:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addgaussian(name=name)
            kwargs = {"injection_axis": injection_axis, "direction": direction, **kwargs}
            gaussian_source = GaussianSource(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").sources.append(gaussian_source)
            return gaussian_source

        def cauchy_lorentzian(self, name: str, injection_axis: INJECTION_AXES, direction: DIRECTIONS,
                              **kwargs: Unpack[CauchyLorentzianSource._Kwargs]) -> CauchyLorentzianSource:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addgaussian(name=name)
            kwargs = {"injection_axis": injection_axis, "direction": direction, **kwargs}
            cauchy_source = CauchyLorentzianSource(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").sources.append(cauchy_source)
            return cauchy_source

    class _Simulation(Collection):

        __slots__ = Collection.__slots__

        def mesh(self, name: str, **kwargs: Unpack[Mesh._Kwargs]) -> Mesh:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addmesh(name=name)
            mesh = Mesh(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").meshes.append(mesh)
            return mesh

        def fdtd_region(self, **kwargs: Unpack[FDTDRegion._Kwargs]) -> FDTDRegion:
            self._simulation.__getattribute__("_validate_unique_name")("FDTD")
            self._simulation.__getattribute__("_lumapi").addfdtd()
            fdtd = FDTDRegion(self._simulation, **kwargs)
            self._simulation.__setattr__("_fdtd", fdtd)
            return fdtd

    class _Layers(Collection):
        __slots__ = Collection.__slots__

        def on_circle(self, circle: Circle, name: str, thickness: float, material: MATERIALS,
                      index: str | float = None) -> Circle:
            """
            Adds a layer with the specified thickness and material on top of the structure corresponding to the
            'circle' argument. The new layer will have the exact same shape as the structure it's placed upon.
            Will only work if the 'circle' argument is actually a circle structure.
            """
            if not isinstance(circle, Circle):
                raise ValueError(f"Expected 'Circle', got '{circle.__class__.__name__}'.")
            layer = self._simulation.functions.copy(circle, name)
            layer.settings.material.set_material(material, index)
            layer.settings.geometry.set_z_span(thickness)
            layer.place_on_top_of(circle)
            return layer

        def on_rectangle(self, rectangle: Rectangle, name: str, thickness: float, material: MATERIALS,
                         index: str | float = None) -> Rectangle:
            """
            Adds a layer with the specified thickness and material on top of the structure corresponding to the
            'rectangle' argument. The new layer will have the exact same shape as the structure it's placed upon.
            Will only work if the 'rectangle' argument is actually a rectangle structure.
            """
            if not isinstance(rectangle, Rectangle):
                raise ValueError(f"Expected 'Rectangle', got '{rectangle.__class__.__name__}'.")
            layer = self._simulation.functions.copy(rectangle, name)
            layer.z_span = thickness
            layer.place_on_top_of(rectangle)
            layer.settings.material.set_material(material, index)
            return layer

        def on_pyramid(self, pyramid: Pyramid, name: str, thickness: float, material: MATERIALS,
                       index: str | float = None) -> Rectangle:
            """
            Adds a layer with the specified thickness and material on top of the structure corresponding to the
            'pyramid' argument. The new layer will have the exact same shape as the structure it's placed upon.
            Will only work if the 'pyramid' argument is actually a pyramid structure.
            """
            if not isinstance(pyramid, Pyramid):
                raise ValueError(f"Expected 'Pyramid', got '{pyramid.__class__.__name__}'.")
            layer = self._simulation.add.structures.rectangle(name, x_span=pyramid.x_span_top,
                                                              y_span=pyramid.y_span_top, z_span=thickness,
                                                              material=material, index=index)
            layer.place_on_top_of(pyramid)
            return layer

        def on_ring(self, ring: Ring, name: str, thickness: float, material: MATERIALS,
                    index: str | float = None) -> Ring:
            """
            Adds a layer with the specified thickness and material on top of the structure corresponding to the
            'ring' argument. The new layer will have the exact same shape as the structure it's placed upon.
            Will only work if the 'ring' argument is actually a ring structure.
            """
            if not isinstance(ring, Ring):
                raise ValueError(f"Expected 'Ring', got '{ring.__class__.__name__}'.")
            layer = self._simulation.functions.copy(ring, name)
            layer.z_span = thickness
            layer.place_on_top_of(ring)
            layer.settings.material.set_material(material, index)
            return layer

        def on_polygon(self, polygon: TPolygon, name: str, thickness: float,
                       material: MATERIALS, index: str | float = None) -> TPolygon:
            """
            Adds a layer with the specified thickness and material on top of the structure corresponding to the
            'polygon' argument. The new layer will have the exact same shape as the structure it's placed upon.
            Will only work if the 'polygon' argument is actually a polygon structure.
            """
            if not isinstance(polygon, PolygonStructureBase):
                raise ValueError(f"Expected 'Polygon' or 'EquilateralPolygon', got '{polygon.__class__.__name__}'.")
            layer = self._simulation.functions.copy(polygon, name)
            layer.z_span = thickness
            layer.place_on_top_of(polygon)
            layer.settings.material.set_material(material, index)
            return layer

    class _Grids(Collection):
        __slots__ = Collection.__slots__

        def rectangular(self, name: str, **kwargs: Unpack[RectangularLattice._Kwargs]
                             ) -> RectangularLattice:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addstructuregroup(name=name)
            layout_group = RectangularLattice(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").layout_groups.append(layout_group)
            return layout_group

    class _Groups(Collection):
        __slots__ = Collection.__slots__

        def layout_group(self, name: str, **kwargs: Unpack[LayoutGroup._Kwargs]) -> LayoutGroup:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addgroup(name=name)
            layout_group = LayoutGroup(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").layout_groups.append(layout_group)
            return layout_group

        def structure_group(self, name: str, **kwargs: Unpack[StructureGroup._Kwargs]) -> StructureGroup:
            name = name.replace(" ", "_")
            self._simulation.__getattribute__("_validate_unique_name")(name)
            self._simulation.__getattribute__("_lumapi").addstructuregroup(name=name)
            structure_group = StructureGroup(name, self._simulation, **kwargs)
            self._simulation.__getattribute__("_active_objects").structure_groups.append(structure_group)
            return structure_group

    _settings = [_Structures, _Monitors, _Sources, _Layers, _Simulation, _Grids]
    _settings_names = ["structures", "monitors", "sources", "layer", "simulation", "groups", "grids"]

    structures: _Structures
    monitors: _Monitors
    sources: _Sources
    simulation: _Simulation
    layer: _Layers
    groups: _Groups
    grids: _Grids
    __slots__ = Collection.__slots__ + _settings_names

    def __init__(self, simulation: Simulation):
        super().__init__(simulation)
        self.structures = self._Structures(simulation)
        self.monitors = self._Monitors(simulation)
        self.sources = self._Sources(simulation)
        self.simulation = self._Simulation(simulation)
        self.layer = self._Layers(simulation)
        self.groups = self._Groups(simulation)
        self.grids = self._Grids(simulation)


class SimulationProperties(Collection):
    __slots__ = GlobalSettingTab.__slots__

    @property
    def fdtd(self) -> FDTDRegion:
        fdtd = self._simulation.__getattribute__("_fdtd")
        if fdtd is not None:
            return fdtd
        else:
            raise ValueError("An FDTD-Region has not yet been added to the simulation.")

    @property
    def global_units(self) -> LENGTH_UNITS:
        return self._simulation.__getattribute__("_global_units")

    @property
    def lumapi(self) -> lumapi.FDTD:
        return self._simulation.__getattribute__("_lumapi")


class SimulationFunctions(Collection):
    __slots__ = Collection.__slots__

    def copy(self, simulation_object: TSimulationObject, new_object_name: str,
             **kwargs: Unpack[TSimulationObject._Kwargs]) -> TSimulationObject:
        lpi = self._simulation.__getattribute__("_lumapi")
        new_object_name = new_object_name.replace(" ", "_")
        lpi.select(simulation_object.name)
        lpi.copy()
        lpi.set("name", new_object_name)
        new_structure = pythoncopy(simulation_object)
        if hasattr(new_structure, "settings"):
            new_structure.settings.__init__(new_structure, self._simulation)
            new_structure._name = new_object_name
        elif hasattr(new_structure, "set_structure"):
            new_structure._name = new_object_name
            old_settings = pythoncopy(simulation_object.set_structure._current_settings)
            new_structure.set_structure.__init__(new_structure)
            new_structure.set_structure._current_settings = old_settings
            new_structure._create_grid()
        new_structure.__getattribute__("_apply_kwargs")(**kwargs)
        self._simulation.__getattribute__("_validate_unique_name")(new_object_name)
        group = getattr(simulation_object, "_group", None)
        if group is not None:
            setattr(new_structure, "_group", group)
            group.__getattribute__("_grouped_objects").append(new_structure)
        return new_structure


class SimulationUtilities(Collection):
    __slots__ = Collection.__slots__

    def create_bmp_and_gds_of_crosssection(self, filename: str, z: float, pixelsize: int,
                                           rows: int = 1, columns: int = 1, units: LENGTH_UNITS = None,
                                           print_progress: bool = False,
                                           gds: bool = True,
                                           config_fdtd: bool = True,
                                           reconfig_fdtd: bool = True) -> None:
        """
        Analyzes the simulation enviroment and creates a bitmap and a gds-file of the cross section at the specified
        z-coordinate.

        Parameters:
            filename (str): Name of the output files. Does not need to include .bmp and .gds suffixes.
            z (float): The z-cooordinate to take the cross section at.
            pixelsize (int): The dimensions of each pixel in the resulting bitmap, and each square in the
                                        gds-file.
            rows (Optional[int]): The amount of times to repeat the unit cell in the y-direction.
            columns (Optional[int]): The amount of times to repeat the unit cell in the z-direction.
            units (Optional[LENGTH_UNITS]): If None is passed, the global units are used. Defaults to None.
            print_progress (Optional[bool]): If True, everything that is being done to the simulation will be printed
                                                to the console.
        """
        self._simulation._create_bmp_and_gds_of_crosssection(filename, z, pixelsize, rows, columns, units,
                                                             print_progress)


class SimulationObjectInterfaces(Collection):
    class _ObjectInterface:
        def __new__(cls, *args, **kwargs):
            raise UserWarning("This is only an interface object, and should only be used for type hinting and "
                              "autocompletion. It is not meant to be initialized. If you want to add this object, "
                              "use the appropriate adding method of the simulation instance.")

    class RectangleInterface(Rectangle, _ObjectInterface):
        ...

    class CircleInterface(Circle, _ObjectInterface):
        ...

    class SphereInterface(Sphere, _ObjectInterface):
        ...

    class RingInterface(Ring, _ObjectInterface):
        ...

    class PyramidInterface(Pyramid, _ObjectInterface):
        ...

    class PolygonInterface(Polygon, _ObjectInterface):
        ...

    class EquilateralPolygonInterface(EquilateralPolygon, _ObjectInterface):
        ...

    class FreqDomainFieldAndPowerInterface(FreqDomainFieldAndPower, _ObjectInterface):
        ...

    class IndexMonitorInterface(IndexMonitor, _ObjectInterface):
        ...

    class PlaneWaveSourceInterface(PlaneWaveSource, _ObjectInterface):
        ...

    class GaussianSourceInterface(GaussianSource, _ObjectInterface):
        ...

    class CauchyLorentzianSourceInterface(CauchyLorentzianSource, _ObjectInterface):
        ...

    class MeshInterface(Mesh, _ObjectInterface):
        ...

    class FDTDRegionInterface(FDTDRegion, _ObjectInterface):
        ...

    class LayoutGroupInterface(LayoutGroup, _ObjectInterface):
        ...

    class StructureGroupInterface(StructureGroup, _ObjectInterface):
        ...

    loaded_object: Dict[str, TSimulationObject] = {}


class Simulation(SimulationBase):
    @dataclass
    class _ActiveObjects(Settings):
        structures: List[TStructure] = field(default_factory=list)
        monitors: List[TSimulationObject] = field(default_factory=list)
        sources: List[TSimulationObject] = field(default_factory=list)
        meshes: List[Mesh] = field(default_factory=list)
        layout_groups: List[LayoutGroup] = field(default_factory=list)
        structure_groups: List[StructureGroup] = field(default_factory=list)
        analysis_groups: List[Group] = field(default_factory=list)
        used_names: List[str] = field(default_factory=list)

    @dataclass
    class _Layer:
        id: int
        material_id: int
        mask: np.ndarray

        def get_name(self) -> str:
            return f"Layer id.: {self.id} - Material id: {self.material_id}"

    @dataclass
    class _Structure:
        id: int
        material_id: int
        layer_id: int
        mask: np.ndarray

        def get_name(self) -> str:
            return f"Structure id: {self.id} - Material id: {self.material_id} - Layer id.: {self.layer_id}"

    @dataclass
    class _Material:
        id: int
        mask: np.ndarray

        def get_name(self) -> str:
            return f"Material id: {self.id}"

    @dataclass
    class _IndexModel(Settings):
        x: np.ndarray
        y: np.ndarray
        z: np.ndarray
        refractive_indices: np.ndarray
        mask: np.ndarray
        materials: List[Simulation._Material]
        structures: List[Simulation._Structure]
        layers: List[Simulation._Layer]

        def _plot_3d(self, ax, what_to_plot: Literal["materials", "structures", "layers"],
                     spotsize: int = 20, alpha: float = 0.5, id_: str = "All Ids") -> None:

            for axis in [self.x, self.y, self.z]:
                if axis is None:
                    raise ValueError("You can't plot a 3d model when the dataset is not 3-dimensional.")

            # Generate 3D grid of coordinates
            X, Y, Z = np.meshgrid(self.x, self.y, self.z, indexing="ij")

            if what_to_plot == "materials":
                plot_objs = self.materials
            elif what_to_plot == "structures":
                plot_objs = self.structures
            elif what_to_plot == "layers":
                plot_objs = self.layers
            else:
                raise ValueError(f"'{what_to_plot}' is not a valid argument for 'what_to_plot'. Choose from "
                                 f"['materials', 'structures'', 'layers'']")

            # Use a colormap for materials
            cmap = ("red", "blue", "green", "black", "orange", "brown", "cyan", "purple")

            color_idx = 0
            for obj in plot_objs:

                if id_ != "All Ids" and str(obj.id) != id_:
                    continue

                # Fetch color
                color = cmap[color_idx]
                color_idx += 1
                if color_idx - 1 > len(cmap):
                    color_idx = 0

                # Get coordinates of the material
                x_indices, y_indices, z_indices = np.where(obj.mask)  # Find True values in mask
                x_coords = X[x_indices, y_indices, z_indices]
                y_coords = Y[x_indices, y_indices, z_indices]
                z_coords = Z[x_indices, y_indices, z_indices]

                # Plot the material
                ax.scatter(x_coords, y_coords, z_coords, color=color, label=obj.get_name(), s=20, alpha=0.5)

            # Set axis labels and legend
            ax.set_xlim(min(self.x), max(self.x))
            ax.set_ylim(min(self.y), max(self.y))
            ax.set_zlim(min(self.z), max(self.z))

            ax.set_title(f"3D Model of {what_to_plot}")
            ax.set_xlabel("X-axis")
            ax.set_ylabel("Y-axis")
            ax.set_zlabel("Z-axis")
            ax.legend(loc="best")
            plt.show()

        def plot_materials(self, spotsize: int = 20, alpha: float = 0.5) -> None:
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection="3d")
            self._plot_3d(ax, what_to_plot="materials", spotsize=spotsize, alpha=alpha)  # type: ignore

        def plot_structures(self, spotsize: int = 20, alpha: float = 0.5) -> None:
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection="3d")
            self._plot_3d(ax, "structures", spotsize=spotsize, alpha=alpha)  # type: ignore

        def plot_layers(self, spotsize: int = 20, alpha: float = 0.5) -> None:
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection="3d")
            self._plot_3d(ax, "layers", spotsize=spotsize, alpha=alpha)  # type: ignore

    @dataclass
    class _IndexValues3D(Settings):
        x: np.ndarray
        y: np.ndarray
        z: np.ndarray
        refractive_indices: np.ndarray

    _type_to_class_map: ClassVar[Dict[str, type]] = {
        "Rectangle": Rectangle, "Circle": Circle, "Sphere": Sphere, "Ring": Ring, "Pyramid": Pyramid,
        "Polygon": Polygon, "GaussianSource": GaussianSource, "Cauchy-Lorentzian": CauchyLorentzianSource,
        "PlaneSource": PlaneWaveSource, "IndexMonitor": IndexMonitor, "DFTMonitor": FreqDomainFieldAndPower,
        "FDTD": FDTDRegion, "Mesh": Mesh, "Structure Group": StructureGroup, "Layout Group": LayoutGroup}

    _type_to_list_map: ClassVar[Dict] = {

    }

    _fdtd: FDTDRegion | None
    global_monitor_settings: GlobalMonitorSettings
    global_source_settings: GlobalSource
    _material_database: MaterialDatabase
    add: SimulationAddMethods
    properties: SimulationProperties
    functions: SimulationFunctions
    utilities: SimulationUtilities
    object_interfaces: SimulationObjectInterfaces
    _print_progress: bool

    def __init__(self, lumapi: lumapi.FDTD, save_path: os.path = None, global_units: LENGTH_UNITS = "nm") -> None:

        # Assign lumerical API
        self._lumapi = lumapi

        # Save the simulation
        self._save_path = save_path

        self.save()

        # Validate and assign global units
        Validate.in_literal(global_units, "global_units", LENGTH_UNITS)
        self._global_units = global_units

        # Initialize member variables
        self._active_objects = self._ActiveObjects(hash=None)
        self._save_path = save_path
        self._material_database = MaterialDatabase(self)
        self._fdtd = None

        # Initialize method collections
        self.global_source_settings = GlobalSource(self)
        self.global_monitor_settings = GlobalMonitorSettings(self)
        self.add = SimulationAddMethods(self)
        self.functions = SimulationFunctions(self)
        self.utilities = SimulationUtilities(self)
        self.properties = SimulationProperties(self)
        self.object_interfaces = SimulationObjectInterfaces(self)

        # Initialize progress string
        self._print_progress = False

    def _save_temp(self) -> None:
        """
        Saves a temporary `.fsp` file of the current simulation state to ensure that scripted functions
        within the simulation take effect.

        This method creates a temporary directory named "Temp_savefiles" in the parent directory, if it
        doesn’t already exist, and saves the simulation to a file named `temporary_savefile.fsp` within
        this directory. Saving a temporary file is particularly useful for applying changes made via
        scripting functions, allowing the simulation environment to update with these changes.
        """

        # Define the directory and file path
        temp_dir = os.path.abspath(os.path.join("..", "Temp_savefiles"))
        os.makedirs(temp_dir, exist_ok=True)  # Create directory if it doesn't exist

        # Define the file path in the Temp_savefiles directory (replace 'file_to_delete.txt' with the actual file name)
        file_path = os.path.join(temp_dir, "temporary_savefile.fsp")

        self.save(save_path=file_path)

    @staticmethod
    def _delete_temp() -> None:
        """
        Deletes the temporary `.fsp` file and its containing directory created to apply scripted
        functions in the simulation environment.

        This method removes the file `temporary_savefile.fsp` and the `Temp_savefiles` directory
        in the parent folder, if they exist. It ensures no residual files or directories are left
        in the system after the operation.
        """

        # Define the directory path
        temp_dir = os.path.abspath(os.path.join("..", "Temp_savefiles"))

        # Delete the file and directory if they exist
        if os.path.isdir(temp_dir):
            # Iterate over and delete all files in the directory
            for file_name in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            # Remove the directory after all files are deleted
            os.rmdir(temp_dir)

    def _get_simulation_objects_in_scope(self, groupscope: str, autoset_new_unique_names: bool,
                                         iterated: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        Recursively retrieves all simulation objects within a specified scope, including nested groups,
        returning a list of dictionaries with object details. Each dictionary contains the object's name,
        type, and scope information, providing a structured representation of the simulation hierarchy.

        Parameters:
        -----------
        groupscope : str
            The name of the group scope to explore, starting with the provided scope and iterating through
            nested groups if present.

        autoset_new_unique_names : bool
            If `True`, assigns unique names to objects by automatically adjusting names to avoid duplicates
            within the scope. This is helpful in complex simulations with potentially overlapping object names.

        iterated : List[Dict[str, str]], optional
            A list of dictionaries representing objects that have already been processed. This list is used
            during recursion to aggregate results across nested group scopes.

        Returns:
        --------
        List[Dict[str, str]]
            A list of dictionaries, each containing:
            - "name": The unique name of the object within the simulation.
            - "type": A string representing the object type as identified by the FDTD simulation program.
            - "scope": The name of the group or scope in which the object resides.
        """
        if iterated is None:
            iterated = []

        # Select the provided group as the groupscope and select all objects in it
        self._lumapi.groupscope(groupscope)
        self._lumapi.selectall()
        num_objects = int(self._lumapi.getnumber())

        # Iterate through all the objects in the group
        for i in range(num_objects):

            name = self._lumapi.get("name", i + 1).replace(" ", "_")
            sim_object_type = self._lumapi.get("type", i + 1)

            used_names = [sim_object["name"].replace(" ", "_") for sim_object in iterated]

            if autoset_new_unique_names and sim_object_type != "FDTD":

                unique_name = get_unique_name(name, used_names)

                self._lumapi.set("name", unique_name, i + 1)

            else:
                unique_name = name

            iterated.append(
                {"name": unique_name, "type": sim_object_type, "scope": groupscope.split("::")[-1]})

            # Check if the object is another group, run this method recursively
            if (sim_object_type == "Layout Group" or
                    (sim_object_type == "Structure Group" and
                     self._lumapi.getnamed(name, "construction group") == 0.0)):
                new_groupscope = groupscope + "::" + unique_name
                iterated = self._get_simulation_objects_in_scope(new_groupscope, autoset_new_unique_names,
                                                                 iterated)
                self._lumapi.groupscope(groupscope)

            self._lumapi.selectall()

        return iterated

    def _print_variable_declarations(self, simulation_variable_name: str, message: str,
                                     exit_after_printing: bool) -> None:
        """
        Prints type declarations for all active simulation objects, enabling autocompletion and type hints
        when manipulating a loaded simulation programmatically.

        This method retrieves all simulation objects within the "::model" scope and generates Python variable
        declarations for each object, formatted for easy copy-pasting into code. These declarations provide
        full autocompletion support, allowing for more streamlined development when interacting with a loaded
        `.fsp` file.

        Parameters:
        -----------
        simulation_variable_name : str
            The name to use for the simulation instance variable in the declarations, representing the
            simulation environment.

        exit_after_printing : bool
            If `True`, the program will exit immediately after printing the declarations. Useful for generating
            declarations without running additional code.
        """

        simulation_objects = self._get_simulation_objects_in_scope("::model", False)

        # Print the type declarations in the desired format
        print("Copy/paste these into your code, replacing the simulation initialization. \n"
              "This yields full autocompletion for every object present in the loaded simulation file.\n\n")

        print("#BEGINNING OF VARIABLE DECLARATIONS"
              "================================================================================")

        print(message)

        for sim_object in simulation_objects:

            object_class = self._type_to_class_map.get(sim_object["type"])
            if object_class.__name__ == "FDTDRegion":
                object_name = "fdtd"
                line = (
                    f"{object_name}: {simulation_variable_name}"
                    f".object_interfaces.{object_class.__name__}Interface "
                    f"= {simulation_variable_name}.__getattribute__('_{object_name}')  # type: ignore"
                )
                if len(line) > 116:
                    line = (
                        f"{object_name}: {simulation_variable_name}"
                        f".object_interfaces.{object_class.__name__}Interface "
                        f"= (\n\t{simulation_variable_name}.__getattribute__('_{object_name}'))  # type: ignore")

            elif object_class is not None:
                object_name = sim_object["name"]
                line = (
                    f"{object_name}: {simulation_variable_name}"
                    f".object_interfaces.{object_class.__name__}Interface "
                    f"= {simulation_variable_name}.{object_name}  # type: ignore")
                if len(line) > 116:
                    line = (
                        f"{object_name}: {simulation_variable_name}"
                        f".object_interfaces.{object_class.__name__}Interface "
                        f"= (\n\t{simulation_variable_name}.{object_name})  # type: ignore")
            else:
                raise ValueError("Something wierd happened here.")

            print(line)

        print("#END OF VARIABLE DECLARATIONS"
              "======================================================================================")

        if exit_after_printing:
            sys.exit("Exited after printing variable declarations.")

    def _get_active_objects(self) -> Simulation._ActiveObjects:
        return self._active_objects

    def _validate_or_get_save_path(self, save_path: str | None, open_explorer: bool = False) -> str:

        # Determine the save path
        if save_path is None and not open_explorer:
            # Use self.save_path if no save_path is provided and explorer is not opened
            save_path = self._save_path
            if not save_path:
                raise ValueError("No save path provided and self.save_path is not set.")
        elif open_explorer:
            # Open a file explorer to select the save path
            root = Tk()
            root.withdraw()  # Hide the main window
            save_path = filedialog.asksaveasfilename(
                title="Select Save Path",
                defaultextension=".fsp",
                filetypes=[("Lumerical Simulation Files", "*.fsp")],
                initialfile=os.path.basename(self._save_path) if self._save_path else None
            )
            root.destroy()
            if not save_path:
                raise ValueError("No path selected. Save operation canceled.")
        elif save_path is not None:
            # Verify that the provided save_path is valid
            save_dir = os.path.dirname(save_path)
            if not os.path.isdir(save_dir):
                raise ValueError(f"The directory does not exist: {save_dir}")
            if not save_path.endswith(".fsp"):
                raise ValueError("The save path must have a .fsp extension.")

        return save_path

    def _initialize_objects_from_loaded_simulation(self) -> None:
        """
        Reads an `.fsp` simulation file and creates Python objects corresponding to each simulation
        object, enabling programmatic manipulation of the simulation environment. For enhanced
        autocompletion and type hints, call `print_variable_declarations()` after executing this
        function.

        This method retrieves all simulation objects within the "::model" scope, iterates over them,
        and instantiates Python representations for each based on the object type. The created objects
        are assigned as attributes to the current instance, making them accessible as standard Python
        objects for easier manipulation.
        """

        simulation_objects = self._get_simulation_objects_in_scope("::model", True)
        self.save()

        for sim_object in simulation_objects:

            if sim_object["type"] == "FDTD":
                instantiated_object = self._type_to_class_map[sim_object["type"]](self)
            else:
                instantiated_object = self._type_to_class_map[sim_object["type"]](sim_object["name"], self)
                self._active_objects.used_names.append(sim_object["name"])
                if isinstance(instantiated_object, Structure):
                    self._active_objects.structures.append(instantiated_object)
                elif isinstance(instantiated_object, MonitorBase):
                    self._active_objects.monitors.append(instantiated_object)
                elif isinstance(instantiated_object, SourceBase):
                    self._active_objects.sources.append(instantiated_object)
                elif isinstance(instantiated_object, Mesh):
                    self._active_objects.meshes.append(instantiated_object)

            if sim_object["scope"] != "model":
                group = getattr(self, sim_object["scope"])
                group.__getattribute__("_grouped_objects").append(instantiated_object)
                setattr(instantiated_object, "_group", group)

            if sim_object["name"] == "FDTD":
                setattr(self, "_fdtd", instantiated_object)
            else:
                setattr(self, sim_object["name"], instantiated_object)

    def save(self, open_explorer: bool = False, save_path: str = None) -> None:
        """Saves the current simulation to a specified path.

        Save path will be updated, so the next time you call this method without arguments,
        it will be saved to this location.


        Args:
            open_explorer (bool): If True, opens a file explorer to choose the save path. Defaults to False.
            save_path (str): The path where the simulation will be saved. If None and open_explorer is False,
                             uses self.save_path. Defaults to None.

        Raises:
            ValueError: If the provided save_path is invalid or not an .fsp file.
        """
        if save_path is None and not open_explorer:
            save_path = self._save_path
        else:
            save_path = self._validate_or_get_save_path(save_path, open_explorer)
        self._lumapi.save(save_path)

    def _validate_unique_name(self, name: str) -> None:
        if name in self._active_objects.used_names:
            raise ValueError(f"The name '{name}' is already taken by another simulation object. Choose a unique name.")
        self._active_objects.used_names.append(name)

    # Functions to extract index information from the simulation region.
    def _offset_FDTD_region_by(self, x: float, y: float) -> None:
        if self._print_progress:
            x_print = convert_length(x, "m", self._global_units)
            y_print = convert_length(y, "m", self._global_units)
            print(f"Offsetting FDTD-region position by {x_print} and {y_print} {self._global_units} "
                  f"in x and y respectively.")
        self._fdtd.x += convert_length(x, "m", self._global_units)
        self._fdtd.y += convert_length(y, "m", self._global_units)

    def _create_index_monitor(self, extraction_type: EXTRACTION_TYPES, z: float = None) -> IndexMonitor:
        """
        Creates an index monitor for extracting index information from the simulation region.
        """

        x_span, y_span, z_span = self._fdtd.x_span, self._fdtd.y_span, self._fdtd.z_span

        if extraction_type == "2d geometry model":

            if self._print_progress:
                print(f"Creating 2D index monitor...")

            if z is None:
                raise ValueError("Extraction mode '2d geometry model' requires a 'z' coordinate.")

            monitor_type = "2d z-normal"
            x_span, y_span, z_span = x_span * 2, y_span * 2, None

        elif extraction_type in ["3d geometry model", "full index model"]:

            if self._print_progress:
                print(f"Creating 3D index monitor...")

            monitor_type = "3d"
            z = self._fdtd.z

            if extraction_type == "full index model":
                fdtd_mesh_grid = self._fdtd.__getattribute__("_get_mesh_grid_and_pml_thickness")()
                x_span = max([x_span + fdtd_mesh_grid.x_min_bc_pml_thickness,
                              x_span + fdtd_mesh_grid.x_max_bc_pml_thickness])
                y_span = max([y_span + fdtd_mesh_grid.y_min_bc_pml_thickness,
                              y_span + fdtd_mesh_grid.y_max_bc_pml_thickness])
                z_span = max([z_span + fdtd_mesh_grid.z_min_bc_pml_thickness,
                              z_span + fdtd_mesh_grid.z_max_bc_pml_thickness])
            else:
                x_span, y_span, z_span = x_span * 2, y_span * 2, z_span * 2
        else:
            raise ValueError(f"'{extraction_type}' is an invalid argument for 'extraction_type'.")

        name = get_unique_name("index_profiling_monitor", self._active_objects.used_names)
        index_monitor = self.add.monitors.index_monitor(name, monitor_type,  # type: ignore
                                                        x_span=x_span, y_span=y_span, z_span=z_span,
                                                        x=self._fdtd.x, y=self._fdtd.y, z=z)
        index_monitor = self._prepare_index_monitor(index_monitor, extraction_type)
        if self._print_progress:
            print("Index monitor created.")
        return index_monitor

    def _prepare_index_monitor(self, index_monitor: IndexMonitor, extraction_type: EXTRACTION_TYPES) -> IndexMonitor:
        """
        Prepares an index monitor for extraction of index information from the simulation region.
        """

        pp = self._print_progress

        if pp:
            print(f"\tOverriding global monitor settings.")
        index_monitor.settings.general.override_global_monitor_settings(True)

        if pp:
            print(f"\tEnabling 'record conformal mesh when possible'.")
        index_monitor.settings.advanced.record_conformal_mesh_when_possible(True)

        if extraction_type in ["3d geometry model", "2d geometry model"]:

            if pp:
                print(f"\tSetting index monitor frequency points to 5.")
            index_monitor.settings.general.set_frequency_points(5)

            if pp:
                print(f"\tSetting index monitor spatial interpolation to 'specified position'.")
            index_monitor.settings.advanced.set_spatial_interpolation("specified position")

            if pp:
                print(f"\tDisabling 'record data in pml'.")
            index_monitor.settings.advanced.record_data_in_pml(False)

        elif extraction_type == "full index model":
            if pp:
                print(f"\tSetting index monitor spatial interpolation to 'none'.")
            index_monitor.settings.advanced.set_spatial_interpolation("none")

            if pp:
                print(f"\tSetting index monitor frequency points to 10.")
            index_monitor.settings.general.set_frequency_points(10)

        else:
            raise ValueError(f"'{extraction_type}' is not a valid argument for 'extraction_type'.")

        return index_monitor

    def _get_all_index_values(self, result: IndexMonitor._Results) -> _IndexValues3D:
        """Fetches the full set of refractive index values from the monitor results."""

        x, y, z = result.x, result.y, result.z

        combined_indices, original_shape = self._get_combined_indices(result)
        original_shape = (*original_shape, result.f_points, 3)  # (x, y, z, frequency_points, 3)
        index_model = self._IndexValues3D(hash=None, x=x, y=y, z=z,
                                          refractive_indices=combined_indices.reshape(original_shape))
        index_model.fill_hash_fields()
        return index_model

    @staticmethod
    def _get_combined_indices(result: IndexMonitor._Results) -> Tuple[ndarray, Any]:
        """
        Takes in raw results and combines the x, y, and z index arrays into one array.
        """
        x_index, y_index, z_index = result.index_x, result.index_y, result.index_z
        reshaped_indices = []
        for axis_index in [x_index, y_index, z_index]:
            if axis_index is not None:
                reshaped_indices.append(axis_index.reshape(-1, axis_index.shape[-1]))  # Shape: (num_points, f_points)
        combined_indices = np.stack(reshaped_indices, axis=-1)  # Shape: (num_points, f_points, 3)
        original_shape = x_index.shape[:-1]
        return combined_indices, original_shape

    @staticmethod
    def _get_filtered_indices(combined_indices: ndarray) -> Tuple[ndarray, ndarray]:
        """
        Takes in an array of combined x, y, and z index values and filters out the points corresponding to
        free space (index 1.0 + 0.j). Returns the filtered array along with the mask of points corresponding to
        not free space.
        """
        # Identify points where all wavelengths are not free space (0.0+0j)
        not_free_space_mask = ~np.all(combined_indices == 1.0 + 0j, axis=(1, 2))

        # Filter combined indices to include only valid points and shift to cube-centered grid
        filtered_indices = combined_indices[not_free_space_mask]

        return filtered_indices, not_free_space_mask

    def _get_materials(self, filtered_indices: ndarray, not_free_space_mask: ndarray,
                       combined_indices: ndarray, original_shape: Tuple[int, ...]) -> list[_Material]:
        """
        Takes in an array of refractive indexes where free space indexes has been set to 0. Filters
        out unique materials and returns a list of boolean masks corresponding to each material.
        """
        # Identify unique materials based on the filtered indices
        unique_materials, material_ids = np.unique(filtered_indices, axis=0, return_inverse=True)

        # Map material IDs back to the original spatial grid
        material_map = np.zeros(combined_indices.shape[0], dtype=int)
        material_map[not_free_space_mask] = material_ids + 1  # Start material IDs from 1
        material_map = material_map.reshape(original_shape)  # Back to 3D

        # Generate material objects
        materials = []
        for i in range(1, len(unique_materials) + 1):
            material_mask = cast(ndarray, (material_map == i))
            shifted_mask = self._shift_from_mesh_grid_to_cube_center(material_mask)
            material_id = i
            material = self._Material(id=material_id, mask=shifted_mask)
            materials.append(material)

        return materials

    def _get_structures(self, materials: List[_Material]) -> List[_Structure]:

        structure_id = 0
        for material in materials:

            # Filter out structures
            labeled_array, num_structures = label(material.mask, structure=np.ones((3,) * material.mask.ndim))

            # Create a mask for each structure
            structure_masks = [(labeled_array == structure_id) for structure_id in range(1, num_structures + 1)]

            # Create structure objects
            structures = []
            for mask in structure_masks:
                structure_id += 1
                mask = cast(ndarray, mask)
                structure = self._Structure(id=structure_id, material_id=material.id, layer_id=1, mask=mask)
                structures.append(structure)

            return structures

    def _get_layers(self, structures: List[_Structure], z_coordinates: ndarray) -> List[_Layer]:

        layer_id = 0
        layers = {}

        structures_dict = {structure.material_id: [] for structure in structures}
        for structure in structures:
            structures_dict[structure.material_id].append(structure)

        layer_objects = []
        for material_id, structures in structures_dict.items():

            for structure in structures:

                # Find the z-coordinates of the structure
                z_indices = np.where(structure.mask)[2]
                min_z = float(z_coordinates[z_indices.min()])
                max_z = float(z_coordinates[z_indices.max()])

                # Group structures by (min_z, max_z)
                layer_key = (min_z, max_z)
                if layer_key not in layers:
                    layers[layer_key] = {"masks": [], "structures": []}
                layers[layer_key]["masks"].append(structure.mask)
                layers[layer_key]["structures"].append(structure)

            for layer_key in layers.keys():

                layer_id += 1
                combined_layer_mask = np.any(layers[layer_key]["masks"], axis=0)  # Combine along axis 0

                layer = self._Layer(id=layer_id,
                                    material_id=material_id,
                                    mask=combined_layer_mask)
                layer_objects.append(layer)

                for struct in layers[layer_key]["structures"]:
                    struct.layer_id = layer_id

        return layer_objects

    @staticmethod
    def _filter_out_only_elements_that_are_the_same(combined_indices: List[ndarray]) -> ndarray:
        """
        Takes in any number of arrays, as long as they have the same shape and returns an array of the same shape
        containing only values for the points that are equal across all arrays.
        """
        # Stack the arrays along a new axis
        arrays = np.stack(combined_indices)

        # Check if all arrays have the same value at each position
        common_mask = np.all(arrays == arrays[0], axis=0)

        # Create a result array initialized with 1.+0.j
        result = np.full_like(combined_indices[0], 1. + 0.j, dtype=complex)

        # Set the positions where all arrays match to their common value
        result[common_mask] = arrays[0][common_mask]

        return result

    @staticmethod
    def _shift_from_mesh_grid_to_cube_center(grid_mask: ndarray) -> np.ndarray:
        """
        Shifts the grid from representing values at mesh grid intersections to representing voxels.
        """
        # Check all corners of each grid cube
        top_left = grid_mask[:-1, :-1]  # Top-left corner
        top_right = grid_mask[:-1, 1:]  # Top-right corner
        bottom_left = grid_mask[1:, :-1]  # Bottom-left corner
        bottom_right = grid_mask[1:, 1:]  # Bottom-right corner

        # Combine all corners using a logical OR
        cube_mask = top_left | top_right | bottom_left | bottom_right
        return cube_mask

    def _get_crossection_mask(self, mask: ndarray, z_coordinates: ndarray, z: float) -> ndarray:
        """
        Exrtracts the cross section at a specified z-coordinate from a 3d boolean mask array.
        """
        # Find the closest z index
        z = convert_length(z_coordinates, self._global_units, "m")
        z_index = np.argmin(np.abs(z_coordinates - z))

        # Extract the 2D cross-section
        cross_section = mask[:, :, z_index]
        return cross_section

    def _get_index_model(self, extraction_type: Literal["2d cross section", "3d"], *args: IndexMonitor._Results,
                         z: float = None) -> _IndexModel:
        """
        Takes in results and returns an index model.
        """
        if extraction_type == "2d cross section" and z is None:
            raise ValueError("For extraction type '2d crossection', a z-coordinate must be provided.")

        index_model = self._IndexModel.initialize_empty()
        index_model.materials = []
        index_model.structures = []
        index_model.layers = []

        # Fetch the x, y, and z coordinates. These are the same for all results, as the index monitor is assumed
        # to be stationary.
        x_coords, y_coords, z_coords = args[0].x, args[0].y, args[0].z

        # Calculate cube center coordinates
        if len(x_coords) > 1:
            x_coords = (x_coords[:-1] + x_coords[1:]) / 2
        if len(y_coords) > 1:
            y_coords = (y_coords[:-1] + y_coords[1:]) / 2
        if len(z_coords) > 1:
            z_coords = (z_coords[:-1] + z_coords[1:]) / 2

        index_model.x = x_coords
        index_model.y = y_coords
        index_model.z = z_coords

        # Fetch all the idex values, combine each result's into an array, and put them all in a list
        all_combined_indices = [self._get_combined_indices(result) for result in args]
        original_shape = all_combined_indices[0][1]
        all_combined_indices = [combined_indices[0] for combined_indices in all_combined_indices]

        if len(all_combined_indices) > 1:
            # Filter out an array of combined indices where all points not the same in all arrays are set to 1.+0.j
            combined_indices = self._filter_out_only_elements_that_are_the_same(all_combined_indices)
        else:
            combined_indices = all_combined_indices[0]

        filtered_indices, not_free_space_mask = self._get_filtered_indices(combined_indices)
        materials = self._get_materials(filtered_indices, not_free_space_mask, combined_indices, original_shape)
        if len(materials) > 1:
            model_mask = np.logical_or(*(material.mask for material in materials))
        elif len(materials) == 0:
            raise ValueError("The crosssection region contains only free space.")
        else:
            model_mask = materials[0].mask

        # if extraction_type == "2d cross section":
        #     index_model.mask = self._get_crossection_mask(model_mask, z_coords, z)
        #     return index_model

        structures = self._get_structures(materials)
        layers = self._get_layers(structures, z_coords)

        index_model.mask = model_mask
        index_model.materials = materials
        index_model.structures = structures
        index_model.layers = layers

        return index_model

    def _create_bmp_and_gds_of_crosssection(self, filename: str, z: float, pixelsize: int,
                                            rows: int = 1, columns: int = 1, units: LENGTH_UNITS = None,
                                            print_progress: bool = False) -> None:
        """
        Analyzes the simulation enviroment and creates a bitmap and a gds-file of the cross section at the specified
        z-coordinate.

        Parameters:
            filename (str): Name of the output files. Does not need to include .bmp and .gds suffixes.
            z (float): The z-cooordinate to take the cross section at.
            pixelsize (int): The dimensions of each pixel in the resulting bitmap, and each square in the
                                        gds-file.
            rows (Optional[int]): The amount of times to repeat the unit cell in the y-direction.
            columns (Optional[int]): The amount of times to repeat the unit cell in the z-direction.
            units (Optional[LENGTH_UNITS]): If None is passed, the global units are used. Defaults to None.
            print_progress (Optional[bool]): If True, everything that is being done to the simulation will be printed
                                                to the console.
        """

        if print_progress:
            self._print_progress = True
        pp = self._print_progress

        if units is not None:
            Validate.in_literal(units, "units", LENGTH_UNITS)
            pixelsize = convert_length(pixelsize, units, "m")
        else:
            pixelsize = convert_length(pixelsize, self._global_units, "m")

        self._save_temp()

        buffer = self._prepare_FDTD_for_gds_extraction(pixelsize)
        index_monitor = self._create_index_monitor("2d geometry model", z)

        if pp:
            print("Fetching index monitor results...")
        result = index_monitor._get_results()

        self._offset_FDTD_region_by(pixelsize/2, pixelsize/2)
        if pp:
            print("Fetching index monitor results...")
        result_1 = index_monitor._get_results()

        self._offset_FDTD_region_by(-pixelsize, -pixelsize)
        if pp:
            print("Fetching index monitor results...")
        result_2 = index_monitor._get_results()

        self._offset_FDTD_region_by(0, pixelsize)
        if pp:
            print("Fetching index monitor results...")
        result_3 = index_monitor._get_results()

        self._offset_FDTD_region_by(pixelsize, -pixelsize)
        if pp:
            print("Fetching index monitor results...")
        result_4 = index_monitor._get_results()

        if pp:
            print("Deleting index monitor...")
        self._lumapi.select(index_monitor.name)
        self._lumapi.delete()

        save_path = os.path.join(os.path.dirname(self._save_path), filename)
        index_model = self._get_index_model("2d cross section", result, result_1, result_2, result_3, result_4, z=z)

        index_model.mask = np.rot90(index_model.mask[:, :, 0])
        tiled_mask = np.tile(index_model.mask, (rows, columns))

        self._save_bitmap(tiled_mask, save_path)

        ps = convert_length(pixelsize, "m", "um")
        index_model.mask = np.rot90(index_model.mask)
        index_model.mask = np.rot90(index_model.mask)
        self._save_gds(index_model.mask, index_model.x, index_model.y, save_path, ps, rows, columns)

        self._reconfigure_sim_enviroment(buffer)
        self._print_progress = False
        return None

    def _prepare_FDTD_for_gds_extraction(self, pixelsize: float) -> dict:

        pp = self._print_progress

        if pp:
            print("Preparing FDTD-Region for geometry extraction...")

        # Init buffer for storing all previous settings for later reconfiguration.
        buffer = {"FDTD": {}}

        buffer["FDTD"]["x"] = (self._get_parameter("FDTD", "x", "float"), "float")
        buffer["FDTD"]["y"] = (self._get_parameter("FDTD", "y", "float"), "float")

        # Get the x span and y span
        x_span = self._get_parameter("FDTD", "x span", "float")
        y_span = self._get_parameter("FDTD", "y span", "float")

        # Ensure x and y-spans are divisible by pixelsize
        if pp:
            print("\tEnsuring dimensions of the simulation region are divisible by pixelsize.")
        if x_span % pixelsize != 0:
            x_span = round(x_span / pixelsize) * pixelsize
            buffer["FDTD"]["x span"] = (self._get_parameter("FDTD", "x span", "float"), "float")
            if pp:
                print(f"\tSetting FDTD x span to {self._fdtd.x_span} {self._global_units}.")
            self._set_parameter("FDTD", "x span", x_span, "float")
        if y_span % pixelsize != 0:
            y_span = round(y_span / pixelsize) * pixelsize
            buffer["FDTD"]["y span"] = (self._get_parameter("FDTD", "y span", "float"), "float")
            if pp:
                print(f"\tSetting FDTD y span to {self._fdtd.y_span} {self._global_units}.")
            self._set_parameter("FDTD", "y span", y_span, "float")

        if pp:
            print("\tDisabling all simulation meshes")
        # Disable all meshes active in the simulation.
        for mesh in self._active_objects.meshes:
            enabled = mesh.enabled
            if enabled:
                mesh.enabled = False
                buffer[mesh.name] = {"enabled": (enabled, "bool")}

        # Make sure the min mesh step is .25 nm.
        min_mesh_step = self._get_parameter("FDTD", "min mesh step", "float")
        if min_mesh_step != convert_length(0.25, "nm", "m"):
            if pp:
                print("\tSetting min mesh step to 0.25 nm.")
            self._fdtd.settings.mesh.set_min_mesh_step(0.25, units="nm")
            buffer["FDTD"]["min mesh step"] = (min_mesh_step, "float")

        mesh_type = self._get_parameter("FDTD", "mesh type", "str")
        if mesh_type != "custom non-uniform":
            if pp:
                print("\tSetting mesh type to 'custom non-uniform'")
            self._fdtd.settings.mesh.mesh_type_settings.set_mesh_type("custom non-uniform")
            buffer["FDTD"]["mesh type"] = (mesh_type, "str")

        # Configure the x and y mesh
        for axis in ["x", "y"]:

            definition = self._get_parameter("FDTD", f"define {axis} mesh by", "str")

            if definition != "maximum mesh step":
                if pp:
                    print(f"\tSetting {axis} mesh definition to 'maximum mesh step'.")
                self._fdtd.settings.mesh.mesh_type_settings.define_mesh_by(**{
                    f"{axis}_definition": "maximum mesh step"})
                buffer["FDTD"][f"define {axis} mesh by"] = (definition, "str")

                max_step = self._get_parameter("FDTD", f"d{axis}", "float")
                if max_step != pixelsize:
                    if pp:
                        ps = convert_length(pixelsize, "m", self._global_units)
                        print(f"\tSetting {axis} maximum mesh step to {ps} {self._global_units}.")
                    self._fdtd.settings.mesh.mesh_type_settings.set_maximum_mesh_step(**{axis: pixelsize}, units="m")
                    buffer["FDTD"][f"d{axis}"] = (max_step, "float")

                allow_grading = self._get_parameter("FDTD", f"allow grading in {axis}", "bool")
                if allow_grading:
                    if pp:
                        print(f"\tDisabling grading for {axis}-mesh.")
                    self._fdtd.settings.mesh.mesh_type_settings.allow_mesh_grading(**{axis: False})
                    buffer["FDTD"][f"allow grading in {axis}"] = (allow_grading, "bool")

        # Configure the z-mesh
        definition = self._get_parameter("FDTD", "define z mesh by", "str")
        if definition != "mesh cells per wavelength":
            if pp:
                print(f"\tSetting z mesh definition to 'mesh cells per wavelength'.")
            self._fdtd.settings.mesh.mesh_type_settings.define_mesh_by(z_definition="mesh cells per wavelength")
            buffer["FDTD"]["define z mesh by"] = (definition, "str")

        mesh_cells_pr_wavelength = self._get_parameter("FDTD", "mesh cells per wavelength", "float")
        if mesh_cells_pr_wavelength != 10:
            if pp:
                print(f"\tSetting mesh cells per wavelength to 10.")
            self._fdtd.settings.mesh.mesh_type_settings.set_mesh_cells_per_wavelength(10)
            buffer["FDTD"]["mesh cells pr wavelength"] = (mesh_cells_pr_wavelength, "float")

        allow_grading = self._get_parameter("FDTD", "allow grading in z", "bool")
        if not allow_grading:
            if pp:
                print(f"\tEnabling grading for z-mesh.")
            self._fdtd.settings.mesh.mesh_type_settings.allow_mesh_grading(z=True)
            buffer["FDTD"]["allow grading in z"] = (allow_grading, "bool")

        grading_factor = self._get_parameter("FDTD", "grading factor", "float")
        if grading_factor != 1.41421:
            if pp:
                print(f"\tSetting grading factor to 1.41421.")
            self._fdtd.settings.mesh.mesh_type_settings.set_grading_factor(1.41421)
            buffer["FDTD"]["grading factor"] = (grading_factor, "float")

        mesh_refinement = self._get_parameter("FDTD", "mesh refinement", "str")
        if mesh_refinement != "precise volume average":
            if pp:
                print(f"\tSetting mesh refinement to 'precise volume average'.")
            self._fdtd.settings.mesh.mesh_refinement_settings.set_precise_volume_average()
            buffer["FDTD"]["mesh refinement"] = (mesh_refinement, "str")

        meshing_refinement = self._get_parameter("FDTD", "meshing refinement", "int")
        if meshing_refinement != 5:
            if pp:
                print(f"\tSetting meshing refinement to 5.")
            self._fdtd.settings.mesh.mesh_refinement_settings.set_precise_volume_average(meshing_refinement)
            buffer["FDTD"]["meshing refinement"] = (meshing_refinement, "int")

        if pp:
            print("FDTD-Region prepared for geometry extraction.")

        # Reverse the order of the keys in the buffer, so that the reconfiguration is done in reverse.
        reversed_buffer = reverse_dict_order(buffer, reverse_nested_dicts=True)
        return reversed_buffer

    def _reconfigure_sim_enviroment(self, buffer: dict) -> None:
        if self._print_progress:
            print("Reconfiguring simulation enviroment...")
        for obj_name in buffer.keys():
            for parameter, value in buffer[obj_name].items():
                self._set_parameter(obj_name, parameter, value[0], value[1])
        if self._print_progress:
            print("Simulation enviroment reconfigured.")

    def _save_bitmap(self, mask: ndarray, output_file, invert: bool = True):
        """
        Save a binary mask as a bitmap image.

        Parameters:
            mask (np.ndarray): 2D binary mask (True/False or 1/0).
            output_file (str): File path to save the bitmap (e.g., "output.png").
            invert (bool): Black becomes white. When using bitmap for milling, usually white areas will be milled.
        """
        if self._print_progress:
            print("Creating bitmap...")

        # Invert mask so that white areas corresponds to milling.
        if invert:
            mask = np.logical_not(mask)

        if not output_file.endswith(".bmp"):
            output_file += ".bmp"

        # Normalize the mask to 0 (black) and 255 (white)
        bitmap = (mask * 255).astype(np.uint8)

        # Create an image from the bitmap
        image = Image.fromarray(bitmap)

        # Save the image as a bitmap
        image.save(output_file)
        if self._print_progress:
            print(f"\tBitmap saved to {output_file}")

    def _save_gds(self, mask, x_coords, y_coords, output_file, pixelsize, rows, columns):
        """
        Create a GDSII file from a mask cross-section.

        Parameters:
            mask (np.ndarray): 2D array representing the mask (True for structure points).
            x_coords (np.ndarray): Array of x-coordinates for the mask.
            y_coords (np.ndarray): Array of y-coordinates for the mask.
            pixelsize (float): The width and height of each rectangle.
            output_file (str): The name of the output GDSII file.

        Returns:
            None
        """
        # Clear the global GDSPY library
        gdspy.current_library = gdspy.GdsLibrary()

        if self._print_progress:
            print("Creating gds-file...")

        # Adjust the coordinates for the tiling
        x_coords -= x_coords[0] + ((x_coords[-1] - x_coords[0]) / 2)
        x_coords = convert_length(x_coords, "m", "um")
        unit_cell_x = (x_coords[-1] - x_coords[0])
        y_coords -= y_coords[0] + ((y_coords[-1] - y_coords[0]) / 2)
        y_coords = convert_length(y_coords, "m", "um")
        unit_cell_y = (y_coords[-1] - y_coords[0])

        total_x = unit_cell_x * columns
        total_y = unit_cell_y * rows

        start_x = -(total_x - unit_cell_x) / 2
        start_y = -(total_y - unit_cell_y) / 2

        if output_file.endswith(".bmp"):
            output_file = output_file[:-4]
        if not output_file.endswith(".gds"):
            output_file += ".gds"

        # Create a GDSII library and a cell
        gds_lib = gdspy.GdsLibrary(name=output_file)
        base_cell = gds_lib.new_cell("CROSS_SECTION")

        # Label connected structures
        labeled_array, num_structures = label(mask, structure=np.ones((3,) * mask.ndim))

        for structure_id in range(1, num_structures + 1):

            # Extract the current structure mask
            structure_mask = labeled_array == structure_id

            # Find the coordinates of all True values in the structure
            y_indices, x_indices = np.where(structure_mask)

            # Convert pixel indices to physical coordinates
            x_polygon = x_coords[x_indices]  # x-coordinates of the structure
            y_polygon = y_coords[y_indices]  # y-coordinates of the structure

            # Create a polygon outline for the structure
            # Sort the coordinates to form a valid polygon using convex hull
            points = np.column_stack((x_polygon, y_polygon))
            hull = ConvexHull(points)
            polygon_coords = points[hull.vertices]

            # Create and add the polygon to the GDS cell
            polygon = gdspy.Polygon(polygon_coords)
            base_cell.add(polygon)

        # gds_lib.add(cell)

        # Create the top-level cell
        top_cell = gdspy.Cell("TOP_LEVEL")

        # Add references to the base cell for tiling
        for i in range(rows):
            for j in range(columns):
                position = (start_x + j * unit_cell_x, start_y + i * unit_cell_y)
                top_cell.add(gdspy.CellReference(base_cell, position))

        gds_lib.add(top_cell)

        # Write to GDSII file
        gds_lib.write_gds(output_file)
        if self._print_progress:
            print(f"\tGDSII file created: {output_file}\n")
