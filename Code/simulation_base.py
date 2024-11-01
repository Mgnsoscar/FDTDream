from __future__ import annotations

# Standard library imports
from typing import Literal, Optional, TypedDict, TypeVar, Type
from typing_extensions import Unpack
import sys

# Third-party library imports
import numpy as np

# Local imports
from fdtd_region import FDTDRegion, Mesh
from lumapi_import import lumapi
from monitors import (GlobalMonitorSettings, FreqDomainFieldAndPowerMonitor, IndexMonitor)
from sources import PlaneSource, GaussianSource, CauchyLorentzianSource, GlobalSource
from base_classes import FDTDSimulationBase, SimulationBaseKwargs
from type_hint_resources import LENGTH_UNITS, PositionalKwargs
from structures import (Rectangle, Circle, Polygon,
                        EquilateralNSidedPolygon, Triangle, Sphere,
                        Ring, Pyramid)
from materials import MaterialDatabase

########################################################################################################################
#                                             CONSTANTS AND LITERALS
########################################################################################################################

PULSE_TYPES = Literal["standard", "broadband"]
T = TypeVar('T', bound='SimulationObject')
TYPE_TO_CLASS_MAP = {
    "DFTMonitor": FreqDomainFieldAndPowerMonitor,
    "GaussianSource": GaussianSource,
    "PlaneSource": PlaneSource,
    "Cauchy-Lorentzian": CauchyLorentzianSource,
    "IndexMonitor": IndexMonitor,
    "Rectangle": Rectangle
}


########################################################################################################################
#                                              SIMULATION BASE CLASS
########################################################################################################################


class FDTDSimulation(FDTDSimulationBase):
    # Define classes here. This is so users won't have to import the classes when assigning variables manually
    # after loading from a .fsp file.
    FreqDomainFieldAndPowerMonitor = FreqDomainFieldAndPowerMonitor
    GaussianSource = GaussianSource
    IndexMonitor = IndexMonitor
    PlaneSource = PlaneSource
    CauchyLorentzianSource = CauchyLorentzianSource

    # Declare settings variables
    global_monitor_settings: GlobalMonitorSettings
    global_source_settings: GlobalSource
    material_database: MaterialDatabase

    # "Private" variables
    _fdtd: FDTDRegion

    def __init__(self, global_units: LENGTH_UNITS = "nm", **kwargs: Unpack[SimulationBaseKwargs]) -> None:
        super().__init__(global_units, **kwargs)

        # Assign variables
        self.global_monitor_settings = GlobalMonitorSettings(parent=None, simulation=self)
        self.global_monitor_settings.set_frequency_points(1000)
        self.global_source_settings = GlobalSource(parent=None, simulation=self)
        self.material_database = MaterialDatabase(parent=None, simulation=self)

    def _create_objects_from_file(self) -> None:

        object_names, object_types = self._get_objects_and_types()

        for name, type_ in zip(object_names, object_types):

            if type_ == "FDTD":
                object_ = FDTDRegion(self)
                setattr(self, "_fdtd", object_)
            else:
                object_ = TYPE_TO_CLASS_MAP[type_](name, self)
                setattr(self, name, object_)

    def print_variable_declarations(self, simulation_variable_name: str, exit_after_printing: bool) -> None:

        object_names, object_types = self._get_objects_and_types()

        # Print the type declarations in the desired format
        print("Type Declarations. Copy/paste these into the begining og your code to get full autocompletion.:\n")

        for name, type_ in zip(object_names, object_types):

            object_class = TYPE_TO_CLASS_MAP.get(type_)
            if object_class:
                print(
                    f"\t{name}: {simulation_variable_name}.__class__.{object_class.__name__} "
                    f"= {simulation_variable_name}.{name}"
                )
        if exit_after_printing:
            sys.exit("Exited after printing variable declarations.")

    @property
    def fdtd(self) -> FDTDRegion:
        fdtd = getattr(self, "_fdtd", None)
        if fdtd is None:
            raise ValueError(f"No FDTD region has been added to the simulation.")
        return fdtd

    @fdtd.setter
    def fdtd(self, value: FDTDRegion) -> None:
        if not isinstance(value, FDTDRegion):
            raise ValueError(f"The 'fdtd' variable name is reserved for an instance of the 'FDTDRegion' class. You can "
                             f"add this using the addfdtd() method.")

    def addfdtd(self, **kwargs: Unpack[FDTDRegion._Kwargs]) -> FDTDRegion:
        if getattr(self, "_fdtd", None) is None:
            super().addfdtd()
            self._fdtd = FDTDRegion(self, **kwargs)

        return self._fdtd

    def addpower(self, name: str,
                 **kwargs: Unpack[FreqDomainFieldAndPowerMonitor._Kwargs]) -> FreqDomainFieldAndPowerMonitor:
        super().addpower(name=name)
        return FreqDomainFieldAndPowerMonitor(name, self, **kwargs)

    def addprofile(self, name: str,
                   **kwargs: Unpack[FreqDomainFieldAndPowerMonitor._Kwargs]) -> FreqDomainFieldAndPowerMonitor:
        super().addprofile(name=name)
        monitor = FreqDomainFieldAndPowerMonitor(name, self, **kwargs)
        monitor.advanced_settings.set_spatial_interpolation("nearest mesh cell")
        return monitor

    def addindex(self, name: str, **kwargs: Unpack[IndexMonitor._Kwargs]) -> IndexMonitor:
        super().addindex(name=name)
        return IndexMonitor(name, self, **kwargs)

    def addgaussian(self, name: str, **kwargs: Unpack[GaussianSource._Kwargs]) -> GaussianSource:
        super().addgaussian(name=name)
        return GaussianSource(name, self, **kwargs)

    def addplane(self, name: str, **kwargs: Unpack[PlaneSource._Kwargs]) -> PlaneSource:
        super().addplane(name=name)
        return PlaneSource(name, self, **kwargs)

    def addCauchyLorentzianSource(self, name: str,
                                  **kwargs: Unpack[CauchyLorentzianSource._Kwargs]) -> CauchyLorentzianSource:
        super().addgaussian(name=name)
        source_ = CauchyLorentzianSource(name, self, **kwargs)
        source_._set_parameter("source shape", "Cauchy-Lorentzian", "str")
        return source_

    def addrect(self, name, **kwargs: Unpack[Rectangle._Kwargs]) -> Rectangle:
        lumapi.FDTD.addrect(self, name=name, use_relative_coordinates=False)
        return Rectangle(name, self, **kwargs)

    def addcircle(self, name, **kwargs: Unpack[Circle._Kwargs]) -> Circle:
        lumapi.FDTD.addcircle(self, name=name, use_relative_coordinates=False)
        return Circle(name, self, **kwargs)

    def addpoly(self, name: str, **kwargs: Unpack[Polygon._Kwargs]) -> Polygon:
        lumapi.FDTD.addpoly(self, name=name, use_relative_coordinates=False)
        return Polygon(name, self, **kwargs)

    def add_N_sided_polygon(self, name: str, N: int,
                            **kwargs: Unpack[EquilateralNSidedPolygon._Kwargs]) -> EquilateralNSidedPolygon:
        if N == 3 or N == 4:
            ValueError("If you are creating a 3 or 4 sided equilateral polygon, use the addrect() or addtriangle() "
                       "methods instead.")
        elif N < 3:
            raise ValueError("The polygon must have at least three sides.")

        lumapi.FDTD.addpoly(self, name=name, use_relative_coordinates=False)
        return EquilateralNSidedPolygon(name, self, N, **kwargs)

    def addtriangle(self, name: str, **kwargs: Unpack[Triangle._Kwargs]) -> Triangle:
        lumapi.FDTD.addpoly(self, name=name, use_relative_coordinates=False)
        return Triangle(name, self, **kwargs)

    def addsphere(self, name: str, **kwargs: Unpack[Sphere._Kwargs]) -> Sphere:
        lumapi.FDTD.addsphere(self, name=name, use_relative_coordinates=False)
        return Sphere(name, self, **kwargs)

    def addring(self, name: str, **kwargs: Unpack[Ring._Kwargs]) -> Ring:
        lumapi.FDTD.addring(self, name=name, use_relative_coordinates=False)
        return Ring(name, self, **kwargs)

    def addpyramid(self, name: str, **kwargs: Unpack[Pyramid._Kwargs]):
        lumapi.FDTD.addpyramid(self, name=name)
        return Pyramid(name, self, **kwargs)

    def addmesh(self, name: str, **kwargs: Unpack[Mesh._Kwargs]) -> Mesh:
        lumapi.FDTD.addmesh(self, name=name)
        return Mesh(name, self, **kwargs)

    def copy(self, object_: T, new_name: str,  **kwargs: Unpack[T.Kwargs]) -> T:
        """Make an excect copy of the object passed to it with the new name passed."""
        super().select(object_.name)
        super().copy()
        self.set("name", new_name)
        new_structure = object_.__class__(new_name, self)
        return new_structure


if __name__ == "__main__":

    # Initialize simulation enviroment
    sim = FDTDSimulation.load_file("materials.fsp", global_units="nm", hide=True)

    print(sim.material_database.get_material_parameters("0index"))


