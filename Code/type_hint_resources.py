# Standard library imports
from typing import Union, Literal, TypedDict, Optional

# Literals for axes and units for length, time, and frequency
AXES = Literal["x", "y", "z"]
LENGTH_UNITS = Literal["m", "mm", "um", "nm", "pm", "angstrom", "fm"]
TIME_UNITS = Literal["s", "ms", "us", "ns", "ps", "fs"]
FREQUENCY_UNITS = Literal["Hz", "KHz", "MHz", "GHz", "THz", "PHz"]

# Literal for parameter types in the overriden getter and setter functions for the simulation
PARAMETER_TYPES = Literal["float", "int", "str", "bool", "list"]

# Literal for selectable materials
MATERIALS = Literal[
        "Au (Gold) - Ciesielski", "PZT (Lead zirconate titanate) - Sintef",
        "Al2O3 - Palik", "SiO2 (Glass) - Palik", "YST (Yttria-stabilized zirconia)- Sintef",
        "TiO2 (Titanium Dioxide) - Sintef",
        "Ta (Tantalum) - CRC", "Ge (Germanium) - Palik", "etch", "InAs - Palik",
        "Cr (Chromium) - CRC", "Ni (Nickel) - CRC", "TiN - Palik", "In (Indium) - Palik",
        "Ni (Nickel) - Palik", "Cr (Chromium) - Palik", "Au (Gold) - Palik",
        "Ge (Germanium) - CRC", "PEC (Perfect Electrical Conductor)", "W (Tungsten) - CRC",
        "InP - Palik", "Ag (Silver) - Palik(0 - 2um)", "Ag (Silver) - Palik",
        "Pt (Platinum) - Palik", "Au (Gold) - CRC", "Cu (Copper) - Palik",
        "W (Tungsten) - Palik", "Ti (Titanium) - CRC", "Cu (Copper) - CRC",
        "Ag (Silver) - Johnson and Christy", "GaAs - Palik", "Fe (Iron) - Palik",
        "Ag (Silver) - Palik(1 - 10um)", "Al (Aluminium) - CRC", "Rh (Rhodium) - Palik",
        "Sn (Tin) - Palik", "Au (Gold) - Johnson and Christy", "Pd (Palladium) - Palik",
        "V (Vanadium) - CRC", "Ag (Silver) - CRC", "Si (Silicon) - Palik",
        "Al (Aluminium) - Palik", "Fe (Iron) - CRC", "Ti (Titanium) - Palik",
        "H2O (Water) - Palik", "PZT on Pt electrode (Lead zirconate titanate on Platinum electrode) - Sintef",
        "<Object defined dielectric>"
    ]


class PositionalKwargs(TypedDict, total=False):
    x: float
    y: float
    z: float
    x_span: float
    y_span: float
    z_span: float
