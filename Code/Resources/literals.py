# Standard library imports
from typing import Literal, Union

#START_MATERIALS
MATERIALS = Union[Literal[
        "Ag (Silver) - Johnson and Christy", "Al (Aluminium) - CRC", "Ag (Silver) - Palik (0-2um)", "W (Tungsten) - Palik", "InAs - Palik", "TiO2 (Titanium Dioxide) - Sarkar", "Cr (Chromium) - CRC", "5CB - Li", "Ge (Germanium) - Palik", "Si3N4 (Silicon Nitride) - Luke", "5PCH - Li", "TiO2 (Titanium Dioxide) - Kischkat", "Ag (Silver) - CRC", "PEC (Perfect Electrical Conductor)", "Al2O3 - Palik", "Al (Aluminium) - Palik", "E44 - Li", "W (Tungsten) - CRC", "TiO2 (Titanium Dioxide) - Devore", "Si3N4 (Silicon Nitride) - Phillip", "Sn (Tin) - Palik", "Cr (Chromium) - Palik", "Fe (Iron) - Palik", "MLC-6608 - Li", "C (graphene) - Falkovsky (mid-IR)", "Pt (Platinum) - Palik", "Au (Gold) - CRC", "Si (Silicon) - Palik", "Fe (Iron) - CRC", "SiO2 (Glass) - Palik", "Si3N4 (Silicon Nitride) - Kischkat", "Pd (Palladium) - Palik", "In (Indium) - Palik", "Ni (Nickel) - CRC", "MLC-9200-100 - Li", "InP - Palik", "MLC-9200-000 - Li", "Ni (Nickel) - Palik", "Cu (Copper) - CRC", "Ge (Germanium) - CRC", "etch", "Au (Gold) - Palik", "Ti (Titanium) - Palik", "TiN - Palik", "TiO2 (Titanium Dioxide) - Siefke", "Ti (Titanium) - CRC", "H2O (Water) - Palik", "Au (Gold) - Johnson and Christy", "GaAs - Palik", "V (Vanadium ) - CRC", "6241-000 - Li", "Cu (Copper) - Palik", "Ta (Tantalum) - CRC", "E7 - Li", "Rh (Rhodium) - Palik", "Ag (Silver) - Palik (1-10um)", "TL-216 - Li", "<Object defined dielectric>"
    ], str]
#END_MATERIALS

AXES = Literal["x", "y", "z"]
LENGTH_UNITS = Literal["m", "cm", "mm", "um", "nm", "pm", "angstrom", "fm"]
TIME_UNITS = Literal["s", "ms", "us", "ns", "ps", "fs"]
FREQUENCY_UNITS = Literal["Hz", "KHz", "MHz", "GHz", "THz", "PHz"]
PARAMETER_TYPES = Literal["float", "int", "str", "bool", "list", "any"]
INDEX_UNITS = Literal["m", "microns", "nm"]
DIMENSION = Literal["2D", "3D"]
BOUNDARY_TYPES = Literal["PML", "Metal", "Periodic", "Symmetric", "Anti-Symmetric", "Bloch", "PMC"]
BOUNDARY_TYPES_LOWER = Literal["pml", "metal", "periodic", "symmetric", "anti-symmetric", "bloch", "pmc"]
BOUNDARIES = Literal["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]
BOUNDARIES_INC_ALL = Literal["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]
PML_PARAMETERS = Literal["profile", "layers", "kappa", "sigma", "polynomial", "alpha",
                         "alpha_polynomial", "min_layers", "max_layers"]
PML_PROFILES = Literal["standard", "stabilized", "steep angle", "custom"]
PML_TYPES = Literal["stretched coordinate PML", "uniaxial anisotropic PML (legacy)"]
BLOCH_UNITS = Literal["bandstructure", "SI"]
DEFINE_MESH_BY = Literal["mesh cells per wavelength", "maximum mesh step",
                         "max mesh step and mesh cells per wavelength", "number of mesh cells"]
MESH_REFINEMENT = Literal["staircase", "conformal variant 0", "conformal variant 1", "conformal variant 2",
                          "dielectric volume average", "volume average", "Yu-Mittra method 1", "Yu-Mittra method 2",
                          "precise volume average"]
MESH_TYPE = Literal["auto non-uniform", "custom non-uniform", "uniform"]
MATERIAL_TYPE = Literal["(n,k) Material", "Analytic material", "Chi2", "Chi3 Raman Kerr", "Chi3/Chi2", "Conductive 2D",
                        "Conductive 3D", "Current Driven Gain (version 1.0.0)", "Debye", "Dielectric",
                        "Four-Level Two-Electron (Version 1.0.0)", "Graphene", "Index perturbation", "Kerr nonlinear",
                        "Lorentz", "Magnetic Electric Lorentz (Version 1.0.0)", "PEC", "Paramagnetic", "Plasma",
                        "Sampled 2D data", "Sampled 3D data", "Sellmeier", "<Object defined dielectric>"]
ANISOTROPY = Literal["None", "Diagonal"]
MATERIAL_LENGTH_UNITS = Literal["m", "cm", "mm", "microns", "nm"]
MATERIAL_FREQUENCY_UNITS = Literal["Hz", "KHz", "MHz", "GHz", "THz", "inverse cm"]
SAMPLE_SPACINGS = Literal["uniform", "chebyshev", "custom"]
SIMULATION_TYPE = Literal["all", "3D", "2D z-normal"]
SPATIAL_INTERPOLATIONS = Literal["specified position", "nearest mesh cell", "none"]
APODIZATIONS = Literal["None", "Full", "Start", "End"]
MONITOR_TYPES_ALL = Literal["point", "linear x", "linear y", "linear z",
                            "2d x-normal", "2d y-normal", "2d z-normal", "3d"]
MONITOR_TYPES_3D = Literal["2d x-normal", "2d y-normal", "2d z-normal", "3d"]
MONITOR_TYPES_2D = Literal["2D x-normal", "2d y-normal", "2d z-normal"]
PULSE_TYPES = Literal["standard", "broadband"]
BEAM_PARAMETERS = Literal["Waist size and position", "Beam size and divergence angle"]
DIRECTION_DEFINITIONS = Literal["axis", "unit-vector", "k-vector"]
POLARIZATION_DEFINITIONS = Literal["angle", "S", "P"]
INJECTION_AXES = Literal["x-axis", "y-axis", "z-axis"]
DIRECTIONS = Literal["forward", "backward"]
PLANE_WAVE_TYPES = Literal["Bloch/periodic", "BFAST", "Diffracting"]
WAVE_SHAPES = Literal["Plane wave", "Gaussian", "Cauchy-Lorentzian"]
CONVERSIONS = Literal["center frequency", "maximum frequency", "minimum frequency",
                      "center wavelength", "maximum wavelength", "minimum wavelength"]
DEFINE_BY = Literal["wavelength", "frequency"]
EXTRACTION_TYPES = Literal["3d geometry model", "2d geometry model", "full index model"]

